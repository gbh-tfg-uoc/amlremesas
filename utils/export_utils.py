"""
Utilidades para exportar gráficos y datos a diferentes formatos.
"""
import io
import base64
from datetime import datetime
from typing import Dict, List, Any, Optional, Union, Tuple
from collections import Counter

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm

# Importar funciones para descripciones de indicadores
from utils.risk_indicators import get_indicator_descriptions, get_indicator_names



def export_figures_to_pdf(
    figures: List[go.Figure],
    titles: List[str],
    filtered_df: pd.DataFrame,
    filename: str = "informe_analisis_datos.pdf"
) -> str:
    """
    Exporta una colección de gráficos Plotly a un archivo PDF con formato mejorado.

    Args:
        figures: Lista de objetos Plotly Figure
        titles: Lista de títulos correspondientes a cada gráfico
        filtered_df: DataFrame con los datos filtrados para incluir un resumen
        filename: Nombre del archivo PDF

    Returns:
        Datos del PDF en base64 para descarga
    """
    # Crear un buffer de memoria para el PDF
    buffer = io.BytesIO()

    # Crear el documento
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=A4,
        leftMargin=1.5*cm,
        rightMargin=1.5*cm,
        topMargin=2*cm,
        bottomMargin=2*cm,
        title="Informe de Análisis de Datos Financieros"
    )

    # Obtener estilos para el PDF
    styles = getSampleStyleSheet()

    # Crear estilos personalizados
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        fontSize=20,
        alignment=1,  # Centrado
        spaceAfter=12,
        textColor=colors.darkblue
    )

    subtitle_style = ParagraphStyle(
        'SubtitleStyle',
        parent=styles['Heading2'],
        fontSize=16,
        spaceBefore=12,
        spaceAfter=10,
        textColor=colors.darkblue
    )

    section_style = ParagraphStyle(
        'SectionStyle',
        parent=styles['Heading3'],
        fontSize=14,
        spaceBefore=10,
        spaceAfter=6,
        textColor=colors.blue
    )

    caption_style = ParagraphStyle(
        'CaptionStyle',
        parent=styles['Italic'],
        fontSize=9,
        alignment=1,  # Centrado
        spaceAfter=15,
        textColor=colors.darkslategray
    )

