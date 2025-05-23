import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from plotly.subplots import make_subplots

def format_es(value, decimals=2):
    """
    Formatea un número al estilo español (1,234.56 -> 1.234,56)
    
    Args:
        value: Número a formatear
        decimals: Número de decimales a mostrar
        
    Returns:
        Cadena formateada según el estilo español
    """
    formato = f"{value:,.{decimals}f}"
    return formato.replace(",", "X").replace(".", ",").replace("X", ".")
from typing import Dict, List, Union, Any
from typing import Dict, List, Any, Optional, Tuple


def create_sankey_diagram(
    df: pd.DataFrame, 
    source_col: str, 
    target_col: str, 
    value_col: str,
    max_nodes_per_side: int = 20,
    colorize: bool = True
) -> go.Figure:
    """
    Crea un diagrama de Sankey que muestre los flujos desde una columna de origen
    hacia una columna de destino, limitado a los N nodos principales en cada lado
    para lograr mayor legibilidad.

    Parámetros:
        df: DataFrame con los datos de transacciones
        source_col: Nombre de la columna con los nodos de origen
        target_col: Nombre de la columna con los nodos de destino
        value_col: Nombre de la columna con los valores de flujo
        max_nodes_per_side: Número máximo de nodos que se mostrarán en cada lado
        colorize: Indica si se deben usar distintos colores para los nodos

    Devuelve:
        Objeto de figura de Plotly
    """
    if df.empty:
        # Return empty figure if no data
        fig = go.Figure()
        fig.update_layout(title="No data available for Sankey diagram")
        return fig
    
    # Crea una copia de Dataframe
    df_sankey = df.copy()
    
    # Asegura que existan las columnas
    if not all(col in df_sankey.columns for col in [source_col, target_col, value_col]):
        fig = go.Figure()
        fig.update_layout(title=f"Missing columns for Sankey diagram: {source_col}, {target_col}, or {value_col}")
        return fig
    
    # Elimina filas con NaN 
    df_sankey = df_sankey.dropna(subset=[source_col, target_col])
    
    if df_sankey.empty:
        fig = go.Figure()
        fig.update_layout(title="No valid data for Sankey diagram after dropping NaN values")
        return fig
    
    # Crea un DataFrame con valores agregados
    df_agg = df_sankey.groupby([source_col, target_col])[value_col].sum().reset_index()
    
    # Calcula los totales
    source_totals = df_agg.groupby(source_col)[value_col].sum().reset_index()
    source_totals = source_totals.sort_values(value_col, ascending=False)
    
    target_totals = df_agg.groupby(target_col)[value_col].sum().reset_index()
    target_totals = target_totals.sort_values(value_col, ascending=False)
    
    # Limita a N por cada lado
    top_sources = source_totals.head(max_nodes_per_side)[source_col].tolist()
    top_targets = target_totals.head(max_nodes_per_side)[target_col].tolist()
    
    # Filtra los datos para incluir únicamente los principales origenes y destinos
    df_agg = df_agg[
        (df_agg[source_col].isin(top_sources)) & 
        (df_agg[target_col].isin(top_targets))
    ]
    
    # Si, después de aplicar el filtrado, el resultado sigue estando vacío, devuelve un diagrama vacío
    if df_agg.empty:
        fig = go.Figure()
        fig.update_layout(title="No data available after limiting to top countries")
        return fig
    
    # Crea listas de valores únicos de origen y destino (ahora limitados a los N principales)
    source_values = df_agg[source_col].unique().tolist()
    target_values = df_agg[target_col].unique().tolist()
    
    # Ordena para garantizar un orden coherente.
    source_values.sort()
    target_values.sort()
    
    # Crea un mapeo de etiquetas a índices, manteniendo separados los orígenes y los destinos
    node_labels = source_values + target_values
    node_indices = {node: i for i, node in enumerate(node_labels)}
    
    # Crea los arreglos de source, target y value para el diagrama de Sankey
    sources = [node_indices[src] for src in df_agg[source_col]]
    targets = [node_indices[tgt] for tgt in df_agg[target_col]]
    values = df_agg[value_col].tolist()
    
    # Asigna colores a los nodos según si son de origen o de destino
    node_colors = []
    
    # Genera los colores para los nodos
    if colorize:
        import matplotlib.colors as mcolors
        import random
        
        # Crea paletas de colores diferenciadas para los orígenes y los destinos
        source_palette = list(mcolors.TABLEAU_COLORS.values())
        target_palette = list(mcolors.CSS4_COLORS.values())
        
        # Si tenemos muchos nodos, asegúrate de que haya suficientes colores
        if len(source_values) > len(source_palette):
            # Añade más colores según sea necesario
            random.seed(42)  # For reproducibility
            for _ in range(len(source_values) - len(source_palette)):
                r = random.random()
                g = random.random()
                b = random.random()
                source_palette.append(f'rgb({int(r*255)},{int(g*255)},{int(b*255)})')
        
        if len(target_values) > len(target_palette):
            # Añade más colores según sea necesario
            random.seed(43)  # Different seed for targets
            for _ in range(len(target_values) - len(target_palette)):
                r = random.random()
                g = random.random()
                b = random.random()
                target_palette.append(f'rgb({int(r*255)},{int(g*255)},{int(b*255)})')
        
        # Asigna colores a los nodos
        source_color_map = {source: source_palette[i % len(source_palette)] 
                           for i, source in enumerate(source_values)}
        
        target_color_map = {target: target_palette[i % len(target_palette)] 
                           for i, target in enumerate(target_values)}
        
        # FRellena la lista de colores de los nodos en el orden de node_labels
        for node in node_labels:
            if node in source_values:
                node_colors.append(source_color_map[node])
            else:
                node_colors.append(target_color_map[node])
    else:
        # Colores predeterminados: los nodos de origen van en azul y los de destino en verde
        for node in node_labels:
            if node in source_values:
                node_colors.append('rgba(31, 119, 180, 0.8)')  # Blue for sources
            else:
                node_colors.append('rgba(44, 160, 44, 0.8)')  # Green for targets
    
    # Crear el diagrama Sankey
    fig = go.Figure(data=[go.Sankey(
        node=dict(
            pad=15,
            thickness=20,
            line=dict(color="black", width=0.5),
            label=node_labels,
            color=node_colors
        ),
        link=dict(
            source=sources,
            target=targets,
            value=values,
            hovertemplate='%{source.label} → %{target.label}: %{value:.2f}<extra></extra>',
        )
    )])
    
    # Actualiza el layout
    fig.update_layout(
        title_text=f"Flujo desde {source_col} hacia {target_col}",
        font_size=12,
        height=550
    )
    
    return fig


