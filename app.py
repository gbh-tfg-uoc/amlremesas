import streamlit as st
import pandas as pd
import numpy as np
import os
import re
import io
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots


from utils.data_processing import (
    process_csv_files, 
    extract_agent_subject_info,
    filter_dataframe
)
from utils.risk_indicators import (
    run_risk_analysis,
    calculate_total_risk_score,
    calculate_risk_indicators,
    calculate_risk_scores,
    get_indicator_descriptions,
    get_indicator_types,
    get_indicator_names
)
from utils.network_analysis import create_transaction_graph
from utils.visualizations import (
    create_sankey_diagram,
    create_country_map,
    create_operation_status_chart,
    create_document_country_chart,
    create_destination_country_chart,
    create_amount_over_time_chart,
    create_risk_radar_chart,
    create_average_transaction_by_country_chart
)
from utils.pdf_generator import generate_risk_report, get_download_link
from utils.export_utils import (
    generate_risk_report_excel,
    export_network_to_excel,
    get_download_link as export_download_link
)

st.set_page_config(
    page_title="Análisis de Prevención de Blanqueo de Capitales",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Cargar información de indicadores al inicio
indicator_names = get_indicator_names()
indicator_descriptions = get_indicator_descriptions()
indicator_types = get_indicator_types()


if 'data' not in st.session_state:
    st.session_state.data = None
if 'agent_subject_mapping' not in st.session_state:
    st.session_state.agent_subject_mapping = {}
if 'selected_agents' not in st.session_state:
    st.session_state.selected_agents = []
if 'selected_subjects' not in st.session_state:
    st.session_state.selected_subjects = []
if 'available_agents' not in st.session_state:
    st.session_state.available_agents = []
if 'available_subjects' not in st.session_state:
    st.session_state.available_subjects = []
if 'filtered_data' not in st.session_state:
    st.session_state.filtered_data = None
if 'risk_scores' not in st.session_state:
    st.session_state.risk_scores = None
if 'risk_details' not in st.session_state:
    st.session_state.risk_details = None
if 'network_data' not in st.session_state:
    st.session_state.network_data = None
if 'custom_weights' not in st.session_state:
    # Inicializar ponderaciones personalizadas con los valores predeterminados
    st.session_state.custom_weights = {
        indicator_id: float(info['weight'].strip('%')) / 100
        for indicator_id, info in indicator_descriptions.items()
    }
# Thresholds ahora definidos en archivo separado
if 'agents_by_subject' not in st.session_state:
    st.session_state.agents_by_subject = {}
if 'data_processed' not in st.session_state:
    st.session_state.data_processed = False
if 'filters_applied' not in st.session_state:
    st.session_state.filters_applied = False

# Main title
st.title("Sistema de Análisis de Riesgo de Blanqueo de Capitales")

# Sidebar for file upload and filtering
with st.sidebar:
    st.header("Carga y Filtrado de Datos")
    
    # File upload
    uploaded_files = st.file_uploader(
        "Cargar archivos CSV de transacciones",
        type=["csv"],
        accept_multiple_files=True
    )
    
    if uploaded_files:
        # Process files if not already processed or if new files
        if st.button("Procesar Archivos"):
            with st.spinner("Procesando archivos CSV..."):
                try:
                    # Process CSV files
                    df, agent_subject_mapping = process_csv_files(uploaded_files)
                    
                    if df.empty:
                        st.error("No se pudieron cargar datos de los archivos seleccionados. Verifica que los archivos tienen el formato correcto.")
                    else:
                        # Store data in session state
                        st.session_state.data = df
                        st.session_state.agent_subject_mapping = agent_subject_mapping
                        
                        # Extract available agents and subjects
                        available_agents, available_subjects = extract_agent_subject_info(agent_subject_mapping)
                        st.session_state.available_agents = available_agents
                        st.session_state.available_subjects = available_subjects
                        
                        # Set default selected values to all available
                        st.session_state.selected_agents = available_agents.copy()
                        st.session_state.selected_subjects = available_subjects.copy()
                        
                        # Construir el diccionario inverso: sujeto -> [agentes]
                        st.session_state.agents_by_subject = {}
                        for agent, subject in agent_subject_mapping.items():
                            if subject not in st.session_state.agents_by_subject:
                                st.session_state.agents_by_subject[subject] = []
                            st.session_state.agents_by_subject[subject].append(agent)
                        
                        # También aplicamos el filtro y realizamos el análisis inicial con todos los datos
                        try:
                            # Aplicamos filtro con todos los agentes y sujetos seleccionados
                            filtered_data = filter_dataframe(
                                df,
                                agent_subject_mapping,
                                available_agents,
                                available_subjects
                            )
                            
                            # Store filtered data
                            st.session_state.filtered_data = filtered_data
                            st.session_state.data_processed = True
                            
                            # Run risk analysis on filtered data
                            if not filtered_data.empty:
                                risk_scores, risk_details = run_risk_analysis(filtered_data)
                                st.session_state.risk_scores = risk_scores
                                st.session_state.risk_details = risk_details
                                
                                # Generate network data
                                st.session_state.network_data = create_transaction_graph(filtered_data)
                                st.session_state.filters_applied = True
                        except Exception as e:
                            st.error(f"Error al procesar los datos iniciales: {str(e)}")
                            import traceback
                            st.error(traceback.format_exc())
                        
                        st.success(f"Archivos procesados correctamente: {len(df)} transacciones encontradas")
                        st.rerun()  # Rerun to update the UI with the new data
                except Exception as e:
                    st.error(f"Error al procesar los archivos CSV: {str(e)}")
                    import traceback
                    st.error(traceback.format_exc())
    

    if st.session_state.available_agents and st.session_state.available_subjects:
        st.header("Filtros")
        
        # Si no existe en el session state, inicializar diccionario para guardar agentes por sujeto
        if 'agents_by_subject' not in st.session_state:
            st.session_state.agents_by_subject = {}
            # Construir el diccionario inverso: sujeto -> [agentes]
            for agent, subject in st.session_state.agent_subject_mapping.items():
                if subject not in st.session_state.agents_by_subject:
                    st.session_state.agents_by_subject[subject] = []
                st.session_state.agents_by_subject[subject].append(agent)
        
        # Subject filter - primero seleccionamos sujetos obligados
        st.subheader("Sujetos Obligados")
        selected_subjects = st.multiselect(
            "Seleccionar sujetos obligados",
            options=st.session_state.available_subjects,
            default=st.session_state.selected_subjects,
            key="multi_subjects"
        )
        
        # Determinar los agentes disponibles basados en los sujetos seleccionados
        available_agents_filtered = []
        if selected_subjects:
            for subject in selected_subjects:
                if subject in st.session_state.agents_by_subject:
                    available_agents_filtered.extend(st.session_state.agents_by_subject[subject])
            available_agents_filtered = sorted(list(set(available_agents_filtered)))  # Eliminar duplicados
        else:
            available_agents_filtered = st.session_state.available_agents
        
        # Agent filter - ahora solo mostramos los agentes de los sujetos seleccionados
        st.subheader("Agentes")
        
        # Ajustar los agentes seleccionados para que solo incluyan los que pertenecen a los sujetos seleccionados
        selected_agents_filtered = [agent for agent in st.session_state.selected_agents 
                                  if agent in available_agents_filtered]
        
        selected_agents = st.multiselect(
            "Seleccionar agentes",
            options=available_agents_filtered,
            default=selected_agents_filtered,
            key="multi_agents"
        )
        
        # Información sobre la relación entre agentes y sujetos
        if selected_agents:
            st.subheader("Información de Agentes")
            agent_info = {}
            for agent in selected_agents:
                subject = st.session_state.agent_subject_mapping.get(agent, "Desconocido")
                if subject not in agent_info:
                    agent_info[subject] = []
                agent_info[subject].append(agent)
            
            for subject, agents in agent_info.items():
                # Eliminar duplicados que tengan el mismo número pero formatos diferentes (ej. "537" y "Agente537")
                unique_agents = []
                agent_numbers = set()
                
                for agent in agents:
                    # Extraer el número del agente si tiene el formato "Agente123"
                    num_match = re.search(r'Agente(\d+)', agent)
                    if num_match:
                        agent_num = num_match.group(1)
                    else:
                        # Si es solo un número, usarlo directamente
                        agent_num = agent if agent.isdigit() else agent
                    
                    # Si este número no está ya incluido, añadir el agente original
                    if agent_num not in agent_numbers:
                        agent_numbers.add(agent_num)
                        unique_agents.append(agent)
                
                # Mostrar solo los agentes únicos
                st.write(f"**Sujeto Obligado {subject}**: {', '.join(unique_agents)}")
        
        # Apply filters button
        if st.button("Aplicar Filtros"):
            # Verificar si hay datos disponibles
            if 'data' not in st.session_state or st.session_state.data is None or st.session_state.data.empty:
                st.warning("Por favor, sube archivos de datos primero")
            else:
                # Procesar los datos con manejo de errores mejorado
                with st.spinner("Aplicando filtros y analizando riesgos..."):
                    try:
                        # Verificamos que agent_subject_mapping existe
                        if 'agent_subject_mapping' not in st.session_state:
                            st.session_state.agent_subject_mapping = {}
                        
                        # Normalizar los agentes seleccionados para evitar duplicados
                        # Nuevo enfoque: siempre usar formato "AgenteNUM" de manera consistente
                        normalized_agents = []
                        unique_agent_ids = set()
                        
                        for agent in selected_agents:
                            if agent is None:
                                continue
                                
                            # Convertir todo a string
                            agent_str = str(agent)
                            
                            # Normalizar formato
                            if agent_str.startswith("Agente"):
                                # Ya está en formato "AgenteNUM", extraer el número
                                agent_num = agent_str[6:]
                                normalized_id = f"Agente{agent_num}"
                            elif agent_str.isdigit():
                                # Es solo un número, añadir prefijo
                                normalized_id = f"Agente{agent_str}"
                            else:
                                # Otro formato, mantener como está
                                normalized_id = agent_str
                            
                            # Añadir solo si es único
                            if normalized_id not in unique_agent_ids:
                                unique_agent_ids.add(normalized_id)
                                normalized_agents.append(normalized_id)
                        
                        # Actualizar valores seleccionados en sesión
                        st.session_state.selected_agents = normalized_agents
                        st.session_state.selected_subjects = selected_subjects
                        
                        # Resetear el estado de network_data para forzar su recálculo
                        st.session_state.network_data = None
                        
                        # Filtrar datos usando la función mejorada de data_processing.py
                        filtered_data = filter_dataframe(
                            st.session_state.data.copy(),  # Enviamos una copia para mayor seguridad
                            st.session_state.agent_subject_mapping,
                            normalized_agents,  # Usar los agentes normalizados
                            st.session_state.selected_subjects
                        )
                        
                        # Verificar que el DataFrame resultante tiene índice único
                        if not filtered_data.empty and filtered_data.index.duplicated().any():
                            # Si hay duplicados, los eliminamos estableciendo un nuevo índice
                            filtered_data = filtered_data.reset_index(drop=True)
                        
                        # Almacenar los datos filtrados
                        st.session_state.filtered_data = filtered_data
                        st.session_state.filters_applied = True
                        
                        # Ejecutar análisis de riesgo solo si hay datos
                        if not filtered_data.empty:
                            # Realizar análisis de riesgo con datos reales, sin valores ficticios
                            try:
                                risk_scores, risk_details = run_risk_analysis(filtered_data)
                                
                                # Asegurar que todos los indicadores del 1-20 estén presentes
                                for i in range(1, 21):
                                    indicator_id = str(i)
                                    if indicator_id not in risk_scores:
                                        # Si no existe el indicador, asignar valor por defecto (1 = riesgo bajo)
                                        risk_scores[indicator_id] = 1
                                    
                                    # También asegurar que risk_details tenga entrada para este indicador
                                    if indicator_id not in risk_details:
                                        # Inicializar con DataFrame vacío
                                        risk_details[indicator_id] = pd.DataFrame(columns=['NUMERO_TRANSACCION', 'Motivo_Riesgo'])
                            except Exception as e:
                                st.error(f"Error en el análisis de riesgo: {str(e)}")
                                risk_scores = {}
                                risk_details = {}
                                # Inicializar con valores predeterminados en caso de error
                                for i in range(1, 21):
                                    risk_scores[str(i)] = 1
                            
                            st.session_state.risk_scores = risk_scores
                            st.session_state.risk_details = risk_details
                            
                            # Mostrar resumen de resultados
                            st.success(f"Filtros aplicados correctamente: {len(filtered_data)} transacciones encontradas")
                            
                            # Visualizar resumen de datos
                            col1, col2 = st.columns(2)
                            # Importar la función de formato español
                            from utils.visualizations import format_es
                            
                            with col1:
                                # Total transacciones con formato separador de miles
                                total_trans = len(filtered_data)
                                formatted_trans = format_es(total_trans, 0)
                                st.metric("Total de transacciones", formatted_trans)
                            
                            with col2:
                                if "IMPORTE" in filtered_data.columns:
                                    total_amount = filtered_data["IMPORTE"].sum()
                                    formatted_amount = format_es(total_amount, 2)
                                    st.metric("Importe total", f"{formatted_amount} €")
                            
                            # Recargar la página para actualizar todas las pestañas
                            st.rerun()
                        else:
                            # No hay datos después del filtrado
                            st.warning("No se encontraron datos con los filtros aplicados")
                            
                            # Reiniciar estados de análisis
                            st.session_state.risk_scores = None
                            st.session_state.risk_details = None
                            st.session_state.network_data = None
                    
                    except Exception as e:
                        # Capturar y mostrar errores de forma detallada
                        st.error(f"Error al aplicar filtros: {str(e)}")
                        import traceback
                        st.code(traceback.format_exc(), language="python")

# Main content area
if st.session_state.data is None:
    # Mostrar página de bienvenida con información sobre la aplicación
    st.header("Trabajo Final de Grado - UOC - Guadalupe Borreguero")
    
    st.markdown("""
    ### Descripción General
    
    Esta aplicación está diseñada para ayudar a identificar patrones y transacciones sospechosas 
    que podrían estar relacionadas con actividades de blanqueo de capitales. El sistema analiza datos 
    de transacciones financieras utilizando 20 indicadores de riesgo agrupados en 4 categorías.
    
    ### Instrucciones de Uso
    
    1. **Carga de Datos**: Sube tus archivos CSV con datos de transacciones utilizando el panel de la izquierda.
    2. **Filtrado**: Selecciona los agentes y sujetos obligados que deseas analizar.
    3. **Análisis**: Explora los diferentes tipos de análisis disponibles en las pestañas:
       - **Análisis de Datos**: Visualizaciones y estadísticas generales de las transacciones
       - **Análisis de Riesgo**: Puntuaciones de riesgo para cada indicador
       - **Análisis de Red**: Visualización de relaciones entre ordenantes y beneficiarios
       - **Reportes**: Generación de informes detallados sobre operaciones sospechosas
    
    ### Indicadores de Riesgo
    
    El sistema evalúa 20 indicadores organizados en las siguientes categorías:
    
    - **DOCUMENTACIÓN**: Análisis de documentos de identidad y nombres de clientes
    - **UMBRALES**: Patrones sospechosos en los importes y características de las transacciones
    - **GEOGRÁFICO**: Riesgos relacionados con países de origen, destino y jurisdicciones
    - **OUTLIERS**: Comportamientos anómalos y desviaciones del perfil habitual
    
    ### Comenzar
    
    Para empezar, sube los archivos CSV de transacciones utilizando el panel de la izquierda 
    y aplica los filtros deseados.
    """)
    
    # Texto explicativo adicional en lugar de imagen
    st.info("Carga archivos CSV para comenzar el análisis. La aplicación procesará los datos y generará visualizaciones interactivas para identificar patrones de riesgo.")

else:
    # Si ya hay datos cargados, mostrar el contenido en pestañas
    # Se ha eliminado la pestaña "Configuración" por solicitud del usuario
    tab1, tab2, tab3, tab4 = st.tabs([
        "Análisis de Datos", 
        "Análisis de Riesgo", 
        "Análisis de Red", 
        "Reportes"
    ])
    
    # Contenido principal de cada pestaña
    with tab1:
        if st.session_state.filtered_data is not None:
            st.header("Análisis de Datos de Transacciones")
            
            # Get the filtered data
            df = st.session_state.filtered_data
            
            # Summary metrics
            col1, col2, col3, col4 = st.columns(4)
            
            # Importar la función de formato español
            from utils.visualizations import format_es
            
            with col1:
                total_amount = df['IMPORTE'].sum()
                st.metric("Importe Total Enviado (€)", f"{format_es(total_amount, 2)}")
            
            with col2:
                avg_amount = df['IMPORTE'].mean()
                st.metric("Importe Promedio (€)", f"{format_es(avg_amount, 2)}")
            
            with col3:
                unique_senders = df['NUM_DOC_ORDENANTE'].nunique()
                st.metric("Ordenantes Únicos", format_es(unique_senders, 0))
            
            with col4:
                # Define a unique beneficiary by name and both surnames
                df['BENEFICIARY_ID'] = df['NOMBRE_BENEFICIARIO'] + ' ' + df['APELLIDO_BENEFICIARIO'] + ' ' + df['SEGUNDO_APELLIDO_BENEFICIARIO']
                unique_beneficiaries = df['BENEFICIARY_ID'].nunique()
                st.metric("Beneficiarios Únicos", format_es(unique_beneficiaries, 0))
                
            # Tabla de estadísticas descriptivas
            st.subheader("Estadísticas Descriptivas")
            
            # Calcular estadísticas
            stats = df['IMPORTE'].describe(percentiles=[0.25, 0.5, 0.75])
            
            # Usar el formato español para todos los valores numéricos
            stats_df = pd.DataFrame({
                'Estadística': [
                    'Total Transacciones', 'Importe Total', 'Importe Medio', 'Importe Mediano', 
                    'Importe Mínimo', 'Importe Máximo', 'Primer Cuartil (25%)', 
                    'Tercer Cuartil (75%)', 'Desviación Estándar'
                ],
                'Valor': [
                    format_es(len(df), 0), 
                    f"{format_es(df['IMPORTE'].sum(), 2)} €", 
                    f"{format_es(df['IMPORTE'].mean(), 2)} €", 
                    f"{format_es(df['IMPORTE'].median(), 2)} €",
                    f"{format_es(df['IMPORTE'].min(), 2)} €", 
                    f"{format_es(df['IMPORTE'].max(), 2)} €", 
                    f"{format_es(stats['25%'], 2)} €", 
                    f"{format_es(stats['75%'], 2)} €", 
                    f"{format_es(df['IMPORTE'].std(), 2)} €"
                ]
            })
            
            st.table(stats_df)
            
            # Añadir opciones de filtrado adicionales
            st.header("Filtros Adicionales")
            
            col_filter1, col_filter2 = st.columns(2)
            
            with col_filter1:
                # Filtro por rango de importes
                min_amount = float(df['IMPORTE'].min())
                max_amount = float(df['IMPORTE'].max())
                selected_amount_range = st.slider(
                    "Rango de Importes (€)",
                    min_value=min_amount,
                    max_value=max_amount,
                    value=(min_amount, max_amount),
                    step=100.0
                )
            
            with col_filter2:
                # Filtro por países destino
                if 'PAIS_DESTINO' in df.columns:
                    available_countries = sorted(df['PAIS_DESTINO'].dropna().unique().tolist())
                    selected_countries = st.multiselect(
                        "Países de Destino",
                        options=available_countries,
                        default=available_countries[:5] if len(available_countries) > 5 else available_countries
                    )
                else:
                    selected_countries = []
            
            # Aplicar filtros adicionales
            df_filtered = df.copy()
            apply_filters = st.button("Aplicar Filtros Adicionales")
            if apply_filters:
                # Filtrar por rango de importes
                df_filtered = df_filtered[(df_filtered['IMPORTE'] >= selected_amount_range[0]) & 
                                        (df_filtered['IMPORTE'] <= selected_amount_range[1])]
                
                # Filtrar por países seleccionados si se han seleccionado algunos
                if selected_countries and 'PAIS_DESTINO' in df.columns:
                    df_filtered = df_filtered[df_filtered['PAIS_DESTINO'].isin(selected_countries)]
                
                # Actualizar DataFrame
                df = df_filtered
                formatted_count = format_es(len(df), 0)
                st.success(f"Filtros aplicados: {formatted_count} transacciones coinciden con los criterios")
            
            # Create two columns for charts
            st.header("Visualizaciones")
            col1, col2 = st.columns(2)
            
            with col1:
                # Mapa de calor por país de destino
                st.subheader("Mapa de Importes por País de Destino")
                fig_map = create_country_map(df, 'PAIS_DESTINO', 'IMPORTE')
                st.plotly_chart(fig_map, use_container_width=True)
                
                # Gráfico de barras de principales países destino por importe
                st.subheader("Top Países de Destino por Importe")
                fig_dest = create_destination_country_chart(df, top_n=10)
                st.plotly_chart(fig_dest, use_container_width=True)
                
                # Operation status chart
                st.subheader("Estado de Operaciones")
                fig_status = create_operation_status_chart(df)
                st.plotly_chart(fig_status, use_container_width=True)
            
            with col2:
                # Chart for sender document countries
                st.subheader("Países de Documento del Ordenante")
                if 'PAIS_DOC_ORDENANTE' in df.columns:
                    fig_doc = create_document_country_chart(df, 'pie')
                    st.plotly_chart(fig_doc, use_container_width=True)
                else:
                    st.warning("No se puede crear el gráfico: columna 'PAIS_DOC_ORDENANTE' no encontrada en los datos")
                    fig_doc = None
                
                # Añadir gráfico de transacción media por país
                st.subheader("Top 20 Países por Importe Medio de Transacción")
                fig_avg = create_average_transaction_by_country_chart(df, top_n=20)
                st.plotly_chart(fig_avg, use_container_width=True)
                
                # Amount over time chart
                st.subheader("Importes de Transacciones en el Tiempo")
                fig_time = create_amount_over_time_chart(df)
                st.plotly_chart(fig_time, use_container_width=True)
            
            # Diagrama Sankey mejorado limitado a 20 países principales
            st.subheader("Flujo de Transacciones: País del Documento → País de Destino (20 principales)")
            if 'PAIS_DOC_ORDENANTE' in df.columns:
                fig_sankey = create_sankey_diagram(
                    df, 
                    'PAIS_DOC_ORDENANTE', 
                    'PAIS_DESTINO', 
                    'IMPORTE',
                    max_nodes_per_side=20,
                    colorize=True
                )
                st.plotly_chart(fig_sankey, use_container_width=True)
            else:
                st.warning("No se puede crear el diagrama de Sankey: columna 'PAIS_DOC_ORDENANTE' no encontrada en los datos")
                fig_sankey = None
            
           
        else:
            st.info("Ejecuta el análisis aplicando filtros en la barra lateral para visualizar los datos")
    
    with tab2:
        if st.session_state.risk_scores is not None:
            st.header("Análisis de Riesgo de Blanqueo de Capitales")
            
            # Obtener datos de la sesión
            risk_scores = st.session_state.risk_scores
            risk_details = st.session_state.risk_details
            df = st.session_state.filtered_data
            
            # Asegurar que los 20 indicadores estén presentes con valores variados
            indicator_names = {
                "1": "Misma documentación en corto espacio de tiempo",
                "2": "Misma documentación con nombres diferentes",
                "3": "Documentación con formato alfanumérico erróneo",
                "4": "Operaciones para eludir umbrales (3.000€)",
                "5": "Operaciones fragmentadas por grupo de clientes",
                "6": "Uso sistemático de importes redondos",
                "7": "Numerosas cancelaciones de operaciones",
                "8": "Transferencias a países de alto riesgo",
                "9": "Operaciones no correspondientes al perfil habitual",
                "10": "Clientes que son personas políticamente expuestas",
                "11": "Variaciones en corredores del agente",
                "12": "Agente con volumen de operaciones mucho mayor",
                "13": "Agente no completa información correctamente",
                "14": "Agente con operaciones sobre media del municipio",
                "15": "Agente con aumento repentino de operaciones",
                "16": "Agente con operaciones sustanciales a destino",
                "17": "Agente concentrando operaciones en fechas/horas",
                "18": "Agente aparece como remitente de dinero",
                "19": "Agentes con remitentes de nacionalidad distinta",
                "20": "Agentes con datos repetitivos de cliente"
            }
            
            # Si risk_scores está vacío o no es un diccionario, inicializarlo con valores predeterminados
            if not risk_scores or not isinstance(risk_scores, dict):
                risk_scores = {}
                
            # Garantizar que todos los indicadores tengan un valor inicial
            for i in range(1, 21):
                indicator_id = str(i)
                if indicator_id not in risk_scores:
                    # Asignar valor por defecto (1 = riesgo bajo)
                    risk_scores[indicator_id] = 1
                elif not isinstance(risk_scores[indicator_id], (int, float)):
                    # Si el valor existente no es un número, reemplazarlo
                    try:
                        # Intentar convertir a número si es posible
                        risk_scores[indicator_id] = float(risk_scores[indicator_id])
                    except (ValueError, TypeError):
                        # Si la conversión falla, asignar un valor por defecto
                        risk_scores[indicator_id] = 1
            
            # Overall risk score
            total_risk = round(calculate_total_risk_score(risk_scores),2)

            # Create gauge chart for total risk
            col1, col2 = st.columns([1, 2])
            
            with col1:
                st.subheader("Puntuación de Riesgo Global")
                
                # Create a gauge chart
                fig = go.Figure(go.Indicator(
                    mode="gauge+number",
                    value=total_risk,
                    domain={'x': [0, 1], 'y': [0, 1]},
                    title={'text': "Nivel de Riesgo"},
                    gauge={
                        'axis': {'range': [0, 4], 'tickwidth': 1, 'tickcolor': "darkblue"},
                        'bar': {'color': "darkblue"},
                        'bgcolor': "white",
                        'borderwidth': 2,
                        'bordercolor': "gray",
                        'steps': [
                            {'range': [0, 1.5], 'color': 'green'},
                            {'range': [1.5, 2.5], 'color': 'yellow'},
                            {'range': [2.5, 3.5], 'color': 'orange'},
                            {'range': [3.5, 4], 'color': 'red'}
                        ],
                    }
                ))
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Risk level interpretation (escala 1-4)
                if total_risk < 1.5:
                    st.success("Nivel de Riesgo Bajo")
                elif total_risk < 2.5:
                    st.info("Nivel de Riesgo Medio")
                elif total_risk < 3.5:
                    st.warning("Nivel de Riesgo Alto")
                else:
                    st.error("Nivel de Riesgo Muy Alto")
            
            with col2:
                # Risk by type
                st.subheader("Riesgo por Tipo")
                
                # Calculate risk by type
                risk_by_type = {}
                weights_by_type = {}
                
                for indicator_id, score in risk_scores.items():
                    ind_type = indicator_types.get(indicator_id, "OTHER")
                    weight = float(indicator_descriptions[indicator_id]["weight"].strip('%')) / 100
                    
                    if ind_type not in risk_by_type:
                        risk_by_type[ind_type] = 0
                        weights_by_type[ind_type] = 0
                    
                    # Convertir score a número de manera segura
                    try:
                        # Si es una lista, tupla u otra secuencia, tomar el primer elemento
                        if isinstance(score, (list, tuple)):
                            if len(score) > 0:
                                numeric_score = float(score[0])
                            else:
                                numeric_score = 1.0  # Valor predeterminado si la lista está vacía
                        else:
                            numeric_score = float(score)
                    except (ValueError, TypeError):
                        # Si no se puede convertir, usamos 1.0 (riesgo bajo)
                        print(f"Error al convertir score del indicador {indicator_id} a número. Usando valor predeterminado.")
                        numeric_score = 1.0
                    
                    risk_by_type[ind_type] += numeric_score * weight
                    weights_by_type[ind_type] += weight
                
                # Normalize by weights
                for ind_type in risk_by_type:
                    if weights_by_type[ind_type] > 0:
                        risk_by_type[ind_type] /= weights_by_type[ind_type]
                
                # Create radar chart for risk by type
                fig = create_risk_radar_chart(risk_by_type)
                st.plotly_chart(fig, use_container_width=True)
            
           
            
            # Añadir tabla con indicadores individuales
            st.subheader("Tabla de Indicadores por Nivel de Riesgo")
            
            # Importar las funciones de la implementación fija
            from utils.fixed_risk_indicators import calcular_riesgos_por_agente, calcular_riesgo_promedio, formatear_valor_riesgo
            from utils.indicadores.riesgo import obtener_nivel_riesgo
            
            # Obtener lista de agentes seleccionados
            selected_agents = []
            if hasattr(st.session_state, 'selected_agents') and st.session_state.selected_agents:
                selected_agents = st.session_state.selected_agents
            
            # Calcular los riesgos por agente utilizando el nuevo enfoque - ÚNICAMENTE DATOS REALES
            riesgos_individuales, resultados_por_tipo, operaciones_sospechosas = calcular_riesgos_por_agente(
                df, selected_agents
            )
            
            # Calcular el promedio de riesgo para cada indicador
            avg_risk_scores = calcular_riesgo_promedio(riesgos_individuales)
            
            # Preparar datos para la tabla
            table_data = []
            
            # Usar estos promedios para la tabla
            for indicator_id, risk_score in avg_risk_scores.items():
                # Convertir id a string para ser compatible con indicator_types
                indicator_id_str = str(indicator_id)
                indicator_type = indicator_types.get(indicator_id_str, "No clasificado")
                
                # Obtener nombre y peso del indicador
                if indicator_id_str in indicator_descriptions:
                    indicator_name = indicator_descriptions[indicator_id_str].get("description", "")
                    weight = indicator_descriptions[indicator_id_str].get("weight", "N/A")
                else:
                    indicator_name = f"Indicador {indicator_id}"
                    weight = "N/A"
                
                # Determinar el nivel de riesgo
                risk_level = obtener_nivel_riesgo(risk_score)
                
                # Añadir a la tabla
                table_data.append({
                    "ID": indicator_id_str,
                    "Indicador": indicator_name,
                    "Tipo": indicator_type,
                    "Puntuación": risk_score,
                    "Nivel": risk_level,
                    "Peso": weight
                })
            
            # Convertir a DataFrame para la visualización en tabla
            indicators_df = pd.DataFrame(table_data)
            
            # Agregar estilo a la tabla según el nivel de riesgo
            def highlight_risk(val):
                if val == "MUY ALTO":
                    return "background-color: #ff9999; font-weight: bold"
                elif val == "ALTO":
                    return "background-color: #ffcccc; font-weight: bold"
                elif val == "MEDIO":
                    return "background-color: #fff2cc"
                else:
                    return "background-color: #ccffcc"
            
            # Calcular el riesgo global
            global_risk_score = 0
            global_weight_sum = 0
            
            for row in table_data:
                try:
                    weight_str = row["Peso"].strip('%')
                    weight = float(weight_str) / 100
                    global_risk_score += row["Puntuación"] * weight
                    global_weight_sum += weight
                except (ValueError, TypeError, AttributeError):
                    # Si el peso no se puede convertir a número, asignar un peso predeterminado
                    pass
            
            # Normalizar el riesgo global
            if global_weight_sum > 0:
                global_risk_score /= global_weight_sum
            
            # Determinar el nivel de riesgo global
            global_risk_level = obtener_nivel_riesgo(global_risk_score)
            
            # Mostrar el riesgo global
            st.markdown(f"### Riesgo Medio de los Agentes filtrados : {formatear_valor_riesgo(global_risk_score)} - {global_risk_level}")
            
            # Crear una barra de progreso para visualizar el riesgo global
            risk_color = "#ccffcc"  # Verde para riesgo bajo
            if global_risk_level == "MEDIO":
                risk_color = "#fff2cc"  # Amarillo para riesgo medio
            elif global_risk_level == "ALTO":
                risk_color = "#ffcccc"  # Naranja para riesgo alto
            elif global_risk_level == "MUY ALTO":
                risk_color = "#ff9999"  # Rojo para riesgo muy alto
            
            # Calcular el porcentaje para la barra de progreso (0 a 100%)
            risk_percent = (global_risk_score - 1) / 3 * 100  # Rango 1-4 convertido a 0-100%
            
            # Crear una barra de progreso HTML personalizada
            st.markdown(
                f"""
                <div style="margin-bottom: 20px;">
                    <div style="width: 100%; background-color: #f1f1f1; border-radius: 5px;">
                        <div style="width: {risk_percent}%; height: 30px; background-color: {risk_color}; 
                            border-radius: 5px; text-align: center; line-height: 30px; color: #333; font-weight: bold;">
                            {global_risk_level}
                        </div>
                    </div>
                </div>
                """, 
                unsafe_allow_html=True
            )
            
            # Ordenar por puntuación descendente - con manejo de errores
            try:
                # Verificar que la columna existe antes de ordenar
                if "Puntuación" in indicators_df.columns:
                    indicators_df = indicators_df.sort_values(by=["Puntuación"], ascending=False)
                else:
                    # Usar ID como alternativa si Puntuación no existe
                    print("ADVERTENCIA: Columna 'Puntuación' no encontrada para ordenar, usando 'ID'")
                    indicators_df = indicators_df.sort_values(by=["ID"])
            except Exception as e:
                print(f"Error al ordenar DataFrame de indicadores: {str(e)}")
                # No ordenar si hay error
            
            # Mostrar tabla con estilo y filtros interactivos
            st.dataframe(
                indicators_df,
                use_container_width=True,
                column_config={
                    "Puntuación": st.column_config.NumberColumn(
                        "Puntuación",
                        help="Valor de 1 a 4 que representa el nivel de riesgo",
                        format="%.2f"
                    ),
                    "Nivel": st.column_config.Column(
                        "Nivel de Riesgo",
                        help="Clasificación de riesgo en categorías",
                        width="medium"
                    )
                },
                hide_index=True
            )
            
            # Botón para descargar la tabla de indicadores en CSV con formato UTF-8-BOM
            csv_data = '\ufeff' + indicators_df.to_csv(index=False, encoding='utf-8-sig', float_format='%.2f')
            st.download_button(
                label="Descargar Tabla de Indicadores (CSV)",
                data=csv_data,
                file_name="tabla_indicadores_riesgo.csv",
                mime="text/csv;charset=utf-8-sig",
                help="Descargar la tabla de indicadores de riesgo en formato CSV"
            )
            
            # Añadir botón para descargar informe PDF que sea EXACTAMENTE IGUAL que el CSV (con datos globales)
            if st.button("Generar Informe PDF de Indicadores", key="pdf_report_button"):
                with st.spinner("Generando informe PDF de indicadores..."):
                    try:
                        # Usar los mismos datos que aparecen en la tabla de indicadores (CSV)
                        from utils.pdf_generator import generate_indicators_pdf
                        
                        # Usar el DataFrame de indicadores que ya hemos creado para la tabla
                        pdf_data = generate_indicators_pdf(
                            indicators_df,  # Este DataFrame tiene el mismo formato que el CSV
                            "Informe de Indicadores de Riesgo",
                            indicator_descriptions,
                            indicator_types
                        )
                        
                        # Display download link
                        st.markdown(
                            get_download_link(pdf_data, "informe_indicadores_riesgo.pdf"),
                            unsafe_allow_html=True
                        )
                        st.success("Informe PDF generado correctamente. Haz clic en el enlace para descargar.")
                    except Exception as e:
                        st.error(f"Error al generar el informe PDF: {str(e)}")
                        import traceback
                        st.code(traceback.format_exc(), language="python")
            
            # Risk details for each indicator
            st.subheader("Hallazgos Detallados de Riesgo")
            
            # Layout mejorado con tarjetas usando flexbox y diseño más claro
            NUM_COLS = 2  # Número de columnas para los indicadores
            
            # Asegurar que cada indicador aparezca solo una vez
            processed_indicators = set()
            unique_indicators = []
            
            for indicator_id, details in risk_details.items():
                if indicator_id not in processed_indicators:
                    unique_indicators.append((indicator_id, details))
                    processed_indicators.add(indicator_id)
            
            # Crear filas de tarjetas para cada grupo de indicadores
            for i in range(0, len(unique_indicators), NUM_COLS):
                # Crear columnas para esta fila
                cols = st.columns(NUM_COLS)
                
                # Procesar cada indicador en esta fila
                for j in range(NUM_COLS):
                    idx = i + j
                    # Verificar que no nos pasemos del límite de indicadores
                    if idx < len(unique_indicators):
                        indicator_id, details = unique_indicators[idx]
                        
                        # Trabajar en la columna correspondiente
                        with cols[j]:
                            # Crear un contenedor con borde para cada indicador
                            st.markdown(f"""
                            <div style="border: 1px solid #ddd; border-radius: 8px; padding: 15px; margin-bottom: 20px;">
                                <h3 style="border-bottom: 1px solid #eee; padding-bottom: 10px; margin-bottom: 15px;">
                                    Indicador {indicator_id}: {indicator_names[indicator_id]}
                                </h3>
                            """, unsafe_allow_html=True)
                            
                            # Visualización del nivel de riesgo - usar promedio calculado si hay datos por agente
                            if 'avg_risk_scores' in locals() and indicator_id in avg_risk_scores:
                                try:
                                    risk_score_value = avg_risk_scores[indicator_id]
                                    # Si es una secuencia, tomar el primer elemento
                                    if isinstance(risk_score_value, (list, tuple)):
                                        if len(risk_score_value) > 0:
                                            risk_level = float(risk_score_value[0])
                                        else:
                                            risk_level = 1.0  # Valor predeterminado si la lista está vacía
                                    else:
                                        risk_level = float(risk_score_value)
                                except (ValueError, TypeError):
                                    risk_level = 1.0  # Valor predeterminado si hay error en la conversión
                            elif indicator_id in risk_scores:
                                try:
                                    risk_score_value = risk_scores[indicator_id]
                                    # Si es una secuencia, tomar el primer elemento
                                    if isinstance(risk_score_value, (list, tuple)):
                                        if len(risk_score_value) > 0:
                                            risk_level = float(risk_score_value[0])
                                        else:
                                            risk_level = 1.0  # Valor predeterminado si la lista está vacía
                                    else:
                                        risk_level = float(risk_score_value)
                                except (ValueError, TypeError):
                                    risk_level = 1.0  # Valor predeterminado si hay error en la conversión
                            else:
                                # Valor predeterminado si no existe el indicador
                                risk_level = 1.0  # Riesgo bajo por defecto
                            
                            # Usar función de formateo de nuestra implementación fija
                            risk_level_display = formatear_valor_riesgo(risk_level)
                                
                            # Determinar nivel y color (escala 1-4)
                            if risk_level < 1.5:
                                color = "green"
                                nivel = "BAJO"
                                emoji = "🟢"
                            elif risk_level < 2.5:
                                color = "yellow"
                                nivel = "MEDIO"
                                emoji = "🟡"
                            elif risk_level < 3.5:
                                color = "orange"
                                nivel = "ALTO"
                                emoji = "🟠"
                            else:
                                color = "red"
                                nivel = "MUY ALTO"
                                emoji = "🔴"
                            
                            # HTML para visualizar el nivel de riesgo de manera más atractiva
                            st.markdown(f"""
                            <div style="display: flex; align-items: center; margin-bottom: 15px; background-color: #f9f9f9; padding: 10px; border-radius: 5px;">
                                <div style="font-size: 28px; margin-right: 12px;">{emoji}</div>
                                <div>
                                    <div style="font-size: 16px; font-weight: bold;">Nivel de Riesgo: {nivel}</div>
                                    <div style="font-size: 20px; font-weight: bold; color: {color};">{risk_level_display}/4</div>
                                </div>
                            </div>
                            
                            <div style="margin-bottom: 15px;">
                                <div><strong>Peso:</strong> {indicator_descriptions[indicator_id]['weight']}</div>
                                <div><strong>Tipo:</strong> {indicator_types[indicator_id]}</div>
                            </div>
                            """, unsafe_allow_html=True)
                            
    
                            # Mostrar los resultados según el tipo de datos
                            if isinstance(details, pd.DataFrame) and not details.empty:
                                # Para DataFrames - Mostrar tabla de transacciones
                                st.markdown("<div style='font-weight: bold; margin-top: 10px;'>Transacciones Detectadas:</div>", unsafe_allow_html=True)
                                
                                # Formatear el DataFrame para mejor visualización
                                df_styled = details.copy()
                                
                                # Asegurar que usamos datos reales para las transacciones
                                if 'NUMERO_TRANSACCION' in df_styled.columns and 'filtered_data' in st.session_state:
                                    # Obtener IDs de transacciones del dataframe de detalles
                                    trans_ids = df_styled['NUMERO_TRANSACCION'].astype(str).unique()
                                    
                                    # Enriquecer con datos completos de las transacciones originales
                                    if len(trans_ids) > 0:
                                        real_transactions = st.session_state.filtered_data[
                                            st.session_state.filtered_data['NUMERO_TRANSACCION'].astype(str).isin(trans_ids)
                                        ]
                                        
                                        # Si encontramos transacciones reales, enriquecer con columnas clave
                                        if not real_transactions.empty:
                                            # Preservar el motivo de riesgo de los detalles originales si existe
                                            if 'Motivo_Riesgo' in df_styled.columns:
                                                motivos = df_styled.set_index('NUMERO_TRANSACCION')['Motivo_Riesgo'].to_dict()
                                                enhanced_df = real_transactions.copy()
                                                enhanced_df['Motivo_Riesgo'] = enhanced_df['NUMERO_TRANSACCION'].astype(str).map(
                                                    lambda x: motivos.get(x, "")
                                                )
                                                df_styled = enhanced_df
                                                
                                                # Reordenar columnas para mejor visualización
                                                cols_order = ['NUMERO_TRANSACCION', 'FECHA', 'IMPORTE', 'NOMBRE_ORDENANTE', 
                                                              'APELLIDO_ORDENANTE', 'NUM_DOC_ORDENANTE', 'PAIS_DOC_ORDENANTE',
                                                              'NOMBRE_BENEFICIARIO', 'APELLIDO_BENEFICIARIO', 'PAIS_DESTINO',
                                                              'Motivo_Riesgo']
                                                
                                                # Usar solo columnas existentes
                                                existing_cols = [col for col in cols_order if col in df_styled.columns]
                                                other_cols = [col for col in df_styled.columns if col not in cols_order]
                                                df_styled = df_styled[existing_cols + other_cols]
                                
                                # Crear columna de prioridad si no existe
                                if 'Prioridad' not in df_styled.columns:
                                    df_styled['Prioridad'] = "ALTA"
                                
                                # Mostrar dataframe con estilo configurable
                                st.dataframe(
                                    df_styled,
                                    use_container_width=True,
                                    column_config={
                                        "Prioridad": st.column_config.SelectboxColumn(
                                            "Prioridad",
                                            help="Nivel de prioridad para revisión",
                                            width="medium",
                                            options=["ALTA", "MEDIA", "BAJA"],
                                            default="ALTA",
                                        )
                                    }
                                )
                                
                                # Opciones de descarga con codificación UTF-8-BOM para Excel (mejor soporte para caracteres españoles)
                                csv_data = '\ufeff' + df_styled.to_csv(index=False, encoding='utf-8-sig')
                                st.download_button(
                                    label=f"Descargar Transacciones Indicador {indicator_id} (CSV)",
                                    data=csv_data,
                                    file_name=f"indicador_{indicator_id}_transacciones_sospechosas.csv",
                                    mime="text/csv;charset=utf-8-sig",
                                    key=f"download_ind_{indicator_id}"
                                )
                            elif isinstance(details, dict) and details:
                                # Para diccionarios - Mostrar pares clave/valor
                                st.markdown("<div style='font-weight: bold; margin-top: 10px;'>Detalles del Indicador:</div>", unsafe_allow_html=True)
                                for key, value in details.items():
                                    st.write(f"**{key}**: {value}")
                            else:
                                # Caso de no hay datos específicos
                                st.info("No hay transacciones específicas detectadas para este indicador.")
                            
                            # Cerrar div del contenedor al final
                            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.info("Ejecuta el análisis de riesgo aplicando filtros en la barra lateral")
    
    with tab3:
        # Verificamos si hay datos filtrados disponibles
        if 'filtered_data' not in st.session_state or st.session_state.filtered_data is None or st.session_state.filtered_data.empty:
            st.info("Carga archivos CSV y aplica filtros para visualizar el análisis de red.")
        # Si hay datos filtrados pero no hay datos de red, los generamos
        elif 'network_data' not in st.session_state or st.session_state.network_data is None:
            st.header("Análisis de Red de Transacciones")
            
            with st.spinner("Generando datos de red iniciales..."):
                try:
                    # Generate network data with default settings
                    df = st.session_state.filtered_data 
                    min_transaction_value = float(df['IMPORTE'].min())
                    
                    # Usar modularidad por defecto o el método elegido por el usuario
                    community_method = 'modularity'  # Método por defecto
                    if 'community_method' in st.session_state:
                        community_method = st.session_state.community_method
                    
                    # Guardar el método seleccionado para uso posterior
                    st.session_state.community_method = community_method
                    
                    # Generar network data con detección de comunidades
                    st.session_state.network_data = create_transaction_graph(
                        df, 
                        min_transaction_value,
                        community_method=community_method
                    )
                    
                    # Mostrar y actualizar
                    st.success("Datos de red generados correctamente")
                    if st.button("Mostrar Visualización de Red", key="show_network_button"):
                        st.rerun()
                except Exception as e:
                    st.error(f"Error al generar los datos de red: {str(e)}")
                    import traceback
                    st.error(traceback.format_exc())
        # Si ya tenemos datos de red, mostramos la interfaz completa
        else:
            st.header("Análisis de Red de Transacciones")
            
            try:
                graph_data = st.session_state.network_data
                df = st.session_state.filtered_data
                
                # Network options
                st.subheader("Filtros de Red")
                
                # Fila 1: Filtros de importe
                filter_row1 = st.columns(2)
                
                with filter_row1[0]:
                    try:
                        min_value = float(df['IMPORTE'].min())
                        max_value = float(df['IMPORTE'].max())
                    except Exception:
                        min_value = 0.0
                        max_value = 5000.0
                    
                    # Filtro por rango de importes
                    transaction_range = st.slider(
                        "Rango de Importes (€)",
                        min_value=min_value,
                        max_value=max_value,
                        value=(min_value, max_value),  # Rango completo por defecto
                        step=10.0
                    )
                    min_transaction_value = transaction_range[0]
                    max_transaction_value = transaction_range[1]
                
                with filter_row1[1]:
                    # Número mínimo de transacciones dirigidas a un mismo beneficiario
                    min_transactions_to_beneficiary = st.slider(
                        "Mínimo de Transacciones a un Mismo Beneficiario",
                        min_value=1,
                        max_value=20,
                        value=1,
                        step=1
                    )
                
                # Fila 2: Filtros de países
                filter_row2 = st.columns(2)
                
                with filter_row2[0]:
                    # Obtener países destino únicos
                    destination_countries = df['PAIS_DESTINO'].dropna().unique().tolist()
                    destination_countries.sort()
                    
                    # Filtro por países destino
                    selected_destination_countries = st.multiselect(
                        "Filtrar por Países Destino",
                        options=destination_countries,
                        default=None
                    )
                
                with filter_row2[1]:
                    # Obtener países del documento del ordenante únicos
                    document_countries = df['PAIS_DOC_ORDENANTE'].dropna().unique().tolist()
                    document_countries.sort()
                    
                    # Filtro por países del documento del ordenante
                    selected_document_countries = st.multiselect(
                        "Filtrar por Países del Documento del Ordenante",
                        options=document_countries,
                        default=None
                    )
                
                # Fila 3: Filtros para comunidades y opciones de visualización
                filter_row3 = st.columns(2)
                
                with filter_row3[0]:
                    # Métodos de detección de comunidades
                    community_method = st.selectbox(
                        "Método de Detección de Comunidades",
                        options=[
                            "modularity", 
                            "label_propagation", 
                            "girvan_newman"
                        ],
                        format_func=lambda x: {
                            "modularity": "Modularidad (Mejor equilibrio)",
                            "label_propagation": "Propagación de Etiquetas (Rápido)",
                            "girvan_newman": "Girvan-Newman (Detallado)"
                        }.get(x, x),
                        index=0,
                        help="Algoritmo usado para detectar comunidades en la red"
                    )
                
                with filter_row3[1]:
                    # Opciones de visualización
                    color_by = st.selectbox(
                        "Colorear nodos por:",
                        options=["País", "Tipo", "Grupo/Comunidad"],
                        index=0,
                        help="Criterio para colorear los nodos en la visualización"
                    )
                    
                # Fila 4: Filtros adicionales de visualización
                filter_row4 = st.columns(1)
                
                with filter_row4[0]:
                    max_nodes = st.slider(
                        "Número Máximo de Nodos a Mostrar",
                        min_value=10,
                        max_value=500,
                        value=50,
                        help="Limita el número de nodos visibles en la visualización para mejorar el rendimiento"
                    )
                
                # Display network visualization
                st.subheader("Red de Transacciones")
                st.markdown("""
                Este gráfico muestra las conexiones entre ordenantes y beneficiarios. 
                Cada nodo representa una persona y cada conexión representa transacciones entre ellos.
                """)
                
                # Calcular la red con los filtros cuando el usuario hace click en el botón
                if st.button("Actualizar Visualización", key="update_network_button"):
                    with st.spinner("Recalculando red..."):
                        # Filtrar por rango de importes
                        filtered_transactions = df[(df['IMPORTE'] >= min_transaction_value) & 
                                                 (df['IMPORTE'] <= max_transaction_value)]
                        
                        if filtered_transactions.empty:
                            st.warning("No hay transacciones que cumplan con los criterios de filtro.")
                            filtered_graph_data = {'nodes': [], 'edges': []}
                        else:
                            # Filtrar por número mínimo de transacciones a un mismo beneficiario
                            if min_transactions_to_beneficiary > 1:
                                # Contar transacciones por beneficiario
                                beneficiary_counts = filtered_transactions.groupby(
                                    ['NOMBRE_BENEFICIARIO', 'APELLIDO_BENEFICIARIO']
                                ).size().reset_index(name='count')
                                
                                # Filtrar beneficiarios con suficientes transacciones
                                beneficiaries_with_min_trans = beneficiary_counts[
                                    beneficiary_counts['count'] >= min_transactions_to_beneficiary
                                ]
                                
                                if beneficiaries_with_min_trans.empty:
                                    st.warning("No hay beneficiarios que reciban el mínimo de transacciones especificado.")
                                    filtered_graph_data = {'nodes': [], 'edges': []}
                                else:
                                    # Crear una máscara para filtrar transacciones
                                    filtered_beneficiaries = set(
                                        zip(beneficiaries_with_min_trans['NOMBRE_BENEFICIARIO'], 
                                            beneficiaries_with_min_trans['APELLIDO_BENEFICIARIO'])
                                    )
                                    
                                    # Función para verificar si un beneficiario está en la lista filtrada
                                    def is_filtered_beneficiary(row):
                                        return (row['NOMBRE_BENEFICIARIO'], row['APELLIDO_BENEFICIARIO']) in filtered_beneficiaries
                                    
                                    # Aplicar el filtro
                                    filtered_transactions = filtered_transactions[
                                        filtered_transactions.apply(is_filtered_beneficiary, axis=1)
                                    ]
                            
                            # Generate network data con las transacciones filtradas
                            filtered_graph_data = create_transaction_graph(
                                filtered_transactions, 
                                min_amount=min_transaction_value,
                                destination_countries=selected_destination_countries if selected_destination_countries else None,
                                document_countries=selected_document_countries if selected_document_countries else None,
                                community_method=community_method
                            )
                            
                            # Identificar posibles tramas (patrones de smurfing/estructuración)
                            try:
                                from utils.pattern_detection import identify_smurfing_patterns
                                smurfing_patterns = identify_smurfing_patterns(filtered_transactions)
                                
                                # Guardar patrones en session_state para mostrarlos luego
                                st.session_state.smurfing_patterns = smurfing_patterns
                                
                                # Si hay patrones, colorear los nodos involucrados
                                if not isinstance(smurfing_patterns, dict) or not smurfing_patterns.get("error"):
                                    # Obtener todas las transacciones involucradas en patrones
                                    pattern_transactions = set()
                                    
                                    # Múltiples remitentes al mismo beneficiario
                                    for pattern in smurfing_patterns.get("multiple_senders_same_beneficiary", []):
                                        pattern_transactions.update(pattern.get("transactions", []))
                                    
                                    # Transacciones estructuradas
                                    for pattern in smurfing_patterns.get("structured_transactions", []):
                                        pattern_transactions.update(pattern.get("transactions", []))
                                    
                                    # Transacciones frecuentes de pequeños importes
                                    for pattern in smurfing_patterns.get("frequent_small_amounts", []):
                                        pattern_transactions.update(pattern.get("transactions", []))
                                    
                                    # Marcar nodos involucrados en patrones
                                    for node in filtered_graph_data['nodes']:
                                        if 'transactions_ids' in node:
                                            # Convertir a strings para comparar
                                            node_trans_ids = [str(tx_id) for tx_id in node.get('transactions_ids', [])]
                                            
                                            # Si hay intersección con pattern_transactions, marcar el nodo
                                            if set(node_trans_ids) & set(map(str, pattern_transactions)):
                                                node['in_pattern'] = True
                                                # Asignar color más llamativo si está en un patrón
                                                if node['type'] == 'sender':
                                                    node['pattern_color'] = "#ff0000"  # Rojo para ordenantes en patrones
                                                else:
                                                    node['pattern_color'] = "#ff6600"  # Naranja para beneficiarios en patrones
                            except Exception as e:
                                st.warning(f"No se pudieron detectar patrones de estructuración: {str(e)}")
                        
                        # Limitar el número de nodos si es necesario
                        if not filtered_transactions.empty and max_nodes and max_nodes > 0 and len(filtered_graph_data['nodes']) > max_nodes:
                            # Ordenar por valor (importe) descendente
                            sorted_nodes = sorted(filtered_graph_data['nodes'], key=lambda x: x.get('value', 0), reverse=True)
                            # Tomar solo los primeros max_nodes
                            selected_node_ids = [node['id'] for node in sorted_nodes[:max_nodes]]
                            # Filtrar nodos
                            filtered_graph_data['nodes'] = [node for node in filtered_graph_data['nodes'] if node['id'] in selected_node_ids]
                            # Filtrar aristas que conectan a estos nodos
                            filtered_graph_data['edges'] = [edge for edge in filtered_graph_data['edges'] 
                                                        if edge['source'] in selected_node_ids and edge['target'] in selected_node_ids]
                        
                        # Actualizar datos en session state
                        st.session_state.network_data = filtered_graph_data
                        st.success("Visualización actualizada")
                        st.rerun()
                
                # Usamos los datos existentes para visualizar
                filtered_graph_data = st.session_state.network_data
            except Exception as e:
                st.error(f"Error al procesar los datos de red: {str(e)}")
                import traceback
                st.error(traceback.format_exc())
                filtered_graph_data = {'nodes': [], 'edges': []}
            
            # Ajustar colores según la selección
            for node in filtered_graph_data['nodes']:
                if color_by == "País":
                    # Ya está configurado por defecto
                    pass
                elif color_by == "Tipo":
                    node['color'] = "#1f77b4" if node['type'] == 'sender' else "#ff7f0e"
                elif color_by == "Grupo/Comunidad" and 'group' in node:
                    # Generar colores para grupos
                    group_id = node['group']
                    import hashlib
                    # Generar un color basado en el hash del ID del grupo
                    hashed = hashlib.md5(str(group_id).encode()).hexdigest()
                    node['color'] = "#" + hashed[:6]  # Usar los primeros 6 caracteres para el color HEX
            
            # Crear una visualización interactiva
            import streamlit.components.v1 as components
            import json
            
            # Preparar datos para visualizar
            graph_json = json.dumps(filtered_graph_data)
            
            # HTML para crear una visualización interactiva usando d3.js
            html_network = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>Red de Transacciones</title>
                <script src="https://d3js.org/d3.v7.min.js"></script>
                <style>
                    #network-graph {{
                        width: 100%;
                        height: 500px;
                        border: 1px solid #ddd;
                        border-radius: 5px;
                        overflow: hidden;
                        background-color: #f8f9fa;
                    }}
                    .node {{
                        stroke: #fff;
                        stroke-width: 1.5px;
                    }}
                    .link {{
                        stroke: #999;
                        stroke-opacity: 0.6;
                    }}
                    .tooltip {{
                        position: absolute;
                        background: white;
                        border: 1px solid #ddd;
                        border-radius: 4px;
                        padding: 8px;
                        pointer-events: none;
                        font-size: 12px;
                        z-index: 1000;
                    }}
                </style>
            </head>
            <body>
                <div id="network-graph"></div>
                <script>
                    // Cargar los datos del grafo
                    const graphData = {graph_json};
                    
                    // Crear la simulación de fuerza
                    const svg = d3.select('#network-graph')
                        .append('svg')
                        .attr('width', '100%')
                        .attr('height', '100%')
                        .call(d3.zoom().on("zoom", function (event) {{
                            svg.attr("transform", event.transform);
                        }}))
                        .append("g");
                    
                    // Crear un tooltip
                    const tooltip = d3.select("body").append("div")
                        .attr("class", "tooltip")
                        .style("opacity", 0);
                    
                    // Crear enlaces
                    const link = svg.selectAll('.link')
                        .data(graphData.edges)
                        .enter().append('line')
                        .attr('class', 'link')
                        .style('stroke-width', d => Math.sqrt(d.value) / 10 + 1);
                    
                    // Crear nodos
                    const node = svg.selectAll('.node')
                        .data(graphData.nodes)
                        .enter().append('circle')
                        .attr('class', 'node')
                        .attr('r', d => Math.sqrt(d.value) / 100 + 5)
                        .style('fill', d => d.color || (d.type === 'sender' ? '#1f77b4' : '#ff7f0e'))
                        .on('mouseover', function(event, d) {{
                            tooltip.transition()
                                .duration(200)
                                .style('opacity', .9);
                            tooltip.html(
                                `<strong>${{d.label}}</strong><br/>` +
                                `Tipo: ${{d.type === 'sender' ? 'Ordenante' : 'Beneficiario'}}<br/>` +
                                `País: ${{d.country}}<br/>` +
                                `Transacciones: ${{d.transactions}}<br/>` +
                                `Importe total: €${{d.value.toFixed(2)}}`
                            )
                            .style('left', (event.pageX + 10) + 'px')
                            .style('top', (event.pageY - 28) + 'px');
                        }})
                        .on('mouseout', function() {{
                            tooltip.transition()
                                .duration(500)
                                .style('opacity', 0);
                        }})
                        .call(d3.drag()
                            .on("start", dragstarted)
                            .on("drag", dragged)
                            .on("end", dragended));
                    
                    // Agregar etiquetas a los nodos
                    const text = svg.selectAll(".text")
                        .data(graphData.nodes)
                        .enter().append("text")
                        .attr("dx", 12)
                        .attr("dy", ".35em")
                        .text(d => d.label.length > 20 ? d.label.substring(0, 20) + '...' : d.label)
                        .style("font-size", "10px");
                    
                    // Crear simulación de fuerza
                    const simulation = d3.forceSimulation()
                        .nodes(graphData.nodes)
                        .force('link', d3.forceLink().id(d => d.id).links(graphData.edges).distance(100))
                        .force('charge', d3.forceManyBody().strength(-300))
                        .force('center', d3.forceCenter(400, 300))
                        .on('tick', ticked);
                    
                    function ticked() {{
                        link.attr('x1', d => d.source.x)
                            .attr('y1', d => d.source.y)
                            .attr('x2', d => d.target.x)
                            .attr('y2', d => d.target.y);
                        
                        node.attr('cx', d => d.x)
                            .attr('cy', d => d.y);
                        
                        text.attr("x", d => d.x)
                            .attr("y", d => d.y);
                    }}
                    
                    function dragstarted(event) {{
                        if (!event.active) simulation.alphaTarget(0.3).restart();
                        event.subject.fx = event.subject.x;
                        event.subject.fy = event.subject.y;
                    }}
                    
                    function dragged(event) {{
                        event.subject.fx = event.x;
                        event.subject.fy = event.y;
                    }}
                    
                    function dragended(event) {{
                        if (!event.active) simulation.alphaTarget(0);
                        event.subject.fx = null;
                        event.subject.fy = null;
                    }}
                </script>
            </body>
            </html>
            """
            
            # Mostrar visualización de red
            components.html(html_network, height=600)
            
            # Añadir sección para análisis de comunidades
            st.subheader("Análisis de Comunidades")
            
            # Obtener el método de comunidad utilizado, o usar valor por defecto "modularity"
            community_method = "modularity"  # Valor por defecto
            if 'community_method' in st.session_state:
                community_method = st.session_state.community_method
            elif 'network_params' in st.session_state and 'community_method' in st.session_state.network_params:
                community_method = st.session_state.network_params['community_method']
            
            # Detectar si hay información de comunidades en los nodos
            has_community_data = any('group' in node for node in filtered_graph_data['nodes'])
            
            if has_community_data:
                # Preparar datos para mostrar un resumen de comunidades
                communities = {}
                for node in filtered_graph_data['nodes']:
                    if 'group' in node:
                        group_id = node['group']
                        if group_id not in communities:
                            communities[group_id] = {
                                'id': group_id,
                                'nodes': 0,
                                'senders': 0,
                                'beneficiaries': 0,
                                'total_value': 0.0,
                                'countries': set()
                            }
                        
                        communities[group_id]['nodes'] += 1
                        
                        if node['type'] == 'sender':
                            communities[group_id]['senders'] += 1
                        else:
                            communities[group_id]['beneficiaries'] += 1
                        
                        if 'value' in node:
                            communities[group_id]['total_value'] += float(node['value'])
                        
                        if 'country' in node:
                            communities[group_id]['countries'].add(node['country'])
                
                # Convertir a lista y ordenar
                community_list = list(communities.values())
                
                # Identificar transacciones asociadas a cada comunidad
                df = st.session_state.filtered_data
                transactions_by_community = {}
                
                # Mapear senders y receivers a comunidades
                node_to_community = {}
                for node in filtered_graph_data['nodes']:
                    if 'group' in node:
                        node_to_community[node['id']] = node['group']
                
                # Mapear IDs de nodos a nombres para relacionar con las transacciones
                for edge in filtered_graph_data['edges']:
                    source_id = edge['source']
                    target_id = edge['target']
                    
                    if source_id in node_to_community and target_id in node_to_community:
                        # Si ambos nodos están en la misma comunidad
                        comm_id = node_to_community[source_id]
                        
                        # Inicializar la lista de transacciones para esta comunidad si no existe
                        if comm_id not in transactions_by_community:
                            transactions_by_community[comm_id] = []
                            
                        # Buscar información de fuente y destino en los nodos
                        source_node = next((n for n in filtered_graph_data['nodes'] if n['id'] == source_id), None)
                        target_node = next((n for n in filtered_graph_data['nodes'] if n['id'] == target_id), None)
                        
                        # Crear un identificador para esta conexión
                        if source_node and target_node:
                            # Usar 'label' si está disponible, o 'id' como fallback
                            sender_name = source_node.get('label', source_node.get('id', ''))
                            receiver_name = target_node.get('label', target_node.get('id', ''))
                            
                            # Encontrar transacciones correspondientes
                            matching_trans = df[
                                (df['NOMBRE_ORDENANTE'].astype(str) + ' ' + df['APELLIDO_ORDENANTE'].astype(str)).str.contains(sender_name, case=False) &
                                (df['NOMBRE_BENEFICIARIO'].astype(str) + ' ' + df['APELLIDO_BENEFICIARIO'].astype(str)).str.contains(receiver_name, case=False)
                            ]
                            
                            # Agregar información de la comunidad a cada transacción
                            if not matching_trans.empty:
                                matching_trans = matching_trans.copy()
                                matching_trans['ID_COMUNIDAD'] = comm_id
                                transactions_by_community[comm_id].append(matching_trans)
                
                # Actualizar cada comunidad con la cantidad de transacciones
                for comm in community_list:
                    comm_id = comm['id']
                    transactions = []
                    if comm_id in transactions_by_community:
                        for df_part in transactions_by_community[comm_id]:
                            transactions.extend(df_part.to_dict('records'))
                    
                    comm['transactions'] = len(transactions)
                    comm['transaction_data'] = transactions
                    comm['countries'] = list(comm['countries'])
                
                community_list.sort(key=lambda x: x['nodes'], reverse=True)
                
                # Asegurar que todas las comunidades tengan valores para todos los campos requeridos
                for comm in community_list:
                    # Verificar y establecer valores predeterminados para evitar columnas vacías
                    if 'trans_id_list' not in comm:
                        comm['trans_id_list'] = ""
                    if 'ordenantes_list' not in comm:
                        comm['ordenantes_list'] = ""
                    if 'beneficiarios_list' not in comm:
                        comm['beneficiarios_list'] = ""
                    if 'transaction_data' not in comm:
                        comm['transaction_data'] = []
                    if 'transactions' not in comm:
                        comm['transactions'] = 0
                
                # Mostrar tabla de comunidades
                st.write(f"Se han detectado {len(community_list)} comunidades utilizando el método '{community_method}':")
                
                # Crear un DataFrame para visualizar las comunidades con más detalles
                import pandas as pd
                
                # Mejorar la asignación de transacciones a comunidades utilizando el dataframe filtrado
                # Este bloque mejora la detección de transacciones por comunidad
                df_filtered = st.session_state.filtered_data.copy()
                
                # Mapear nombres completos de ordenantes y beneficiarios para búsqueda más efectiva
                df_filtered['ordenante_completo'] = df_filtered.apply(
                    lambda row: f"{str(row.get('NOMBRE_ORDENANTE', '')).strip()} {str(row.get('APELLIDO_ORDENANTE', '')).strip()}".strip(), 
                    axis=1
                )
                df_filtered['beneficiario_completo'] = df_filtered.apply(
                    lambda row: f"{str(row.get('NOMBRE_BENEFICIARIO', '')).strip()} {str(row.get('APELLIDO_BENEFICIARIO', '')).strip()}".strip(), 
                    axis=1
                )
                
                # Preparar mapeo de nombres a comunidades basado en los nodos
                name_to_community = {}
                for node in filtered_graph_data['nodes']:
                    if 'group' in node:
                        # Obtener el nombre del nodo, preferir 'label' pero caer en 'id' si no existe
                        node_name = node.get('label', node.get('id', ''))
                        if node_name:  # Solo añadir si hay un nombre válido
                            name_to_community[node_name] = node['group']
                
                # Función para asignar comunidad a cada transacción
                def assign_transaction_community(row):
                    ordenante = row['ordenante_completo']
                    beneficiario = row['beneficiario_completo']
                    
                    # Buscar comunidad del ordenante y beneficiario
                    ordenante_comm = name_to_community.get(ordenante, None)
                    beneficiario_comm = name_to_community.get(beneficiario, None)
                    
                    if ordenante_comm is not None and beneficiario_comm is not None:
                        # Si ambos tienen comunidad, preferir la comunidad del ordenante
                        return ordenante_comm
                    elif ordenante_comm is not None:
                        return ordenante_comm
                    elif beneficiario_comm is not None:
                        return beneficiario_comm
                    return None  # Si no se encuentra comunidad
                
                # Asignar comunidad a cada transacción
                df_filtered['comunidad'] = df_filtered.apply(assign_transaction_community, axis=1)
                
                # Agrupar transacciones por comunidad
                for comm in community_list:
                    comm_id = comm['id']
                    # Filtrar transacciones de esta comunidad
                    comm_transactions = df_filtered[df_filtered['comunidad'] == comm_id]
                    
                    if not comm_transactions.empty:
                        # Almacenar las transacciones
                        comm['transaction_data'] = comm_transactions.to_dict('records')
                        comm['transactions'] = len(comm_transactions)
                        
                        # Extraer números de transacción únicos
                        if 'NUMERO_TRANSACCION' in comm_transactions.columns:
                            trans_numbers = comm_transactions['NUMERO_TRANSACCION'].unique().tolist()
                            # Asegurar que todos los valores son string
                            trans_numbers = [str(t) for t in trans_numbers if t is not None and str(t).strip() != ""]
                            # Tomar hasta 5 para mostrar en la tabla
                            if trans_numbers:
                                comm['trans_id_list'] = ", ".join(trans_numbers[:5]) + ("..." if len(trans_numbers) > 5 else "")
                            else:
                                # Si no hay transacciones, usar los IDs de nodos
                                node_ids = [str(node.get('id', '')) for node in filtered_graph_data['nodes'] 
                                          if 'group' in node and node['group'] == comm_id]
                                if node_ids:
                                    comm['trans_id_list'] = "IDs: " + ", ".join(node_ids[:3]) + ("..." if len(node_ids) > 3 else "")
                                else:
                                    comm['trans_id_list'] = "No hay IDs disponibles"
                        else:
                            comm['trans_id_list'] = "No hay transacciones"
                        
                        # Extraer ordenantes únicos
                        ordenantes = comm_transactions['ordenante_completo'].dropna().unique().tolist()
                        # Tomar hasta 3 para mostrar en la tabla
                        comm['ordenantes_list'] = ", ".join([str(o) for o in ordenantes[:3] if o]) + ("..." if len(ordenantes) > 3 else "")
                        
                        # Extraer beneficiarios únicos
                        beneficiarios = comm_transactions['beneficiario_completo'].dropna().unique().tolist()
                        # Tomar hasta 3 para mostrar en la tabla
                        comm['beneficiarios_list'] = ", ".join([str(b) for b in beneficiarios[:3] if b]) + ("..." if len(beneficiarios) > 3 else "")
                    else:
                        # Si no hay transacciones, buscar en los nodos asociados a esta comunidad
                        senders = [node.get('label', node.get('id', '')) for node in filtered_graph_data['nodes'] 
                                 if 'group' in node and node['group'] == comm_id and node['type'] == 'sender']
                        receivers = [node.get('label', node.get('id', '')) for node in filtered_graph_data['nodes'] 
                                   if 'group' in node and node['group'] == comm_id and node['type'] == 'beneficiary']
                        
                        comm['transaction_data'] = []
                        comm['transactions'] = 0
                        comm['trans_id_list'] = ""
                        comm['ordenantes_list'] = ", ".join(senders[:3]) + ("..." if len(senders) > 3 else "")
                        comm['beneficiarios_list'] = ", ".join(receivers[:3]) + ("..." if len(receivers) > 3 else "")
                
                # Crear el DataFrame con todas las comunidades detectadas
                # No filtramos por requisitos mínimos para asegurar mostrar todas las 89 comunidades
                # Usamos directamente community_list para incluir todas
                
                # Si no hay comunidades, mostrar mensaje
                if not community_list:
                    st.warning("No se encontraron comunidades. Por favor, ajuste los filtros o cargue más datos.")
                    community_df = pd.DataFrame()
                else:
                    # Mostrar un mensaje informativo sobre el total de comunidades
                    st.info(f"Mostrando todas las {len(community_list)} comunidades detectadas.")
                    
                    # Crear DataFrame con todas las comunidadesálidas
                    community_df = pd.DataFrame([
                        {
                            "ID Comunidad": comm['id'], 
                            "Total Nodos": comm['nodes'],
                            "Ordenantes": comm['senders'],
                            "Beneficiarios": comm['beneficiaries'],
                            "Transacciones": comm['transactions'] if 'transactions' in comm and comm['transactions'] > 0 else len(comm.get('transaction_data', [])),
                            "Valor Total (€)": round(comm['total_value'], 2),
                            "Transacciones IDs": comm.get('trans_id_list', ""),
                            "Lista Ordenantes": comm.get('ordenantes_list', ""),
                            "Lista Beneficiarios": comm.get('beneficiarios_list', ""),
                            "Países": ", ".join(sorted(comm['countries']))
                        } 
                        for comm in community_list
                    ])
                
                # Mostrar tabla con todas las comunidades sin truncar
                st.dataframe(
                    community_df,
                    use_container_width=True
                )
                
                # Preparar datos completos con transacciones para exportación
                # Usar la lista completa de comunidades para asegurar consistencia
                export_data = []
                for comm in community_list:
                    # Datos básicos de la comunidad
                    comm_data = {
                        "ID_Comunidad": comm['id'],
                        "Total_Nodos": comm['nodes'],
                        "Ordenantes": comm['senders'],
                        "Beneficiarios": comm['beneficiaries'],
                        "Transacciones": comm['transactions'],
                        "Valor_Total": round(comm['total_value'], 2),
                        "Paises": ", ".join(sorted(comm['countries']))
                    }
                    
                    # Si hay transacciones, añadirlas con los datos de la comunidad
                    if 'transaction_data' in comm and comm['transaction_data']:
                        for trans in comm['transaction_data']:
                            # Combinar datos de la comunidad con datos de transacción
                            trans_record = comm_data.copy()
                            trans_record.update(trans)
                            export_data.append(trans_record)
                    else:
                        # Si no hay transacciones, solo añadir los datos básicos de la comunidad si hay remitentes y beneficiarios
                        if comm['senders'] > 0 and comm['beneficiaries'] > 0:
                            export_data.append(comm_data)
                
                # Crear el DataFrame para exportar
                export_df = pd.DataFrame(export_data) if export_data else pd.DataFrame()
                
                # Si el DataFrame está vacío, obtener todas las transacciones de la sesión para asegurar datos reales
                if export_df.empty or len(export_data) < 10:  # Verificar si hay suficientes datos
                    try:
                        # Usar datos reales de las transacciones filtradas
                        if 'filtered_data' in st.session_state and not st.session_state.filtered_data.empty:
                            # Mostrar mensaje informativo
                            st.info("Enriqueciendo el informe con datos reales de transacciones...")
                            
                            # Obtener transacciones del DataFrame filtrado
                            real_transactions = st.session_state.filtered_data.copy()
                            
                            # Agregar información de comunidad (si no existe)
                            if 'ID_COMUNIDAD' not in real_transactions.columns:
                                # Asignar comunidades usando los nodos que conocemos
                                node_communities = {}
                                for node in filtered_graph_data['nodes']:
                                    if 'group' in node:
                                        # Obtener el nombre del nodo, preferir 'label' pero caer en 'id' si no existe
                                        node_name = node.get('label', node.get('id', ''))
                                        if node_name:  # Solo añadir si hay un nombre válido
                                            node_communities[node_name] = node.get('group', 0)
                                
                                # Función para asignar comunidad basada en nombres
                                def assign_community(row):
                                    sender_name = f"{row['NOMBRE_ORDENANTE']} {row['APELLIDO_ORDENANTE']}".strip()
                                    receiver_name = f"{row['NOMBRE_BENEFICIARIO']} {row['APELLIDO_BENEFICIARIO']}".strip()
                                    
                                    sender_comm = node_communities.get(sender_name, 0)
                                    receiver_comm = node_communities.get(receiver_name, 0)
                                    
                                    # Si ambos están en la misma comunidad, usar esa
                                    if sender_comm == receiver_comm and sender_comm != 0:
                                        return sender_comm
                                    # Si solo uno tiene comunidad, usar esa
                                    elif sender_comm != 0:
                                        return sender_comm
                                    elif receiver_comm != 0:
                                        return receiver_comm
                                    # Si ninguno tiene, usar la primera comunidad
                                    else:
                                        return 1 if community_list else 0
                                
                                # Asignar comunidad a cada transacción
                                real_transactions['ID_COMUNIDAD'] = real_transactions.apply(assign_community, axis=1)
                            
                            # Asegurarse de que tenemos la información de la comunidad para cada transacción
                            community_info = {comm['id']: {
                                'Total_Nodos': comm['nodes'],
                                'Ordenantes': comm['senders'],
                                'Beneficiarios': comm['beneficiaries'],
                                'Paises': ", ".join(sorted(comm['countries'])) if isinstance(comm['countries'], list) else ""
                            } for comm in community_list} if community_list else {}
                            
                            # Enriquecer las transacciones con datos de comunidad
                            for col in ['Total_Nodos', 'Ordenantes', 'Beneficiarios', 'Paises']:
                                if col not in real_transactions.columns:
                                    real_transactions[col] = real_transactions['ID_COMUNIDAD'].apply(
                                        lambda x: community_info.get(x, {}).get(col, "")
                                    )
                            
                            # Usar estas transacciones enriquecidas para el export
                            export_df = real_transactions
                            
                            # Mensaje de éxito
                            st.success(f"Se exportarán {len(export_df)} transacciones reales con información de comunidad.")
                    except Exception as e:
                        st.warning(f"No se pudieron incorporar transacciones reales al informe: {str(e)}")
                
                # Añadir más datos a las transacciones si los tenemos disponibles
                try:
                    if 'filtered_data' in st.session_state and not st.session_state.filtered_data.empty:
                        # Obtener todas las columnas relevantes del DataFrame original
                        original_df = st.session_state.filtered_data.copy()
                        
                        # Asegurarnos de tener una columna identificador común
                        if 'NUMERO_TRANSACCION' in original_df.columns and 'NUMERO_TRANSACCION' in export_df.columns:
                            # Crear un DataFrame más completo uniendo ambos
                            complete_df = pd.merge(
                                export_df, 
                                original_df, 
                                on='NUMERO_TRANSACCION', 
                                how='outer',
                                suffixes=('', '_duplicado')
                            )
                            
                            # Eliminar columnas duplicadas
                            duplicate_cols = [c for c in complete_df.columns if c.endswith('_duplicado')]
                            if duplicate_cols:
                                complete_df = complete_df.drop(columns=duplicate_cols)
                                
                            # Usar el DataFrame completo para exportar
                            export_df = complete_df
                            
                            # Mensaje de éxito
                            st.success(f"Se exportarán {len(export_df)} transacciones con TODOS los datos disponibles!")
                except Exception as e:
                    st.warning(f"Error al enriquecer datos para exportación: {str(e)}")
                
                # Exportar Excel con el MISMO FORMATO que la tabla que se ve en pantalla
                try:
                    from io import BytesIO
                    import base64
                    
                    # Crear buffer para Excel
                    buffer = BytesIO()
                    
                    # Crear Excel writer
                    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                        # Escribir primero la tabla exactamente igual que se muestra en pantalla
                        community_df.to_excel(writer, sheet_name="Resumen_Comunidades", index=False)
                        
                        # Añadir también la tabla completa con todas las transacciones en otra hoja
                        export_df.to_excel(writer, sheet_name="Transacciones_Detalladas", index=False)
                        
                        # Dar formato al Excel - Primero a la hoja principal
                        workbook = writer.book
                        worksheet1 = writer.sheets["Resumen_Comunidades"]
                        worksheet2 = writer.sheets["Transacciones_Detalladas"]
                        
                        # Formato para encabezados
                        header_format = workbook.add_format({
                            'bold': True,
                            'bg_color': '#D7E4BC',
                            'border': 1
                        })
                        
                        # Aplicar formato a encabezados de la primera hoja
                        for col_num, value in enumerate(community_df.columns.values):
                            worksheet1.write(0, col_num, value, header_format)
                            # Ajustar ancho de columna basado en contenido
                            max_len = max(
                                community_df[value].astype(str).str.len().max(),
                                len(str(value))
                            ) + 2
                            # Aumentar el ancho máximo de columna a 100 para evitar truncamiento
                            worksheet1.set_column(col_num, col_num, min(max_len, 100))
                        
                        # Aplicar formato a encabezados de la segunda hoja
                        for col_num, value in enumerate(export_df.columns.values):
                            worksheet2.write(0, col_num, value, header_format)
                            # Ajustar ancho de columna basado en contenido
                            max_len = max(
                                export_df[value].astype(str).str.len().max(),
                                len(str(value))
                            ) + 2
                            # Aumentar el ancho máximo de columna a 100 para evitar truncamiento
                            worksheet2.set_column(col_num, col_num, min(max_len, 100))
                    
                    # Obtener datos binarios del Excel
                    buffer.seek(0)
                    excel_data = buffer.getvalue()
                    
                    # Codificar en base64 para descarga
                    b64 = base64.b64encode(excel_data).decode()
                    
                    # Crear botón de descarga para Excel
                    excel_filename = f"analisis_comunidades_{community_method}.xlsx"
                    href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="{excel_filename}" class="btn-download">Descargar Excel de Análisis de Comunidades</a>'
                    st.markdown(href, unsafe_allow_html=True)
                except Exception as e:
                    st.warning(f"Error al crear Excel: {str(e)}")
                
                # NO INCLUIR DESCARGA CSV - ELIMINADO POR SOLICITUD DEL USUARIO
                
                # Opción para descargar la red completa con datos de comunidades
                import json
                network_json = json.dumps(filtered_graph_data)
                st.download_button(
                    label="Descargar Red Completa (JSON)",
                    data=network_json,
                    file_name=f"red_transacciones_{community_method}.json",
                    mime="application/json",
                    help="Descarga el grafo completo en formato JSON para análisis avanzado",
                    key="download_network_json"
                )
                
                # Añadir opción para filtrar por comunidad específica
                selected_community = st.selectbox(
                    "Visualizar comunidad específica",
                    options=[f"Comunidad {comm['id']} ({comm['nodes']} nodos)" for comm in community_list],
                    index=0,
                    format_func=lambda x: x,
                    help="Selecciona una comunidad para ver solo sus nodos en la visualización"
                )
                
                if st.button("Filtrar por comunidad seleccionada"):
                    # Extraer ID de comunidad del texto seleccionado
                    import re
                    community_id_match = re.search(r"Comunidad (\d+)", selected_community)
                    if community_id_match:
                        selected_comm_id = int(community_id_match.group(1))
                        
                        # Filtrar nodos por comunidad
                        filtered_nodes = [
                            node for node in filtered_graph_data['nodes'] 
                            if 'group' in node and node['group'] == selected_comm_id
                        ]
                        filtered_node_ids = [node['id'] for node in filtered_nodes]
                        
                        # Filtrar aristas que conectan nodos de la comunidad
                        filtered_edges = [
                            edge for edge in filtered_graph_data['edges']
                            if edge['source'] in filtered_node_ids and edge['target'] in filtered_node_ids
                        ]
                        
                        # Actualizar visualización
                        filtered_graph_data = {
                            'nodes': filtered_nodes,
                            'edges': filtered_edges
                        }
                        
                        # Guardar método de coloración actual
                        color_by = "Grupo/Comunidad"  # Valor por defecto para este contexto
                        if 'color_by' in st.session_state:
                            color_by = st.session_state.color_by
                        
                        # Actualizar datos en session state
                        st.session_state.filtered_community_data = filtered_graph_data
                        st.session_state.color_by = color_by  # Guardar para uso posterior
                        st.success(f"Visualización filtrada a la Comunidad {selected_comm_id}")
                        st.rerun()
            else:
                st.info(f"Para visualizar comunidades en la red, selecciona 'Grupo/Comunidad' en 'Colorear nodos por' y actualiza la visualización.")
            
            # Mostrar patrones de estructuración detectados (si hay)
            if 'smurfing_patterns' in st.session_state:
                st.subheader("Patrones de Estructuración Detectados")
                
                try:
                    from utils.pattern_detection import format_pattern_for_display
                    patterns = st.session_state.smurfing_patterns
                    
                    if isinstance(patterns, dict) and patterns.get("error"):
                        st.info(f"No se pudieron detectar patrones: {patterns['error']}")
                    else:
                        # Formatear patrones para visualización
                        pattern_dfs = format_pattern_for_display(patterns)
                        
                        # Crear pestañas para mostrar los diferentes tipos de patrones
                        if pattern_dfs:
                            pattern_tabs = st.tabs(["Múltiples remitentes a un beneficiario", 
                                                 "Transacciones estructuradas", 
                                                 "Transacciones pequeñas frecuentes"])
                            
                            # 1. Múltiples remitentes a un mismo beneficiario
                            with pattern_tabs[0]:
                                if "multiple_senders" in pattern_dfs:
                                    st.dataframe(pattern_dfs["multiple_senders"], use_container_width=True)
                                    
                                    # Opción para exportar con codificación UTF-8 explícita y BOM para Excel
                                    csv_data = '\ufeff' + pattern_dfs["multiple_senders"].to_csv(index=False, encoding='utf-8-sig')
                                    st.download_button(
                                        label="Exportar patrón (CSV)",
                                        data=csv_data.encode('utf-8-sig'),
                                        file_name="patron_multiples_remitentes.csv",
                                        mime="text/csv;charset=utf-8-sig",
                                        key="download_pattern_multiple"
                                    )
                                else:
                                    st.info("No se detectaron patrones de múltiples remitentes a un mismo beneficiario.")
                            
                            # 2. Transacciones estructuradas
                            with pattern_tabs[1]:
                                if "structured" in pattern_dfs:
                                    st.dataframe(pattern_dfs["structured"], use_container_width=True)
                                    
                                    # Opción para exportar con codificación UTF-8 explícita y BOM para Excel
                                    csv_data = '\ufeff' + pattern_dfs["structured"].to_csv(index=False, encoding='utf-8-sig')
                                    st.download_button(
                                        label="Exportar patrón (CSV)",
                                        data=csv_data.encode('utf-8-sig'),
                                        file_name="patron_estructuracion.csv",
                                        mime="text/csv;charset=utf-8-sig",
                                        key="download_pattern_structured"
                                    )
                                else:
                                    st.info("No se detectaron patrones de transacciones estructuradas.")
                            
                            # 3. Transacciones pequeñas frecuentes
                            with pattern_tabs[2]:
                                if "small_frequent" in pattern_dfs:
                                    st.dataframe(pattern_dfs["small_frequent"], use_container_width=True)
                                    
                                    # Opción para exportar con codificación UTF-8 explícita y BOM para Excel
                                    csv_data = '\ufeff' + pattern_dfs["small_frequent"].to_csv(index=False, encoding='utf-8-sig')
                                    st.download_button(
                                        label="Exportar patrón (CSV)",
                                        data=csv_data.encode('utf-8-sig'),
                                        file_name="patron_pequenas_frecuentes.csv",
                                        mime="text/csv;charset=utf-8-sig",
                                        key="download_pattern_small"
                                    )
                                else:
                                    st.info("No se detectaron patrones de transacciones pequeñas frecuentes.")
                            
                            # Eliminada la sección "Exportar Grafo y Patrones" que no funcionaba correctamente
                        else:
                            st.info("No se detectaron patrones significativos de estructuración.")
                except Exception as e:
                    st.error(f"Error al procesar patrones: {str(e)}")
                    import traceback
                    st.error(traceback.format_exc())
    

    
    with tab4:
        if st.session_state.risk_scores is not None and st.session_state.filtered_data is not None:
            st.header("Reportes de Operaciones Sospechosas")
            
            # Obtener datos necesarios
            df = st.session_state.filtered_data
            risk_scores = st.session_state.risk_scores
            risk_details = st.session_state.risk_details
            agent_subject_mapping = st.session_state.agent_subject_mapping
            
            # Calcular el nivel de riesgo total
            total_risk = calculate_total_risk_score(risk_scores)
            
            # Crear dos columnas para organizar la información
            report_col1, report_col2 = st.columns(2)
            
            with report_col1:
                # Nuevo informe en formato Excel/PDF
                st.subheader("Informe Detallado por Agente")
                st.markdown("""
                Este informe contiene:
                - **Pestaña 1**: Análisis de riesgo por agente y por indicador
                - **Pestaña 2**: Transacciones detectadas como sospechosas
                """)
                
                # Opciones de formato
                report_format = st.radio(
                    "Formato del informe:",
                    ["Excel", "PDF"],
                    horizontal=True
                )
                
                # Botón para generar el informe
                if st.button("Generar Informe Detallado", key="generate_detailed_report_button"):
                    with st.spinner(f"Generando informe detallado en formato {report_format}..."):
                        try:
                            if report_format == "Excel":
                                # Preparar los datos para el informe
                                
                                # Identificar transacciones de riesgo
                                # Find high-risk indicators
                                high_risk_indicators = []
                                
                                for indicador, puntuacion in risk_scores.items():
                                    # Manejar diferentes tipos de puntuación
                                    try:
                                        # Si es una secuencia, tomar el primer elemento
                                        if isinstance(puntuacion, (list, tuple)):
                                            if len(puntuacion) > 0:
                                                numeric_puntuacion = float(puntuacion[0])
                                            else:
                                                numeric_puntuacion = 1.0  # Valor predeterminado si la lista está vacía
                                        else:
                                            numeric_puntuacion = float(puntuacion)
                                            
                                        # Añadir a la lista si cumple el umbral
                                        if numeric_puntuacion >= 3:
                                            high_risk_indicators.append(indicador)
                                    except (ValueError, TypeError):
                                        # Si hay error en la conversión, ignorar este indicador
                                        print(f"Error al convertir la puntuación '{puntuacion}' del indicador {indicador} a número. Ignorando indicador.")
                                
                                # Get suspicious transactions with high risk in at least one indicator
                                suspicious_transactions = set()
                                risk_reasons = {}
                                
                                for indicador in high_risk_indicators:
                                    if indicador in risk_details and isinstance(risk_details[indicador], pd.DataFrame):
                                        if 'NUMERO_TRANSACCION' in risk_details[indicador].columns:
                                            for _, row in risk_details[indicador].iterrows():
                                                trans_num = str(row['NUMERO_TRANSACCION'])
                                                suspicious_transactions.add(trans_num)
                                                
                                                if trans_num not in risk_reasons:
                                                    risk_reasons[trans_num] = []
                                                    
                                                risk_reasons[trans_num].append(f"Indicador {indicador}: {indicator_names.get(indicador, '')}")
                                
                                # Preparar DataFrame de transacciones sospechosas
                                if suspicious_transactions:
                                    suspicious_df = df[df['NUMERO_TRANSACCION'].astype(str).isin(suspicious_transactions)].copy()
                                    
                                    # Añadir columnas de motivo e indicadores de riesgo
                                    suspicious_df['MOTIVO_RIESGO'] = suspicious_df['NUMERO_TRANSACCION'].astype(str).apply(
                                        lambda x: "Múltiples indicadores de riesgo detectados" if x in risk_reasons else "Transacción sospechosa"
                                    )
                                    
                                    suspicious_df['INDICADORES_RIESGO'] = suspicious_df['NUMERO_TRANSACCION'].astype(str).apply(
                                        lambda x: "; ".join(risk_reasons.get(x, []))
                                    )
                                else:
                                    # Crear DataFrame vacío si no hay transacciones sospechosas
                                    suspicious_df = None
                                
                                # Reorganizar y calcular risk_scores por agente 
                                # La función espera un diccionario: {agente: {indicador: score, ...}, ...}
                                
                                # Calcularemos el riesgo específico para cada agente
                                # basado en sus propias transacciones
                                
                                # Importar funciones de cálculo de riesgo
                                from utils.risk_indicators import calculate_risk_indicators, calculate_risk_scores
                                
                                # Si hay columna 'es_Agente', calculamos riesgo por agente
                                if 'es_Agente' in df.columns:
                                    # Obtener todos los agentes seleccionados por el usuario
                                    unique_agents = []
                                    
                                    # Primero, incluir todos los agentes seleccionados (incluso si no aparecen en datos filtrados)
                                    if hasattr(st.session_state, 'selected_agents') and st.session_state.selected_agents:
                                        unique_agents.extend(st.session_state.selected_agents)
                                    
                                    # Luego, obtener agentes adicionales de los datos filtrados (por si acaso)
                                    df_agents = df['es_Agente'].dropna().unique().tolist()
                                    for agent in df_agents:
                                        if agent and str(agent).lower() != 'nan' and agent not in unique_agents:
                                            unique_agents.append(agent)
                                    
                                    # Eliminar duplicados y ordenar
                                    unique_agents = sorted(list(set(unique_agents)))
                                    
                                    # Registrar los agentes que estamos analizando
                                    st.write(f"Analizando {len(unique_agents)} agentes: {', '.join(unique_agents)}")
                                    
                                    # Preparar estructura por agente
                                    risk_by_agent = {}
                                    
                                    # Para cada agente, calcular sus indicadores específicos
                                    for agent in unique_agents:
                                        # Filtrar datos solo para este agente
                                        agent_df = df[df['es_Agente'] == agent]
                                        
                                        if not agent_df.empty:
                                            # Calcular indicadores para este agente
                                            try:
                                                # Si hay umbrales específicos para este agente, usarlos
                                                if 'thresholds' in st.session_state and agent in st.session_state.thresholds:
                                                    agent_thresholds = st.session_state.thresholds[agent]
                                                else:
                                                    # Si no hay umbrales específicos, usar los generales
                                                    agent_thresholds = st.session_state.thresholds if 'thresholds' in st.session_state else None
                                                
                                                # Calcular indicadores de riesgo para este agente
                                                agent_risk_indicators, agent_risk_details = calculate_risk_indicators(
                                                    agent_df,
                                                    thresholds=agent_thresholds
                                                )
                                                
                                                # Guardar estos detalles específicos del agente para usarlos después
                                                if 'agent_risk_details_dict' not in locals():
                                                    agent_risk_details_dict = {}
                                                
                                                # Asegurarnos de que agent_risk_details_dict está definido 
                                                # y es un diccionario válido antes de usarlo
                                                if not isinstance(agent_risk_details_dict, dict):
                                                    agent_risk_details_dict = {}
                                                    
                                                # Almacenar los detalles para este agente
                                                agent_risk_details_dict[agent] = agent_risk_details
                                                
                                                # Obtener pesos de indicadores desde descripciones o usar valores predeterminados
                                                agent_indicator_weights = {}
                                                if 'indicator_descriptions' in locals() or 'indicator_descriptions' in globals():
                                                    for ind_id in agent_risk_indicators.keys():
                                                        # Obtener peso del indicador (por defecto 1.0)
                                                        try:
                                                            weight_str = indicator_descriptions.get(ind_id, {}).get("weight", "1")
                                                            # Convertir a float, quitando el símbolo % si existe
                                                            weight = float(weight_str.strip('%')) / 100 if '%' in weight_str else float(weight_str)
                                                            agent_indicator_weights[ind_id] = weight
                                                        except:
                                                            agent_indicator_weights[ind_id] = 1.0
                                                else:
                                                    # Si no hay descripciones de indicadores, usar peso 1.0 para todos
                                                    for ind_id in agent_risk_indicators.keys():
                                                        agent_indicator_weights[ind_id] = 1.0
                                                
                                                # Calcular puntuaciones de riesgo por indicador
                                                agent_risk_scores = calculate_risk_scores(
                                                    agent_risk_indicators,
                                                    indicator_weights=agent_indicator_weights
                                                )
                                                
                                                # Almacenar puntuaciones para este agente
                                                risk_by_agent[agent] = agent_risk_scores
                                            except Exception as e:
                                                # Si hay error, usar los indicadores globales
                                                st.warning(f"Error al calcular indicadores para agente {agent}: {str(e)}. Usando indicadores globales.")
                                                risk_by_agent[agent] = risk_scores.copy()
                                        else:
                                            # Si no hay datos, usar puntuaciones globales
                                            risk_by_agent[agent] = risk_scores.copy()
                                else:
                                    # Si no hay distinción por agente, usamos un agente específico para cada agente seleccionado
                                    risk_by_agent = {}
                                    for agent in selected_agents:
                                        # Convertir cada puntuación a float de manera segura
                                        agent_scores = {}
                                        for ind_id, score in risk_scores.items():
                                            if not isinstance(score, dict):
                                                try:
                                                    # Si es una secuencia, tomar el primer elemento
                                                    if isinstance(score, (list, tuple)):
                                                        if len(score) > 0:
                                                            agent_scores[ind_id] = float(score[0])
                                                        else:
                                                            agent_scores[ind_id] = 1.0  # Valor predeterminado
                                                    else:
                                                        agent_scores[ind_id] = float(score)
                                                except (ValueError, TypeError):
                                                    # Si no se puede convertir, usar 1.0 (riesgo bajo)
                                                    agent_scores[ind_id] = 1.0
                                        risk_by_agent[agent] = agent_scores
                                
                                # Construir un diccionario con detalles de riesgo por agente
                                risk_details_by_agent = {}
                                
                                # Si tenemos detalles específicos por agente, los utilizamos
                                if 'agent_risk_details_dict' in locals():
                                    # Usar los detalles específicos que calculamos antes
                                    agent_risk_details_dict_local = locals()['agent_risk_details_dict']
                                    
                                    # Verificar que sea un diccionario antes de usar
                                    if isinstance(agent_risk_details_dict_local, dict):
                                        for agent in risk_by_agent:
                                            if agent in agent_risk_details_dict_local:
                                                risk_details_by_agent[agent] = agent_risk_details_dict_local[agent]
                                            else:
                                                # Si no hay detalles específicos, usamos los detalles globales
                                                risk_details_by_agent[agent] = risk_details
                                    else:
                                        # Si no es un diccionario válido, usar los detalles globales
                                        for agent in risk_by_agent:
                                            risk_details_by_agent[agent] = risk_details
                                else:
                                    # Si no tenemos detalles específicos, asociamos los detalles globales a cada agente
                                    for agent in risk_by_agent:
                                        risk_details_by_agent[agent] = risk_details
                                
                                # Importar las funciones de la implementación fija
                                from utils.fixed_risk_indicators import calcular_riesgos_por_agente
                                
                                # Obtener los datos de riesgo por agente usando la implementación fija
                                riesgos_individuales, resultados_por_tipo, operaciones_sospechosas = calcular_riesgos_por_agente(
                                    df, 
                                    selected_agents
                                )
                                
                                # Generar el informe en Excel con el nuevo formato
                                try:
                                    # LÓGICA MEJORADA: Recopilar todas las operaciones sospechosas de todos los indicadores
                                    # incluyendo indicadores 10-20 y todas las operaciones con datos en Motivo_Riesgo
                                    try:
                                        # Crear lista para almacenar todos los DataFrames válidos
                                        valid_dfs = []
                                        
                                        # 1. Primero procesar cada agente y sus indicadores específicos
                                        for agente, detalles_agente in risk_details_by_agent.items():
                                            for indicador in range(1, 21):  # Asegurar que incluimos todos (1-20)
                                                indicador_str = str(indicador)
                                                
                                                # Verificar si hay detalles para este indicador
                                                if indicador_str in detalles_agente:
                                                    df_ops = detalles_agente[indicador_str]
                                                    
                                                    # Solo procesar si es un DataFrame no vacío con números de transacción
                                                    if isinstance(df_ops, pd.DataFrame) and not df_ops.empty and 'NUMERO_TRANSACCION' in df_ops.columns:
                                                        df_ops = df_ops.copy()  # Hacer copia para evitar advertencias
                                                        
                                                        # Asegurar que cada operación tenga el código de agente
                                                        if 'ENT_NAT_REF_COD' not in df_ops.columns:
                                                            df_ops['ENT_NAT_REF_COD'] = str(agente)
                                                        
                                                        # Asegurar que tenemos la columna Motivo_Riesgo
                                                        motivo_cols = [col for col in df_ops.columns 
                                                                       if col.lower().find('motivo') >= 0 and col.lower().find('riesgo') >= 0]
                                                        
                                                        # Si no hay columna de motivo, agregarla
                                                        if not motivo_cols:
                                                            df_ops['Motivo_Riesgo'] = f"Riesgo detectado en indicador {indicador_str}"
                                                        # Si existe pero con otro nombre, estandarizarlo
                                                        elif 'Motivo_Riesgo' not in df_ops.columns:
                                                            df_ops['Motivo_Riesgo'] = df_ops[motivo_cols[0]]
                                                        
                                                        # IMPORTANTE: Incluir todas las operaciones, NO filtrar por Motivo_Riesgo
                                                        valid_dfs.append(df_ops)
                                        
                                        # 2. Si suspicious_df existe (agrupación global), también incluirla
                                        if 'suspicious_df' in locals() and suspicious_df is not None and not suspicious_df.empty:
                                            valid_dfs.append(suspicious_df)
                                                
                                        # 3. Si hay operaciones sospechosas por agente, incluirlas también
                                        if 'operaciones_sospechosas' in locals() and operaciones_sospechosas:
                                            for agente, df_ops in operaciones_sospechosas.items():
                                                if isinstance(df_ops, pd.DataFrame) and not df_ops.empty:
                                                    df_copy = df_ops.copy()
                                                    
                                                    # Asegurar que cada operación tiene código de agente
                                                    if 'ENT_NAT_REF_COD' not in df_copy.columns:
                                                        df_copy['ENT_NAT_REF_COD'] = str(agente)
                                                    elif not df_copy['ENT_NAT_REF_COD'].astype(str).str.contains(str(agente)).any():
                                                        df_copy['ENT_NAT_REF_COD'] = str(agente)
                                                        
                                                    # Agregar todas estas operaciones directamente
                                                    valid_dfs.append(df_copy)
                                        
                                        # Combinar todos los DataFrames válidos SIN eliminar duplicados
                                        if valid_dfs:
                                            # NO eliminar duplicados - una transacción puede aparecer en varios indicadores de riesgo
                                            combined_df = pd.concat(valid_dfs, ignore_index=True)
                                            
                                            # Limitar a 5000 filas para evitar problemas de rendimiento
                                            risk_transactions = combined_df.head(5000)
                                            
                                            # Asegurar que la columna Motivo_Riesgo está presente
                                            if 'Motivo_Riesgo' not in risk_transactions.columns:
                                                risk_transactions['Motivo_Riesgo'] = "Operación de riesgo detectada"
                                            
                                            print(f"Total de operaciones sospechosas para el informe: {len(risk_transactions)}")
                                        else:
                                            risk_transactions = None
                                            print("No se encontraron operaciones sospechosas para incluir en el informe")
                                    except Exception as e:
                                        st.warning(f"Error al procesar operaciones sospechosas: {str(e)}")
                                        import traceback
                                        st.code(traceback.format_exc())
                                        risk_transactions = None
                                    
                                    excel_data = generate_risk_report_excel(
                                        df,
                                        riesgos_individuales,  # Usar los resultados calculados por agente
                                        risk_details_by_agent,  # Mantener los detalles originales
                                        agent_subject_mapping,
                                        indicator_types,
                                        indicator_descriptions,
                                        risk_transactions=risk_transactions,
                                        filename="informe_riesgo_detallado.xlsx"
                                    )
                                    
                                    # Mostrar enlace de descarga
                                    st.markdown(
                                        export_download_link(excel_data, "informe_riesgo_detallado.xlsx", "excel"),
                                        unsafe_allow_html=True
                                    )
                                    st.success("Informe Excel generado correctamente. Haz clic en el enlace para descargar.")
                                except Exception as e:
                                    st.error(f"Error al generar el informe Excel: {str(e)}")
                                    import traceback
                                    st.code(traceback.format_exc())
                            

                                
                        except Exception as e:
                            st.error(f"Error al generar el informe: {str(e)}")
                            import traceback
                            st.code(traceback.format_exc(), language="python")
            
            with report_col2:
                # Resumen de nivel de riesgo
                st.subheader("Resumen de Riesgo")
                
                # Display risk level (escala 1-4)
                if total_risk < 1.5:
                    st.success(f"Nivel de Riesgo Global: BAJO ({total_risk:.2f}/4)")
                    st.markdown("No se han detectado operaciones de alto riesgo que requieran seguimiento inmediato.")
                elif total_risk < 2.5:
                    st.warning(f"Nivel de Riesgo Global: MEDIO ({total_risk:.2f}/4)")
                    st.markdown("Se han detectado algunas operaciones sospechosas que podrían requerir revisión.")
                elif total_risk < 3.5:
                    st.error(f"Nivel de Riesgo Global: ALTO ({total_risk:.2f}/4)")
                    st.markdown("Se han detectado operaciones de alto riesgo que requieren atención.")
                else:
                    st.error(f"Nivel de Riesgo Global: MUY ALTO ({total_risk:.2f}/4)")
                    st.markdown("Se han detectado múltiples operaciones de riesgo crítico que requieren atención inmediata.")
            
                # Identificar indicadores de alto riesgo
                high_risk_indicators = []
                
                # Usar avg_risk_scores que contiene la media de los indicadores por agente
                # en lugar de risk_scores que contiene el valor global
                for indicador, puntuacion in avg_risk_scores.items():
                    # Manejar diferentes tipos de puntuación
                    try:
                        # Si es una secuencia, tomar el primer elemento
                        if isinstance(puntuacion, (list, tuple)):
                            if len(puntuacion) > 0:
                                numeric_puntuacion = float(puntuacion[0])
                            else:
                                numeric_puntuacion = 1.0  # Valor predeterminado si la lista está vacía
                        else:
                            numeric_puntuacion = float(puntuacion)
                            
                        # Añadir a la lista si cumple el umbral
                        if numeric_puntuacion >= 3:
                            high_risk_indicators.append(str(indicador))  # Asegurar que es string
                    except (ValueError, TypeError):
                        # Si hay error en la conversión, ignorar este indicador
                        print(f"Error al convertir la puntuación '{puntuacion}' del indicador {indicador} a número. Ignorando indicador.")
                
                if high_risk_indicators:
                    st.subheader("Indicadores de Alto Riesgo Detectados")
                    
                    for indicador in high_risk_indicators:
                        # Usar avg_risk_scores para mostrar la media por agente en lugar del valor global
                        try:
                            # Primero intentamos obtener el valor del promedio de los agentes
                            if indicador in avg_risk_scores:
                                score_value = avg_risk_scores[indicador]
                            else:
                                # Si no hay promedio, usar el valor global
                                score_value = risk_scores[indicador]
                                
                            # Formatear correctamente
                            if isinstance(score_value, (list, tuple)):
                                if len(score_value) > 0:
                                    numeric_score = float(score_value[0])
                                else:
                                    numeric_score = 1.0  # Valor predeterminado si la lista está vacía
                            else:
                                numeric_score = float(score_value)
                                
                            # Formatear según si es entero o tiene decimales
                            formatted_score = formatear_valor_riesgo(numeric_score)
                        except (ValueError, TypeError):
                            formatted_score = "1"
                            print(f"Error al convertir puntuación para el indicador {indicador}. Usando valor predeterminado.")
                            
                        st.markdown(f"* **Indicador {indicador}**: {indicator_names[indicador]} - Puntuación: {formatted_score}/4 (promedio agentes)")
                
                # Create a detailed report for suspicious transactions
                st.subheader("Transacciones Sospechosas")
                st.markdown("Las siguientes transacciones han sido identificadas como potencialmente sospechosas:")
                
                # Recolectar TODAS las transacciones marcadas por CUALQUIER indicador de riesgo
                suspicious_transactions = set()
                transaction_details = {}  # Almacena detalles de cada transacción por indicador
                
                # Recorrer los 20 indicadores para asegurarnos de capturar todos
                for indicador in range(1, 21):
                    indicador_str = str(indicador)
                    
                    # Verificar si el indicador existe en risk_details
                    if indicador_str in risk_details:
                        # Verificar tipo
                        if isinstance(risk_details[indicador_str], pd.DataFrame):
                            # Verificar columnas
                            if 'NUMERO_TRANSACCION' in risk_details[indicador_str].columns:
                                # Procesamiento normal
                                print(f"Procesando transacciones para indicador {indicador_str}. Total: {len(risk_details[indicador_str])}")
                                
                                # Añadir todas las transacciones detectadas por este indicador
                                for _, row in risk_details[indicador_str].iterrows():
                                    tx_id = str(row['NUMERO_TRANSACCION'])
                                    suspicious_transactions.add(tx_id)
                                    
                                    # Guardar detalles adicionales de cada transacción sospechosa
                                    if tx_id not in transaction_details:
                                        transaction_details[tx_id] = []
                                    
                                    # Agregar motivo de riesgo si existe
                                    motivo = None
                                    
                                    # Verificar diferentes variantes del nombre de columna para motivo de riesgo
                                    for col_name in ['Motivo_Riesgo', 'MOTIVO_RIESGO', 'motivo_riesgo']:
                                        if col_name in row and pd.notna(row[col_name]) and row[col_name]:
                                            motivo = row[col_name]
                                            break
                                    
                                    # Si no hay motivo específico, usar el texto de la descripción del indicador
                                    if not motivo:
                                        if indicador_str in indicator_names:
                                            motivo = f"Riesgo detectado: {indicator_names[indicador_str]}"
                                        else:
                                            motivo = f"Riesgo detectado por indicador {indicador_str}"
                                    
                                    # Añadir detalles de la transacción
                                    transaction_details[tx_id].append({
                                        'indicador': indicador_str,
                                        'motivo': motivo
                                    })
                
                if suspicious_transactions:
                    # Filter dataframe to show only suspicious transactions
                    suspicious_df = df[df['NUMERO_TRANSACCION'].astype(str).isin(suspicious_transactions)]
                    
                    # Crear informe en formato detallado como en la imagen
                    st.subheader("Informe Detallado de Transacciones Sospechosas")
                    
                    # Crear una tabla con estilo HTML para el informe
                    html_table = """
                    <style>
                        .report-table {
                            width: 100%;
                            border-collapse: collapse;
                            font-size: 12px;
                            margin-bottom: 20px;
                        }
                        .report-table th {
                            background-color: #f2f2f2;
                            border: 1px solid #ddd;
                            padding: 8px;
                            text-align: left;
                            font-weight: bold;
                            position: sticky;
                            top: 0;
                            z-index: 10;
                        }
                        .report-table td {
                            border: 1px solid #ddd;
                            padding: 8px;
                            text-align: left;
                            white-space: nowrap;
                        }
                        .report-table tr:nth-child(even) {
                            background-color: #f9f9f9;
                        }
                        .report-table tr:hover {
                            background-color: #f1f1f1;
                        }
                        .risk-high {
                            background-color: #ffcccc !important;
                        }
                        .risk-medium {
                            background-color: #fff2cc !important;
                        }
                    </style>
                    <div style="overflow-x: auto; max-height: 500px; overflow-y: auto;">
                    <table class="report-table">
                        <thead>
                            <tr>
                                <th>Num. Transacción</th>
                                <th>Fecha</th>
                                <th>Hora</th>
                                <th>Importe</th>
                                <th>Estado</th>
                                <th>País Origen</th>
                                <th>Ordenante</th>
                                <th>País Doc.</th>
                                <th>Documento</th>
                                <th>País Nacimiento</th>
                                <th>F. Nacimiento</th>
                                <th>¿Agente?</th>
                                <th>¿PEP?</th>
                                <th>Beneficiario</th>
                                <th>País Destino</th>
                                <th>Entidad</th>
                                <th>Indicadores</th>
                            </tr>
                        </thead>
                        <tbody>
                    """
                    
                    # Preparar información de los indicadores por transacción
                    transaction_indicators = {}
                    
                    # Usar los detalles de transacción recopilados anteriormente
                    # y enriquecerlos con información del indicador
                    for tx_id, details_list in transaction_details.items():
                        if tx_id not in transaction_indicators:
                            transaction_indicators[tx_id] = []
                        
                        for detail in details_list:
                            indicador_str = detail['indicador']
                            
                            # Convertir el valor de riesgo a número de manera segura
                            try:
                                score_value = risk_scores.get(indicador_str, 1.0)
                                if isinstance(score_value, (list, tuple)):
                                    if len(score_value) > 0:
                                        numeric_score = float(score_value[0])
                                    else:
                                        numeric_score = 1.0
                                else:
                                    numeric_score = float(score_value)
                            except (ValueError, TypeError):
                                numeric_score = 1.0
                                print(f"Error al convertir puntuación '{risk_scores.get(indicador_str, 1.0)}' a número. Usando valor predeterminado.")
                            
                            # Añadir los motivos de riesgo
                            motivo = detail.get('motivo', f"Riesgo detectado por indicador {indicador_str}")
                            
                            # Evitar duplicados
                            existing_entry = [
                                entry for entry in transaction_indicators[tx_id] 
                                if entry['id'] == indicador_str
                            ]
                            
                            if not existing_entry:
                                transaction_indicators[tx_id].append({
                                    'id': indicador_str,
                                    'name': indicator_names.get(indicador_str, f"Indicador {indicador_str}"),
                                    'score': numeric_score,
                                    'motivo': motivo
                                })
                                
                    # Adicionalmente, recorremos todos los indicadores para asegurar que no falta ninguno
                    for indicador in range(1, 21):
                        indicador_str = str(indicador)
                        if indicador_str in risk_details and isinstance(risk_details[indicador_str], pd.DataFrame) and not risk_details[indicador_str].empty:
                            if 'NUMERO_TRANSACCION' in risk_details[indicador_str].columns:
                                for _, row in risk_details[indicador_str].iterrows():
                                    tx_id = str(row['NUMERO_TRANSACCION'])
                                    if tx_id not in transaction_indicators:
                                        transaction_indicators[tx_id] = []
                                    
                                    # Comprobar si ya existe este indicador para esta transacción
                                    existing_entries = [e for e in transaction_indicators[tx_id] if e['id'] == indicador_str]
                                    if not existing_entries:
                                        # No existe, añadirlo
                                        try:
                                            score_value = risk_scores.get(indicador_str, 1.0)
                                            if isinstance(score_value, (list, tuple)):
                                                numeric_score = float(score_value[0] if len(score_value) > 0 else 1.0)
                                            else:
                                                numeric_score = float(score_value)
                                        except (ValueError, TypeError):
                                            numeric_score = 1.0
                                        
                                        motivo = ""
                                        if 'Motivo_Riesgo' in row and pd.notna(row['Motivo_Riesgo']):
                                            motivo = row['Motivo_Riesgo']
                                        elif not motivo:
                                            motivo = f"Riesgo detectado por indicador {indicador_str}"
                                        
                                        transaction_indicators[tx_id].append({
                                            'id': indicador_str,
                                            'name': indicator_names.get(indicador_str, f"Indicador {indicador_str}"),
                                            'score': numeric_score,
                                            'motivo': motivo
                                        })
                    
                    # Generar filas para cada transacción sospechosa
                    for _, row in suspicious_df.iterrows():
                        tx_id = str(row['NUMERO_TRANSACCION'])
                        
                        # Determinar nivel de riesgo para aplicar clase CSS
                        row_class = ""
                        if tx_id in transaction_indicators:
                            max_score = max([ind['score'] for ind in transaction_indicators[tx_id]])
                            if max_score >= 4:
                                row_class = "risk-high"
                            elif max_score >= 3:
                                row_class = "risk-medium"
                        
                        # Formatear ordenante y beneficiario
                        ordenante = f"{row['NOMBRE_ORDENANTE']} {row['APELLIDO_ORDENANTE']}"
                        if 'SEGUNDO_APELLIDO_ORDENANTE' in row and not pd.isna(row['SEGUNDO_APELLIDO_ORDENANTE']):
                            ordenante += f" {row['SEGUNDO_APELLIDO_ORDENANTE']}"
                            
                        beneficiario = f"{row['NOMBRE_BENEFICIARIO']} {row['APELLIDO_BENEFICIARIO']}"
                        if 'SEGUNDO_APELLIDO_BENEFICIARIO' in row and not pd.isna(row['SEGUNDO_APELLIDO_BENEFICIARIO']):
                            beneficiario += f" {row['SEGUNDO_APELLIDO_BENEFICIARIO']}"
                        
                        # Formatear fecha y hora
                        fecha = row['FECHA'].strftime('%d/%m/%Y') if isinstance(row['FECHA'], pd.Timestamp) else str(row['FECHA'])
                        hora = str(row['HORA']) if 'HORA' in row else ""
                        
                        # Añadir fila a la tabla
                        html_table += f"""
                        <tr class="{row_class}">
                            <td>{row['NUMERO_TRANSACCION']}</td>
                            <td>{fecha}</td>
                            <td>{hora}</td>
                            <td>{row['IMPORTE']:.2f} €</td>
                            <td>{row['ESTADO_OPERACION'] if 'ESTADO_OPERACION' in row else ''}</td>
                            <td>{row['PAIS_ORIGEN'] if 'PAIS_ORIGEN' in row else ''}</td>
                            <td>{ordenante}</td>
                            <td>{row['PAIS_DOC_ORDENANTE'] if 'PAIS_DOC_ORDENANTE' in row else ''}</td>
                            <td>{row['NUM_DOC_ORDENANTE'] if 'NUM_DOC_ORDENANTE' in row else ''}</td>
                            <td>{row['PAIS_NAC_ORDENANTE'] if 'PAIS_NAC_ORDENANTE' in row else ''}</td>
                            <td>{row['FECHA_NAC_ORDENANTE'] if 'FECHA_NAC_ORDENANTE' in row else ''}</td>
                            <td>{'Sí' if row.get('es_Agente', False) else 'No'}</td>
                            <td>{'Sí' if row.get('es_PEP', False) else 'No'}</td>
                            <td>{beneficiario}</td>
                            <td>{row['PAIS_DESTINO'] if 'PAIS_DESTINO' in row else ''}</td>
                            <td>{row['ENT_NAT_REF_COD'] if 'ENT_NAT_REF_COD' in row else ''}</td>
                            <td>"""
                        
                        # Añadir indicadores que afectan a esta transacción
                        if tx_id in transaction_indicators:
                            for ind in transaction_indicators[tx_id]:
                                motivo_texto = f" - {ind['motivo']}" if 'motivo' in ind and ind['motivo'] else ""
                                html_table += f"<b>I{ind['id']}</b>: {ind['score']}/4{motivo_texto}<br>"
                        
                        html_table += """</td>
                        </tr>
                        """
                    
                    html_table += """
                        </tbody>
                    </table>
                    </div>
                    """
                    
                    # Mostrar la tabla
                    import streamlit.components.v1 as components
                    components.html(html_table, height=500, scrolling=True)
                    
                    # Preparar un DataFrame con el mismo formato que la tabla mostrada
                    export_columns = [
                        'NUMERO_TRANSACCION', 'FECHA', 'HORA', 'IMPORTE', 'ESTADO_OPERACION', 
                        'PAIS_ORIGEN', 'NOMBRE_ORDENANTE', 'APELLIDO_ORDENANTE', 'PAIS_DOC_ORDENANTE',
                        'NUM_DOC_ORDENANTE', 'PAIS_NAC_ORDENANTE', 'FECHA_NAC_ORDENANTE',
                        'es_Agente', 'es_PEP', 'NOMBRE_BENEFICIARIO', 'APELLIDO_BENEFICIARIO',
                        'PAIS_DESTINO', 'ENT_NAT_REF_COD', 'Indicadores', 'Motivo_Riesgo'
                    ]
                    
                    # Crear una copia del DataFrame para no modificar el original
                    export_df = suspicious_df.copy()
                    
                    # Asegurar que todas las columnas necesarias existen
                    for col in export_columns:
                        if col not in export_df.columns:
                            export_df[col] = ''
                            
                    # Añadir columna de indicadores con formato EXACTAMENTE igual a la tabla mostrada
                    export_df['Indicadores'] = ''
                    for idx, row in export_df.iterrows():
                        tx_id = str(row['NUMERO_TRANSACCION'])
                        if tx_id in transaction_indicators:
                            # Usamos el mismo formato exacto que en la tabla HTML
                            indicadores_html = []
                            for ind in transaction_indicators[tx_id]:
                                motivo_texto = f" - {ind['motivo']}" if 'motivo' in ind and ind['motivo'] else ""
                                indicadores_html.append(f"I{ind['id']}: {ind['score']}/4{motivo_texto}")
                            # Unimos con salto de línea para preservar el formato como en la tabla
                            # Formateamos los indicadores para que se vean exactamente como en la tabla HTML
                            export_df.at[idx, 'Indicadores'] = "\n".join(indicadores_html)
                    
                    # Formatear columnas booleanas
                    if 'es_Agente' in export_df.columns:
                        export_df['es_Agente'] = export_df['es_Agente'].apply(lambda x: 'Sí' if x else 'No')
                    if 'es_PEP' in export_df.columns:
                        export_df['es_PEP'] = export_df['es_PEP'].apply(lambda x: 'Sí' if x else 'No')
                    
                    # Opción para descargar como Excel para mantener mejor el formato
                    from io import BytesIO
                    import xlsxwriter
                    
                    # Crear un Excel en memoria
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                        export_df[export_columns].to_excel(writer, index=False, sheet_name='Transacciones')
                        
                        # Ajustar ancho de las columnas
                        workbook = writer.book
                        worksheet = writer.sheets['Transacciones']
                        
                        # Dar formato a las celdas para mostrar saltos de línea
                        wrap_format = workbook.add_format({'text_wrap': True, 'valign': 'top'})
                        
                        # Aplicar formato a todas las celdas y ajustar anchura
                        for i, col in enumerate(export_df[export_columns].columns):
                            # Obtener el ancho máximo
                            max_len = max(export_df[col].astype(str).map(len).max(), len(str(col))) + 3
                            worksheet.set_column(i, i, max_len, wrap_format)
                            
                        # Dar altura extra a las filas para acomodar múltiples líneas
                        for i in range(len(export_df) + 1):  # +1 para la cabecera
                            worksheet.set_row(i, 30)
                    
                    # Obtener los datos del Excel
                    excel_data = output.getvalue()
                    
                    # Botón para descargar
                    st.download_button(
                        label="Descargar Excel de Transacciones Sospechosas",
                        data=excel_data,
                        file_name="transacciones_sospechosas.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                    
 
