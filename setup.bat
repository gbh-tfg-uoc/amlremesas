@echo off
ECHO Instalando dependencias para el Sistema de Análisis de Riesgo...

REM Verificar si Python está instalado
python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    ECHO ADVERTENCIA: Python no está instalado o no está en el PATH. Por favor, instale Python 3.8 o superior.
    PAUSE
    EXIT /B
)

REM Verificar si pip está instalado
pip --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    ECHO ADVERTENCIA: pip no está instalado. Intentando instalar...
    python -m ensurepip --upgrade
    IF %ERRORLEVEL% NEQ 0 (
        ECHO Error al instalar pip. Por favor, instálelo manualmente.
        PAUSE
        EXIT /B
    )
)

REM Instalar dependencias
ECHO Instalando paquetes requeridos...
pip install streamlit pandas numpy matplotlib plotly networkx fuzzywuzzy python-levenshtein rapidfuzz babel pycountry pytz reportlab xlsxwriter openpyxl

REM Verificar que las carpetas necesarias existen
IF NOT EXIST utils (
    ECHO ADVERTENCIA: La carpeta 'utils' no existe. Creando carpeta y estructura básica...
    mkdir utils\indicadores
    type nul > utils\__init__.py
    type nul > utils\indicadores\__init__.py
    ECHO Carpetas creadas. Por favor, asegúrese de copiar los archivos de código fuente necesarios.
)

ECHO.
ECHO La instalación ha finalizado.
ECHO.
ECHO Para iniciar la aplicación, ejecute:
ECHO streamlit run app.py --server.port 5000
ECHO.
ECHO La aplicación estará disponible en http://localhost:5000
PAUSE