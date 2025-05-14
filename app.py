import streamlit as st
import pandas as pd
from datetime import datetime
import xlsxwriter
import io
import re

# ---------- CHECK FUNCTIONS ----------

def check_range(val, low, high):
    if pd.isna(val): return 'NA'
    if val < low: return 'Low Chlorine'
    if val > high: return 'High Chlorine'
    return 'Pass'

def check_chlorine_range(row):
    return check_range(row.get('Free Chlorine Reading'), 3, 8)

def check_cya_range(row):
    val = row.get('Cyanuric Acid Reading')
    items = str(row.get('Items Used', '')).lower()
    if pd.isna(val): return 'NA'
    if val < 40:
        return 'Low and Adjusted' if 'stabilizer' in items else 'Fail'
    elif val > 80:
        return 'High CYA'
    else:
        return 'Pass'

def check_phosphate_range(row):
    val = row.get('Phosphorus Reading')
    items = str(row.get('Items Used', '')).lower()
    if pd.isna(val): return 'NA'
    if any(k in items for k in ['phosphate', 'phosfree', 'pool perfect']):
        return 'Pass'
    return 'Fail' if val >= 600 else 'Pass'

def check_color_condition(row):
    cond = row.get('Water Condition Reading')
    color = row.get('Water Color Reading')
    if pd.isna(cond) or pd.isna(color): return 'NA'
    issues = []
    if cond != 'Crystal Clear': issues.append(cond)
    if color != 'Blue': issues.append(color)
    return f"Fail - {', '.join(issues)}" if issues else 'Pass'

def check_filter_pressure(row):
    val = row.get('Filter Pressure')
    if pd.isna(val): return 'NA'
    if val == 0: return 'Fail'
    if val < 5: return 'Low Pressure'
    if val > 22: return 'High Pressure'
    return 'Pass'

def check_system_primed(row):
    value = str(row.get('System Primed and Running', '')).strip().lower()
    return 'Fail' if value == 'no' else 'Pass'

def check_followup(row):
    status = row.get('Service Status')
    return 'Pass' if status == 'Complete' else 'Fail' if pd.notna(status) else 'NA'

def check_items_inventory(row):
    notes = f"{row.get('Private Notes', '')}{row.get('Customer Notes', '')}".lower()
    used = str(row.get('Items Used', '')).lower()
    keywords = ['install', 'leave', 'using', 'sell', 'complete']
    if 'chem' in used:
        return 'Pass'
    if any(k in notes for k in keywords) and not any(k in used for k in keywords):
        return 'Fail'
    return 'Pass' if notes.strip() else 'NA'

def check_note_followup(row):
    notes = f"{row.get('Private Notes', '')} {row.get('Customer Notes', '')}".lower()
    followup_keywords = ['follow up', 'schedule', 'quote', 'return', 'next visit', 'need to come back']
    exclusion_phrases = ['have a good', 'see you next year', 'closed for the season']
    if any(phrase in notes for phrase in exclusion_phrases):
        return 'Pass'
    return 'Fail' if any(k in notes for k in followup_keywords) else 'Pass' if notes.strip() else 'NA'

def check_add_notes_next_visit(row):
    value = row.get('Add Notes for Next Visit', False)
    if value is True or str(value).strip().lower() == 'true' or value == 1:
        return 'Fail'
    return ''

def check_quote_needed(row):
    value = row.get('Quote needed?', False)
    if value is True or str(value).strip().lower() == 'true' or value == 1:
        return 'Fail'
    return ''

def check_chlorine_added(row):
    val = row.get('Free Chlorine Reading')
    items = str(row.get('Items Used', '')).lower()
    if pd.isna(val): return 'NA'
    if val < 3:
        return 'Pass' if 'shock' in items else 'Fail'
    return 'Pass'

def assign_manager(row):
    tech = str(row.get('Tech 1 First Name', '')).strip()
    quentin_team = {'Nate', 'David', 'Luke', 'Quentin'}
    alex_team = {'Noah', 'Garrett', 'Alex', 'Avery'}
    if tech in quentin_team: return 'Quentin'
    elif tech in alex_team: return 'Alex'
    return 'Z - Other'

def check_water_sample(row):
    return 'Sample to Test' if pd.notna(row.get('Water Samples')) and str(row.get('Water Samples')).strip() != '' else ''

def spelling_rank(row):
    note = str(row.get('Customer Notes', '')).strip()
    if not note:
        return 3
    words = note.split()
    issues = sum(1 for word in words if re.search(r'[^a-zA-Z0-9.,?!\'\"()\-\s]', word))
    if issues > 4 or len(words) < 3:
        return 1
    elif issues > 1:
        return 2
    return 3

