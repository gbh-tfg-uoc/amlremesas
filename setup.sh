#!/bin/bash

# Script de instalación para el Sistema de Análisis de Riesgo de Lavado de Dinero

echo "Instalando dependencias para el Sistema de Análisis de Riesgo..."

# Verificar si Python está instalado
if command -v python3 &>/dev/null; then
    echo "Python 3 encontrado"
else
    echo "ADVERTENCIA: Python 3 no está instalado. Por favor, instale Python 3.8 o superior."
    exit 1
fi

# Verificar si pip está instalado
if command -v pip3 &>/dev/null; then
    echo "Pip encontrado"
else
    echo "ADVERTENCIA: pip no está instalado. Intentando instalar..."
    python3 -m ensurepip --upgrade
fi

# Instalar dependencias
echo "Instalando paquetes requeridos..."
pip3 install streamlit pandas numpy matplotlib plotly networkx fuzzywuzzy python-levenshtein rapidfuzz babel pycountry pytz reportlab xlsxwriter openpyxl

# Verificar que las carpetas necesarias existen
if [ ! -d "utils" ]; then
    echo "ADVERTENCIA: La carpeta 'utils' no existe. Creando carpeta y estructura básica..."
    mkdir -p utils/indicadores
    touch utils/__init__.py
    touch utils/indicadores/__init__.py
    echo "Carpetas creadas. Por favor, asegúrese de copiar los archivos de código fuente necesarios."
fi

echo ""
echo "La instalación ha finalizado."
echo ""
echo "Para iniciar la aplicación, ejecute:"
echo "streamlit run app.py --server.port 5000"
echo ""
echo "La aplicación estará disponible en http://localhost:5000"