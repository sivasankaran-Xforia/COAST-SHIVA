import pandas as pd
import plotly.express as px
import numpy as np

def get_individual_chart_data(file_path: str):
    df = pd.read_excel(file_path)
    charts_data = []

    def create_and_append(fig):
        safe_fig = fig.to_plotly_json()

        # force all ndarrays inside the fig into lists
        def ensure_lists(obj):
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            if isinstance(obj, dict):
                return {k: ensure_lists(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [ensure_lists(v) for v in obj]
            return obj

        charts_data.append(ensure_lists(safe_fig))

    # 1. Patients by Condition
    if "Condition" in df.columns:
        condition_counts = df['Condition'].value_counts().reset_index()
        # KEY CHANGE: Pass columns as lists directly to the px.bar function
        fig_cond = px.bar(
            x=condition_counts['Condition'].tolist(), 
            y=condition_counts['count'].tolist(), 
            title='Patients by Condition',
            labels={'x': 'Condition', 'y': 'Number of Patients'}
        )
        create_and_append(fig_cond)

    # 2. Patients per Nurse
    if "Nurse Name" in df.columns:
        nurse_counts = df['Nurse Name'].value_counts().reset_index()
        # KEY CHANGE: Pass columns as lists
        fig_nurse = px.bar(
            x=nurse_counts['Nurse Name'].tolist(), 
            y=nurse_counts['count'].tolist(), 
            title='Patients per Nurse',
            labels={'x': 'Nurse', 'y': 'Number of Patients'}
        )
        create_and_append(fig_nurse)

    # 3. Average Progress Score per Therapy Type
    if "Therapy Type" in df.columns and "Progress Score" in df.columns:
        avg_progress = df.groupby('Therapy Type')['Progress Score'].mean().reset_index()
        # KEY CHANGE: Pass columns as lists
        fig_progress = px.bar(
            x=avg_progress['Therapy Type'].tolist(), 
            y=avg_progress['Progress Score'].tolist(),
            title='Average Progress Score per Therapy Type',
            labels={'x': 'Therapy Type', 'y': 'Average Progress Score'}
        )
        create_and_append(fig_progress)
        fig_box = px.box(
            df, 
            x='Therapy Type', 
            y='Progress Score',
            title='Progress Score Distribution by Therapy Type',
            labels={'x': 'Therapy Type', 'y': 'Progress Score'}
        )
        create_and_append(fig_box)

    # Add other charts
    if "Gender" in df.columns:
        # This chart works correctly without changes because it handles the data differently
        create_and_append(px.pie(df, names='Gender', title='Gender Distribution'))
    if "Recovery Status" in df.columns:
        create_and_append(px.pie(df, names='Recovery Status', title='Recovery Status'))
    
    return charts_data

'''
import pandas as pd
import plotly.express as px
from fastapi.responses import HTMLResponse

"""
front end implementation: 
<iframe id="reportFrame" src="/dashboard/?file_path=uploads/patients.xlsx" 
        width="100%" height="1200px"></iframe>
"""

def generate_dashboard(file_path: str):
    df = pd.read_excel(file_path)
    
    # Ensure Date columns are datetime
    if "Date of Join" in df.columns:
        df['Date of Join'] = pd.to_datetime(df['Date of Join'])

    # Start building figures
    figs = []

    # 1. Patients by Condition (interactive filter)
    if "Condition" in df.columns:
        fig_cond = px.bar(df, x='Condition', title='Patients by Condition')
        # Add dropdown filter for Therapy Type
        if "Therapy Type" in df.columns:
            buttons = []
            therapy_types = df['Therapy Type'].unique()
            for therapy in therapy_types:
                filtered_df = df[df['Therapy Type'] == therapy]
                buttons.append(dict(
                    method='update',
                    label=therapy,
                    args=[{'x': [filtered_df['Condition']],
                           'y': [filtered_df['Condition'].value_counts()]},
                          {'title': f'Patients by Condition - {therapy}'}]
                ))
            buttons.append(dict(
                method='update',
                label='All',
                args=[{'x': [df['Condition']], 'y': [df['Condition'].value_counts()]},
                      {'title': 'Patients by Condition - All'}]
            ))
            fig_cond.update_layout(
                updatemenus=[dict(active=0, buttons=buttons, x=1.15, y=0.8)]
            )
        figs.append(fig_cond)

    # 2. Patients per Nurse (dropdown by Condition)
    if "Nurse Name" in df.columns:
        fig_nurse = px.bar(df, x='Nurse Name', title='Patients per Nurse')
        if "Condition" in df.columns:
            buttons = []
            conditions = df['Condition'].unique()
            for cond in conditions:
                filtered_df = df[df['Condition'] == cond]
                buttons.append(dict(
                    method='update',
                    label=cond,
                    args=[{'x': [filtered_df['Nurse Name']],
                           'y': [filtered_df['Nurse Name'].value_counts()]},
                          {'title': f'Patients per Nurse - {cond}'}]
                ))
            buttons.append(dict(
                method='update',
                label='All',
                args=[{'x': [df['Nurse Name']], 'y': [df['Nurse Name'].value_counts()]},
                      {'title': 'Patients per Nurse - All'}]
            ))
            fig_nurse.update_layout(
                updatemenus=[dict(active=0, buttons=buttons, x=1.15, y=0.8)]
            )
        figs.append(fig_nurse)

    # 3. Average Progress Score per Therapy Type (dropdown by Condition)
    if "Therapy Type" in df.columns and "Progress Score" in df.columns:
        fig_progress = px.bar(df.groupby('Therapy Type')['Progress Score'].mean().reset_index(),
                              x='Therapy Type', y='Progress Score',
                              title='Average Progress Score per Therapy Type')
        if "Condition" in df.columns:
            buttons = []
            conditions = df['Condition'].unique()
            for cond in conditions:
                filtered_df = df[df['Condition'] == cond]
                grouped = filtered_df.groupby('Therapy Type')['Progress Score'].mean().reset_index()
                buttons.append(dict(
                    method='update',
                    label=cond,
                    args=[{'x': [grouped['Therapy Type']],
                           'y': [grouped['Progress Score']]},
                          {'title': f'Average Progress Score per Therapy Type - {cond}'}]
                ))
            buttons.append(dict(
                method='update',
                label='All',
                args=[{'x': [df.groupby('Therapy Type')['Progress Score'].mean().reset_index()['Therapy Type']],
                       'y': [df.groupby('Therapy Type')['Progress Score'].mean().reset_index()['Progress Score']]},
                      {'title': 'Average Progress Score per Therapy Type - All'}]
            ))
            fig_progress.update_layout(
                updatemenus=[dict(active=0, buttons=buttons, x=1.15, y=0.8)]
            )
        figs.append(fig_progress)

    # Add other charts (Length of Stay, Gender, Recovery Status, Join Trend, etc.)
    # For brevity, include basic non-filtered charts
    if "Gender" in df.columns:
        figs.append(px.pie(df, names='Gender', title='Gender Distribution'))
    if "Recovery Status" in df.columns:
        figs.append(px.pie(df, names='Recovery Status', title='Recovery Status'))
    if "Length of Stay" in df.columns:
        figs.append(px.histogram(df, x='Length of Stay', nbins=20, title='Length of Stay Distribution'))
    if "Readmission Flag" in df.columns: 
        # Get the value counts and reset the index
        counts_df = df['Readmission Flag'].value_counts().reset_index(name='count')
        # Change the x-axis to use the correct column name
        figs.append(px.bar(counts_df, x='Readmission Flag', y='count', title='Readmission Count'))

    # Combine all figures into HTML
    dashboard_html = ""
    for fig in figs:
        dashboard_html += fig.to_html(full_html=False, include_plotlyjs='cdn')
        dashboard_html += "<hr>"

    return HTMLResponse(dashboard_html)
'''