criteria_columns = [
    'Chlorine Range', 'CYA Range', 'Phosphate Range Untreated', 'Color And Condition',
    'Filter Pressure', 'System Primed', 'Followup', 'Items added to inventory?',
    'Note Followup Criteria', 'Chlorine Added'
]

def compute_action_items(row):
    items = [f"{col}: {row[col]}" for col in criteria_columns if row[col] == 'Fail']
    if row.get('Water Sample') == 'Sample to Test':
        items.append('Water Sample: Sample to Test')
    return ', '.join(items)

def calculate_score(row):
    return sum(row[col] == 'Fail' for col in criteria_columns)

def determine_marked_ready(row):
    billing = str(row.get('Billing Status', '')).strip().lower()
    inventory = row.get('Items added to inventory?')
    followup = row.get('Note Followup Criteria')
    if billing == 'not billed': return ''
    if billing == 'ready' and (inventory == 'Fail' or followup == 'Fail'):
        return 'Yes'
    if billing == 'ready': return 'Ready'
    return ''

# ---------- STREAMLIT APP ----------

st.set_page_config(layout="wide")
st.title("Pool Service Report Analyzer")

uploaded_file = st.file_uploader("Upload your service CSV file", type=["csv"])

if uploaded_file:
    df = pd.read_csv(uploaded_file)

    excluded = [
        'note', 'admin-end of day checklist', 'admin-load sheets',
        'admin-office task', 'admin-warehouse work - technicians'
    ]
    df_filtered = df[~df['Service Type'].str.strip().str.lower().isin(excluded)].copy()

    df_filtered['Manager'] = df_filtered.apply(assign_manager, axis=1)
    df_filtered['Manager - Tech - Duration'] = df_filtered['Manager'] + ' - ' + df_filtered['Tech 1 First Name'] + ' - ' + df_filtered['Duration'].astype(str)

    df_filtered['Chlorine Range'] = df_filtered.apply(check_chlorine_range, axis=1)
    df_filtered['CYA Range'] = df_filtered.apply(check_cya_range, axis=1)
    df_filtered['Phosphate Range Untreated'] = df_filtered.apply(check_phosphate_range, axis=1)
    df_filtered['Color And Condition'] = df_filtered.apply(check_color_condition, axis=1)
    df_filtered['Filter Pressure'] = df_filtered.apply(check_filter_pressure, axis=1)
    df_filtered['System Primed'] = df_filtered.apply(check_system_primed, axis=1)
    df_filtered['Followup'] = df_filtered.apply(check_followup, axis=1)
    df_filtered['Items added to inventory?'] = df_filtered.apply(check_items_inventory, axis=1)
    df_filtered['Note Followup Criteria'] = df_filtered.apply(check_note_followup, axis=1)
    df_filtered['Add Notes for Next Visit'] = df_filtered.apply(check_add_notes_next_visit, axis=1)
    df_filtered['Quote needed?'] = df_filtered.apply(check_quote_needed, axis=1)
    df_filtered['Chlorine Added'] = df_filtered.apply(check_chlorine_added, axis=1)
    df_filtered['Water Sample'] = df_filtered.apply(check_water_sample, axis=1)
    df_filtered['Spelling Rank (1-3)'] = df_filtered.apply(spelling_rank, axis=1)
    df_filtered['Marked Ready'] = df_filtered.apply(determine_marked_ready, axis=1)
    df_filtered['Action Items'] = df_filtered.apply(compute_action_items, axis=1)
    df_filtered['Score'] = df_filtered.apply(calculate_score, axis=1)

    output_columns = [
        'Customer Name', 'Service Type', 'Manager - Tech - Duration', 'Score', 'Marked Ready',
        'Action Items', 'Add Notes for Next Visit', 'Quote needed?', 'Spelling Rank (1-3)', 'Water Sample',
        'Chlorine Range', 'Chlorine Added', 'CYA Range', 'Phosphate Range Untreated',
        'Color And Condition', 'Filter Pressure', 'System Primed', 'Followup',
        'Items added to inventory?', 'Note Followup Criteria', 'Manager'
    ]

    df_output = df_filtered[output_columns].sort_values(by=['Manager', 'Score'], ascending=[True, False])

    st.success("\u2705 Analysis complete.")
    st.dataframe(df_output, use_container_width=True)

    # Create Excel file in memory
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_output.to_excel(writer, sheet_name='Analysis Results', index=False)
        df.to_excel(writer, sheet_name='Original Data', index=False)

    st.download_button(
        label="\ud83d\udcc5 Download Excel Report",
        data=output.getvalue(),
        file_name=f'Service_Report_Analysis_{datetime.today().strftime("%m-%d")}_Final.xlsx',
        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
