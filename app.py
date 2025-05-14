import streamlit as st
import pandas as pd
from datetime import datetime
import re

# ---------- DEFINE CHECK FUNCTIONS (same as your original) ----------
# Copy all your check functions here exactly as-is
# e.g., check_range, check_chlorine_range, etc.

# ---------- STREAMLIT APP ----------
st.set_page_config(layout="wide")
st.title("Pool Service Report Analyzer")

uploaded_file = st.file_uploader("Upload your service CSV file", type=['csv'])

if uploaded_file:
    df = pd.read_csv(uploaded_file)

    excluded = [
        'note', 'admin-end of day checklist', 'admin-load sheets',
        'admin-office task', 'admin-warehouse work - technicians'
    ]
    df_filtered = df[~df['Service Type'].str.strip().str.lower().isin(excluded)].copy()

    # Add new calculated columns
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

    st.success("Analysis Complete!")
    st.dataframe(df_output, use_container_width=True)

    # Download link
    csv = df_output.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Download analyzed report as CSV",
        data=csv,
        file_name=f'Service_Report_Analysis_{datetime.today().strftime("%m-%d")}_Final.csv',
        mime='text/csv'
    )
