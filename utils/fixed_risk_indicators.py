import pandas as pd
import numpy as np
from typing import Tuple, List, Dict, Any
import re
from datetime import datetime, timedelta
import warnings
import traceback

# Desactivar advertencias de copia de pandas para uso interno
pd.options.mode.chained_assignment = None

# Importar manteniendo la consistencia con las interfaces
from utils.indicadores.riesgo import *

def safe_concat(df_list, **kwargs):
    """
    Concatenación segura de DataFrames con manejo de errores.
    """
    if not df_list:
        return pd.DataFrame()
        
    # Filtrar DataFrames nulos o vacíos
    valid_dfs = [df for df in df_list if df is not None and not df.empty]
    
    if not valid_dfs:
        return pd.DataFrame()
    
    try:
        return pd.concat(valid_dfs, **kwargs)
    except Exception as e:
        print(f"Error al concatenar DataFrames: {str(e)}")
        return pd.DataFrame()

def calcular_riesgos_por_agente(df, selected_agents=None):
    """
    Calcula los riesgos para cada agente seleccionado.
    Versión corregida que maneja todos los errores potenciales.
    
    Args:
        df: DataFrame con los datos a analizar
        selected_agents: Lista de agentes seleccionados para análisis
        
    Returns:
        Tuple con tres diccionarios:
        - Riesgos individuales por agente
        - Resultados por tipo de riesgo por agente
        - Operaciones sospechosas por agente
    """
    # Validar entrada
    if df is None or (hasattr(df, 'empty') and df.empty):
        print("DataFrame vacío - devolviendo valores por defecto")
        return {}, {}, {}
    
    # Asegurar que tenemos una copia segura para trabajar
    try:
        df_safe = df.copy()
    except Exception as e:
        print(f"Error al crear copia del DataFrame: {str(e)}")
        return {}, {}, {}
    
    # Verificar que tenemos una columna que identifica agentes
    agente_column = None
    for col in ['AGENTE', 'ENT_NAT_REF_COD', 'COD_AGENTE', 'ID_Agente']:
        if col in df_safe.columns:
            agente_column = col
            break
        
    if not agente_column:
        print("Advertencia: No se encontró columna de identificación de agente.")
        return {}, {}, {}
    
    # Normalizar agentes (prefijo "Agente" consistente)
    def normalize_agent(agent):
        if agent is None:
            return None
            
        agent_str = str(agent)
        
        # Si ya tiene el formato "AgenteXXX"
        if agent_str.startswith("Agente"):
            return agent_str
        # Si es solo un número, añadir el prefijo
        elif agent_str.isdigit():
            return f"Agente{agent_str}"
        # Cualquier otro caso, mantener como está
        return agent_str
    
    # Normalizar agentes seleccionados
    normalized_selected = None
    if selected_agents:
        normalized_selected = [normalize_agent(agent) for agent in selected_agents]
    
    try:
        # Obtener agentes únicos
        agent_values = df_safe[agente_column].dropna().astype(str).unique()
        unique_agents = [normalize_agent(agent) for agent in agent_values]
        
        # Si se especifica una lista de agentes, filtrarla
        if normalized_selected:
            unique_agents = [agent for agent in unique_agents if agent in normalized_selected]
    except Exception as e:
        print(f"Error al obtener agentes únicos: {str(e)}")
        return {}, {}, {}
    
    # Inicializar diccionarios de resultados
    resultados_por_agente = {}  # {agente: {indicador: valor, ...}, ...}
    resultados_por_tipo = {}    # {agente: {tipo_indicador: valor_promedio, ...}, ...}
    operaciones_sospechosas = {} # {agente: DataFrame con operaciones sospechosas}
    
    # Calcular riesgos para cada agente
    for agente in unique_agents:
        if pd.isna(agente) or agente is None:
            continue
            
        # Filtrar DataFrame por agente (permitiendo coincidencias parciales)
        try:
            df_agente = df_safe[df_safe[agente_column].astype(str).str.contains(agente, regex=False)]
            
            # Si está vacío, intentar quitar el prefijo "Agente" para la búsqueda
            if df_agente.empty and agente.startswith("Agente"):
                agent_num = agente[6:]  # Quitar "Agente"
                df_agente = df_safe[df_safe[agente_column].astype(str) == agent_num]
            
            if df_agente.empty:
                print(f"Sin datos para el agente {agente}")
                continue
        except Exception as e:
            print(f"Error al filtrar datos para el agente {agente}: {str(e)}")
            continue
        
        # Inicializar valores y estructuras para este agente
        indicadores_valores = {}
        resultados_por_agente[agente] = {}
        operaciones_sospechosas[agente] = pd.DataFrame()
        
        # Calcular los 20 indicadores para este agente con manejo de errores
        for indicador_id in range(1, 21):
            indicador_str = str(indicador_id)
            
            try:
                # Obtener el nombre de la función a invocar
                func_name = f"calcular_riesgo_indicador_{indicador_id}"
                calc_func = globals().get(func_name)
                
                if calc_func is not None:
                    # Con manejo de errores
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore")
                        try:
                            score, df_result = calc_func(df_agente)
                            
                            # Guardamos el valor (score es un entero del 1 al 4)
                            indicadores_valores[indicador_str] = int(score) if isinstance(score, (int, float)) else 1
                            
                            # Agregamos operaciones sospechosas
                            if df_result is not None and not df_result.empty:
                                operaciones_sospechosas[agente] = safe_concat(
                                    [operaciones_sospechosas[agente], df_result], 
                                    ignore_index=True
                                )
                        except Exception as indic_error:
                            print(f"Error en indicador {indicador_id} para agente {agente}: {str(indic_error)}")
                            indicadores_valores[indicador_str] = 1  # Valor por defecto (mínimo riesgo)
                else:
                    print(f"Función para indicador {indicador_id} no encontrada")
                    indicadores_valores[indicador_str] = 1
            except Exception as e:
                print(f"Error general en indicador {indicador_id} para agente {agente}: {str(e)}")
                indicadores_valores[indicador_str] = 1
        
        # Actualizar diccionario de resultados para este agente
        resultados_por_agente[agente] = indicadores_valores
        
        # Calcular promedios por tipo de indicador
        try:
            tipos_indicador = {
                'DOCUMENTACIÓN': ['1', '2', '3', '13', '20'],
                'UMBRALES': ['4', '5', '6', '7'],
                'GEOGRÁFICO': ['8', '11', '19'],
                'OUTLIERS': ['9', '10', '12', '14', '15', '16', '17', '18']
            }
            
            resultados_por_tipo[agente] = {}
            for tipo, indicadores in tipos_indicador.items():
                # Filtrar valores disponibles
                valores = [indicadores_valores.get(ind, 1) for ind in indicadores]
                # Calcular promedio
                promedio = sum(valores) / len(valores) if valores else 1.0
                resultados_por_tipo[agente][tipo] = promedio
                
        except Exception as e:
            print(f"Error al calcular promedios por tipo para agente {agente}: {str(e)}")
            # Valores por defecto
            resultados_por_tipo[agente] = {
                'DOCUMENTACIÓN': 1.0,
                'UMBRALES': 1.0,
                'GEOGRÁFICO': 1.0,
                'OUTLIERS': 1.0
            }
    
    # Resultados para el conjunto global
    try:
        # Calcular resultados para el conjunto global si hay datos
        if not df_safe.empty:
            agente_global = "GLOBAL"
            indicadores_valores = {}
            operaciones_sospechosas[agente_global] = pd.DataFrame()
            
            # Cálculo para cada indicador
            for indicador_id in range(1, 21):
                indicador_str = str(indicador_id)
                
                try:
                    func_name = f"calcular_riesgo_indicador_{indicador_id}"
                    calc_func = globals().get(func_name)
                    
                    if calc_func is not None:
                        with warnings.catch_warnings():
                            warnings.simplefilter("ignore")
                            try:
                                score, df_result = calc_func(df_safe)
                                indicadores_valores[indicador_str] = int(score) if isinstance(score, (int, float)) else 1
                                
                                if df_result is not None and not df_result.empty:
                                    operaciones_sospechosas[agente_global] = safe_concat(
                                        [operaciones_sospechosas[agente_global], df_result], 
                                        ignore_index=True
                                    )
                            except Exception as indic_error:
                                print(f"Error en indicador {indicador_id} para conjunto global: {str(indic_error)}")
                                indicadores_valores[indicador_str] = 1
                    else:
                        indicadores_valores[indicador_str] = 1
                except Exception:
                    indicadores_valores[indicador_str] = 1
            
            # Agregar resultados globales
            resultados_por_agente[agente_global] = indicadores_valores
            
            # Promedios por tipo para el conjunto global
            resultados_por_tipo[agente_global] = {}
            for tipo, indicadores in tipos_indicador.items():
                valores = [indicadores_valores.get(ind, 1) for ind in indicadores]
                promedio = sum(valores) / len(valores) if valores else 1.0
                resultados_por_tipo[agente_global][tipo] = promedio
                
    except Exception as e:
        print(f"Error al calcular indicadores para el conjunto global: {str(e)}")
    
    return resultados_por_agente, resultados_por_tipo, operaciones_sospechosas