# Define una función para el pie de página y numeración
    def add_page_number(canvas, doc):
        """Añade número de página y fecha en el pie de página"""
        canvas.saveState()
        canvas.setFont('Helvetica', 8)
        # Fecha en la izquierda
        canvas.drawString(doc.leftMargin, 0.75 * cm, 
                        datetime.now().strftime("%d/%m/%Y %H:%M"))
        # Número de página en la derecha
        canvas.drawRightString(A4[0] - doc.rightMargin, 0.75 * cm, 
                            f"Página {canvas.getPageNumber()}")
        canvas.restoreState()

    # Lista para los elementos del PDF
    elements = []

    # Portada
    elements.append(Spacer(1, 3*cm))
    elements.append(Paragraph("INFORME DE ANÁLISIS DE DATOS FINANCIEROS", title_style))
    elements.append(Spacer(1, 1*cm))

    # Fecha de generación
    date_str = datetime.now().strftime("%d de %B de %Y, %H:%M")
    elements.append(Paragraph(f"Generado el: {date_str}", 
                             ParagraphStyle('Date', parent=styles["Normal"], 
                                           alignment=1, spaceAfter=5)))

    elements.append(Spacer(1, 2*cm))

    # Datos del informe
    elements.append(Paragraph("Este informe contiene:", 
                            ParagraphStyle('Info', parent=styles["Normal"], 
                                         alignment=1, fontSize=12)))
    elements.append(Spacer(1, 0.3*cm))

    # Lista de contenidos
    contents = [
        "• Resumen de los datos analizados con estadísticas clave",
        f"• {len(figures)} visualizaciones detalladas",
        "• Análisis de transacciones financieras"
    ]

    for item in contents:
        elements.append(Paragraph(item, 
                               ParagraphStyle('ListItem', parent=styles["Normal"], 
                                            alignment=1, fontSize=11, spaceAfter=5)))

    # Salto de página después de la portada
    elements.append(PageBreak())

    # Índice
    elements.append(Paragraph("ÍNDICE", subtitle_style))
    elements.append(Spacer(1, 0.5*cm))

    index_items = [
        ["1. Resumen de Datos Analizados", ""],
    ]

    for i, title in enumerate(titles):
        index_items.append([f"2.{i+1}. {title}", ""])

    # Tabla de índice
    index_table = Table(index_items, colWidths=[16*cm, 1*cm])
    index_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('LINEBELOW', (0, 0), (-1, -1), 0.5, colors.lightgrey),
    ]))

    elements.append(index_table)
    elements.append(Spacer(1, 1*cm))
    elements.append(PageBreak())

    # Resumen de datos
    elements.append(Paragraph("1. RESUMEN DE DATOS ANALIZADOS", subtitle_style))
    elements.append(Spacer(1, 0.5*cm))

    # Extraer información sobre datos analizados
    total_rows = len(filtered_df)

    # Determinar rango de fechas
    if 'FECHA' in filtered_df.columns and not filtered_df.empty:
        try:
            start_date = filtered_df['FECHA'].min() 
            end_date = filtered_df['FECHA'].max()
            # Formatear fechas si son datetime
            if hasattr(start_date, 'strftime'):
                start_date = start_date.strftime("%d/%m/%Y")
            if hasattr(end_date, 'strftime'):
                end_date = end_date.strftime("%d/%m/%Y")
        except:
            start_date = "N/A" 
            end_date = "N/A"
    else:
        start_date = "N/A" 
        end_date = "N/A"

    # Calcular estadísticas de importes
    if 'IMPORTE' in filtered_df.columns and not filtered_df.empty:
        try:
            total_amount = filtered_df['IMPORTE'].sum()
            avg_amount = filtered_df['IMPORTE'].mean()
            max_amount = filtered_df['IMPORTE'].max()
            min_amount = filtered_df['IMPORTE'].min()

            # Calcular valor mediano
            median_amount = filtered_df['IMPORTE'].median()
            # Calcular percentiles 25 y 75
            p25 = filtered_df['IMPORTE'].quantile(0.25)
            p75 = filtered_df['IMPORTE'].quantile(0.75)
        except:
            total_amount = 0
            avg_amount = 0
            max_amount = 0
            min_amount = 0
            median_amount = 0
            p25 = 0
            p75 = 0
    else:
        total_amount = 0
        avg_amount = 0
        max_amount = 0
        min_amount = 0
        median_amount = 0
        p25 = 0
        p75 = 0

    # Datos generales para el resumen
    summary_data = [
        ["Métrica", "Valor"],
        ["Total de transacciones", f"{total_rows:,}"],
        ["Período analizado", f"{start_date} a {end_date}"],
        ["Importe total", f"{total_amount:,.2f} €"],
        ["Importe promedio", f"{avg_amount:,.2f} €"],
        ["Importe máximo", f"{max_amount:,.2f} €"],
        ["Importe mínimo", f"{min_amount:,.2f} €"],
        ["Importe mediano", f"{median_amount:,.2f} €"],
    ]

    # Añadir información de países si está disponible
    if 'PAIS_DESTINO' in filtered_df.columns and not filtered_df.empty:
        try:
            # Top países destino
            top_countries = filtered_df['PAIS_DESTINO'].value_counts().nlargest(3)
            top_countries_str = ", ".join([f"{country} ({count})" for country, count in top_countries.items()])
            summary_data.append(["Principales países destino", top_countries_str])

            # Número total de países destino
            unique_countries = filtered_df['PAIS_DESTINO'].nunique()
            summary_data.append(["Total países destino", f"{unique_countries}"])
        except:
            pass

    # Añadir tasas de éxito si están disponibles
    if 'ESTADO_OPERACION' in filtered_df.columns and not filtered_df.empty:
        try:
            success_rate = (filtered_df['ESTADO_OPERACION'] == 'EXITOSA').mean() * 100
            summary_data.append(["Tasa de éxito", f"{success_rate:.1f}%"])
        except:
            pass

    # Añadir número de agentes únicos si está disponible
    if 'CODIGO_AGENTE' in filtered_df.columns and not filtered_df.empty:
        try:
            unique_agents = filtered_df['CODIGO_AGENTE'].nunique()
            summary_data.append(["Número de agentes", f"{unique_agents}"])
        except:
            pass

    # Crear tabla de resumen con estilo mejorado
    table = Table(summary_data, colWidths=[8*cm, 8*cm])
    table.setStyle(TableStyle([
        # Encabezado
        ('BACKGROUND', (0, 0), (1, 0), colors.lightblue),
        ('TEXTCOLOR', (0, 0), (1, 0), colors.black),
        ('FONTNAME', (0, 0), (1, 0), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (1, 0), 'CENTER'),
        # Celdas de datos
        ('BACKGROUND', (0, 1), (0, -1), colors.lightgrey),
        ('TEXTCOLOR', (0, 1), (0, -1), colors.black),
        ('ALIGN', (0, 1), (0, -1), 'LEFT'),
        ('ALIGN', (1, 1), (1, -1), 'RIGHT'),
        ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 1), (1, -1), 'Helvetica'),
        # Espaciado y bordes
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ('BOX', (0, 0), (-1, -1), 1.5, colors.black),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 0.7*cm))

    # Añadir comentario sobre el resumen
    elements.append(Paragraph(
        "Este resumen muestra las principales métricas extraídas del conjunto de datos analizado. "
        "Las visualizaciones siguientes ofrecen un análisis más detallado de patrones y tendencias.",
        ParagraphStyle('SummaryNote', parent=styles["Normal"], fontSize=10)
    ))

    # Salto de página antes de comenzar con las visualizaciones
    elements.append(PageBreak())

    # Título de la sección de visualizaciones
    elements.append(Paragraph("2. VISUALIZACIONES", subtitle_style))
    elements.append(Spacer(1, 0.3*cm))

    # Para cada gráfico proporcionado
    for i, (fig, title) in enumerate(zip(figures, titles)):
        # Crear una nueva página para cada gráfico excepto el primero
        if i > 0:
            elements.append(PageBreak())

        # Título de la visualización
        elements.append(Paragraph(f"2.{i+1}. {title}", section_style))
        elements.append(Spacer(1, 0.5*cm))

        # Exportar la figura a imagen en memoria - método mejorado
        try:
            # Implementación básica para generar imágenes a partir de figuras de Plotly
            from io import BytesIO
            import base64
            from PIL import Image as PILImage, ImageDraw

            # Usar un enfoque directo para generar una imagen representativa basada en datos reales
            buffer = BytesIO()

            # Intentar primero con to_image (imagen estática)
            try:
                # Configurar la figura para una mejor visualización
                fig.update_layout(
                    width=800,
                    height=500,
                    margin=dict(l=40, r=40, t=50, b=40)
                )

                # Generar representación en bytes de la figura
                img_bytes = fig.to_image(format="png", engine="auto")
                buffer.write(img_bytes)
                buffer.seek(0)

                # Crear imagen para ReportLab desde los bytes
                img = Image(buffer)
                img.drawHeight = 12*cm
                img.drawWidth = 16*cm

            except Exception as img_error:
                print(f"Error al generar imagen con to_image: {str(img_error)}")

                # Plan B: Crear una visualización de datos básica basada en los datos reales
                # Crear una imagen con datos representativos
                img_pil = PILImage.new('RGB', (800, 500), color=(248, 249, 250))
                draw = ImageDraw.Draw(img_pil)

                # Dibujar un marco y título
                draw.rectangle([(10, 10), (790, 490)], outline=(70, 130, 180), width=3)
                draw.text((400, 30), title, fill=(0, 80, 150))

                # Obtener y mostrar datos reales para visualización básica
                if hasattr(fig, 'data') and fig.data:
                    # Si tenemos datos en la figura, podemos crear una representación básica
                    try:
                        # Extraer valores numéricos para una visualización básica
                        values = []
                        for trace in fig.data:
                            if hasattr(trace, 'y') and trace.y is not None:
                                values.extend([v for v in trace.y if v is not None])
                            elif hasattr(trace, 'z') and trace.z is not None:
                                for row in trace.z:
                                    values.extend([v for v in row if v is not None])

                        # Dibujar una visualización básica si tenemos valores
                        if values:
                            max_val = max(values) if values else 1
                            min_val = min(values) if values else 0
                            range_val = max_val - min_val if max_val != min_val else 1

                            # Dibujar barras básicas para representar los datos
                            bar_width = 700 // (len(values) if len(values) < 20 else 20)
                            bar_width = max(5, min(30, bar_width))  # Limitar ancho entre 5 y 30 px

                            for i, val in enumerate(values[:20]):  # Limitar a 20 valores
                                normalized_height = int(400 * (val - min_val) / range_val)
                                x_pos = 50 + i * (bar_width + 5)
                                draw.rectangle(
                                    [(x_pos, 460), (x_pos + bar_width, 460 - normalized_height)],
                                    fill=(41, 128, 185),
                                    outline=(25, 80, 115)
                                )
                    except Exception as vis_error:
                        print(f"Error al crear visualización básica: {str(vis_error)}")

                # Guardar en buffer
                buffer = BytesIO()
                img_pil.save(buffer, format='PNG')
                buffer.seek(0)

                # Crear imagen para ReportLab
                img = Image(buffer)
                img.drawHeight = 12*cm
                img.drawWidth = 16*cm

            elements.append(img)
            elements.append(Spacer(1, 0.3*cm))

            # Añadir número y título de la figura como pie
            elements.append(Paragraph(
                f"Figura {i+1}. {title}",
                caption_style
            ))

        except Exception as e:
            # Mensaje de error más detallado
            print(f"Error al exportar figura a imagen: {str(e)}")

            # Crear un buffer y una imagen básica con explicación
            try:
                from PIL import Image as PILImage, ImageDraw

                # Crear imagen en blanco con mensaje informativo
                img_pil = PILImage.new('RGB', (800, 300), color = (240, 240, 240))
                draw = ImageDraw.Draw(img_pil)

                # Añadir textos informativos
                draw.text((50, 50), f"Visualización: {title}", fill=(0, 0, 100))
                draw.text((50, 100), "No se pudo generar la imagen del gráfico.", fill=(150, 0, 0))
                draw.text((50, 150), "Posible causa: Se requiere el paquete kaleido para exportar gráficos de Plotly.", fill=(0, 0, 0))
                draw.text((50, 200), "Utilice la aplicación web para ver esta visualización de forma interactiva.", fill=(0, 0, 0))

                # Guardar en buffer
                buf = io.BytesIO()
                img_pil.save(buf, format='PNG')
                buf.seek(0)

                # Crear imagen para ReportLab
                img = Image(buf)
                img.drawHeight = 7*cm
                img.drawWidth = 15*cm

                elements.append(img)

            except Exception as img_err:
                # Si falla la creación de la imagen alternativa, añadir solo texto
                elements.append(Paragraph(
                    f"No se pudo generar la visualización: {title}",
                    ParagraphStyle('Error', parent=styles['Heading3'], textColor=colors.red)
                ))
                elements.append(Paragraph(
                    f"Error: {str(e)}",
                    ParagraphStyle('ErrorDetail', parent=styles['Normal'], textColor=colors.red)
                ))

        # Añadir nota informativa sobre la visualización
        elements.append(Spacer(1, 0.5*cm))
        elements.append(Paragraph(
            "Nota: Esta visualización estática es parte del análisis. Para una experiencia "
            "interactiva con filtros y detalles, utilice la aplicación web completa.",
            ParagraphStyle('VisualizationNote', parent=styles["Italic"], fontSize=9)
        ))

    # Añadir página final con conclusiones
    elements.append(PageBreak())
    elements.append(Paragraph("NOTAS FINALES", subtitle_style))
    elements.append(Spacer(1, 0.5*cm))

    # Texto de conclusiones
    elements.append(Paragraph(
        "Este informe proporciona una visión general de los datos analizados. "
        "Las visualizaciones presentadas son estáticas y representan un momento específico del análisis.",
        styles["Normal"]
    ))

    elements.append(Spacer(1, 0.3*cm))

    elements.append(Paragraph(
        "Para un análisis más profundo y visualizaciones interactivas, se recomienda utilizar "
        "la aplicación web completa, donde puede aplicar filtros personalizados, explorar "
        "transacciones específicas y actualizar los datos en tiempo real.",
        styles["Normal"]
    ))

    elements.append(Spacer(1, 0.5*cm))

    # Información de contacto
    elements.append(Paragraph(
        "Sistema de Análisis de Riesgo de Lavado de Dinero",
        ParagraphStyle('Contact', parent=styles["Normal"], fontSize=10, alignment=1)
    ))

    # Construir el documento con numeración de páginas
    doc.build(elements, onFirstPage=add_page_number, onLaterPages=add_page_number)

    # Obtener el PDF del buffer
    pdf_data = buffer.getvalue()
    buffer.close()

    # Codificar para descargar
    b64_pdf = base64.b64encode(pdf_data).decode('utf-8')

    return b64_pdf



