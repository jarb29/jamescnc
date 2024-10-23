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
    st.title("📅 Nave1/CNC Dashboard")
    default_month_index = months.index(cm) - 1  # Index to control the month
    default_years_index = years.index(cy)
    selected_month = st.sidebar.selectbox('Selecciones Mes', months, index=default_month_index)
    selected_year = st.sidebar.selectbox('Selecciones Año', years, index=default_years_index)
    costos_mes = st.sidebar.number_input('Introduzca Gasto/Mes', value=15000000, min_value=0)
    costos_mm = st.sidebar.number_input('Introduzca Costo/mm', value=160, min_value=0)

    # Input for espesor values
    espesor_input = st.text_area(
        'Introduzca espesor limites (comma-separated, e.g., "15, 20, 30")',
        value="12, 32"
    ).strip()

    # Convert the espesor input to a list of integers and handle errors
    try:
        espesor_list = [int(x.strip()) for x in espesor_input.split(',')]
    except ValueError:
        st.error("Introduzca un numero entero, separado por comas.")
        espesor_list = []

# Process the data
df = create_dataframe_from_items(items)

# Filter by sabimet and steelk
filtered_df_sabimet = filter_by_year_month(df, selected_year, selected_month, 'sabimet')
filtered_df_steelk = filter_by_year_month(df, selected_year, selected_month, 'steelk')
# st.subheader("filtered_df_sabimet")

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
# st.subheader("aggregated_df_sabimet")
columns_to_convert = ['placas', 'cantidadPerforacionesPlacas', 'espesor']
for col in columns_to_convert:
    aggregated_df_sabimet[col] = aggregated_df_sabimet[col].apply(lambda x: float(x) if isinstance(x, Decimal) else x)


aggregated_df_sttelk = filter_drop_duplicates_groupby_and_aggregate(
    filtered_df_steelk,
    'origen',
    'Progreso',
    agg_dict
)

per_sabimet = sum(aggregated_df_sabimet['perforaTotal'])
per_stellk = sum(aggregated_df_sttelk['perforaTotal'])

pr_sabimet = per_sabimet / (per_sabimet + per_stellk)
pr_stellk = per_stellk / (per_sabimet + per_stellk)





# Function to render data for each section
def render_section(title, aggregated_df, espesor_list, pr, costos_mes):
    with st.expander(title):
        avg_espesor = round(float(weighted_average_espesor(aggregated_df)), 2)
        result = group_by_espesor(aggregated_df, espesor_list)  # Use the espesor list from UI
        perforaciones = float(sum(aggregated_df['perforaTotal']))
        result['Costo mm'] = round(((result['perforaTotal'] / perforaciones) * costos_mes) / (result['mm_total']),2)
        result['Costo mm'] = result['Costo mm'].fillna(0)  # Replace NaN values with 0

        mm_total = round(float(result['mm_total'].sum()), 2)
        costo_mm = round(costos_mes * (pr / mm_total), 2)

        mm_margin = costos_mm - costo_mm

        # CSS for cards with stronger colors
        st.markdown("""
            <style>
                .card {
                    border-radius: 10px;
                    padding: 20px;
                    text-align: center;
                    font-size: 24px;
                    font-weight: bold;
                    color: #ffffff;
                    margin-bottom: 20px;
                    border: 1px solid transparent;
                }
                .card-header {
                    font-size: 16px;
                    font-weight: normal;
                    color: rgba(255, 255, 255, 0.7);
                }
                .blue { background-color: #007bff; }
                .teal { background-color: #20c997; }
                .purple { background-color: #6f42c1; }
                .red { background-color: #dc3545; }
                .center-me { margin: 0 auto; }
                .styled-table {
                    border-collapse: collapse;
                    margin: 25px 0;
                    font-size: 18px;
                    text-align: left;
                    width: 100%;
                }
                .styled-table thead tr {
                    background-color: #009879;
                    color: #ffffff;
                }
                .styled-table th, .styled-table td {
                    padding: 12px 15px;
                    border: 1px solid #ddd;
                }
                .styled-table tbody tr:nth-of-type(even) {
                    background-color: #f3f3f3;
                }
                .styled-table tbody tr:nth-of-type(odd) {
                    background-color: #ffffff;
                }
                .styled-table tbody tr:hover {
                    background-color: #f1f1f1;
                }
                .styled-table tbody td {
                    color: #333333;
                    font-weight: normal;
                }
                .styled-table tfoot tr {
                    background-color: #009879;
                    color: #ffffff;
                    font-weight: bold;
                }
            </style>
        """, unsafe_allow_html=True)

        # Display aggregated results in metric cards
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.markdown(f"""
            <div class="card blue center-me">
                <div class="card-header">Espesor Promedio</div>
                {float(avg_espesor)}
            </div>
            """, unsafe_allow_html=True)

        with col2:
            st.markdown(f"""
            <div class="card teal center-me">
                <div class="card-header">MM Total</div>
                {float(mm_total)}
            </div>
            """, unsafe_allow_html=True)

        with col3:
            st.markdown(f"""
            <div class="card purple center-me">
                <div class="card-header">Costo Global/mm</div>
                {float(costo_mm)}
                <div style="font-size:12px; text-align:left;">Diferencia: 
                    {round(float(mm_margin), 2)}$ a
                    {costos_mm}$
                </div>
            </div>
            """, unsafe_allow_html=True)

        with col4:
            st.markdown(f"""
            <div class="card red center-me">
                <div class="card-header">Perforaciones</div>
                {perforaciones}
            </div>
            """, unsafe_allow_html=True)

        # Use container for remaining data
        with st.container():
            result = result.drop(columns=['perforaTotal', 'placas', 'Tiempo Proceso (min)'])

            col1 = st.columns(1)[0]  # Fixed single column selection

            with col1:
                st.subheader("Espesores")
                st.dataframe(result.reset_index(drop=True), use_container_width=True)



# Example call to render_section (You will need your data to run this code)
render_section("Sabimet", aggregated_df_sabimet, espesor_list, pr_sabimet, costos_mes)
st.markdown('---')
render_section("Steelk", aggregated_df_sttelk, espesor_list, pr_stellk, costos_mes)