def calcular_riesgo_promedio(riesgos_individuales):
    """
    Calcula el riesgo promedio para cada indicador, excluyendo el valor global.
    Solo utiliza los valores de los agentes individuales.
    
    Args:
        riesgos_individuales: Diccionario con riesgos por agente
        
    Returns:
        Diccionario con el riesgo promedio por indicador
    """
    if not riesgos_individuales:
        return {str(i): 1 for i in range(1, 21)}
    
    # Inicializar diccionario para la suma de valores por indicador
    sumas_por_indicador = {str(i): 0 for i in range(1, 21)}
    conteos_por_indicador = {str(i): 0 for i in range(1, 21)}
    
    # Sumar todos los valores por indicador, EXCLUYENDO el agente GLOBAL
    for agente, indicadores in riesgos_individuales.items():
        # No incluir el valor global en el cálculo del promedio
        if agente == "GLOBAL":
            continue
            
        for indicador, valor in indicadores.items():
            try:
                sumas_por_indicador[indicador] += float(valor)
                conteos_por_indicador[indicador] += 1
            except (ValueError, TypeError, KeyError):
                pass  # Ignorar valores no numéricos o indicadores no válidos
    
    # Calcular promedio para cada indicador
    promedios = {}
    for indicador in sumas_por_indicador:
        if conteos_por_indicador[indicador] > 0:
            promedios[indicador] = sumas_por_indicador[indicador] / conteos_por_indicador[indicador]
        else:
            promedios[indicador] = 1.0  # Valor por defecto
    
    return promedios

def formatear_valor_riesgo(valor):
    """
    Formatea un valor numérico para mostrar 2 decimales SIEMPRE (excepto para valores como 0, 1, 2, 3, 4).
    
    Args:
        valor: Valor numérico a formatear
        
    Returns:
        Valor formateado con 2 decimales
    """
    try:
        # Convertir a float para asegurar compatibilidad
        numeric_val = float(valor)
        
        # Si es exactamente un entero entre 0 y 4, mantenerlo como entero
        if numeric_val in [0, 1, 2, 3, 4]:
            return int(numeric_val)
        else:
            # Para cualquier otro valor, siempre mostrar 2 decimales
            return "{:.2f}".format(numeric_val)
    except (ValueError, TypeError):
        # En caso de error (ej. valor no numérico), devolver el valor original como string
        return str(valor)