def create_country_map(df: pd.DataFrame, country_col: str, value_col: str) -> go.Figure:
    """
    Crea un mapa coroplético que muestre los valores por país.

    Parámetros:
        df: DataFrame con los datos de transacciones
        country_col: Nombre de la columna con el país
        value_col: Nombre de la columna con los valores

    Devuelve:
        Objeto de figura de Plotly
    """
    if df.empty:
        # Devuelve una figura vacía si no hay datos
        fig = go.Figure()
        fig.update_layout(title="No data available for country map")
        return fig
    
    # Crea una copia del DataFrame
    df_map = df.copy()
    
    # Asegúrate de que disponemos de las columnas necesarias
    if not all(col in df_map.columns for col in [country_col, value_col]):
        fig = go.Figure()
        fig.update_layout(title=f"Missing columns for country map: {country_col} or {value_col}")
        return fig
    
    # Elimina las filas con NaN en la columna de país
    df_map = df_map.dropna(subset=[country_col])
    
    if df_map.empty:
        fig = go.Figure()
        fig.update_layout(title="No valid data for country map after dropping NaN values")
        return fig
    
    # Agrupa los valores por país
    country_values = df_map.groupby(country_col)[value_col].sum().reset_index()
    
    # Crea el mapa coroplético
    fig = px.choropleth(
        country_values,
        locations=country_col,
        locationmode="country names",
        color=value_col,
        hover_name=country_col,
        color_continuous_scale=px.colors.sequential.Blues,
        labels={value_col: "Amount (€)"},
        title=f"Total by {country_col}"
    )
    
    # Actualiza el diseño
    fig.update_layout(
        geo=dict(
            showframe=False,
            showcoastlines=True,
            projection_type='equirectangular'
        ),
        height=400
    )
    
    return fig