def export_dataframe_to_excel(
    df: pd.DataFrame,
    figures: List[go.Figure] = None,
    titles: List[str] = None,
    sheet_name: str = "Datos",
    filename: str = "datos_analisis.xlsx"
) -> str:
    """
    Exporta un DataFrame a Excel, incluyendo gráficos si se proporcionan.

    Args:
        df: DataFrame a exportar
        figures: Lista opcional de objetos Plotly Figure para incluir
        titles: Lista opcional de títulos correspondientes a cada gráfico
        sheet_name: Nombre de la hoja de Excel
        filename: Nombre del archivo Excel

    Returns:
        Datos del Excel en base64 para descarga
    """
    # Crear un buffer de memoria para el Excel
    buffer = io.BytesIO()

    # Crear un ExcelWriter
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        # Escribir el DataFrame a Excel
        df.to_excel(writer, sheet_name=sheet_name, index=False)

        # Obtener el objeto workbook y worksheet
        workbook = writer.book
        worksheet = writer.sheets[sheet_name]

        # Formato para números
        number_format = workbook.add_format({'num_format': '#,##0.00'})

        # Formato para fechas
        date_format = workbook.add_format({'num_format': 'dd/mm/yyyy'})

        # Formato para cabeceras
        header_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'top',
            'fg_color': '#D7E4BC',
            'border': 1
        })

        # Aplicar formato a cabeceras
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, header_format)

        # Aplicar formatos de columna basados en el tipo de datos
        for i, col in enumerate(df.columns):
            column_width = max(df[col].astype(str).str.len().max(), len(col) + 2)
            worksheet.set_column(i, i, column_width)

            # Aplicar formato de número para columnas numéricas
            if pd.api.types.is_numeric_dtype(df[col]):
                if 'IMPORTE' in col or 'importe' in col.lower():
                    worksheet.set_column(i, i, column_width, number_format)

            # Aplicar formato de fecha para columnas de fecha
            elif pd.api.types.is_datetime64_any_dtype(df[col]):
                worksheet.set_column(i, i, column_width, date_format)

        # Si se proporcionaron gráficos, añadirlos a hojas separadas
        if figures and len(figures) > 0:
            # Verificar si los títulos están disponibles
            if not titles or len(titles) != len(figures):
                # Generar títulos genéricos si no se proporcionaron
                titles = [f"Gráfico {i+1}" for i in range(len(figures))]

            # Crear una hoja de índice para los gráficos
            charts_index_sheet = workbook.add_worksheet("Índice Gráficos")

            # Estilo para títulos
            title_format = workbook.add_format({
                'bold': True, 
                'font_size': 14, 
                'align': 'center',
                'valign': 'vcenter',
                'border': 0
            })

            # Formato para índice
            index_format = workbook.add_format({
                'bold': True,
                'font_size': 12
            })

            # Formato para enlaces internos
            link_format = workbook.add_format({
                'color': 'blue',
                'underline': True,
                'font_size': 11
            })

            # Agregar un título a la hoja de índice
            charts_index_sheet.merge_range('A1:D1', 'ÍNDICE DE VISUALIZACIONES', title_format)

            # Crear un resumen de los gráficos disponibles
            charts_index_sheet.merge_range('A2:D2', f'Este informe contiene {len(figures)} visualizaciones', 
                                   workbook.add_format({'italic': True, 'align': 'center'}))

            # Cabeceras de la tabla de índice
            charts_index_sheet.write(3, 0, "Nº", index_format)
            charts_index_sheet.write(3, 1, "Título", index_format)
            charts_index_sheet.write(3, 2, "Hoja", index_format)
            charts_index_sheet.write(3, 3, "Descripción", index_format)

            # Ajustar ancho de columnas del índice
            charts_index_sheet.set_column(0, 0, 5)    # Nº
            charts_index_sheet.set_column(1, 1, 30)   # Título
            charts_index_sheet.set_column(2, 2, 15)   # Hoja
            charts_index_sheet.set_column(3, 3, 50)   # Descripción

            # Para cada gráfico, crear una hoja separada
            for i, (fig, title) in enumerate(zip(figures, titles)):
                # Crear nombre de hoja seguro (sin caracteres especiales y máximo 31 caracteres)
                safe_title = f"Gráfico_{i+1}"
                sheet_title = f"Gráfico {i+1}: {title}"

                # Crear una hoja para este gráfico
                chart_sheet = workbook.add_worksheet(safe_title)

                try:
                    # Usar una descripción del gráfico en lugar de la imagen
                    # Título del gráfico en la hoja
                    chart_sheet.merge_range('A1:H1', sheet_title, title_format)

                    # Crear texto descriptivo del gráfico
                    chart_sheet.merge_range('A3:H3', "Descripción del gráfico:", workbook.add_format({
                        'bold': True, 'font_size': 12
                    }))

                    # Añadir una descripción del gráfico
                    description = fig.layout.title.text if hasattr(fig.layout, 'title') and hasattr(fig.layout.title, 'text') else title
                    chart_sheet.merge_range('A4:H4', description, workbook.add_format({
                        'italic': True, 'text_wrap': True, 'font_size': 11
                    }))

                    # Crear un área con información de series y datos
                    chart_sheet.merge_range('A6:H6', "Información de datos:", workbook.add_format({
                        'bold': True, 'font_size': 12
                    }))

                    # En filas siguientes, añadir datos clave
                    chart_sheet.write('A8', "Tipo de gráfico:", workbook.add_format({'bold': True}))
                    chart_sheet.write('B8', fig.layout.template.layout.title.text if hasattr(fig.layout, 'template') else "Gráfico de datos")

                    # Ajustar ancho de columnas
                    chart_sheet.set_column(0, 0, 20)
                    chart_sheet.set_column(1, 7, 15)

                    # Añadir este gráfico al índice con enlace a la hoja
                    charts_index_sheet.write(4 + i, 0, i+1)  # Número

                    # Escribir título con enlace interno a la hoja del gráfico
                    charts_index_sheet.write_url(
                        4 + i, 1,  # Fila y columna
                        f"internal:'{safe_title}'!A1",  # Enlace interno a la hoja
                        link_format,  # Formato de enlace
                        string=title  # Texto visible
                    )

                    charts_index_sheet.write(4 + i, 2, safe_title)  # Nombre de hoja

                    # Descripción breve (extraer del título o dejarlo en blanco)
                    charts_index_sheet.write(4 + i, 3, f"Visualización de {title}")

                except Exception as e:
                    # Si hay error al exportar el gráfico, añadir mensaje de error
                    error_format = workbook.add_format({'color': 'red', 'italic': True})
                    chart_sheet.merge_range('A3:H3', f"Error al exportar gráfico: {str(e)}", error_format)
                    charts_index_sheet.write(4 + i, 3, "Error al generar (ver detalles en la hoja)", error_format)

            # Añadir nota explicativa al final del índice
            charts_index_sheet.merge_range(
                5 + len(figures), 0, 5 + len(figures), 3,
                "Nota: Para una experiencia interactiva completa, utilice la aplicación web de análisis.",
                workbook.add_format({'italic': True})
            )

    # Obtener el Excel del buffer
    excel_data = buffer.getvalue()
    buffer.close()

    # Codificar para descarga
    b64_excel = base64.b64encode(excel_data).decode('utf-8')

    return b64_excel


