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
        
    # st.sidebar.success(f"Retrieved {len(items)} records from DynamoDB")
except Exception as e:
    st.error(f"Error connecting to DynamoDB: {str(e)}")
    items = []

# Get months and years
months, years, cm, cy = get_months_and_years_since("01/08/2024")

# Sidebar Configuration
# Custom CSS for sidebar enhancement
st.markdown("""
    <style>
        .sidebar-title {
            background: linear-gradient(90deg, #1e3c72 0%, #2a5298 100%);
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            text-align: center;
        }
        
        .sidebar-section {
            background: rgba(30, 60, 114, 0.1);
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 20px;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .sidebar-header {
            color: #3498db;
            font-size: 1.1em;
            font-weight: bold;
            margin-bottom: 10px;
            border-bottom: 2px solid #3498db;
            padding-bottom: 5px;
        }
        
        .stNumberInput > div > div > input {
            background-color: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 5px;
            color: white;
        }
        
        .stSelectbox > div > div > select {
            background-color: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 5px;
        }
        
        .stTextArea > div > div > textarea {
            background-color: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 5px;
        }
    </style>
""", unsafe_allow_html=True)

# Sidebar Configuration
with st.sidebar:
    # Logo and Title Section
    st.image("data/logo.png", use_container_width=True)
    st.markdown("""
        <div class="sidebar-title">
            <h1 style='color: white; font-size: 24px; margin: 0;'>📅 Nave1/CNC Costos</h1>
        </div>
    """, unsafe_allow_html=True)
    
    # Date Selection Section
    st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    st.markdown('<p class="sidebar-header">📆 Selección de Período</p>', unsafe_allow_html=True)
    
    if cm == 1:
        default_month_index = months.index(cm)
    else:
        default_month_index = months.index(cm) - 1

    default_years_index = years.index(cy)

    col1, col2 = st.columns(2)
    with col1:
        selected_month = st.selectbox(
            'Mes',
            months,
            index=default_month_index,
            help="Seleccione el mes para el análisis"
        )
    with col2:
        selected_year = st.selectbox(
            'Año',
            years,
            index=default_years_index,
            help="Seleccione el año para el análisis"
        )
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Cost Parameters Section
    st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    st.markdown('<p class="sidebar-header">💰 Parámetros de Costos</p>', unsafe_allow_html=True)
    
    costos_mes = st.number_input(
        'Gasto/Mes',
        value=15000000,
        min_value=0,
        help="Introduzca el gasto mensual total"
    )
    
    costos_mm = st.number_input(
        'Costo/mm',
        value=160,
        min_value=0,
        help="Introduzca el costo por milímetro"
    )
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Thickness Configuration Section
    st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    st.markdown('<p class="sidebar-header">📏 Configuración de Espesor</p>', unsafe_allow_html=True)
    
    espesor_input = st.text_area(
        'Límites de Espesor',
        value="12, 32",
        help='Introduzca los límites de espesor separados por comas (ejemplo: "15, 20, 30")'
    ).strip()

    try:
        espesor_list = [int(x.strip()) for x in espesor_input.split(',')]
        st.success(f"Límites configurados: {', '.join(map(str, espesor_list))}")
    except ValueError:
        st.error("⚠️ Por favor, introduzca números enteros separados por comas.")
        espesor_list = []
    st.markdown('</div>', unsafe_allow_html=True)


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
    # Enhanced CSS with modern design and animations
    st.markdown("""
        <style>
            /* Modern Card Design */
            .metric-card {
                background: linear-gradient(135deg, rgba(255,255,255,0.1) 0%, rgba(255,255,255,0.05) 100%);
                backdrop-filter: blur(10px);
                -webkit-backdrop-filter: blur(10px);
                border-radius: 20px;
                padding: 20px;
                margin: 10px;
                border: 1px solid rgba(255,255,255,0.1);
                box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
                transition: all 0.3s ease;
            }
            
            .metric-card:hover {
                transform: translateY(-5px);
                box-shadow: 0 12px 40px 0 rgba(31, 38, 135, 0.45);
            }
            
            .metric-header {
                font-size: 0.9rem;
                text-transform: uppercase;
                letter-spacing: 0.1em;
                color: rgba(255,255,255,0.7);
                margin-bottom: 10px;
            }
            
            .metric-value {
                font-size: 2rem;
                font-weight: bold;
                background: linear-gradient(120deg, #ffffff, #a5a5a5);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                margin: 10px 0;
            }
            
            .metric-footer {
                font-size: 0.8rem;
                color: rgba(255,255,255,0.6);
            }
            
            /* Card Variants */
            .blue-card {
                background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            }
            
            .teal-card {
                background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
            }
            
            .purple-card {
                background: linear-gradient(135deg, #834d9b 0%, #d04ed6 100%);
            }
            
            .red-card {
                background: linear-gradient(135deg, #cb2d3e 0%, #ef473a 100%);
            }
            
            /* Section Header */
            .section-header {
                background: linear-gradient(90deg, #1e3c72 0%, #2a5298 100%);
                padding: 15px 25px;
                border-radius: 15px;
                margin-bottom: 20px;
                color: white;
                font-size: 1.5rem;
                font-weight: bold;
                text-align: center;
                box-shadow: 0 4px 15px rgba(0,0,0,0.2);
            }
            
            /* Table Styling */
            .styled-table {
                background: rgba(255,255,255,0.05);
                border-radius: 15px;
                overflow: hidden;
                margin: 20px 0;
            }
            
            .styled-table th {
                background: rgba(255,255,255,0.1);
                padding: 12px;
                text-align: left;
            }
            
            .styled-table td {
                padding: 12px;
                border-top: 1px solid rgba(255,255,255,0.05);
            }
        </style>
    """, unsafe_allow_html=True)

    # Section Header
    st.markdown(f'<div class="section-header">{title}</div>', unsafe_allow_html=True)

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

            # Metric Cards Display
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.markdown(f"""
                <div class="metric-card blue-card">
                    <div class="metric-header">
                        <i class="fas fa-ruler"></i> Espesor Promedio
                    </div>
                    <div class="metric-value">{float(avg_espesor)}</div>
                    <div class="metric-footer">milímetros</div>
                </div>
                """, unsafe_allow_html=True)

            with col2:
                st.markdown(f"""
                <div class="metric-card teal-card">
                    <div class="metric-header">
                        <i class="fas fa-chart-line"></i> MM Total
                    </div>
                    <div class="metric-value">{float(mm_total):,.0f}</div>
                    <div class="metric-footer">milímetros totales</div>
                </div>
                """, unsafe_allow_html=True)

            with col3:
                st.markdown(f"""
                <div class="metric-card purple-card">
                    <div class="metric-header">
                        <i class="fas fa-dollar-sign"></i> Costo Global/mm
                    </div>
                    <div class="metric-value">${float(costo_mm):,.2f}</div>
                    <div class="metric-footer">
                        Diferencia: ${round(float(mm_margin), 2):,.2f} a ${costos_mm:,.2f}
                    </div>
                </div>
                """, unsafe_allow_html=True)

            with col4:
                st.markdown(f"""
                <div class="metric-card red-card">
                    <div class="metric-header">
                        <i class="fas fa-tools"></i> Perforaciones
                    </div>
                    <div class="metric-value">{int(perforaciones):,}</div>
                    <div class="metric-footer">total perforaciones</div>
                </div>
                """, unsafe_allow_html=True)

            # Enhanced Table Display
            st.markdown("### Análisis Detallado")
            display_result = result.copy()
            if 'perforaTotal' in display_result.columns:
                display_result = display_result.drop(columns=['perforaTotal'])
            if 'placas' in display_result.columns:
                display_result = display_result.drop(columns=['placas'])
            if 'Tiempo Proceso (min)' in display_result.columns:
                display_result = display_result.drop(columns=['Tiempo Proceso (min)'])

            # Style the dataframe
            st.markdown('<div class="styled-table">', unsafe_allow_html=True)
            st.dataframe(
                display_result.style
                .background_gradient(cmap='viridis', subset=['Costo mm'])
                .format({
                    'mm_total': '{:,.0f}',
                    'Costo mm': '${:,.2f}'
                }),
                use_container_width=True
            )
            st.markdown('</div>', unsafe_allow_html=True)

        else:
            show_no_data_message(title, selected_month, selected_year)
            
    except Exception as e:
        st.error(f"Error processing data for {title}: {str(e)}")
        st.exception(e)


# Main Data Processing
try:
    df = create_dataframe_from_items(items)

    # Filter data
    filtered_df_sabimet = filter_by_year_month(df, selected_year, selected_month, 'sabimet')
    filtered_df_steelk = filter_by_year_month(df, selected_year, selected_month, 'steelk')

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
        else:
            aggregated_df_sttelk = pd.DataFrame()

        # Calculate proportions only if we have data
        per_sabimet = sum(aggregated_df_sabimet['perforaTotal']) if not aggregated_df_sabimet.empty else 0
        per_stellk = sum(aggregated_df_sttelk['perforaTotal']) if not aggregated_df_sttelk.empty else 0

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
