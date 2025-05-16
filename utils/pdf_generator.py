"""
Generación de informes en PDF para el análisis de riesgo.
"""
import io
import base64
from datetime import datetime
from typing import Dict, List, Union, Any, Optional, Tuple

import pandas as pd
import numpy as np
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from io import BytesIO
import base64

# Importar función para formatear valores de riesgo
from utils.fixed_risk_indicators import formatear_valor_riesgo


def generate_indicators_pdf(
    indicators_df: pd.DataFrame,
    title: str = "Informe de Indicadores de Riesgo",
    indicator_descriptions: Dict[str, Dict[str, str]] = None,
    indicator_types: Dict[str, str] = None
) -> str:
    """
    Genera un informe PDF a partir del DataFrame de indicadores de riesgo,
    con el mismo formato exacto que el CSV.
    
    Args:
        indicators_df: DataFrame con los indicadores de riesgo
        title: Título del informe
        indicator_descriptions: Descripciones de los indicadores
        indicator_types: Tipos de los indicadores (DOCUMENTACIÓN, UMBRALES, etc.)
        
    Returns:
        String en base64 con el PDF generado
    """
    # Configurar el documento
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    
    # Personalizar estilos
    styles.add(ParagraphStyle(name='Center', alignment=1))
    styles.add(ParagraphStyle(name='Right', alignment=2))
    styles.add(ParagraphStyle(name='Left', alignment=0))
    
    # Preparar contenido
    elements = []
    
    # Título e introducción
    elements.append(Paragraph(f"<b>{title}</b>", styles['Title']))
    elements.append(Spacer(1, 0.25*inch))
    
    fecha_actual = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    elements.append(Paragraph(f"<i>Generado el {fecha_actual}</i>", styles['Italic']))
    elements.append(Spacer(1, 0.25*inch))
    
    # Agregar descripción del informe
    elements.append(Paragraph("Este informe muestra los indicadores de riesgo detectados en el análisis de los datos financieros seleccionados. La puntuación de riesgo se basa en una escala de 1 a 4, donde 1 representa riesgo bajo y 4 representa riesgo crítico.", styles['Normal']))
    elements.append(Spacer(1, 0.25*inch))
    
    # Crear tabla de indicadores
    data = []
    
    # Adaptamos los encabezados a las columnas reales que existen en el DataFrame
    headers = ["ID", "Indicador", "Tipo", "Puntuación", "Nivel", "Peso"]
    data.append(headers)
    
    # Añadir filas con los datos de indicadores
    for _, row in indicators_df.iterrows():
        data.append([
            str(row['ID']),
            row['Indicador'],
            row.get('Tipo', ""),
            f"{row['Puntuación']:.2f}" if isinstance(row['Puntuación'], (int, float)) else str(row['Puntuación']),
            row['Nivel'],
            row.get('Peso', "")
        ])
    
    # Configurar la tabla
    table_style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ALIGN', (0, 1), (0, -1), 'CENTER'),  # ID centrado
        ('ALIGN', (1, 1), (1, -1), 'LEFT'),    # Categoría alineada a la izquierda
        ('ALIGN', (2, 1), (2, -1), 'LEFT'),    # Indicador alineado a la izquierda
        ('ALIGN', (3, 1), (3, -1), 'LEFT'),    # Descripción alineada a la izquierda
        ('ALIGN', (4, 1), (4, -1), 'CENTER'),  # Puntuación centrada
        ('ALIGN', (5, 1), (5, -1), 'CENTER'),  # Nivel centrado
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ])
    
    # Aplicar colores según nivel de riesgo
    for i, row in enumerate(data[1:], 1):
        nivel = row[5]
        if nivel == "BAJO":
            table_style.add('BACKGROUND', (5, i), (5, i), colors.lightgreen)
        elif nivel == "MEDIO":
            table_style.add('BACKGROUND', (5, i), (5, i), colors.yellow)
        elif nivel == "ALTO":
            table_style.add('BACKGROUND', (5, i), (5, i), colors.orange)
        elif nivel == "CRÍTICO":
            table_style.add('BACKGROUND', (5, i), (5, i), colors.red)
    
    # Crear la tabla y ajustar anchos de columna
    col_widths = [30, 180, 80, 70, 70, 50]  # Ancho de las columnas ajustadas
    table = Table(data, colWidths=col_widths)
    table.setStyle(table_style)
    elements.append(table)
    
    # Agregar leyenda de niveles de riesgo
    elements.append(Spacer(1, 0.5*inch))
    elements.append(Paragraph("<b>Leyenda de Niveles de Riesgo:</b>", styles['Normal']))
    elements.append(Spacer(1, 0.1*inch))
    
    legend_data = [
        ["Nivel", "Puntuación", "Descripción"],
        ["BAJO", "1.00 - 1.99", "Riesgo bajo, no requiere acción inmediata"],
        ["MEDIO", "2.00 - 2.99", "Riesgo moderado, requiere monitoreo"],
        ["ALTO", "3.00 - 3.99", "Riesgo alto, requiere atención pronta"],
        ["CRÍTICO", "4.00", "Riesgo crítico, requiere acción inmediata"]
    ]
    
    legend_style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (0, 1), colors.lightgreen),
        ('BACKGROUND', (0, 2), (0, 2), colors.yellow),
        ('BACKGROUND', (0, 3), (0, 3), colors.orange),
        ('BACKGROUND', (0, 4), (0, 4), colors.red),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ALIGN', (0, 1), (0, -1), 'CENTER'),
        ('ALIGN', (1, 1), (1, -1), 'CENTER'),
        ('ALIGN', (2, 1), (2, -1), 'LEFT'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
    ])
    
    legend_table = Table(legend_data, colWidths=[60, 80, 300])
    legend_table.setStyle(legend_style)
    elements.append(legend_table)
    
    # Agregar función para números de página
    def add_page_number(canvas, doc):
        canvas.saveState()
        canvas.setFont('Helvetica', 8)
        page_num = f"Página {doc.page} de ?"  # No podemos saber el total exacto de páginas
        canvas.drawRightString(
            doc.width + doc.leftMargin - 10,
            doc.bottomMargin - 20,
            page_num
        )
        canvas.drawString(
            doc.leftMargin,
            doc.bottomMargin - 20,
            f"Generado: {fecha_actual}"
        )
        canvas.restoreState()
    
    # Generar PDF
    doc.build(elements, onFirstPage=add_page_number, onLaterPages=add_page_number)
    
    # Convertir PDF a base64
    pdf_data = buffer.getvalue()
    buffer.close()
    encoded_pdf = base64.b64encode(pdf_data).decode('utf-8')
    
    return encoded_pdf


