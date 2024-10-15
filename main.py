import boto3
import streamlit as st
import altair as alt
import pandas as pd
from util_functions import *
import re
from decimal import Decimal

# Initialize DynamoDB resource
dynamo = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamo.Table('MECANIZADO_CLOSE2-dev')

# Scan the DynamoDB table and retrieve all items
response = table.scan()
items = response['Items']

while 'LastEvaluatedKey' in response:
    response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
    items.extend(response['Items'])

# Get months and years since a particular date
months, years, cm, cy = get_months_and_years_since("01/08/2024")

# Streamlit configuration for the web app
st.set_page_config(
    page_title="Kupfer Nave1/CNC Dashboard",
    page_icon="📉",
    layout="wide",
    initial_sidebar_state="expanded"
)
alt.themes.enable("dark")

# Sidebar setup in Streamlit
with st.sidebar:
    st.sidebar.image("data/logo.png", use_column_width=True)
    st.title("📅 Nave1/Cnc Dashboard")
    default_month_index = months.index(cm) - 1  # Index to control the month
    default_years_index = years.index(cy)
    selected_month = st.sidebar.selectbox('Select a month', months, index=default_month_index)
    selected_year = st.sidebar.selectbox('Select a year', years, index=default_years_index)
    costos_mes = st.sidebar.number_input('Enter valor for Costo/Mes', value=15000000)

    # Input for espesor values
    espesor_input = st.text_area('Enter espesor values (comma-separated, e.g., "15, 20, 30")', value="12, 32, 100")

    # Convert the espesor input to a list of integers
    try:
        espesor_list = [int(x.strip()) for x in espesor_input.split(',')]
    except ValueError:
        st.error("Please enter valid integers separated by commas.")
        espesor_list = []

# Process the data
df = create_dataframe_from_items(items)

filtered_df_sabimet = filter_by_year_month(df, selected_year, selected_month, 'sabimet')
filtered_df_steelk = filter_by_year_month(df, selected_year, selected_month, 'steelk')

# Define aggregation dictionary
agg_dict = {
    'cantidadPerforacionesTotal': 'sum',
    'cantidadPerforacionesPlacas': 'sum',
    'perforaTotal': 'sum',
    'kg': 'mean',
    'placas': 'sum',
    'tiempo': 'mean',
    'tiempo_seteo': 'mean',
    'Tiempo Proceso (min)': 'sum'
}

# Aggregate the filtered data
aggregated_df_sabimet = filter_drop_duplicates_groupby_and_aggregate(
    filtered_df_sabimet,
    'origen',
    'Progreso',
    agg_dict
)


aggregated_df_sttelk = filter_drop_duplicates_groupby_and_aggregate(
    filtered_df_steelk,
    'origen',
    'Progreso',
    agg_dict
)



per_sabimet = sum(aggregated_df_sabimet['perforaTotal'])
per_stellk = sum(aggregated_df_sttelk['perforaTotal'])

pr_sabimet = per_sabimet/(per_sabimet+per_stellk )
pr_stellk  = per_stellk/(per_sabimet+per_stellk )


# --- Savimet Section ---
st.header("Sabimet")

# Compute metrics
avg_espesor_sabimet  = round(float(weighted_average_espesor(aggregated_df_sabimet )), 2)
result_sabimet  = group_by_espesor(aggregated_df_sabimet , espesor_list)  # Use the espesor list from UI
mm_total_sabimet  = round(float(result_sabimet['mm_total'].sum()), 2)
costo_mm_sabimet  = round(costos_mes*(pr_sabimet/mm_total_sabimet), 2)

# Display aggregated results in cards with colors
col1, col2, col3 = st.columns(3)
with col1:
    st.metric(label="Average Espesor", value=float(avg_espesor_sabimet), delta_color="off", delta=None)
with col2:
    st.metric(label="MM Total", value=float(mm_total_sabimet), delta_color="off", delta=None)
with col3:
    st.metric(label="Costo/mm", value=float(costo_mm_sabimet), delta_color="off", delta=None)
    st.metric(label="Perforaciones", value=float(sum(aggregated_df_sabimet['perforaTotal'])),
              delta_color="off", delta=None)

# Display the DataFrame
st.subheader("Costo por Espesor")
df_cost_sabimet = pd.DataFrame({
    'espesor': espesor_list,
    'Costo': [round(value * costo_mm_sabimet) for value in espesor_list]
})
st.dataframe(df_cost_sabimet)
st.markdown('---')
# --- Steelk Section ---
st.header("Steelk")

# Compute metrics
avg_espesor_sttelk = round(float(weighted_average_espesor(aggregated_df_sttelk)), 2)
result_sttelk = group_by_espesor(aggregated_df_sttelk, espesor_list)  # Use the espesor list from UI
mm_total_sttelk = round(float(result_sttelk['mm_total'].sum()), 2)
costo_mm_sttelk = round(costos_mes*(pr_stellk/mm_total_sttelk), 2)

# Display aggregated results in cards with colors
col1, col2, col3 = st.columns(3)
with col1:
    st.metric(label="Average Espesor", value=float(avg_espesor_sttelk), delta_color="off", delta=None)
with col2:
    st.metric(label="MM Total", value=float(mm_total_sttelk), delta_color="off", delta=None)
with col3:
    st.metric(label="Costo/mm", value=float(costo_mm_sttelk), delta_color="off", delta=None)
    st.metric(label="Perforaciones", value=float(sum(aggregated_df_sttelk['perforaTotal'])),
              delta_color="off", delta=None)

# Display the DataFrame
st.subheader("Costo por Espesor")
df_cost_sttelk = pd.DataFrame({
    'espesor': espesor_list,
    'Costo': [round(value * costo_mm_sttelk ) for value in espesor_list]
})
st.dataframe(df_cost_sttelk)

# --- Additional UI enhancements ---
st.markdown('---')
st.subheader("Raw Data (Savimet)")
# st.dataframe(aggregated_df_sabimet)

st.subheader("Espesores")
st.dataframe(result_sabimet)

st.markdown('---')
st.subheader("Raw Data (Steelk)")
# st.dataframe(aggregated_df_sttelk)
st.subheader("Espesores")
st.dataframe(result_sttelk)