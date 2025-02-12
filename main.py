import boto3
import streamlit as st
import altair as alt
import pandas as pd
from util_functions import *
import re
from decimal import Decimal

# Streamlit Configuration
st.set_page_config(
    page_title="Costo/CNC",
    page_icon="📉",
    layout="wide",
    initial_sidebar_state="expanded"
)
alt.themes.enable("dark")

# Custom CSS for no data message
st.markdown("""
    <style>
        .no-data-message {
            text-align: center;
            padding: 40px;
            background: #1E1E1E;
            border-radius: 10px;
            margin: 20px 0;
        }
        .no-data-message h2 {
            color: #666;
            font-size: 24px;
            margin-bottom: 10px;
        }
        .no-data-message p {
            color: #999;
            font-size: 16px;
        }
        .info-icon {
            font-size: 48px;
            color: #666;
            margin-bottom: 20px;
        }
    </style>
""", unsafe_allow_html=True)

# DynamoDB Setup and Data Retrieval
try:
    dynamo = boto3.resource('dynamodb', region_name='us-east-1')
    table = dynamo.Table("sam-stack-irlaa-MecanizadoCloseTable-1IKYW80FKFRII")
    
    items = []
    response = table.scan()
    items.extend(response['Items'])
    
    while 'LastEvaluatedKey' in response:
        response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        items.extend(response['Items'])
        
    st.sidebar.success(f"Retrieved {len(items)} records from DynamoDB")
except Exception as e:
    st.error(f"Error connecting to DynamoDB: {str(e)}")
    items = []

# Get months and years
months, years, cm, cy = get_months_and_years_since("01/08/2024")

# Sidebar Configuration
with st.sidebar:
    st.sidebar.image("data/logo.png", use_container_width=True)
    st.title("📅 Nave1/CNC Costos")
    
    if cm == 1:
        default_month_index = months.index(cm)
    else:
        default_month_index = months.index(cm) - 1

    default_years_index = years.index(cy)

    selected_month = st.sidebar.selectbox('Seleccione Mes', months, index=default_month_index)
    selected_year = st.sidebar.selectbox('Seleccione Año', years, index=default_years_index)
    costos_mes = st.sidebar.number_input('Introduzca Gasto/Mes', value=15000000, min_value=0)
    costos_mm = st.sidebar.number_input('Introduzca Costo/mm', value=160, min_value=0)

    espesor_input = st.text_area(
        'Introduzca espesor limites (comma-separado, e.g., "15, 20, 30")',
        value="12, 32"
    ).strip()

    try:
        espesor_list = [int(x.strip()) for x in espesor_input.split(',')]
    except ValueError:
        st.error("Introduzca un numero entero, separado por comas.")
        espesor_list = []

def show_no_data_message(title, month, year):
    st.markdown(f"""
        <div class="no-data-message">
            <div class="info-icon">ℹ️</div>
            <h2>No hay datos disponibles para {title}</h2>
            <p>No se encontraron registros para el mes {month} del año {year}.</p>
            <p>Por favor, seleccione un período diferente o verifique que existan datos para este período.</p>
        </div>
    """, unsafe_allow_html=True)

# Aggregation Configuration
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

def render_section(title, aggregated_df, espesor_list, pr, costos_mes):
    with st.expander(title):
        if aggregated_df.empty:
            show_no_data_message(title, selected_month, selected_year)
            return

        try:
            avg_espesor = round(float(weighted_average_espesor(aggregated_df)), 2)
            result = group_by_espesor(aggregated_df, espesor_list)
            perforaciones = float(sum(aggregated_df['perforaTotal']))
            
            if perforaciones > 0:
                result['Costo mm'] = round(((result['perforaTotal'] / perforaciones) * costos_mes) / (result['mm_total']), 2)
                result['Costo mm'] = result['Costo mm'].fillna(0)

                mm_total = round(float(result['mm_total'].sum()), 2)
                costo_mm = round(costos_mes * (pr / mm_total), 2) if mm_total > 0 else 0
                mm_margin = costos_mm - costo_mm

                # CSS styling
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
                    </style>
                """, unsafe_allow_html=True)

                # Display metrics
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
                        {int(perforaciones)}
                    </div>
                    """, unsafe_allow_html=True)

                # Display results table
                with st.container():
                    # Drop unnecessary columns before displaying
                    display_result = result.copy()
                    if 'perforaTotal' in display_result.columns:
                        display_result = display_result.drop(columns=['perforaTotal'])
                    if 'placas' in display_result.columns:
                        display_result = display_result.drop(columns=['placas'])
                    if 'Tiempo Proceso (min)' in display_result.columns:
                        display_result = display_result.drop(columns=['Tiempo Proceso (min)'])
                    
                    st.subheader("Espesores")
                    st.dataframe(display_result.reset_index(drop=True), use_container_width=True)

            else:
                show_no_data_message(title, selected_month, selected_year)
                
        except Exception as e:
            st.error(f"Error processing data for {title}: {str(e)}")
            st.error("Full error details:")
            st.exception(e)