def create_operation_status_chart(df: pd.DataFrame) -> go.Figure:
    """
    Crea un gráfico que muestre la distribución de los estados de operación.
    
    Parámetros:
        df: DataFrame con los datos de transacciones
        
    Devuelve:
        Objeto de figura de Plotly
    """
    if df.empty or 'ESTADO_OPERACION' not in df.columns:
        # Return empty figure if no data or missing column
        fig = go.Figure()
        fig.update_layout(title="No data available for operation status chart")
        return fig
    
    # Cuenta operaciones por estatus
    status_counts = df['ESTADO_OPERACION'].value_counts().reset_index()
    status_counts.columns = ['Status', 'Count']
    
    # Crea un mapa de color
    color_map = {
        'EXITOSA': 'green',
        'CANCELADA': 'red',
        'FALLIDA': 'orange'
    }
    
    # Crea el gráfico
    fig = px.pie(
        status_counts,
        values='Count',
        names='Status',
        title="Operation Status Distribution",
        color='Status',
        color_discrete_map=color_map
    )
    
    # Actualiza el layout
    fig.update_layout(
        legend_title="Status",
        height=400
    )
    
    return fig


def create_document_country_chart(df: pd.DataFrame, chart_type: str = 'bar') -> go.Figure:
    """
    Crea un gráfico que muestre la distribución de los países del documento del remitente.

    Parámetros:
        df: DataFrame con los datos de transacciones  
        chart_type: Tipo de gráfico a crear ('bar' o 'pie')

    Devuelve:
        Objeto de figura de Plotly
    """
    if df.empty or 'PAIS_DOC_ORDENANTE' not in df.columns:
        # Devuelve una figura vacía si no hay datos o falta la columna necesaria
        fig = go.Figure()
        fig.update_layout(title="No data available for document country chart")
        return fig
    
    # Elimina las filas con valores NaN en el país del documento.
    df_chart = df.dropna(subset=['PAIS_DOC_ORDENANTE'])
    
    if df_chart.empty:
        fig = go.Figure()
        fig.update_layout(title="No valid data for document country chart after dropping NaN values")
        return fig
    
    # Cuenta los documentos por país
    doc_counts = df_chart['PAIS_DOC_ORDENANTE'].value_counts().reset_index()
    doc_counts.columns = ['Country', 'Count']
    
    # Selecciona los 15 países principales
    top_countries = doc_counts.head(15)
    
    # Crea el gráfico 
    if chart_type == 'pie':
        # Create a pie chart
        fig = px.pie(
            top_countries,
            values='Count',
            names='Country',
            title="Países de Origen de los Documentos de Ordenantes",
            color_discrete_sequence=px.colors.qualitative.Pastel,
            hover_data=['Count']
        )
        
        # Actualiza el layout
        fig.update_layout(
            legend_title="País",
            height=450
        )
        
        # Actualiza traces
        fig.update_traces(textposition='inside', textinfo='percent+label')
        
    else:  # Por defecto, utiliza un gráfico de barras
        # Crea un grafico de barras
        fig = px.bar(
            top_countries,
            x='Country',
            y='Count',
            title="Principales Países de Origen de los Documentos",
            color='Count',
            color_continuous_scale=px.colors.sequential.Blues,
            labels={'Count': 'Número de Transacciones', 'Country': 'País del Documento'}
        )
        
        # Actualiza el layout
        fig.update_layout(
            xaxis_title="País del Documento",
            yaxis_title="Número de Transacciones",
            height=400
        )
    
    return fig


