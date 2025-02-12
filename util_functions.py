import pandas as pd
from typing import List, Dict, Any



from datetime import datetime


def get_months_and_years_since(date_str):
    initial_date = datetime.strptime(date_str, "%d/%m/%Y")
    current_date = datetime.now()

    months = set()
    years = set()

    while initial_date <= current_date:
        months.add(initial_date.month)
        years.add(initial_date.year)
        initial_date = add_months(initial_date, 1)

    # Separate current month and year
    cur_month = current_date.month
    cur_year = current_date.year

    return sorted(list(months)), sorted(list(years)), cur_month, cur_year


def add_months(date, months):
    month = date.month - 1 + months
    year = date.year + month // 12
    month = month % 12 + 1
    day = min(date.day, [31,29,31,30,31,30,31,31,30,31,30,31][month-1])
    return datetime(year, month, day)




def filter_by_year_month(df, year, month, nego):
    filtered_items = []
    for index, row in df.iterrows():
        close_at_date = row['Terminado']
        if pd.to_datetime(close_at_date).year == year and pd.to_datetime(close_at_date).month == month and row['negocio']== nego:
            filtered_items.append(row)
    return pd.DataFrame(filtered_items)



def weighted_average_espesor(df):
    """
    Function to calculate the weighted average of 'Espesor' with 'Programas cortados' as weights
    :param df: DataFrame
    :return: float - weighted average of 'Espesor'
    """
    columns_to_convert = ['perforaTotal', 'espesor']
    for col in columns_to_convert:
        df[col] = df[col].apply(lambda x: float(x) if isinstance(x, Decimal) else x)


    total_programs = df['perforaTotal'].sum()
    weighted_sum = (df['espesor'] * df['perforaTotal']).sum()
    weighted_average = weighted_sum / total_programs

    return weighted_average





def create_dataframe_from_items(items):
    columns = [
        'pv', 'Inicio', 'cantidadPerforacionesTotal', 'Terminado', 'cantidadPerforacionesPlacas', 'kg',
        'tipoMecanizado', 'progress_createdAt', 'origen', 'maquina', 'placas', 'hora_reporte', 'tiempo',
        'tiempo_seteo', 'espesor', 'negocio'
    ]

    rows = []

    for item in items:
        # Extract the fixed part of the data with renamed columns
        fixed_values = {
            'pv': item['pv'],
            'Inicio': item['data']['createdAt'],
            'cantidadPerforacionesTotal': item['data']['cantidadPerforacionesTotal'],
            'Terminado': item['timestamp'],
            'cantidadPerforacionesPlacas': item['data']['cantidadPerforacionesPlacas'],
            'kg': item['data']['kg'],
            'tipoMecanizado': item['data']['tipoMecanizado'],
            'espesor': item['data'].get('espesor', 0)  # Assuming 'espesor' comes from 'data' dictionary
        }

        # Process each progress element
        for progress_item in item['data']['progress']:
            row = {
                'progress_createdAt': progress_item.get('createdAt', '0'),
                'origen': progress_item.get('origen', '0'),
                'maquina': progress_item.get('maquina', '0'),
                'placas': float(progress_item.get('placas', 0)) if 'placas' in progress_item else 0,
                'hora_reporte': progress_item.get('hora_reporte', '0'),
                'negocio': item['data'].get('negocio', 'does not exist'),
                'tiempo': float(progress_item.get('tiempo', 0)) if 'tiempo' in progress_item else 0,
                'tiempo_seteo': float(progress_item.get('tiempo_seteo', 0)) if 'tiempo_seteo' in progress_item else 0
            }

            # Combine fixed values with progress item specific values
            combined_row = {**fixed_values, **row}
            rows.append(combined_row)

    # Create DataFrame from rows
    df = pd.DataFrame(rows, columns=columns)
    df['Inicio'] = pd.to_datetime(df['Inicio'], errors='coerce')
    df['Terminado'] = pd.to_datetime(df['Terminado'], errors='coerce')
    columns_to_convert = ['placas', 'cantidadPerforacionesPlacas']
    for col in columns_to_convert:
        df[col] = df[col].apply(lambda x: float(x) if isinstance(x, Decimal) else x)

    df['perforaTotal'] = df['placas']*df['cantidadPerforacionesPlacas']
    df['Tiempo Proceso (min)'] = round((df['Terminado'] - df['Inicio']).dt.total_seconds() / 60, 2)

    return df


def filter_drop_duplicates_groupby_and_aggregate(df, column_name, value, agg_dict):
    """
    Filters the DataFrame based on the column name and value,
    removes duplicate rows, groups by 'pv' and 'espesor',
    and aggregates the grouped data.

    Parameters:
    - df: pandas.DataFrame
    - column_name: str, name of the column to filter by
    - value: value to filter the rows
    - agg_dict: dict, dictionary specifying aggregation methods for columns

    Returns:
    - pandas.DataFrame containing the aggregated data
    """
    # Filter the DataFrame
    filtered_df = df[df[column_name] == value]

    # Drop duplicate rows
    filtered_dedup_df = filtered_df.drop_duplicates()

    # Group by 'pv' and 'espesor'
    grouped_df = filtered_dedup_df.groupby(['pv', 'espesor'])

    # Aggregate the data
    aggregated_df = grouped_df.agg(agg_dict)

    return drop_zero_value_columns(aggregated_df.reset_index())



def drop_zero_value_columns(df):
    """
    Drops columns from the DataFrame where all the values are zero.

    Parameters:
    - df: pandas.DataFrame

    Returns:
    - pandas.DataFrame with zero-value columns removed
    """
    # Identify columns where all values are zero
    zero_value_columns = [col for col in df.columns if (df[col] == 0).all()]

    # Drop these columns
    df_dropped = df.drop(columns=zero_value_columns)

    return df_dropped

import pandas as pd
from decimal import Decimal


def group_by_espesor(df, espesor_list):
    # Example column conversions, assuming espesor, placas, and cantidadPerforacionesPlacas need conversion
    df = df.drop(columns=['pv'])
    df['espesor'] = df['espesor'].apply(lambda x: float(x) if isinstance(x, Decimal) else x)
    df['placas'] = df['placas'].apply(lambda x: float(x) if isinstance(x, Decimal) else x)
    df['cantidadPerforacionesPlacas'] = df['cantidadPerforacionesPlacas'].apply(
        lambda x: float(x) if isinstance(x, Decimal) else x)

    df['mm_total'] = df['espesor'] * df['perforaTotal']
    df['Perforaciones'] = df['perforaTotal']
    df['espesor'] = pd.to_numeric(df['espesor'], errors='coerce')

    # Sort espesor_list to ensure correct interval creation
    espesor_list = sorted(espesor_list)

    # Create intervals based on espesor_list with inclusive upper bounds
    intervals = [-float('inf')] + espesor_list
    labels = [f'<= {espesor_list[0]}'] + [f'{espesor_list[i - 1]} < esp <= {espesor_list[i]}' for i in
                                          range(1, len(espesor_list))]
    labels.append(f'> {espesor_list[-1]}')

    # Categorize espesor into groups
    df['espesor_group'] = pd.cut(df['espesor'], bins=intervals + [float('inf')], labels=labels, right=True)

    # Group by espesor_group and sum other columns
    grouped_df = df.groupby('espesor_group', observed=False).sum().reset_index()
    grouped_df = grouped_df.drop(columns=['espesor', 'cantidadPerforacionesPlacas', 'cantidadPerforacionesTotal'])

    return  grouped_df
