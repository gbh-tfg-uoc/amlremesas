#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para ejecutar la aplicación de Análisis de Riesgo de Lavado de Dinero.
Este script configura el entorno y lanza la aplicación con los parámetros correctos.
"""

import os
import sys
import subprocess
import webbrowser
from pathlib import Path

def check_dependencies():
    """Verifica que todas las dependencias estén instaladas."""
    try:
        import streamlit
        import pandas
        import numpy
        import matplotlib
        import plotly
        import networkx
        import fuzzywuzzy
        import babel
        import pycountry
        return True
    except ImportError as e:
        print(f"Error: Dependencia faltante - {e}")
        print("Por favor, ejecute 'setup.sh' (Linux/Mac) o 'setup.bat' (Windows) para instalar las dependencias.")
        return False

def ensure_streamlit_config():
    """Asegura que exista la configuración de Streamlit."""
    config_dir = Path.home() / ".streamlit"
    config_file = config_dir / "config.toml"
    
    # Si no existe el directorio de configuración, lo creamos
    if not config_dir.exists():
        config_dir.mkdir(parents=True, exist_ok=True)
    
    # Si no existe el archivo de configuración o está vacío, escribimos la configuración
    if not config_file.exists() or config_file.stat().st_size == 0:
        with open(config_file, "w") as f:
            f.write("""[server]
headless = true
address = "0.0.0.0"
port = 5000

[browser]
gatherUsageStats = false
""")

def main():
    """Función principal que ejecuta la aplicación."""
    print("Iniciando Sistema de Análisis de Riesgo de Lavado de Dinero...")
    
    # Verificar dependencias
    if not check_dependencies():
        return 1
    
    # Asegurar configuración de Streamlit
    ensure_streamlit_config()
    
    # Directorio del script (para asegurarnos de ejecutar desde el directorio correcto)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    # Comando para ejecutar Streamlit
    cmd = [sys.executable, "-m", "streamlit", "run", "app.py", "--server.port", "5000"]
    
    # Abrir el navegador automáticamente
    url = "http://localhost:5000"
    webbrowser.open(url, new=2)
    
    # Ejecutar Streamlit
    print(f"Ejecutando: {' '.join(cmd)}")
    print(f"La aplicación estará disponible en: {url}")
    process = subprocess.Popen(cmd)
    
    try:
        # Mantener el proceso ejecutándose
        process.wait()
    except KeyboardInterrupt:
        print("\nDeteniendo la aplicación...")
        process.terminate()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())