# In the main processing section, after filtering:
try:
    df = create_dataframe_from_items(items)
    st.sidebar.info(f"Total records: {len(df)}")

    # Filter data
    filtered_df_sabimet = filter_by_year_month(df, selected_year, selected_month, 'sabimet')
    filtered_df_steelk = filter_by_year_month(df, selected_year, selected_month, 'steelk')

    st.sidebar.info(f"Sabimet records: {len(filtered_df_sabimet)}")
    st.sidebar.info(f"Steelk records: {len(filtered_df_steelk)}")

    # Check if we have data before proceeding
    if filtered_df_sabimet.empty and filtered_df_steelk.empty:
        st.markdown("""
            <div class="no-data-message">
                <div class="info-icon">📊</div>
                <h2>No hay datos disponibles</h2>
                <p>No se encontraron registros para ninguna de las categorías en el período seleccionado.</p>
                <p>Por favor, seleccione un período diferente o verifique la disponibilidad de datos.</p>
            </div>
        """, unsafe_allow_html=True)
    else:
        # Process Sabimet data if available
        if not filtered_df_sabimet.empty:
            aggregated_df_sabimet = filter_drop_duplicates_groupby_and_aggregate(
                filtered_df_sabimet,
                'origen',
                'Progreso',
                agg_dict
            )
            st.sidebar.info(f"Aggregated Sabimet records: {len(aggregated_df_sabimet)}")
            
            # Convert decimal types
            columns_to_convert = ['placas', 'cantidadPerforacionesPlacas', 'espesor']
            for col in columns_to_convert:
                if col in aggregated_df_sabimet.columns:
                    aggregated_df_sabimet[col] = aggregated_df_sabimet[col].apply(
                        lambda x: float(x) if isinstance(x, Decimal) else x
                    )
        else:
            aggregated_df_sabimet = pd.DataFrame()

        # Process Steelk data if available
        if not filtered_df_steelk.empty:
            aggregated_df_sttelk = filter_drop_duplicates_groupby_and_aggregate(
                filtered_df_steelk,
                'origen',
                'Progreso',
                agg_dict
            )
            st.sidebar.info(f"Aggregated Steelk records: {len(aggregated_df_sttelk)}")
        else:
            aggregated_df_sttelk = pd.DataFrame()

        # Calculate proportions only if we have data
        per_sabimet = sum(aggregated_df_sabimet['perforaTotal']) if not aggregated_df_sabimet.empty else 0
        per_stellk = sum(aggregated_df_sttelk['perforaTotal']) if not aggregated_df_sttelk.empty else 0

        st.sidebar.info(f"Sabimet perforaciones: {per_sabimet}")
        st.sidebar.info(f"Steelk perforaciones: {per_stellk}")

        total_per = per_sabimet + per_stellk
        if total_per > 0:
            pr_sabimet = per_sabimet / total_per
            pr_stellk = per_stellk / total_per
        else:
            pr_sabimet = pr_stellk = 0

        # Render sections
        render_section("Sabimet", aggregated_df_sabimet, espesor_list, pr_sabimet, costos_mes)
        st.markdown('---')
        render_section("Steelk", aggregated_df_sttelk, espesor_list, pr_stellk, costos_mes)

except Exception as e:
    st.error(f"Error in main data processing: {str(e)}")
    st.exception(e)
