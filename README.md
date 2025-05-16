# Sistema de Análisis de Riesgo de Lavado de Dinero

Una aplicación Streamlit para el análisis avanzado de riesgos de lavado de dinero, detección de patrones sospechosos y generación de informes detallados. La aplicación utiliza algoritmos de análisis de 20 indicadores diferentes de riesgo, visualización de redes de transacciones, y detección de comunidades para facilitar la identificación de actividades potencialmente sospechosas.

## Características principales

- **Análisis de 20 indicadores de riesgo**: Evaluación exhaustiva basada en indicadores específicos como documentación repetida, operaciones estructuradas, y perfiles de alto riesgo.
- **Visualización de redes de transacciones**: Representación gráfica de conexiones entre remitentes y beneficiarios.
- **Detección de comunidades**: Identificación automática de grupos conectados de operaciones.
- **Análisis de patrones**: Detección de actividades estructuradas y repetitivas.
- **Exportación de informes**: Generación de reportes detallados en formatos CSV y Excel.
- **Interfaz intuitiva**: Filtros dinámicos y visualización interactiva de los datos.

## Requisitos del sistema

- Python 3.8 o superior
- Los paquetes listados en `requirements.txt`

## Instalación

Siga estos pasos para instalar y ejecutar la aplicación en su entorno local:

1. Clone o descargue este repositorio:
```bash
git clone https://github.com/tu-usuario/analisis-riesgo-ld.git
cd analisis-riesgo-ld
```

2. Instale las dependencias necesarias:
```bash
pip install streamlit pandas numpy matplotlib plotly networkx fuzzywuzzy python-levenshtein rapidfuzz babel pycountry pytz reportlab xlsxwriter openpyxl
```

Alternativamente, puede instalar desde el archivo de dependencias proporcionado:
```bash
pip install -r dependencies.txt
```

3. Ejecute la aplicación:
```bash
streamlit run app.py --server.port 5000
```

La aplicación estará disponible en `http://localhost:5000` en su navegador.

### Estructura de archivos necesaria

Para asegurar el correcto funcionamiento, se debe mantener la siguiente estructura de carpetas:
```
analisis-riesgo-ld/
├── app.py                 # Archivo principal de la aplicación
├── utils/                 # Carpeta con módulos de utilidades
│   ├── __init__.py
│   ├── column_definitions.py
│   ├── data_processing.py
│   ├── export_utils.py
│   ├── network_analysis.py
│   ├── visualizations.py
│   ├── fixed_risk_indicators.py
│   ├── risk_indicators.py
│   └── indicadores/
│       ├── __init__.py
│       └── riesgo.py      # Implementación de los 20 indicadores de riesgo
```

### Uso de datos de ejemplo

Los archivos de ejemplo incluidos en `attached_assets/` se pueden utilizar para pruebas. Se recomienda usar los archivos:
- `informe_riesgo_04.xlsx`
- `informe_riesgo_detallado(5).xlsx`

## Archivos y carpetas

- **app.py**: Punto de entrada principal de la aplicación Streamlit.
- **utils/**: Módulos de utilidades para análisis de riesgo, procesamiento de datos y visualización.
  - **indicadores/riesgo.py**: Implementación de los 20 indicadores de riesgo.
  - **data_processing.py**: Funciones para el procesamiento de datos transaccionales.
  - **export_utils.py**: Utilidades para la exportación de informes.
  - **network_analysis.py**: Módulo para análisis de redes de transacciones.
  - **visualizations.py**: Componentes de visualización y gráficos.

## Uso

1. Cargue archivos CSV con datos de transacciones financieras.
2. Seleccione los filtros deseados (por agente, importe, país, etc.).
3. Ejecute el análisis utilizando los botones de acción.
4. Explore los resultados en las diferentes pestañas:
   - **Exploración de Datos**: Visualización y filtrado de transacciones.
   - **Análisis de Riesgo**: Evaluación de los 20 indicadores y detalle de transacciones sospechosas.
   - **Análisis de Red**: Visualización gráfica de las conexiones entre remitentes y beneficiarios.
   - **Reportes**: Generación de informes detallados y detección de patrones.

## Datos de ejemplo

La aplicación incluye algunos archivos de ejemplo en la carpeta `attached_assets/` que pueden utilizarse para probar las funcionalidades del sistema.

## Licencia

Este proyecto está licenciado bajo [Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License (CC BY-NC-SA 4.0)](https://creativecommons.org/licenses/by-nc-sa/4.0/).

### Esto significa que puedes:
- **Compartir** — copiar y redistribuir el material en cualquier medio o formato
- **Adaptar** — remezclar, transformar y construir a partir del material

### Bajo los siguientes términos:
- **Atribución** — Debes dar crédito de manera adecuada, proporcionar un enlace a la licencia e indicar si se han realizado cambios. Puedes hacerlo en cualquier forma razonable, pero no de forma que sugiera que el licenciador te respalda a ti o el uso que haces.
- **NoComercial** — No puedes utilizar el material para fines comerciales.
- **CompartirIgual** — Si remezclas, transformas o creas a partir del material, debes distribuir tu contribución bajo la misma licencia que el original.

![CC BY-NC-SA](https://licensebuttons.net/l/by-nc-sa/4.0/88x31.png)