def create_destination_country_chart(df: pd.DataFrame, top_n: int = 20) -> go.Figure:
    """
    Crea un gráfico de barras que muestre los principales países de destino por monto.

    Parámetros:
        df: DataFrame con los datos de transacciones  
        top_n: Número de países principales a mostrar

    Devuelve:
        Objeto de figura de Plotly
    """
    if df.empty or 'PAIS_DESTINO' not in df.columns or 'IMPORTE' not in df.columns:
        # Devuelve una figura vacía si no hay datos o faltan columnas
        fig = go.Figure()
        fig.update_layout(title="No data available for destination country chart")
        return fig
    
    # Elimina las filas con valores NaN en el país de destino o en el importe
    df_chart = df.dropna(subset=['PAIS_DESTINO', 'IMPORTE'])
    
    if df_chart.empty:
        fig = go.Figure()
        fig.update_layout(title="No valid data for destination country chart after dropping NaN values")
        return fig
    
    # Suma los montos por país de destino
    dest_amounts = df_chart.groupby('PAIS_DESTINO')['IMPORTE'].sum().reset_index()
    dest_amounts = dest_amounts.sort_values('IMPORTE', ascending=False)
    
    # Selecciona los N países principales
    top_countries = dest_amounts.head(top_n)
    
    # Crea un gráfico de barras
    fig = px.bar(
        top_countries,
        x='PAIS_DESTINO',
        y='IMPORTE',
        title=f"Principales {top_n} Países Destino por Importe",
        color='IMPORTE',
        color_continuous_scale=px.colors.sequential.Reds,
        labels={'IMPORTE': 'Importe Total (€)', 'PAIS_DESTINO': 'País Destino'}
    )
    
    # Crea una lista personalizada de valores para los ticks del eje Y
    max_value = top_countries['IMPORTE'].max()
    tick_values = np.linspace(0, max_value, 6)
    tick_texts = [f"€{format_es(val, 2)}" for val in tick_values]
    
    # Formatea el eje Y para mostrar los valores como moneda con formato español
    fig.update_layout(
        xaxis_title="País Destino",
        yaxis_title="Importe Total (€)",
        height=450,
        yaxis=dict(
            tickvals=tick_values,
            ticktext=tick_texts,
            separatethousands=True
        )
    )
    
    # Rota las etiquetas del eje X para mejorar la legibilidad
    fig.update_xaxes(tickangle=45)
    
    return fig


def create_amount_over_time_chart(df: pd.DataFrame) -> go.Figure:
    """
    Crea un gráfico de líneas que muestre los montos de transacciones a lo largo del tiempo.

    Parámetros:
        df: DataFrame con los datos de transacciones

    Devuelve:
        Objeto de figura de Plotly
    """
    if df.empty or 'FECHA' not in df.columns or 'IMPORTE' not in df.columns:
        # Devuelve una figura vacía si no hay datos o faltan columnas.
        fig = go.Figure()
        fig.update_layout(title="No data available for amount over time chart")
        return fig
    
    # Crea una copia del DataFrame
    df_time = df.copy()
    
    # Asegúrate de que la columna de fecha esté en formato datetime
    if not pd.api.types.is_datetime64_any_dtype(df_time['FECHA']):
        df_time['FECHA'] = pd.to_datetime(df_time['FECHA'], errors='coerce')
    
    # Elimina las filas con valores NaN en la fecha
    df_time = df_time.dropna(subset=['FECHA'])
    
    if df_time.empty:
        fig = go.Figure()
        fig.update_layout(title="No valid data for amount over time chart after dropping NaN values")
        return fig
    
    # Re-muestrea los datos por día
    df_time_daily = df_time.groupby(df_time['FECHA'].dt.date)['IMPORTE'].agg(['sum', 'count']).reset_index()
    df_time_daily.columns = ['Date', 'Total Amount', 'Transaction Count']
    
    # Crea la figura con dos ejes Y
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    # Añadir una linea de importe
    fig.add_trace(
        go.Scatter(
            x=df_time_daily['Date'],
            y=df_time_daily['Total Amount'],
            name='Total Amount',
            line=dict(color='blue', width=2)
        ),
        secondary_y=False
    )
    
    # Agrega la línea de conteo de transacciones
    fig.add_trace(
        go.Scatter(
            x=df_time_daily['Date'],
            y=df_time_daily['Transaction Count'],
            name='Transaction Count',
            line=dict(color='red', width=2, dash='dot')
        ),
        secondary_y=True
    )
    
    # Crear valores personalizados para el eje Y de importes
    max_amount = df_time_daily['Total Amount'].max()
    amount_tick_values = np.linspace(0, max_amount, 6)
    amount_tick_texts = [f"€{format_es(val, 2)}" for val in amount_tick_values]
    
    # Crear valores personalizados para el eje Y de número de transacciones
    max_count = df_time_daily['Transaction Count'].max()
    count_tick_values = np.linspace(0, max_count, 6)
    count_tick_texts = [format_es(val, 0) for val in count_tick_values]
    
    # Actualiza el diseño con formato español
    fig.update_layout(
        title="Actividad de Transacciones en el Tiempo",
        xaxis_title="Fecha",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        height=400
    )
    
    # Actualiza los títulos de los ejes Y con formato en español
    fig.update_yaxes(
        title_text="Importe Total (€)",
        secondary_y=False,
        tickvals=amount_tick_values,
        ticktext=amount_tick_texts
    )
    fig.update_yaxes(
        title_text="Número de Transacciones",
        secondary_y=True,
        tickvals=count_tick_values,
        ticktext=count_tick_texts
    )
    
    return fig