def generate_risk_report_excel(
    df: pd.DataFrame,
    risk_scores: Dict[str, Dict[str, float]],
    risk_details: Dict[str, Dict[str, Any]],
    agent_subject_mapping: Dict[str, str],
    indicator_types: Dict[str, str],
    indicator_descriptions: Dict[str, Dict[str, str]],
    risk_transactions: pd.DataFrame = None,
    filename: str = "informe_riesgo_detallado.xlsx"
) -> str:
    """
    INFORME DE RIESGO ACTUALIZADO:
    Genera un informe detallado en Excel con dos pestañas:
    1. Riesgos: muestra valores individuales de riesgo (1-4) para cada uno de los 20 indicadores por agente/entidad
    2. Operaciones Sospechosas: detalla las operaciones sospechosas con su motivo de riesgo



    Args:
        df: DataFrame con los datos filtrados
        risk_scores: Diccionario con puntuaciones de riesgo por agente y por indicador.
                     Formato: {agente1: {1: valor, 2: valor, ...}, agente2: {...}}
                     Donde los valores están en escala 1-4 para cada indicador.
        risk_details: Diccionario con detalles de riesgo por indicador
        agent_subject_mapping: Diccionario que mapea agentes a sujetos obligados
        indicator_types: Diccionario que mapea indicadores a sus tipos (DOCUMENTACIÓN, UMBRALES, GEOGRÁFICO, OUTLIERS)
        indicator_descriptions: Diccionario con descripciones de los indicadores
        risk_transactions: DataFrame opcional con transacciones de riesgo
        filename: Nombre del archivo Excel a generar

    Returns:
        Datos del Excel en base64 para descarga
    """
    buffer = io.BytesIO()

    # Crear un ExcelWriter
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        workbook = writer.book

        # Formatos para Excel
        header_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'top',
            'fg_color': '#D7E4BC',
            'border': 1
        })

        title_format = workbook.add_format({
            'bold': True,
            'font_size': 14,
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
            'fg_color': '#4F81BD',
            'font_color': 'white'
        })

        subtitle_format = workbook.add_format({
            'bold': True,
            'font_size': 12,
            'border': 1,
            'fg_color': '#B8CCE4'
        })

        agent_format = workbook.add_format({
            'bold': True,
            'border': 1,
            'fg_color': '#E4DFEC'
        })

        number_format = workbook.add_format({
            'num_format': '0.00',
            'border': 1
        })

        percent_format = workbook.add_format({
            'num_format': '0.00%',
            'border': 1
        })

        date_format = workbook.add_format({
            'num_format': 'dd/mm/yyyy',
            'border': 1
        })

        currency_format = workbook.add_format({
            'num_format': '#,##0.00 €',
            'border': 1
        })

        text_format = workbook.add_format({
            'border': 1
        })

        # Formato para celdas de riesgo (escala 1-4)
        low_risk_format = workbook.add_format({
            'num_format': '0.00',
            'border': 1,
            'bg_color': '#C6EFCE',  # Verde claro para riesgo bajo (valor 1)
            'font_color': '#006100'
        })

        medium_risk_format = workbook.add_format({
            'num_format': '0.00',
            'border': 1,
            'bg_color': '#FFEB9C',  # Amarillo claro para riesgo medio (valor 2)
            'font_color': '#9C5700'
        })

        high_risk_format = workbook.add_format({
            'num_format': '0.00',
            'border': 1,
            'bg_color': '#FFC7CE',  # Rojo claro para riesgo alto (valor 3)
            'font_color': '#9C0006'
        })

        very_high_risk_format = workbook.add_format({
            'num_format': '0.00',
            'border': 1,
            'bg_color': '#FF0000',  # Rojo intenso para riesgo muy alto (valor 4)
            'font_color': '#FFFFFF'
        })

        # Formato para celdas con valor cero (sin riesgo)
        zero_risk_format = workbook.add_format({
            'border': 1,
            'font_color': '#FFFFFF'  # Texto blanco para ocultar el cero
        })

        # === PESTAÑA 1: ANÁLISIS DE RIESGO POR AGENTE ===
        # Preparar datos para la primera hoja: Análisis por agente con el formato exacto solicitado

        # Determinar todos los indicadores únicos y sus tipos (asegurando que sean 20 indicadores)
        all_indicators = [str(i) for i in range(1, 21)]

        # Agrupar indicadores por tipo
        indicators_by_type = {}
        for ind_id in all_indicators:
            ind_type = indicator_types.get(ind_id, "General")
            if ind_type not in indicators_by_type:
                indicators_by_type[ind_type] = []
            indicators_by_type[ind_type].append(ind_id)

        # Crear encabezados para la tabla con el formato exacto del ejemplo (informe_riesgo_02.xlsx)
        headers = [
            "Entidad", 
            "Riesgo_Conjunto"
        ]

        # Añadir encabezados para los tipos de indicadores (con formato del ejemplo)
        for ind_type in sorted(indicators_by_type.keys()):
            headers.append(f"Riesgo_{ind_type}")

        # Añadir encabezados para cada indicador individual con formato exacto del ejemplo
        for ind_id in all_indicators:
            headers.append(f"Indicador_{ind_id}")

        # Usar solo los agentes que tienen datos de riesgo en risk_scores (esto contiene solo los agentes filtrados)
        unique_agents = []

        # Extraer de risk_scores para asegurar que incluimos solo los agentes con datos de riesgo
        for agent in risk_scores.keys():
            if agent and str(agent).strip() and str(agent).lower() != 'nan':
                unique_agents.append(agent)

        # Eliminar posibles duplicados y ordenar alfabéticamente
        unique_agents = sorted(list(set(unique_agents)))

        # Si no hay agentes, verificar si podemos extraerlos del DataFrame
        if not unique_agents and 'es_Agente' in df.columns:
            df_agents = df['es_Agente'].dropna().unique().tolist()
            for agent in df_agents:
                if agent and str(agent).strip() and str(agent).lower() != 'nan':
                    unique_agents.append(agent)

            # Ordenar de nuevo
            unique_agents = sorted(list(set(unique_agents)))

        # Preparar datos de la tabla
        table_data = []

        # Diccionario para acumular valores por indicador para calcular promedios después
        indicator_values = {ind_id: [] for ind_id in all_indicators}
        type_values = {ind_type: [] for ind_type in indicators_by_type.keys()}
        global_values = []

        # Obtener puntuaciones de riesgo por agente
        for agent in unique_agents:
            subject = agent_subject_mapping.get(agent, "Desconocido")

            # Si no hay datos de riesgo para este agente, creamos valores predeterminados
            if agent not in risk_scores:
                # Crear un diccionario de valores por defecto
                default_agent_scores = {ind_id: 1.0 for ind_id in all_indicators}
                agent_scores = default_agent_scores
            else:
                # Verificar qué estructura tiene risk_scores[agent]
                agent_data = risk_scores[agent]

                # Si agent_data es un float o int, podría ser un error, pero es posible que
                # cada agente tenga un valor por cada indicador
                if not isinstance(agent_data, dict):
                    try:
                        print(f"Aviso: Convirtiendo datos del agente {agent} a diccionario.")
                        # Intentar convertir en un float y asignarlo a un diccionario
                        if isinstance(agent_data, (float, int)):
                            agent_scores = {ind_id: float(agent_data) for ind_id in all_indicators}
                        else:
                            # Si no es un valor numérico, establecer valores predeterminados (escala 1-4)
                            agent_scores = {ind_id: 1.0 for ind_id in all_indicators}
                    except Exception as e:
                        print(f"Error al procesar puntuaciones para el agente {agent}: {e}")
                        agent_scores = {ind_id: 1.0 for ind_id in all_indicators}
                else:
                    agent_scores = agent_data

                # Asegurarse que todos los indicadores estén presentes (con valor 1 como mínimo por la escala 1-4)
                for ind_id in all_indicators:
                    if ind_id not in agent_scores or agent_scores[ind_id] is None:
                        agent_scores[ind_id] = 1.0
                    # Convertir a float en caso de que sea un entero o string
                    if not isinstance(agent_scores[ind_id], float):
                        try:
                            agent_scores[ind_id] = float(agent_scores[ind_id])
                        except (ValueError, TypeError):
                            agent_scores[ind_id] = 1.0

            # Datos básicos (solo nombre del agente, como en el ejemplo informe_riesgo_02.xlsx)
            row = [agent]

            # Calcular el riesgo global para este agente basado en las puntuaciones individuales
            weights = {ind_id: float(indicator_descriptions.get(ind_id, {}).get("weight", "1").strip('%').replace(',', '.'))/100 
                      for ind_id in agent_scores.keys()}

            # Evitar división por cero si no hay pesos
            total_weight = sum(weights.values())
            if total_weight > 0:
                global_risk = sum(agent_scores[ind_id] * weights[ind_id] for ind_id in agent_scores) / total_weight
            else:
                global_risk = 1.0

            # Guardar para calcular promedios después
            global_values.append(global_risk)

            row.append(global_risk)

            # Calcular riesgo por tipo de indicador a partir de los indicadores individuales
            risk_by_type = {}
            weights_by_type = {ind_type: 0 for ind_type in indicators_by_type.keys()}
            indicator_sums_by_type = {ind_type: 0 for ind_type in indicators_by_type.keys()}

            # Agrupar los indicadores por tipo y calcular la suma ponderada
            for ind_id, score in agent_scores.items():
                ind_type = indicator_types.get(ind_id, "General")
                weight = weights.get(ind_id, 1.0)

                # Verificar si el tipo existe, si no, añadirlo
                if ind_type not in indicator_sums_by_type:
                    indicator_sums_by_type[ind_type] = 0
                    weights_by_type[ind_type] = 0

                # Acumular para este tipo
                indicator_sums_by_type[ind_type] += score * weight
                weights_by_type[ind_type] += weight

            # Calcular el riesgo promedio por tipo
            for ind_type in set(indicators_by_type.keys()) | set(indicator_sums_by_type.keys()):
                if ind_type in weights_by_type and weights_by_type[ind_type] > 0:
                    risk_by_type[ind_type] = indicator_sums_by_type[ind_type] / weights_by_type[ind_type]
                else:
                    risk_by_type[ind_type] = 1.0  # Valor por defecto

                # Asegurar que type_values tenga esta clave
                if ind_type not in type_values:
                    type_values[ind_type] = []

                # Guardar para calcular promedios después
                type_values[ind_type].append(risk_by_type[ind_type])

            # Añadir riesgo por tipo (formateado con dos decimales si no es entero)
            for ind_type in sorted(indicators_by_type.keys()):
                risk_value = risk_by_type.get(ind_type, 1.0)
                # Convertir a entero si es aproximadamente un entero, sino dejarlo con 2 decimales
                if abs(risk_value - round(risk_value)) < 0.01:
                    risk_value = int(round(risk_value))
                else:
                    risk_value = round(risk_value, 2)
                row.append(risk_value)

            # Añadir puntuación para cada indicador individual usando la función formatear_valor_riesgo
            for ind_id in all_indicators:
                value = agent_scores.get(ind_id, 1.0)
                # Importamos la función desde utils.indicadores_riesgo para mantener consistencia
                from utils.risk_indicators import formatear_valor_riesgo
                formatted_value = formatear_valor_riesgo(value)
                row.append(formatted_value)
                # Guardar para calcular promedios después
                indicator_values[ind_id].append(formatted_value)

            table_data.append(row)

        # Calcular fila de medias si hay más de un agente
        if len(table_data) > 1:
            avg_row = ["PROMEDIO"]  # Primer elemento es 'PROMEDIO'

            # Añadir promedio del riesgo global usando la función formatear_valor_riesgo
            avg_global = sum(global_values) / len(global_values) if global_values else 1.0
            # Importamos la función desde utils.indicadores_riesgo para mantener consistencia
            from utils.risk_indicators import formatear_valor_riesgo
            formatted_avg_global = formatear_valor_riesgo(avg_global)
            # Convertir a string para evitar problemas con tipos incompatibles
            avg_row.append(str(formatted_avg_global))

            # Añadir promedio por tipo de indicador usando función formatear_valor_riesgo
            for ind_type in sorted(indicators_by_type.keys()):
                values = type_values[ind_type]
                avg = sum(values) / len(values) if values else 1.0
                # Importamos la función desde utils.indicadores_riesgo para mantener consistencia
                from utils.risk_indicators import formatear_valor_riesgo
                formatted_avg = formatear_valor_riesgo(avg)
                # Convertir a string para evitar problemas con tipos incompatibles
                avg_row.append(str(formatted_avg))

            # Añadir promedio para cada indicador individual usando función formatear_valor_riesgo
            for ind_id in all_indicators:
                values = indicator_values[ind_id]
                avg = sum(values) / len(values) if values else 1.0
                # Importamos la función desde utils.indicadores_riesgo para mantener consistencia
                from utils.risk_indicators import formatear_valor_riesgo
                formatted_avg = formatear_valor_riesgo(avg)
                # Convertir a string para evitar problemas con tipos incompatibles
                avg_row.append(str(formatted_avg))

            table_data.append(avg_row)

        # Crear hoja para análisis por agente (igual que archivo ejemplo)
        worksheet1 = workbook.add_worksheet("Riesgos")

        # Añadir título
        worksheet1.merge_range('A1:E1', 'INFORME DE ANÁLISIS DE RIESGO POR AGENTE', title_format)
        worksheet1.merge_range('A2:E2', f'Fecha: {datetime.now().strftime("%d/%m/%Y %H:%M")}', subtitle_format)

        # Escribir encabezados
        for col_num, header in enumerate(headers):
            worksheet1.write(3, col_num, header, header_format)

        # Escribir datos
        row_offset = 4  # Empezamos en la fila 4 (después de los encabezados)
        for row_num, row_data in enumerate(table_data):
            is_avg_row = row_num == len(table_data) - 1 and len(table_data) > 1

            for col_num, cell_value in enumerate(row_data):
                # Formatear celdas según el tipo de dato
                if col_num <= 1:  # Agente y Sujeto Obligado
                    cell_format = agent_format if is_avg_row else text_format
                    worksheet1.write(row_num + row_offset, col_num, cell_value, cell_format)
                else:  # Valores numéricos
                    # Importar función de formato desde fixed_risk_indicators.py
                    from utils.fixed_risk_indicators import formatear_valor_riesgo

                    # Determinar formato de riesgo
                    if isinstance(cell_value, (int, float)):
                        # Asegurar que se muestre entero si es entero, y con 2 decimales si no lo es
                        numeric_val = formatear_valor_riesgo(cell_value)
                    elif isinstance(cell_value, str):
                        try:
                            # Si es un entero con punto decimal ("1.0", "2.0", etc.) o decimal
                            if '.' in cell_value and cell_value.replace('.', '', 1).isdigit():
                                float_val = float(cell_value)
                                # Usar formatear_valor_riesgo para consistencia en toda la app
                                numeric_val = formatear_valor_riesgo(float_val)
                            # Si es un entero sin punto decimal
                            elif cell_value.isdigit():
                                int_val = int(cell_value)
                                numeric_val = int_val  # Ya es entero, no necesita formateo
                            else:
                                # No es un número válido
                                worksheet1.write(row_num + row_offset, col_num, cell_value, text_format)
                                continue
                        except (ValueError, AttributeError):
                            # No se pudo convertir a número
                            worksheet1.write(row_num + row_offset, col_num, cell_value, text_format)
                            continue
                    else:
                        worksheet1.write(row_num + row_offset, col_num, cell_value, text_format)
                        continue

                    # Si el valor es cero, dejamos la celda en blanco
                    if numeric_val == 0:
                        # Solo para la fila de promedios, mostramos el cero
                        if is_avg_row:
                            worksheet1.write(row_num + row_offset, col_num, numeric_val, low_risk_format)
                        else:
                            worksheet1.write_blank(row_num + row_offset, col_num, None, text_format)
                    # Para valores de 4, consideramos riesgo muy alto (escala 1-4)
                    elif numeric_val == 4:
                        cell_format = very_high_risk_format
                        worksheet1.write(row_num + row_offset, col_num, numeric_val, cell_format)
                    # Para valores de 3, consideramos riesgo alto (escala 1-4)
                    elif numeric_val == 3:
                        cell_format = high_risk_format
                        worksheet1.write(row_num + row_offset, col_num, numeric_val, cell_format)
                    # Para valores de 2, consideramos riesgo medio (escala 1-4)
                    elif numeric_val == 2:
                        cell_format = medium_risk_format
                        worksheet1.write(row_num + row_offset, col_num, numeric_val, cell_format)
                    # Para valores de 1, consideramos riesgo bajo (escala 1-4)
                    elif numeric_val == 1:
                        cell_format = low_risk_format
                        worksheet1.write(row_num + row_offset, col_num, numeric_val, cell_format)
                    # Para valores intermedios o fuera de rango (por ejemplo, promedios)
                    else:
                        try:
                            # Asegurar que estamos trabajando con un número
                            float_val = float(numeric_val)
                            # Si es mayor a 3.5, considerar riesgo muy alto
                            if float_val > 3.5:
                                cell_format = very_high_risk_format
                            # Si está entre 2.5 y 3.5, considerar riesgo alto
                            elif float_val > 2.5:
                                cell_format = high_risk_format
                            # Si está entre 1.5 y 2.5, considerar riesgo medio
                            elif float_val >= 1.5:
                                cell_format = medium_risk_format
                            # Si es menor a 1.5 pero mayor a 0, considerar riesgo bajo
                            else:
                                cell_format = low_risk_format
                        except (ValueError, TypeError):
                            # Si no se puede convertir a número, usar formato normal
                            cell_format = text_format

                        worksheet1.write(row_num + row_offset, col_num, numeric_val, cell_format)

        # Ajustar anchos de columna
        worksheet1.set_column(0, 1, 15)  # Agente y Sujeto
        worksheet1.set_column(2, 2, 12)  # Riesgo Global
        worksheet1.set_column(3, len(headers)-1, 15)  # Resto de columnas

        # === PESTAÑA 2: TRANSACCIONES DE RIESGO ===
        # Preparar datos para la segunda pestaña: Transacciones de riesgo

        # Filtrar transacciones de riesgo si no se proporciona un DataFrame específico
        if risk_transactions is None and 'Motivo_Riesgo' in df.columns:
            risk_transactions = df[df['Motivo_Riesgo'].astype(str).str.strip() != ""].copy()
        elif risk_transactions is None:
            # Crear un DataFrame vacío con las columnas básicas necesarias
            # Usamos un conjunto básico de columnas para evitar errores
            default_columns = ["NUMERO_TRANSACCION", "FECHA", "HORA", "IMPORTE", "PAIS_ORIGEN", 
                        "NOMBRE_ORDENANTE", "APELLIDO_ORDENANTE", "NUM_DOC_ORDENANTE", 
                        "NOMBRE_BENEFICIARIO", "APELLIDO_BENEFICIARIO", "PAIS_DESTINO", 
                        "ENT_NAT_REF_COD", "Motivo_Riesgo"]
            # Añadimos las columnas disponibles en el DataFrame original
            if df is not None and not df.empty:
                for col in df.columns:
                    if col not in default_columns:
                        default_columns.append(col)
            risk_transactions = pd.DataFrame(columns=default_columns)

        if 'INDICADORES_RIESGO' not in risk_transactions.columns:
            risk_transactions['INDICADORES_RIESGO'] = ""

        # Eliminar filas duplicadas o con información insuficiente
        if not risk_transactions.empty:
            # Verificar las columnas disponibles
            motivo_column = None
            potential_columns = ['Motivo_Riesgo', 'MOTIVO_RIESGO', 'Motivo', 'MOTIVO']

            for col in potential_columns:
                if col in risk_transactions.columns:
                    motivo_column = col
                    break

            # Si no hay columna de motivo, agregamos una por defecto
            if motivo_column is None:
                risk_transactions['Motivo_Riesgo'] = "Operación detectada por indicador de riesgo"
                motivo_column = 'Motivo_Riesgo'

            # Ahora usamos la columna encontrada para filtrar
            risk_transactions = risk_transactions.copy()

            # Enriquecer la información de indicadores de riesgo con las descripciones
            indicator_descriptions_lookup = get_indicator_descriptions()

            # Crear una columna con los indicadores detallados cuando exista información
            # Si aún no existe la columna Motivo_Riesgo, crearla
            if 'Motivo_Riesgo' not in risk_transactions.columns:
                risk_transactions['Motivo_Riesgo'] = "Operación detectada por indicador de riesgo"

            if 'INDICADORES_RIESGO' in risk_transactions.columns:
                def enriquecer_indicadores(row):
                    if pd.isna(row['INDICADORES_RIESGO']) or row['INDICADORES_RIESGO'] == "":
                        return row['Motivo_Riesgo'] if 'Motivo_Riesgo' in row and not pd.isna(row['Motivo_Riesgo']) else "Transacción marcada como riesgo"

                    # Separar los indicadores si existe una lista
                    indicadores = str(row['INDICADORES_RIESGO']).split(',')
                    detalles = []

                    # Añadir descripción detallada para cada indicador
                    for ind in indicadores:
                        ind = ind.strip()
                        if ind in indicator_descriptions_lookup:
                            detalles.append(f"Indicador {ind}: {indicator_descriptions_lookup[ind]['description']}")
                        else:
                            detalles.append(f"Indicador {ind}")

                    # Si no hay detalles, usar el motivo de riesgo general si existe
                    if not detalles and 'Motivo_Riesgo' in row and not pd.isna(row['Motivo_Riesgo']) and row['Motivo_Riesgo'] != "":
                        return row['Motivo_Riesgo']

                    return ", ".join(detalles) if detalles else "Transacción marcada como riesgo"

                # Aplicar el enriquecimiento a la columna MOTIVO_RIESGO
                try:
                    risk_transactions['Motivo_Riesgo'] = risk_transactions.apply(enriquecer_indicadores, axis=1)
                except Exception as e:
                    print(f"Error al enriquecer indicadores: {str(e)}")
                    # En caso de error, asegurar que existe la columna
                    if 'Motivo_Riesgo' not in risk_transactions.columns:
                        risk_transactions['Motivo_Riesgo'] = "Operación detectada por indicador de riesgo"

        # Crear hoja para transacciones de riesgo (igual que en el ejemplo)
        worksheet2 = workbook.add_worksheet("Operaciones Sospechosas")

        # Añadir título
        worksheet2.merge_range('A1:G1', 'TRANSACCIONES DETECTADAS COMO RIESGO', title_format)
        worksheet2.merge_range('A2:G2', f'Fecha: {datetime.now().strftime("%d/%m/%Y %H:%M")}', subtitle_format)

        # Seleccionar columnas para mostrar - usando strings en lugar de variables no definidas
        risk_columns = ["NUMERO_TRANSACCION", "FECHA", "HORA", "IMPORTE", "ESTADO_OPERACION", "PAIS_ORIGEN", 
                        "NOMBRE_ORDENANTE", "APELLIDO_ORDENANTE", "SEGUNDO_APELLIDO_ORDENANTE", 
                        "PAIS_DOC_ORDENANTE", "NUM_DOC_ORDENANTE", "PAIS_NAC_ORDENANTE", "FECHA_NAC_ORDENANTE", 
                        "es_Agente", "NOMBRE_BENEFICIARIO", "APELLIDO_BENEFICIARIO", "SEGUNDO_APELLIDO_BENEFICIARIO", 
                        "PAIS_DESTINO", "ENT_TOW_CIT_RES", "ENT_COD_PAR_ENT", "ENT_NAT_REF_COD", "es_PEP", 
                        "Motivo_Riesgo", "INDICADORES_RIESGO"]

        # Filtrar columnas que existen en el DataFrame
        risk_columns = [col for col in risk_columns if col in risk_transactions.columns]



        # Escribir encabezados
        for col_num, column in enumerate(risk_columns):
            # Usar el nombre de la columna directamente como encabezado
            worksheet2.write(3, col_num, column, header_format)

        # Escribir datos - resetear el índice para evitar filas en blanco
        risk_transactions = risk_transactions.reset_index(drop=True)

        for idx, row in enumerate(risk_transactions.itertuples()):
            row_data = row._asdict()
            for col_num, column in enumerate(risk_columns):
                if column in row_data:
                    cell_value = row_data[column]
                else:
                    cell_value = ""

                # Formatear según el tipo de dato
                if column == 'IMPORTE':
                    worksheet2.write(idx + 4, col_num, cell_value, currency_format)
                elif column == 'FECHA':
                    if pd.notna(cell_value):
                        try:
                            if not isinstance(cell_value, datetime):
                                cell_value = pd.to_datetime(cell_value)
                            worksheet2.write_datetime(idx + 4, col_num, cell_value, date_format)
                        except:
                            worksheet2.write(idx + 4, col_num, str(cell_value), text_format)
                    else:
                        worksheet2.write(idx + 4, col_num, "", text_format)
                else:
                    worksheet2.write(idx + 4, col_num, str(cell_value) if pd.notna(cell_value) else "", text_format)

        # Ajustar anchos de columna
        for i, column in enumerate(risk_columns):
            column_width = 15  # Ancho predeterminado

            if column in ['Motivo_Riesgo', 'INDICADORES_RIESGO']:
                column_width = 40  # Columnas más anchas para descripciones
            elif column in ['NUMERO_TRANSACCION']:
                column_width = 20
            elif column in ['FECHA', 'HORA', 'IMPORTE', 'es_Agente']:
                column_width = 12

            worksheet2.set_column(i, i, column_width)

    # Obtener los datos del Excel
    excel_data = buffer.getvalue()
    buffer.close()

    # Codificar para descarga
    b64_excel = base64.b64encode(excel_data).decode('utf-8')

    return b64_excel