def generate_risk_report(
    df: pd.DataFrame,
    risk_scores: Dict[str, Dict[str, float]],
    risk_details: Dict[str, Dict[str, Any]],
    selected_agents: List[str],
    selected_subjects: List[str],
    indicator_descriptions: Dict[str, Dict[str, str]],
    indicator_types: Dict[str, str] = None,
    filename: str = "informe_riesgo.pdf"
) -> str:
    """
    Genera un informe detallado en PDF del análisis de riesgo realizado,
    con el mismo formato que el informe Excel.
    
    Args:
        df: DataFrame con datos analizados
        risk_scores: Diccionario con puntuaciones de riesgo por agente y por indicador.
                    Formato: {agente1: {1: valor, 2: valor, ...}, agente2: {...}}
        risk_details: Diccionario con detalles por indicador (transacciones sospechosas)
        selected_agents: Lista de agentes seleccionados para el análisis
        selected_subjects: Lista de sujetos obligados seleccionados
        indicator_descriptions: Diccionario con descripciones de indicadores
        indicator_types: Diccionario opcional con tipos de indicadores
        filename: Nombre del archivo PDF a generar
        
    Returns:
        URL del PDF para descarga en Streamlit
    """
    # FUNCIÓN DE DEPURACIÓN - en modo seguro para evitar errores
    def debug_print(message, obj=None):
        try:
            print(f"DEBUG PDF: {message}")
            if obj is not None:
                if isinstance(obj, dict):
                    print(f"  - Tipo: {type(obj)}, Claves: {list(obj.keys())[:5]}...")
                elif isinstance(obj, list):
                    print(f"  - Tipo: {type(obj)}, Longitud: {len(obj)}, Primeros elementos: {obj[:3]}...")
                else:
                    print(f"  - Tipo: {type(obj)}, Valor: {str(obj)[:100]}...")
        except Exception as e:
            print(f"Error en depuración: {str(e)}")
            pass
    # Crear un buffer para el PDF en memoria
    buffer = io.BytesIO()
    
    # Crear el documento
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=A4,
        leftMargin=1.5*cm,
        rightMargin=1.5*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )
    
    # Obtener estilos
    styles = getSampleStyleSheet()
    
    # Crear estilo para títulos
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        fontSize=18,
        alignment=1, # Centrado
        spaceAfter=12
    )
    
    subtitle_style = ParagraphStyle(
        'SubtitleStyle',
        parent=styles['Heading2'],
        fontSize=14,
        spaceBefore=12,
        spaceAfter=8
    )
    
    info_style = ParagraphStyle(
        'InfoStyle',
        parent=styles['Normal'],
        fontSize=10,
        spaceBefore=6,
        spaceAfter=6
    )
    
    normal_style = styles['Normal']
    
    # Elementos del PDF
    elements = []
    
    # Título del informe
    date_str = datetime.now().strftime("%d/%m/%Y %H:%M")
    
    # Título principal
    elements.append(Paragraph(f"INFORME DE ANÁLISIS DE RIESGO", title_style))
    elements.append(Paragraph(f"Fecha: {date_str}", info_style))
    elements.append(Spacer(1, 0.5*cm))
    
    # Resumen de datos analizados
    elements.append(Paragraph("1. Resumen de Datos Analizados", subtitle_style))
    
    # Información sobre datos analizados
    total_rows = len(df)
    start_date = df['FECHA'].min() if 'FECHA' in df.columns and not df.empty else "N/A"
    end_date = df['FECHA'].max() if 'FECHA' in df.columns and not df.empty else "N/A"
    
    # Tabla de resumen
    summary_data = [
        ["Total de transacciones", f"{total_rows:,}"],
        ["Período analizado", f"{start_date} a {end_date}"],
        ["Número de agentes", f"{len(selected_agents)}"],
        ["Número de sujetos obligados", f"{len(selected_subjects)}"]
    ]
    
    t = Table(summary_data, colWidths=[10*cm, 6*cm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.black),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
    ]))
    elements.append(t)
    
    elements.append(Spacer(1, 0.5*cm))
    
    # Filtros aplicados
    elements.append(Paragraph("2. Filtros Aplicados", subtitle_style))
    
    # Preparar listas de sujetos obligados y agentes de manera más legible
    elements.append(Paragraph("2.1. Sujetos Obligados Seleccionados:", info_style))
    if selected_subjects:
        # Crear una lista formateada en columnas
        subjects_data = []
        subjects_row = []
        for i, subject in enumerate(sorted(selected_subjects)):
            subjects_row.append(subject)
            if (i + 1) % 3 == 0 or i == len(selected_subjects) - 1:
                # Completar la fila con celdas vacías si es necesario
                while len(subjects_row) < 3:
                    subjects_row.append("")
                subjects_data.append(subjects_row)
                subjects_row = []
        
        # Crear tabla para los sujetos obligados
        subjects_table = Table(subjects_data, colWidths=[5*cm, 5*cm, 5*cm])
        subjects_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ('BACKGROUND', (0, 0), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ]))
        elements.append(subjects_table)
    else:
        elements.append(Paragraph("Todos los sujetos obligados", normal_style))
    
    elements.append(Spacer(1, 0.3*cm))
    
    # Lista de agentes seleccionados
    elements.append(Paragraph("2.2. Agentes Seleccionados:", info_style))
    if selected_agents:
        # Crear una lista formateada en columnas
        agents_data = []
        agents_row = []
        for i, agent in enumerate(sorted(selected_agents)):
            agents_row.append(agent)
            if (i + 1) % 3 == 0 or i == len(selected_agents) - 1:
                # Completar la fila con celdas vacías si es necesario
                while len(agents_row) < 3:
                    agents_row.append("")
                agents_data.append(agents_row)
                agents_row = []
        
        # Crear tabla para los agentes
        agents_table = Table(agents_data, colWidths=[5*cm, 5*cm, 5*cm])
        agents_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ('BACKGROUND', (0, 0), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ]))
        elements.append(agents_table)
    else:
        elements.append(Paragraph("Todos los agentes", normal_style))
    
    elements.append(Spacer(1, 0.7*cm))
    
    # Resultados del análisis de riesgo
    elements.append(Paragraph("3. Resultados del Análisis de Riesgo", subtitle_style))
    
    # Determinar todos los indicadores únicos y sus tipos
    all_indicators = [str(i) for i in range(1, 21)]
    
    # Agrupar indicadores por tipo
    indicators_by_type = {}
    for ind_id in all_indicators:
        ind_type = indicator_types.get(ind_id, "General")
        if ind_type not in indicators_by_type:
            indicators_by_type[ind_type] = []
        indicators_by_type[ind_type].append(ind_id)
    
    # PARTE 1: TABLA DE ANÁLISIS DE RIESGO POR AGENTE (como en Excel)
    elements.append(Paragraph("3.1. Análisis de Riesgo por Agente", subtitle_style))
    
    # Crear encabezados para la tabla principal de riesgos por agente
    headers = ["Entidad", "Riesgo Global"]
    
    # Añadir encabezados para los tipos de indicadores
    sorted_types = sorted(indicators_by_type.keys())
    for ind_type in sorted_types:
        headers.append(f"Riesgo {ind_type}")
    
    # Añadir encabezados para cada indicador individual
    for ind_id in all_indicators:
        ind_desc = indicator_descriptions.get(ind_id, {}).get('description', f"Indicador {ind_id}")[:20]
        headers.append(f"Ind. {ind_id}: {ind_desc}")
    
    # Crear data para la tabla: una fila por agente + fila de promedio
    data = [headers]
    
    # Calcular promedios (excluyendo 'GLOBAL')
    # Inicializar diccionario para la suma de valores por indicador
    sumas_por_indicador = {str(i): 0 for i in range(1, 21)}
    conteos_por_indicador = {str(i): 0 for i in range(1, 21)}
    
    # Diccionario para almacenar promedios por tipo de riesgo
    promedios_por_tipo = {tipo: 0 for tipo in sorted_types}
    conteos_por_tipo = {tipo: 0 for tipo in sorted_types}
    
    # Obtener todos los agentes que tienen datos de riesgo (excluyendo 'GLOBAL')
    agents_with_data = [agent for agent in risk_scores.keys() if agent != "GLOBAL"]
    
    # Debug para verificar puntuaciones por agente
    debug_print("Risk scores por agente", risk_scores)
    
    # Para cada agente, crear una fila con sus datos
    for agent in agents_with_data:
        # Inicializar fila con el nombre del agente
        row = [agent]
        
        # Calcular riesgo global (promedio de los 20 indicadores) para este agente
        agent_scores = risk_scores.get(agent, {})
        debug_print(f"Agent: {agent}, Scores:", agent_scores)
        
        if agent_scores:
            # Convertir todas las puntuaciones a float de manera segura
            total_valid = 0
            total_sum = 0
            for i in range(1, 21):
                ind_id = str(i)
                if ind_id in agent_scores:
                    try:
                        score_value = float(agent_scores[ind_id])
                        total_sum += score_value
                        total_valid += 1
                    except (ValueError, TypeError):
                        pass
            
            if total_valid > 0:
                total_risk = total_sum / total_valid
            else:
                total_risk = 1.0  # Valor predeterminado si no hay datos válidos
                
            row.append(formatear_valor_riesgo(total_risk))
        else:
            row.append(formatear_valor_riesgo(1.0))  # Valor por defecto si no hay datos
        
        # Calcular promedios por tipo de indicador para este agente
        for ind_type in sorted_types:
            type_indicators = indicators_by_type.get(ind_type, [])
            
            # Convertir indicadores a valores numéricos de manera segura
            valid_scores = []
            for ind_id in type_indicators:
                if ind_id in agent_scores:
                    try:
                        score_value = float(agent_scores[ind_id])
                        valid_scores.append(score_value)
                    except (ValueError, TypeError):
                        pass
            
            if valid_scores:
                type_avg = sum(valid_scores) / len(valid_scores)
            else:
                type_avg = 1.0  # Valor predeterminado
                
            # Añadir a promedios globales
            promedios_por_tipo[ind_type] += type_avg
            conteos_por_tipo[ind_type] += 1
            
            # Añadir a la fila
            row.append(formatear_valor_riesgo(type_avg))
        
        # Añadir puntajes para cada indicador individual
        for ind_id in all_indicators:
            # Extraer el valor del indicador de manera segura
            if ind_id in agent_scores:
                try:
                    score = float(agent_scores[ind_id])
                except (ValueError, TypeError):
                    score = 1.0  # Valor predeterminado si no es número
            else:
                score = 1.0  # Valor predeterminado si no existe
            
            # Contribuir al promedio general (excluyendo 'GLOBAL')
            sumas_por_indicador[ind_id] += score
            conteos_por_indicador[ind_id] += 1
            
            # Convertir a formato de texto antes de añadir a la fila
            score_text = formatear_valor_riesgo(score)
            row.append(score_text)
        
        # Añadir la fila a los datos de la tabla
        data.append(row)
    
    # Calcular promedios finales
    promedios = {}
    for ind_id in all_indicators:
        if conteos_por_indicador[ind_id] > 0:
            promedios[ind_id] = sumas_por_indicador[ind_id] / conteos_por_indicador[ind_id]
        else:
            promedios[ind_id] = 1.0
    
    # Añadir fila de PROMEDIOS (usando solo los valores de los agentes individuales)
    promedio_row = ["PROMEDIO"]
    
    # Calcular promedio global (promedio de todos los indicadores)
    total_avg = sum(promedios.values()) / len(promedios)
    promedio_row.append(formatear_valor_riesgo(total_avg))
    
    # Añadir promedios por tipo
    for ind_type in sorted_types:
        if conteos_por_tipo[ind_type] > 0:
            type_avg = promedios_por_tipo[ind_type] / conteos_por_tipo[ind_type]
        else:
            type_avg = 1.0
        promedio_row.append(formatear_valor_riesgo(type_avg))
    
    # Añadir promedios para cada indicador individual
    for ind_id in all_indicators:
        promedio_row.append(formatear_valor_riesgo(promedios[ind_id]))
    
    # Añadir fila de promedios a los datos
    data.append(promedio_row)
    
    # Crear la tabla principal
    col_widths = [3*cm]  # Primera columna más ancha
    for i in range(1, len(headers)):
        if i <= 1 + len(sorted_types):  # Columnas de riesgo global y tipos
            col_widths.append(2*cm)
        else:  # Columnas de indicadores individuales
            col_widths.append(1.7*cm)
    
    # Ajustar anchos para que quepa en la página
    total_width = sum(col_widths)
    if total_width > 18*cm:  # 21cm (A4) - márgenes
        scale_factor = 18*cm / total_width
        col_widths = [w * scale_factor for w in col_widths]
    
    risk_table = Table(data, colWidths=col_widths)
    
    # Estilos base de la tabla
    table_style = [
        # Encabezados con mejor visibilidad
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkgrey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),  # Texto más pequeño en encabezados
        ('TOPPADDING', (0, 0), (-1, 0), 5),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 5),
        
        # Cuerpo de la tabla
        ('FONTSIZE', (0, 1), (-1, -1), 8),  # Texto más pequeño en el cuerpo
        ('ALIGN', (1, 1), (-1, -1), 'CENTER'),  # Centrar todos los valores
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        
        # Fila de promedios
        ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        
        # Bordes
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ]
    
    # Añadir colores según nivel de riesgo para todas las celdas con valores numéricos
    for row in range(1, len(data)):  # Para cada fila (excepto encabezados)
        for col in range(1, len(data[0])):  # Para cada columna con valores
            try:
                # Intentar convertir a número
                value = float(data[row][col]) if not isinstance(data[row][col], str) else float(data[row][col].replace(',', '.'))
                
                # Asignar color según nivel de riesgo
                if value < 2:
                    table_style.append(('TEXTCOLOR', (col, row), (col, row), colors.green))
                elif value < 3:
                    table_style.append(('TEXTCOLOR', (col, row), (col, row), colors.orange))
                elif value < 3.5:
                    table_style.append(('TEXTCOLOR', (col, row), (col, row), colors.red))
                else:
                    table_style.append(('TEXTCOLOR', (col, row), (col, row), colors.darkred))
            except:
                pass  # No es un número, ignorar
    
    risk_table.setStyle(TableStyle(table_style))
    elements.append(risk_table)
    
    elements.append(Spacer(1, 0.5*cm))
    
    # PARTE 2: TRANSACCIONES SOSPECHOSAS (como en el Excel)
    elements.append(Paragraph("3.2. Operaciones Sospechosas", subtitle_style))
    elements.append(Spacer(1, 0.3*cm))
    
    # Recopilar transacciones sospechosas de todos los indicadores
    suspicious_transactions = []
    
    # Debug para verificar risk_details
    debug_print("Risk details structure", risk_details)
    
    # Verificar si risk_details contiene transacciones en una estructura compleja
    if isinstance(risk_details, dict):
        # Combinar todas las transacciones sospechosas en una lista
        for ind_id, ind_details in risk_details.items():
            debug_print(f"Procesando indicador {ind_id}", ind_details)
            
            if isinstance(ind_details, dict) and 'transactions' in ind_details:
                transactions_data = ind_details['transactions']
                debug_print(f"Transactions data type", type(transactions_data))
                
                # Si es una lista de DataFrames o diccionarios
                if isinstance(transactions_data, list):
                    for i, tx in enumerate(transactions_data):
                        if isinstance(tx, pd.DataFrame):
                            debug_print(f"DataFrame en posición {i}, shape: {tx.shape}")
                            # Procesar cada fila del DataFrame
                            for _, row in tx.iterrows():
                                # Solo incluir si tiene Motivo_Riesgo
                                if 'Motivo_Riesgo' in row and pd.notna(row['Motivo_Riesgo']):
                                    tx_dict = row.to_dict()
                                    tx_dict['INDICADOR'] = ind_id
                                    suspicious_transactions.append(tx_dict)
                        elif isinstance(tx, dict):
                            # Solo incluir si tiene Motivo_Riesgo
                            if 'Motivo_Riesgo' in tx and pd.notna(tx['Motivo_Riesgo']):
                                tx_copy = tx.copy()  # Hacer una copia para no modificar el original
                                tx_copy['INDICADOR'] = ind_id
                                suspicious_transactions.append(tx_copy)
                # Si es un solo DataFrame
                elif isinstance(transactions_data, pd.DataFrame):
                    debug_print(f"DataFrame único para indicador {ind_id}, shape: {transactions_data.shape}")
                    for _, row in transactions_data.iterrows():
                        # Solo incluir si tiene Motivo_Riesgo
                        if 'Motivo_Riesgo' in row and pd.notna(row['Motivo_Riesgo']):
                            tx_dict = row.to_dict()
                            tx_dict['INDICADOR'] = ind_id
                            suspicious_transactions.append(tx_dict)
    
    # Si no hay transacciones sospechosas, mostrar mensaje
    if not suspicious_transactions:
        elements.append(Paragraph("No se encontraron operaciones sospechosas.", info_style))
    else:
        # Seleccionar columnas más importantes a mostrar (como en Excel)
        risk_columns = [
            "NUMERO_TRANSACCION", "FECHA", "IMPORTE", "ESTADO_OPERACION", 
            "NOMBRE_ORDENANTE", "APELLIDO_ORDENANTE", "PAIS_DOC_ORDENANTE",
            "NOMBRE_BENEFICIARIO", "APELLIDO_BENEFICIARIO", "PAIS_DESTINO",
            "Motivo_Riesgo", "INDICADOR"
        ]
        
        # Crear tabla con encabezados
        headers = [col.replace("_", " ").title() for col in risk_columns]
        data = [headers]
        
        # Añadir filas de datos
        for tx in suspicious_transactions:
            row = []
            for col in risk_columns:
                # Obtener el valor si existe, sino ''
                value = tx.get(col, '')
                
                # Formatear fechas
                if col == 'FECHA' and pd.notna(value):
                    if isinstance(value, pd.Timestamp) or isinstance(value, datetime):
                        value = value.strftime('%d/%m/%Y')
                    elif isinstance(value, str) and len(value) > 10:
                        try:
                            value = pd.to_datetime(value).strftime('%d/%m/%Y')
                        except:
                            pass
                
                # Formatear importes
                elif col == 'IMPORTE' and pd.notna(value):
                    try:
                        value = f"{float(value):,.2f}"
                    except:
                        pass
                        
                row.append(str(value) if pd.notna(value) else '')
            
            data.append(row)
        
        # Limitar a un máximo de filas para no hacer el PDF demasiado grande
        max_rows = 50  # Ajustar según necesidad
        if len(data) > max_rows + 1:  # +1 por el encabezado
            data = data[:max_rows + 1]
            elements.append(Paragraph(f"Mostrando las primeras {max_rows} transacciones sospechosas (de un total de {len(suspicious_transactions)}):", info_style))
        else:
            elements.append(Paragraph(f"Total de transacciones sospechosas: {len(suspicious_transactions)}", info_style))
        
        elements.append(Spacer(1, 0.2*cm))
        
        # Crear tabla responsive (ajustar el ancho de columnas según el contenido)
        col_widths = []
        for i, col in enumerate(risk_columns):
            if col in ['NUMERO_TRANSACCION', 'FECHA', 'IMPORTE', 'ESTADO_OPERACION', 'INDICADOR']:
                col_widths.append(1.5*cm)
            elif col in ['Motivo_Riesgo']:
                col_widths.append(4*cm)
            else:
                col_widths.append(2*cm)
        
        # Ajustar anchos para que quepa en la página
        total_width = sum(col_widths)
        if total_width > 18*cm:  # 21cm (A4) - márgenes
            scale_factor = 18*cm / total_width
            col_widths = [w * scale_factor for w in col_widths]
        
        # Crear tabla
        susp_table = Table(data, colWidths=col_widths, repeatRows=1)
        
        # Estilos de la tabla
        table_style = [
            # Encabezados
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 7),  # Texto pequeño para que quepa
            
            # Centrar algunas columnas
            ('ALIGN', (0, 1), (0, -1), 'CENTER'),  # NUMERO_TRANSACCION
            ('ALIGN', (1, 1), (1, -1), 'CENTER'),  # FECHA
            ('ALIGN', (2, 1), (2, -1), 'RIGHT'),   # IMPORTE
            
            # Bordes
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]
        
        susp_table.setStyle(TableStyle(table_style))
        elements.append(susp_table)
    
    elements.append(Spacer(1, 0.5*cm))
    
    # Pie de página
    elements.append(Spacer(1, 1*cm))
    elements.append(Paragraph(
        "Este informe ha sido generado automáticamente por el sistema de análisis de riesgo. " +
        "Los resultados deben ser interpretados por personal especializado.",
        ParagraphStyle('Footer', parent=styles['Italic'], fontSize=8, alignment=1)
    ))
    
    # Construir el documento
    doc.build(elements)
    
    # Obtener el PDF del buffer
    pdf_data = buffer.getvalue()
    buffer.close()
    
    # Codificar para descargar en Streamlit
    b64_pdf = base64.b64encode(pdf_data).decode('utf-8')
    
    return b64_pdf


def get_download_link(pdf_data: str, filename: str = "informe_riesgo.pdf") -> str:
    """
    Crea un enlace HTML para descargar el PDF.
    
    Args:
        pdf_data: Datos del PDF en base64
        filename: Nombre del archivo para la descarga
        
    Returns:
        Enlace HTML para descargar
    """
    href = f'<a href="data:application/octet-stream;base64,{pdf_data}" download="{filename}">Descargar Informe PDF</a>'
    return href