def create_risk_heatmap(risk_scores: Dict[str, int], indicator_descriptions: Dict[str, Dict[str, str]], indicator_types: Dict[str, str] = None) -> go.Figure:
    """
    Crea una visualización de mapa de calor (heatmap) de los puntajes de riesgo para cada indicador, separados por tipo.

    Parámetros:
        risk_scores: Diccionario que asigna a cada ID de indicador su puntaje de riesgo  
        indicator_descriptions: Diccionario que asigna a cada ID de indicador su descripción  
        indicator_types: Diccionario que asigna a cada ID de indicador su tipo

    Devuelve:
        Objeto de figura de Plotly
    """
    if not risk_scores:
        # Devuelve una figura vacía si no hay datos
        fig = go.Figure()
        fig.update_layout(title="No risk score data available")
        return fig
    
    # Convierte los puntajes de riesgo a un DataFrame para su visualización
    risk_data = []
    
    # Usa un tipo predeterminado si no se proporciona
    if indicator_types is None:
        indicator_types = {}
    
    for indicator_id, score in risk_scores.items():
        if indicator_id in indicator_descriptions:
            description = indicator_descriptions[indicator_id]['description']
            weight = indicator_descriptions[indicator_id]['weight']
            
            # Trunca las descripciones largas
            short_desc = description[:50] + '...' if len(description) > 50 else description
            
            # Obtén el tipo de indicador o usa un valor por defecto
            indicator_type = indicator_types.get(indicator_id, "General")
            
            risk_data.append({
                'Indicator': f"{indicator_id}. {short_desc}",
                'Risk Score': score,
                'Weight': weight,
                'Type': indicator_type
            })
    
    # Crea un DataFrame
    risk_df = pd.DataFrame(risk_data)
    
    # Ordena por indicator ID
    risk_df['Indicator_ID'] = risk_df['Indicator'].str.extract(r'^(\d+)\.').astype(int)
    risk_df = risk_df.sort_values('Indicator_ID')
    
    # Si no se dispone de información sobre los tipos, crea un único mapa de calor
    if 'Type' not in risk_df.columns or len(risk_df['Type'].unique()) <= 1:
        # Crea un único mapa de calor
        fig = px.imshow(
            risk_df[['Risk Score']].T,
            x=risk_df['Indicator'],
            y=['Risk Score'],
            color_continuous_scale=[
                [0, 'green'],
                [0.33, 'yellow'],
                [0.67, 'orange'],
                [1, 'red']
            ],
            zmin=1,
            zmax=4,
            labels={'color': 'Risk Level'}
        )
    else:
        # Obtén los tipos únicos y crea una subgráfica (subplot) para cada uno
        types = sorted(risk_df['Type'].unique())
        
        # Crea una cuadrícula de subgráficas (subplot) — una fila por cada tipo
        fig = make_subplots(
            rows=len(types),
            cols=1,
            subplot_titles=[f"Indicadores de tipo: {t}" for t in types],
            vertical_spacing=0.1
        )
        
        # Agrega un mapa de calor para cada tipo
        for i, type_name in enumerate(types):
            # Filtra los datos correspondientes a ese tipo
            type_df = risk_df[risk_df['Type'] == type_name].copy()
            
            if not type_df.empty:
                # Crea el mapa de calor para ese tipo
                heatmap = go.Heatmap(
                    z=type_df[['Risk Score']].T.values,
                    x=type_df['Indicator'],
                    y=['Risk Score'],
                    colorscale=[
                        [0, 'green'],
                        [0.33, 'yellow'],
                        [0.67, 'orange'],
                        [1, 'red']
                    ],
                    zmin=1,
                    zmax=4,
                    hovertemplate='<b>%{x}</b><br>Risk Score: %{z}<extra></extra>'
                )
                
                # Add to subplot
                fig.add_trace(heatmap, row=i+1, col=1)
    
    # Añade anotaciones
    for i, indicator in enumerate(risk_df['Indicator']):
        score = risk_df.iloc[i]['Risk Score']
        weight = risk_df.iloc[i]['Weight']
        
        fig.add_annotation(
            x=indicator,
            y='Risk Score',
            text=f"{score}<br>({weight})",
            showarrow=False,
            font=dict(color="black" if score < 3 else "white")
        )
    
    # Actualiza el layout
    fig.update_layout(
        title="Risk Scores by Indicator",
        xaxis_title="",
        yaxis_title="",
        height=200,
        xaxis={'side': 'top'}
    )
    
    # Rotate x-axis labels
    fig.update_xaxes(tickangle=45)
    
    return fig