# Función auxiliar para formatear valores de riesgo
def formatear_valor_riesgo(valor):
    """
    Formatea un valor numérico para mostrar 2 decimales solo si no es entero.

    Args:
        valor: Valor numérico a formatear

    Returns:
        Valor formateado (entero o con 2 decimales)
    """
    try:
        # Convertir a float para asegurar compatibilidad
        float_valor = float(valor)

        # Verificar si es aproximadamente igual a un entero
        if abs(float_valor - round(float_valor)) < 0.01:
            return int(round(float_valor))
        else:
            # Si no es entero, mostrar con 2 decimales
            return round(float_valor, 2)
    except (ValueError, TypeError):
        # En caso de error (por ejemplo, si valor no es numérico), 
        # devolver el valor original
        return valor


def export_network_to_excel(
    network_data: Dict[str, Any],
    df: pd.DataFrame,
    filename: str = "analisis_red.xlsx"
) -> str:
    """
    Exporta los datos de análisis de red a Excel con formato mejorado,
    nombres de comunidades descriptivos, y ahora con hojas de transacciones
    de ordenantes y beneficiarios.
    """
    import io, base64
    import pandas as pd

    buffer = io.BytesIO()
    writer = pd.ExcelWriter(buffer, engine='xlsxwriter')

    # --- 1) Hoja de Nodos ---
    nodes = network_data.get('nodes', [])
    if nodes:
        # Crear una lista de diccionarios con datos de nodos
        nodes_data = []
        for n in nodes:
            # Asegurar que todos los campos necesarios estén presentes
            node_dict = {
                'ID': n['id'],
                'Nombre': n.get('label', n['id']),  # Usar ID como fallback si no hay label
                'Tipo': 'Remitente' if n['type']=='sender' else 'Beneficiario',
                'País': n.get('country', 'Desconocido'),
                'Valor': n.get('value', 0),
                'Transacciones': n.get('transactions', 0),
                'Comunidad ID': n.get('group', ''),
                'Comunidad': n.get('community_name', f"Comunidad {n.get('group', '')}")
            }
            nodes_data.append(node_dict)
            
        # Crear DataFrame a partir de la lista de diccionarios
        nodes_df = pd.DataFrame(nodes_data)
        
        # Asegurar que las columnas siempre existen aunque estén vacías
        if 'Comunidad ID' not in nodes_df.columns:
            nodes_df['Comunidad ID'] = ''
        if 'Comunidad' not in nodes_df.columns:
            nodes_df['Comunidad'] = ''
            
        # Ordenar el DataFrame
        try:
            nodes_df.sort_values(['Comunidad ID', 'Tipo'], inplace=True)
        except:
            # En caso de error, intentar ordenar solo por tipo
            try:
                nodes_df.sort_values(['Tipo'], inplace=True)
            except:
                pass  # Si hay error al ordenar, dejarlo como está
        nodes_df.to_excel(writer, sheet_name='Nodos', index=False)
        ws = writer.sheets['Nodos']
        for col, width in zip(['A','B','C','D','E','F','G','H'], [15,30,12,15,12,12,12,40]):
            ws.set_column(f'{col}:{col}', width)

    # --- 2) Hoja de Conexiones (Aristas) ---
    edges = network_data.get('edges', [])
    if edges:
        # Crear una lista de diccionarios con datos de aristas
        edges_data = []
        for e in edges:
            # Asegurar que todos los campos necesarios estén presentes
            edge_dict = {
                'Remitente ID': e.get('source', ''),
                'Beneficiario ID': e.get('target', ''),
                'Importe Total': e.get('value', 0),
                'Número Transacciones': e.get('transactions', 0),
                'Transacciones ID': e.get('transaction_ids', []),
            }
            edges_data.append(edge_dict)
            
        # Crear DataFrame a partir de la lista de diccionarios
        edges_df = pd.DataFrame(edges_data)
        
        # Añadir nombres legibles buscando en nodes_df
        try:
            id2label = nodes_df.set_index('ID')['Nombre'].to_dict()
            # Aplicar mapeo de manera segura, con valor por defecto si no se encuentra
            edges_df['Remitente'] = edges_df['Remitente ID'].apply(
                lambda x: id2label.get(x, f"ID: {x}")
            )
            edges_df['Beneficiario'] = edges_df['Beneficiario ID'].apply(
                lambda x: id2label.get(x, f"ID: {x}")
            )
        except:
            # Si hay error al mapear nombres, crear columnas vacías
            edges_df['Remitente'] = edges_df['Remitente ID']
            edges_df['Beneficiario'] = edges_df['Beneficiario ID']
            
        # Reordenar columnas
        try:
            edges_df = edges_df[['Remitente ID', 'Remitente', 'Beneficiario ID', 'Beneficiario',
                               'Importe Total', 'Número Transacciones', 'Transacciones ID']]
        except:
            # Si hay error (posiblemente porque alguna columna no existe), mantener columnas disponibles
            pass
            
        # Intentar ordenar por importe
        try:
            edges_df.sort_values('Importe Total', ascending=False, inplace=True)
        except:
            pass
        edges_df.to_excel(writer, sheet_name='Conexiones', index=False)
        ws = writer.sheets['Conexiones']
        for col, width in zip(['A','B','C','D','E','F'], [15,30,15,30,15,15]):
            ws.set_column(f'{col}:{col}', width)

    # --- 3) Hoja de Comunidades enriquecida ---
    if nodes and edges:
        try:
            # Mapeo ID nodo → comunidad (más robusto)
            node2comm = {}
            for n in nodes:
                # Asegurar que la ID del nodo y el grupo existen
                node_id = n.get('id', '')
                if node_id:  # Solo agregar si hay ID
                    group = n.get('group', '')
                    node2comm[node_id] = group
                    
            # Obtener comunidades, o generar comunidades básicas si no existen
            comms = network_data.get('communities', [])
            if not comms:
                # Si no hay comunidades definidas, crear una lista con IDs únicos de grupos
                unique_groups = set(g for g in node2comm.values() if g)
                comms = [{'id': g, 'name': f'Comunidad {g}'} for g in unique_groups]
                
            comm_rows = []
            for comm in comms:
                # Intentar obtener id y nombre de manera segura
                try:
                    cid = comm.get('id', '')
                    if not cid:  # Saltar si no hay ID de comunidad
                        continue
                        
                    name = comm.get('name', f'Comunidad {cid}')
                    
                    # Filtrar miembros por grupo/comunidad
                    members = []
                    senders = []
                    bens = []
                    
                    for n in nodes:
                        if n.get('group', '') == cid:
                            members.append(n)
                            if n.get('type', '') == 'sender':
                                senders.append(n)
                            else:
                                bens.append(n)
                                
                    # Filtrar aristas internas a la comunidad de manera segura
                    ecs = []
                    for e in edges:
                        source = e.get('source', '')
                        target = e.get('target', '')
                        
                        if (source in node2comm and target in node2comm and 
                            node2comm.get(source) == cid and 
                            node2comm.get(target) == cid):
                            ecs.append(e)
                    
                    # Calcular estadísticas de comunidad
                    total_tx = sum(e.get('transactions', 0) for e in ecs)
                    total_amt = sum(e.get('value', 0) for e in ecs)
                    avg_amt = total_amt / len(ecs) if ecs else 0
                    
                    # Conteo de países
                    country_counter = Counter()
                    for n in members:
                        country = n.get('country', 'Desconocido')
                        if country:  # Solo contar si hay país
                            country_counter[country] += 1
                            
                    top3 = country_counter.most_common(3)
                    paises_principales = ", ".join(f"{pais} ({cnt})" for pais, cnt in top3)
                    
                    # Lista de transacciones únicas en esta comunidad
                    tx_ids = []
                    for e in ecs:
                        if 'transaction_ids' in e and isinstance(e['transaction_ids'], list):
                            tx_ids.extend(e['transaction_ids'])
                    
                    # Lista de IDs de remitentes y beneficiarios
                    remitente_ids = [n.get('id', '') for n in senders]
                    beneficiario_ids = [n.get('id', '') for n in bens]
                    
                    comm_rows.append({
                        'ID': cid,
                        'Nombre': name,
                        'Total Nodos': len(members),
                        'Remitentes': len(senders),
                        'Beneficiarios': len(bens),
                        'Total Aristas': len(ecs),
                        'Total Transacciones': total_tx,
                        'Importe Total Comunidad': total_amt,
                        'Importe Medio Transacción': round(avg_amt, 2),
                        'Países Principales': paises_principales,
                        'IDs Transacciones': tx_ids,
                        'IDs Remitentes': remitente_ids,
                        'IDs Beneficiarios': beneficiario_ids
                    })
                except Exception as e:
                    # En caso de error, continuar con la siguiente comunidad
                    print(f"Error procesando comunidad {comm.get('id', 'desconocida')}: {str(e)}")
                    continue
        except Exception as e:
            # En caso de error general, crear una fila con mensaje de error
            print(f"Error procesando comunidades: {str(e)}")
            comm_rows = [{
                'ID': 0,
                'Nombre': 'Error al procesar comunidades',
                'Total Nodos': 0,
                'Remitentes': 0,
                'Beneficiarios': 0,
                'Total Aristas': 0,
                'Total Transacciones': 0,
                'Importe Total Comunidad': 0,
                'Importe Medio Transacción': 0,
                'Países Principales': ''
            }]

        comm_df = pd.DataFrame(comm_rows)
        comm_df.sort_values('Total Nodos', ascending=False, inplace=True)
        comm_df.to_excel(writer, sheet_name='Comunidades', index=False)
        ws = writer.sheets['Comunidades']
        for col, width in zip(['A','B','C','D','E','F','G','H','I','J'], 
                              [8,40,12,12,12,15,18,20,30,20]):
            ws.set_column(f'{col}:{col}', width)

    # --- 4) Hoja Transacciones Ordenantes ---
    try:
        # Primero verificar que existen las columnas necesarias
        required_columns = ['NUM_DOC_ORDENANTE', 'IMPORTE']
        if all(col in df.columns for col in required_columns):
            # Asegurar valores válidos para agrupar (no NaN/None)
            df_valid = df.copy()
            
            # Rellenar valores faltantes para evitar errores de agrupación
            for col in ['NUM_DOC_ORDENANTE', 'NOMBRE_ORDENANTE', 'PAIS_DOC_ORDENANTE']:
                if col in df_valid.columns:
                    df_valid[col] = df_valid[col].fillna('Desconocido')
                else:
                    df_valid[col] = 'Desconocido'
            
            # Agrupar y agregar estadísticas
            senders_tx = (
                df_valid
                .groupby(['NUM_DOC_ORDENANTE', 'NOMBRE_ORDENANTE', 'PAIS_DOC_ORDENANTE'])
                .agg(Total_Importe=('IMPORTE', 'sum'),
                    Num_Transacciones=('IMPORTE', 'count'),
                    Importe_Medio=('IMPORTE', 'mean'))
                .reset_index()
            )
            
            # Renombrar columnas para mejor legibilidad
            senders_tx.rename(columns={
                'NUM_DOC_ORDENANTE': 'Ordenante ID',
                'NOMBRE_ORDENANTE': 'Ordenante',
                'PAIS_DOC_ORDENANTE': 'País'
            }, inplace=True)
            
            # Ordenar por importe total para mayor claridad
            senders_tx.sort_values('Total_Importe', ascending=False, inplace=True)
            
            # Exportar a Excel
            senders_tx.to_excel(writer, sheet_name='Tx Ordenantes', index=False)
            ws = writer.sheets['Tx Ordenantes']
            for i, w in enumerate([20, 30, 15, 18, 18, 18]):
                ws.set_column(i, i, w)
        else:
            # Si faltan columnas requeridas, crear hoja con mensaje informativo
            empty_df = pd.DataFrame({
                'Información': ['No hay datos suficientes para generar análisis de ordenantes.', 
                               f'Columnas requeridas: {", ".join(required_columns)}',
                               f'Columnas disponibles: {", ".join(df.columns)}']
            })
            empty_df.to_excel(writer, sheet_name='Tx Ordenantes', index=False)
    except Exception as e:
        # Si ocurre algún error, crear hoja con mensaje de error
        error_df = pd.DataFrame({
            'Error': [f'Error al procesar datos de ordenantes: {str(e)}']
        })
        error_df.to_excel(writer, sheet_name='Tx Ordenantes', index=False)

    # --- 5) Hoja Transacciones Beneficiarios ---
    try:
        # Verificar que existen las columnas necesarias
        required_columns = ['IMPORTE']
        id_columns = ['BENEFICIARIO_ID', 'NUM_DOC_BENEFICIARIO']  # Intentar con cualquiera de estos
        
        # Verificar si tenemos al menos una columna de ID válida
        has_id_column = any(col in df.columns for col in id_columns)
        
        if has_id_column and 'IMPORTE' in df.columns:
            # Crear una copia para no modificar el original
            df_valid = df.copy()
            
            # Si no existe BENEFICIARIO_ID pero existe NUM_DOC_BENEFICIARIO, usar ese
            if 'BENEFICIARIO_ID' not in df_valid.columns and 'NUM_DOC_BENEFICIARIO' in df_valid.columns:
                df_valid['BENEFICIARIO_ID'] = df_valid['NUM_DOC_BENEFICIARIO']
            
            # Rellenar valores faltantes para evitar errores
            for col in ['BENEFICIARIO_ID', 'NOMBRE_BENEFICIARIO', 'PAIS_DESTINO']:
                if col in df_valid.columns:
                    df_valid[col] = df_valid[col].fillna('Desconocido')
                else:
                    df_valid[col] = 'Desconocido'
            
            # Agrupar y agregar estadísticas
            bens_tx = (
                df_valid
                .groupby(['BENEFICIARIO_ID', 'NOMBRE_BENEFICIARIO', 'PAIS_DESTINO'])
                .agg(Total_Importe=('IMPORTE', 'sum'),
                     Num_Transacciones=('IMPORTE', 'count'),
                     Importe_Medio=('IMPORTE', 'mean'))
                .reset_index()
            )
            
            # Renombrar columnas para mejor legibilidad
            bens_tx.rename(columns={
                'BENEFICIARIO_ID': 'Beneficiario ID',
                'NOMBRE_BENEFICIARIO': 'Beneficiario',
                'PAIS_DESTINO': 'País'
            }, inplace=True)
            
            # Ordenar por importe total
            bens_tx.sort_values('Total_Importe', ascending=False, inplace=True)
            
            # Exportar a Excel
            bens_tx.to_excel(writer, sheet_name='Tx Beneficiarios', index=False)
            
            # Ajustar anchos de columna
            ws = writer.sheets['Tx Beneficiarios']
            for i, w in enumerate([20, 30, 15, 18, 18, 18]):
                ws.set_column(i, i, w)
        else:
            # Si faltan columnas requeridas, crear hoja con mensaje informativo
            empty_df = pd.DataFrame({
                'Información': ['No hay datos suficientes para generar análisis de beneficiarios.', 
                               f'Columnas requeridas: {", ".join(required_columns)} y al menos una de {", ".join(id_columns)}',
                               f'Columnas disponibles: {", ".join(df.columns)}']
            })
            empty_df.to_excel(writer, sheet_name='Tx Beneficiarios', index=False)
    except Exception as e:
        # Si ocurre algún error, crear hoja con mensaje de error
        error_df = pd.DataFrame({
            'Error': [f'Error al procesar datos de beneficiarios: {str(e)}']
        })
        error_df.to_excel(writer, sheet_name='Tx Beneficiarios', index=False)
        ws = writer.sheets['Tx Beneficiarios']
        for i,w in enumerate([20,30,15,18,18]):
            ws.set_column(i, i, w)

    # Finalmente guardar y codificar
    writer.close()
    excel_data = buffer.getvalue()
    buffer.close()
    return base64.b64encode(excel_data).decode('utf-8')


def get_download_link(data: str, filename: str, file_type: str = "pdf") -> str:
    """
    Crea un enlace HTML para descargar un archivo.

    Args:
        data: Datos en base64
        filename: Nombre del archivo para la descarga
        file_type: Tipo de archivo ('pdf' o 'excel')

    Returns:
        Enlace HTML para descargar
    """
    if file_type == "pdf":
        mime_type = "application/pdf"
    elif file_type == "excel":
        mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else:
        mime_type = "application/octet-stream"

    href = f'<a href="data:{mime_type};base64,{data}" download="{filename}" class="btn-download">Descargar {filename}</a>'
    return href