def create_risk_radar_chart(risk_by_type: Dict[str, float]) -> go.Figure:
    """
   Crea una visualización en gráfico de radar de los puntajes de riesgo por tipo.

    Parámetros:
        risk_by_type: Diccionario que asigna a cada tipo de riesgo su puntaje

    Devuelve:
        Objeto de figura de Plotly
    """
    if not risk_by_type:
        # Devuelve una figura vacía si no hay datos
        fig = go.Figure()
        fig.update_layout(title="No risk type data available")
        return fig
    
    # Ordena los tipos de riesgo
    types = sorted(risk_by_type.keys())
    values = [risk_by_type[t] for t in types]
    
    # Crea el gráfico de radar
    fig = go.Figure()
    
    fig.add_trace(go.Scatterpolar(
        r=values,
        theta=types,
        fill='toself',
        name='Risk Level',
        line_color='darkblue',
        fillcolor='rgba(51, 102, 204, 0.5)'
    ))
    
    # Actualiza el layout
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[1, 4]
            )
        ),
        showlegend=False
    )
    
    return fig


def create_indicator_histogram(
    indicator_id: str,
    umbral_info: Dict[str, Union[float, str]],
    title: str = None,
    data=None
) -> go.Figure:
    """
    Crea una visualización tipo histograma para un indicador, con líneas de umbral.
        Basado en datos reales de transacciones provenientes del estado de sesión.

    Parámetros:
        indicator_id: ID del indicador  
        umbral_info: Diccionario con la información de umbrales ('medium', 'high', 'descripcion')  
        title: Título opcional para el gráfico  
        data: Datos reales opcionales a usar en lugar de los datos de riesgo por defecto

    Devuelve:
        Objeto de figura de Plotly
    """
    import numpy as np
    import plotly.graph_objects as go
    import plotly.express as px
    import pandas as pd
    from typing import Dict, Union, List, Any, Optional
    
    # Si no hay datos específicos, intentamos extraer datos reales de la sesión
    if data is None and 'st' in globals():
        import streamlit as st
        
        # Usar datos reales de transacciones filtradas si están disponibles
        if 'filtered_data' in st.session_state and not st.session_state.filtered_data.empty:
            all_transactions = st.session_state.filtered_data
            
            # Obtener datos específicos del indicador desde risk_details
            if 'risk_details' in st.session_state and indicator_id in st.session_state.risk_details:
                details = st.session_state.risk_details[indicator_id]
                
                # Si details es un DataFrame, extraer los valores relevantes para el histograma
                if isinstance(details, pd.DataFrame) and not details.empty:
                    # Intentar obtener transacciones específicas de riesgo
                    if 'NUMERO_TRANSACCION' in details.columns:
                        # Obtener números de transacción del detalle de riesgo
                        trans_ids = details['NUMERO_TRANSACCION'].astype(str).unique()
                        
                        # Obtener las transacciones completas desde filtered_data
                        risk_transactions = all_transactions[
                            all_transactions['NUMERO_TRANSACCION'].astype(str).isin(trans_ids)
                        ]
                        
                        # Extraer datos según el tipo de indicador
                        if not risk_transactions.empty:
                            if 'IMPORTE' in risk_transactions.columns:
                                data = risk_transactions['IMPORTE'].dropna().values
                            elif 'monto' in risk_transactions.columns:
                                data = risk_transactions['monto'].dropna().values
                            
                            # Utilizar Motivo_Riesgo si está disponible y no tenemos otros datos
                            if (data is None or len(data) == 0) and 'Motivo_Riesgo' in details.columns:
                                import re
                                numeric_values = []
                                for motivo in details['Motivo_Riesgo'].astype(str):
                                    # Buscar porcentajes o valores numéricos en el texto
                                    matches = re.findall(r'(\d+\.\d+|\d+)%|\((\d+\.\d+|\d+)\)', motivo)
                                    if matches:
                                        # Aplanar la lista de tuplas y filtrar valores no vacíos
                                        values = [float(val) for tup in matches for val in tup if val]
                                        if values:
                                            numeric_values.append(max(values))
                                
                                if numeric_values:
                                    data = np.array(numeric_values)
        
        # Si no se pudo obtener datos de transacciones específicas, usar datos generales filtrados
        if data is None and 'filtered_data' in st.session_state and not st.session_state.filtered_data.empty:
            df = st.session_state.filtered_data
            
            # Seleccionar columnas adecuadas según el tipo de indicador
            if indicator_id in ['1', '2']:  # Documentación
                if 'NUM_DOC_ORDENANTE' in df.columns:
                    # Contar frecuencia de documentos
                    doc_counts = df['NUM_DOC_ORDENANTE'].value_counts().values
                    data = doc_counts
            elif indicator_id in ['4', '5', '6']:  # Importes
                if 'IMPORTE' in df.columns:
                    data = df['IMPORTE'].dropna().values
            elif indicator_id in ['8', '11', '18']:  # Países
                if 'PAIS_DESTINO' in df.columns:
                    # Contar frecuencia de países
                    country_counts = df['PAIS_DESTINO'].value_counts().values
                    data = country_counts
            elif indicator_id in ['9', '12', '14', '15']:  # Variaciones
                if 'IMPORTE' in df.columns and 'FECHA' in df.columns:
                    # Importes por fecha
                    data = df['IMPORTE'].dropna().values
            else:
                # Utilizar importes por defecto si no hay lógica específica
                if 'IMPORTE' in df.columns:
                    data = df['IMPORTE'].dropna().values
    
    # Si aún no tenemos datos, utilizamos un texto informativo en lugar de datos simulados
    if data is None or len(data) == 0:
        # Crear figura con mensaje informativo
        fig = go.Figure()
        fig.add_annotation(
            text="No hay datos reales disponibles para este indicador",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=14)
        )
        # Configurar el diseño
        fig.update_layout(
            title=title or f"Distribución - Indicador {indicator_id}",
            height=300
        )
        return fig
    
    # Crear DataFrame
    df_data = pd.DataFrame({
        umbral_info.get('descripcion', f'Valor Indicador {indicator_id}'): data
    })
    
    # Definir título si no se proporciona
    if title is None:
        title = f'Distribución de {umbral_info.get("descripcion", f"Indicador {indicator_id}")}'
    
    # Crear el histograma
    fig = px.histogram(
        df_data, 
        x=df_data.columns[0],  # Primera columna
        title=title,
        color_discrete_sequence=['#3366CC'],
        opacity=0.7,
        nbins=30
    )
    
    # Añadir líneas verticales para los umbrales (compatibilidad con diferentes nombres)
    if 'low' in umbral_info or 'bajo' in umbral_info:
        bajo_value = umbral_info.get('low', umbral_info.get('bajo', 0))
        fig.add_vline(x=bajo_value, line_dash="dash", line_color="green", 
                    annotation_text="Umbral Bajo", annotation_position="top right")
    
    if 'medium' in umbral_info or 'medio' in umbral_info:
        medio_value = umbral_info.get('medium', umbral_info.get('medio', 0))
        fig.add_vline(x=medio_value, line_dash="dash", line_color="orange", 
                    annotation_text="Umbral Medio", annotation_position="top right")
    
    if 'high' in umbral_info or 'alto' in umbral_info:
        alto_value = umbral_info.get('high', umbral_info.get('alto', 0))
        fig.add_vline(x=alto_value, line_dash="dash", line_color="red", 
                    annotation_text="Umbral Alto", annotation_position="top right")
    
    # Actualizar diseño
    fig.update_layout(
        xaxis_title=umbral_info.get('descripcion', f'Valor Indicador {indicator_id}'),
        yaxis_title="Frecuencia",
        bargap=0.1,
        height=300
    )
    
    return fig


def create_average_transaction_by_country_chart(df: pd.DataFrame, top_n: int = 20) -> go.Figure:
    """
    Crea un gráfico de barras que muestre los principales países según el monto promedio de transacción.

    Parámetros:
        df: DataFrame con los datos de transacciones  
        top_n: Número de países principales a mostrar

    Devuelve:
        Objeto de figura de Plotly
    """
    if 'PAIS_DESTINO' not in df.columns or 'IMPORTE' not in df.columns:
        # Devuelve una figura vacía si no existen las columnas necesarias
        return go.Figure()
    
    # Agrupa por país de destino y calcula el monto promedio de transacción
    country_avg = df.groupby('PAIS_DESTINO')['IMPORTE'].agg(['mean', 'count']).reset_index()
    
    # Filtra los países con al menos 3 transacciones para asegurar significancia estadística
    min_transactions = 3
    country_avg = country_avg[country_avg['count'] >= min_transactions]
    
    # Ordena y selecciona los países principales según el monto promedio
    country_avg = country_avg.sort_values(by='mean', ascending=False).head(top_n)
    
    # Crea el gráfico de barras
    fig = px.bar(
        country_avg,
        x='PAIS_DESTINO',
        y='mean',
        title=f'Top {top_n} Países por Importe Medio de Transacción',
        labels={'PAIS_DESTINO': 'País', 'mean': 'Importe Medio (€)', 'count': 'Nº Transacciones'},
        color='mean',
        color_continuous_scale='Viridis',
        hover_data=['count']
    )
    
    # Crear una lista personalizada de valores para los ticks del eje Y
    max_value = country_avg['mean'].max()
    tick_values = np.linspace(0, max_value, 6)
    tick_texts = [f"€{format_es(val, 2)}" for val in tick_values]
    
    # Personaliza el diseño con marcas (ticks) formateadas en español
    fig.update_layout(
        xaxis_title='País de Destino',
        yaxis_title='Importe Medio por Transacción (€)',
        xaxis_tickangle=-45,
        coloraxis_showscale=False,
        height=500,
        yaxis=dict(
            tickvals=tick_values,
            ticktext=tick_texts
        )
    )
    
    # Agrega los importes formateados (por ejemplo, con símbolo de euro y separadores de miles con punto).
    for i, row in enumerate(country_avg.itertuples()):
        # Usar nuestra función de formato español
        formatted_mean = format_es(row.mean, 2)
        
        # Acceder a count desde el objeto namedtuple
        count_value = row[3]  # La posición 3 corresponde a la columna 'count'
        
        fig.add_annotation(
            x=row.PAIS_DESTINO,
            y=row.mean,
            text=f'{formatted_mean} €<br>({count_value} transacciones)',
            showarrow=False,
            yshift=10,
            font=dict(size=10)
        )
    
    return fig
