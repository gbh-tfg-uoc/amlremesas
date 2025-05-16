import pandas as pd
import numpy as np
from typing import Tuple, List, Dict, Any
import re
from datetime import datetime, timedelta
from utils.indicadores.riesgo import *

# Funciones integradas de utils/indicadores_riesgo.py
def calcular_riesgos_por_agente(df, selected_agents=None):
    """
    Calcula los riesgos para cada agente seleccionado.

    Args:
        df: DataFrame con los datos a analizar
        selected_agents: Lista de agentes seleccionados para análisis

    Returns:
        Tuple con tres diccionarios:
        - Riesgos individuales por agente
        - Resultados por tipo de riesgo por agente
        - Operaciones sospechosas por agente
    """
    if df.empty:
        return {}, {}, {}

    # Verificar que tenemos una columna que identifica agentes
    agente_column = None
    if 'ENT_NAT_REF_COD' in df.columns:
        agente_column = 'ENT_NAT_REF_COD'
    elif 'COD_AGENTE' in df.columns:
        agente_column = 'COD_AGENTE'
    elif 'ID_Agente' in df.columns:
        agente_column = 'ID_Agente'

    if not agente_column:
        print("Advertencia: No se encontró columna de identificación de agente.")
        return {}, {}, {}

    # Obtener agentes únicos
    unique_agents = df[agente_column].dropna().unique()

    # Si se especifica una lista de agentes, filtrarla
    if selected_agents:
        unique_agents = [agent for agent in unique_agents if agent in selected_agents]

    # Inicializar diccionarios de resultados
    resultados_por_agente = {}  # {agente: {indicador: valor, ...}, ...}
    resultados_por_tipo = {}    # {agente: {tipo_indicador: valor_promedio, ...}, ...}
    operaciones_sospechosas = {} # {agente: DataFrame con operaciones sospechosas}

    # Calcular riesgos para cada agente
    for agente in unique_agents:
        if pd.isna(agente):
            continue

        # Filtrar DataFrame por agente
        df_agente = df[df[agente_column] == agente]

        if df_agente.empty:
            continue

        # Calcular los 20 indicadores para este agente
        indicadores_valores = {}
        try:
            # Indicador 1: Uso de la misma documentación en corto espacio de tiempo
            score, df_result = calcular_riesgo_indicador_1(df_agente)
            indicadores_valores['1'] = score
            if not df_result.empty:
                df_result = df_result.copy()
                df_result['Indicador'] = '1'
                if agente not in operaciones_sospechosas:
                    operaciones_sospechosas[agente] = pd.DataFrame()
                operaciones_sospechosas[agente] = pd.concat([operaciones_sospechosas[agente], df_result], ignore_index=True)

            # Indicador 2: Documento repetido con nombres diferentes
            score, df_result = calcular_riesgo_indicador_2(df_agente)
            indicadores_valores['2'] = score
            if not df_result.empty:
                df_result = df_result.copy()
                df_result['Indicador'] = '2'
                if agente not in operaciones_sospechosas:
                    operaciones_sospechosas[agente] = pd.DataFrame()
                operaciones_sospechosas[agente] = pd.concat([operaciones_sospechosas[agente], df_result], ignore_index=True)

            # Indicador 3: Documentación con formato alfanumérico erróneo
            score, df_result = calcular_riesgo_indicador_3(df_agente)
            indicadores_valores['3'] = score
            if not df_result.empty:
                df_result = df_result.copy()
                df_result['Indicador'] = '3'
                if agente not in operaciones_sospechosas:
                    operaciones_sospechosas[agente] = pd.DataFrame()
                operaciones_sospechosas[agente] = pd.concat([operaciones_sospechosas[agente], df_result], ignore_index=True)

            # Indicador 4: Operaciones para eludir umbrales
            score, df_result = calcular_riesgo_indicador_4(df_agente)
            indicadores_valores['4'] = score
            if not df_result.empty:
                df_result = df_result.copy()
                df_result['Indicador'] = '4'
                if agente not in operaciones_sospechosas:
                    operaciones_sospechosas[agente] = pd.DataFrame()
                operaciones_sospechosas[agente] = pd.concat([operaciones_sospechosas[agente], df_result], ignore_index=True)

            # Indicador 5: Operaciones fragmentadas por grupo de clientes
            score, df_result = calcular_riesgo_indicador_5(df_agente)
            indicadores_valores['5'] = score
            if not df_result.empty:
                df_result = df_result.copy()
                df_result['Indicador'] = '5'
                if agente not in operaciones_sospechosas:
                    operaciones_sospechosas[agente] = pd.DataFrame()
                operaciones_sospechosas[agente] = pd.concat([operaciones_sospechosas[agente], df_result], ignore_index=True)

            # Indicador 6: Uso sistemático de importes redondos
            score, df_result = calcular_riesgo_indicador_6(df_agente)
            indicadores_valores['6'] = score
            if not df_result.empty:
                df_result = df_result.copy()
                df_result['Indicador'] = '6'
                if agente not in operaciones_sospechosas:
                    operaciones_sospechosas[agente] = pd.DataFrame()
                operaciones_sospechosas[agente] = pd.concat([operaciones_sospechosas[agente], df_result], ignore_index=True)

            # Indicador 7: Numerosas cancelaciones de operaciones
            score, df_result = calcular_riesgo_indicador_7(df_agente)
            indicadores_valores['7'] = score
            if not df_result.empty:
                df_result = df_result.copy()
                df_result['Indicador'] = '7'
                if agente not in operaciones_sospechosas:
                    operaciones_sospechosas[agente] = pd.DataFrame()
                operaciones_sospechosas[agente] = pd.concat([operaciones_sospechosas[agente], df_result], ignore_index=True)

            # Indicador 8: Transferencias a países de alto riesgo
            score, df_result = calcular_riesgo_indicador_8(df_agente)
            indicadores_valores['8'] = score
            if not df_result.empty:
                df_result = df_result.copy()
                df_result['Indicador'] = '8'
                if agente not in operaciones_sospechosas:
                    operaciones_sospechosas[agente] = pd.DataFrame()
                operaciones_sospechosas[agente] = pd.concat([operaciones_sospechosas[agente], df_result], ignore_index=True)

            # Indicador 9: Operaciones no correspondientes al perfil habitual
            score, df_result = calcular_riesgo_indicador_9(df_agente)
            indicadores_valores['9'] = score
            if not df_result.empty:
                df_result = df_result.copy()
                df_result['Indicador'] = '9'
                if agente not in operaciones_sospechosas:
                    operaciones_sospechosas[agente] = pd.DataFrame()
                operaciones_sospechosas[agente] = pd.concat([operaciones_sospechosas[agente], df_result], ignore_index=True)

            # Indicador 10: Personas políticamente expuestas
            score, df_result = calcular_riesgo_indicador_10(df_agente)
            indicadores_valores['10'] = score
            if not df_result.empty:
                df_result = df_result.copy()
                df_result['Indicador'] = '10'
                if agente not in operaciones_sospechosas:
                    operaciones_sospechosas[agente] = pd.DataFrame()
                operaciones_sospechosas[agente] = pd.concat([operaciones_sospechosas[agente], df_result], ignore_index=True)

            # Indicador 11: Cambios en patrones hacia países riesgo
            score, df_result = calcular_riesgo_indicador_11(df_agente)
            indicadores_valores['11'] = score
            if not df_result.empty:
                df_result = df_result.copy()
                df_result['Indicador'] = '11'
                if agente not in operaciones_sospechosas:
                    operaciones_sospechosas[agente] = pd.DataFrame()
                operaciones_sospechosas[agente] = pd.concat([operaciones_sospechosas[agente], df_result], ignore_index=True)

            # Indicador 12: Volumen anormalmente elevado
            score, df_result = calcular_riesgo_indicador_12(df_agente)
            indicadores_valores['12'] = score
            if not df_result.empty:
                df_result = df_result.copy()
                df_result['Indicador'] = '12'
                if agente not in operaciones_sospechosas:
                    operaciones_sospechosas[agente] = pd.DataFrame()
                operaciones_sospechosas[agente] = pd.concat([operaciones_sospechosas[agente], df_result], ignore_index=True)

            # Indicador 13: Información incompleta de clientes
            score, df_result = calcular_riesgo_indicador_13(df_agente)
            indicadores_valores['13'] = score
            if not df_result.empty:
                df_result = df_result.copy()
                df_result['Indicador'] = '13'
                if agente not in operaciones_sospechosas:
                    operaciones_sospechosas[agente] = pd.DataFrame()
                operaciones_sospechosas[agente] = pd.concat([operaciones_sospechosas[agente], df_result], ignore_index=True)

            # Indicador 14: Importes superiores a la media del municipio
            score, df_result = calcular_riesgo_indicador_14(df_agente)
            indicadores_valores['14'] = score
            if not df_result.empty:
                df_result = df_result.copy()
                df_result['Indicador'] = '14'
                if agente not in operaciones_sospechosas:
                    operaciones_sospechosas[agente] = pd.DataFrame()
                operaciones_sospechosas[agente] = pd.concat([operaciones_sospechosas[agente], df_result], ignore_index=True)

            # Indicador 15: Aumentos repentinos de actividad
            score, df_result = calcular_riesgo_indicador_15(df_agente)
            indicadores_valores['15'] = score
            if not df_result.empty:
                df_result = df_result.copy()
                df_result['Indicador'] = '15'
                if agente not in operaciones_sospechosas:
                    operaciones_sospechosas[agente] = pd.DataFrame()
                operaciones_sospechosas[agente] = pd.concat([operaciones_sospechosas[agente], df_result], ignore_index=True)

            # Indicador 16: Importes mayores para ciertos destinos
            score, df_result = calcular_riesgo_indicador_16(df_agente)
            indicadores_valores['16'] = score
            if not df_result.empty:
                df_result = df_result.copy()
                df_result['Indicador'] = '16'
                if agente not in operaciones_sospechosas:
                    operaciones_sospechosas[agente] = pd.DataFrame()
                operaciones_sospechosas[agente] = pd.concat([operaciones_sospechosas[agente], df_result], ignore_index=True)

            # Indicador 17: Concentración temporal de operaciones
            score, df_result = calcular_riesgo_indicador_17(df_agente)
            indicadores_valores['17'] = score
            if not df_result.empty:
                df_result = df_result.copy()
                df_result['Indicador'] = '17'
                if agente not in operaciones_sospechosas:
                    operaciones_sospechosas[agente] = pd.DataFrame()
                operaciones_sospechosas[agente] = pd.concat([operaciones_sospechosas[agente], df_result], ignore_index=True)

            # Indicador 18: Un mismo remitente a varios países
            score, df_result = calcular_riesgo_indicador_18(df_agente)
            indicadores_valores['18'] = score
            if not df_result.empty:
                df_result = df_result.copy()
                df_result['Indicador'] = '18'
                if agente not in operaciones_sospechosas:
                    operaciones_sospechosas[agente] = pd.DataFrame()
                operaciones_sospechosas[agente] = pd.concat([operaciones_sospechosas[agente], df_result], ignore_index=True)

            # Indicador 19: Remitentes de nacionalidades distintas al país destino
            score, df_result = calcular_riesgo_indicador_19(df_agente)
            indicadores_valores['19'] = score
            if not df_result.empty:
                df_result = df_result.copy()
                df_result['Indicador'] = '19'
                if agente not in operaciones_sospechosas:
                    operaciones_sospechosas[agente] = pd.DataFrame()
                operaciones_sospechosas[agente] = pd.concat([operaciones_sospechosas[agente], df_result], ignore_index=True)

            # Indicador 20: Datos genéricos o repetitivos
            score, df_result = calcular_riesgo_indicador_20(df_agente)
            indicadores_valores['20'] = score
            if not df_result.empty:
                df_result = df_result.copy()
                df_result['Indicador'] = '20'
                if agente not in operaciones_sospechosas:
                    operaciones_sospechosas[agente] = pd.DataFrame()
                operaciones_sospechosas[agente] = pd.concat([operaciones_sospechosas[agente], df_result], ignore_index=True)

        except Exception as e:
            print(f"Error al calcular indicadores para agente {agente}: {str(e)}")
            continue

        # Guardar resultados por agente
        resultados_por_agente[agente] = indicadores_valores

        # Calcular promedios por tipo de indicador
        try:
            from utils.umbral_definitions import TIPOS_INDICADORES

            tipos_valores = {}
            for tipo in set(TIPOS_INDICADORES.values()):
                if tipo != 'No clasificado':
                    indicadores_tipo = [k for k, v in TIPOS_INDICADORES.items() if v == tipo]
                    valores_tipo = [indicadores_valores.get(ind, 1) for ind in indicadores_tipo if ind in indicadores_valores]
                    if valores_tipo:
                        tipos_valores[tipo] = sum(valores_tipo) / len(valores_tipo)
                    else:
                        tipos_valores[tipo] = 1.0

            resultados_por_tipo[agente] = tipos_valores
        except Exception as e:
            print(f"Error al calcular promedios por tipo para agente {agente}: {str(e)}")

    # Calcular riesgo global (promedio de todos los agentes)
    df_global = df.copy()
    global_valores = {}

    try:
        # Calcular todos los indicadores para el conjunto global
        # Indicador 1: Uso de la misma documentación en corto espacio de tiempo
        score, df_result = calcular_riesgo_indicador_1(df_global)
        global_valores['1'] = score
        df_result = df_result.copy()
        df_result['Indicador'] = '1'
        if not df_result.empty:
            if "GLOBAL" not in operaciones_sospechosas:
                operaciones_sospechosas["GLOBAL"] = pd.DataFrame()
            operaciones_sospechosas["GLOBAL"] = pd.concat([operaciones_sospechosas["GLOBAL"], df_result], ignore_index=True)

        # Indicador 2: Documento repetido con nombres diferentes
        score, df_result = calcular_riesgo_indicador_2(df_global)
        global_valores['2'] = score
        df_result = df_result.copy()
        df_result['Indicador'] = '2'
        if not df_result.empty:
            if "GLOBAL" not in operaciones_sospechosas:
                operaciones_sospechosas["GLOBAL"] = pd.DataFrame()
            operaciones_sospechosas["GLOBAL"] = pd.concat([operaciones_sospechosas["GLOBAL"], df_result], ignore_index=True)

        # Indicador 3: Documentación con formato alfanumérico erróneo
        score, df_result = calcular_riesgo_indicador_3(df_global)
        global_valores['3'] = score
        df_result = df_result.copy()
        df_result['Indicador'] = '3'
        if not df_result.empty:
            if "GLOBAL" not in operaciones_sospechosas:
                operaciones_sospechosas["GLOBAL"] = pd.DataFrame()
            operaciones_sospechosas["GLOBAL"] = pd.concat([operaciones_sospechosas["GLOBAL"], df_result], ignore_index=True)

        # Indicador 4: Operaciones para eludir umbrales
        score, df_result = calcular_riesgo_indicador_4(df_global)
        global_valores['4'] = score
        df_result = df_result.copy()
        df_result['Indicador'] = '4'        
        if not df_result.empty:
            if "GLOBAL" not in operaciones_sospechosas:
                operaciones_sospechosas["GLOBAL"] = pd.DataFrame()
            operaciones_sospechosas["GLOBAL"] = pd.concat([operaciones_sospechosas["GLOBAL"], df_result], ignore_index=True)

        # Indicador 5: Operaciones fragmentadas por grupo de clientes
        score, df_result = calcular_riesgo_indicador_5(df_global)
        global_valores['5'] = score
        df_result = df_result.copy()
        df_result['Indicador'] = '5'        
        if not df_result.empty:
            if "GLOBAL" not in operaciones_sospechosas:
                operaciones_sospechosas["GLOBAL"] = pd.DataFrame()
            operaciones_sospechosas["GLOBAL"] = pd.concat([operaciones_sospechosas["GLOBAL"], df_result], ignore_index=True)

        # Indicador 6: Uso sistemático de importes redondos
        score, df_result = calcular_riesgo_indicador_6(df_global)
        global_valores['6'] = score
        df_result = df_result.copy()
        df_result['Indicador'] = '6'
        if not df_result.empty:
            if "GLOBAL" not in operaciones_sospechosas:
                operaciones_sospechosas["GLOBAL"] = pd.DataFrame()
            operaciones_sospechosas["GLOBAL"] = pd.concat([operaciones_sospechosas["GLOBAL"], df_result], ignore_index=True)

        # Indicador 7: Numerosas cancelaciones de operaciones
        score, df_result = calcular_riesgo_indicador_7(df_global)
        global_valores['7'] = score
        df_result = df_result.copy()
        df_result['Indicador'] = '7'
        if not df_result.empty:
            if "GLOBAL" not in operaciones_sospechosas:
                operaciones_sospechosas["GLOBAL"] = pd.DataFrame()
            operaciones_sospechosas["GLOBAL"] = pd.concat([operaciones_sospechosas["GLOBAL"], df_result], ignore_index=True)

        # Indicador 8: Transferencias a países de alto riesgo
        score, df_result = calcular_riesgo_indicador_8(df_global)
        global_valores['8'] = score
        df_result = df_result.copy()
        df_result['Indicador'] = '8'
        if not df_result.empty:
            if "GLOBAL" not in operaciones_sospechosas:
                operaciones_sospechosas["GLOBAL"] = pd.DataFrame()
            operaciones_sospechosas["GLOBAL"] = pd.concat([operaciones_sospechosas["GLOBAL"], df_result], ignore_index=True)

        # Indicador 9: Operaciones no correspondientes al perfil habitual
        score, df_result = calcular_riesgo_indicador_9(df_global)
        global_valores['9'] = score
        df_result = df_result.copy()
        df_result['Indicador'] = '9'
        if not df_result.empty:
            if "GLOBAL" not in operaciones_sospechosas:
                operaciones_sospechosas["GLOBAL"] = pd.DataFrame()
            operaciones_sospechosas["GLOBAL"] = pd.concat([operaciones_sospechosas["GLOBAL"], df_result], ignore_index=True)

        # Indicador 10: Personas políticamente expuestas
        score, df_result = calcular_riesgo_indicador_10(df_global)
        global_valores['10'] = score
        df_result = df_result.copy()
        df_result['Indicador'] = '10'
        if not df_result.empty:
            if "GLOBAL" not in operaciones_sospechosas:
                operaciones_sospechosas["GLOBAL"] = pd.DataFrame()
            operaciones_sospechosas["GLOBAL"] = pd.concat([operaciones_sospechosas["GLOBAL"], df_result], ignore_index=True)

        # Indicador 11: Cambios en patrones hacia países riesgo
        score, df_result = calcular_riesgo_indicador_11(df_global)
        global_valores['11'] = score
        df_result = df_result.copy()
        df_result['Indicador'] = '11'
        if not df_result.empty:
            if "GLOBAL" not in operaciones_sospechosas:
                operaciones_sospechosas["GLOBAL"] = pd.DataFrame()
            operaciones_sospechosas["GLOBAL"] = pd.concat([operaciones_sospechosas["GLOBAL"], df_result], ignore_index=True)

        # Indicador 12: Volumen anormalmente elevado
        score, df_result = calcular_riesgo_indicador_12(df_global)
        global_valores['12'] = score
        df_result = df_result.copy()
        df_result['Indicador'] = '12'
        if not df_result.empty:
            if "GLOBAL" not in operaciones_sospechosas:
                operaciones_sospechosas["GLOBAL"] = pd.DataFrame()
            operaciones_sospechosas["GLOBAL"] = pd.concat([operaciones_sospechosas["GLOBAL"], df_result], ignore_index=True)

        # Indicador 13: Información incompleta de clientes
        score, df_result = calcular_riesgo_indicador_13(df_global)
        global_valores['13'] = score
        df_result = df_result.copy()
        df_result['Indicador'] = '13'
        if not df_result.empty:
            if "GLOBAL" not in operaciones_sospechosas:
                operaciones_sospechosas["GLOBAL"] = pd.DataFrame()
            operaciones_sospechosas["GLOBAL"] = pd.concat([operaciones_sospechosas["GLOBAL"], df_result], ignore_index=True)

        # Indicador 14: Importes superiores a la media del municipio
        score, df_result = calcular_riesgo_indicador_14(df_global)
        global_valores['14'] = score
        df_result = df_result.copy()
        df_result['Indicador'] = '14'
        if not df_result.empty:
            if "GLOBAL" not in operaciones_sospechosas:
                operaciones_sospechosas["GLOBAL"] = pd.DataFrame()
            operaciones_sospechosas["GLOBAL"] = pd.concat([operaciones_sospechosas["GLOBAL"], df_result], ignore_index=True)

        # Indicador 15: Aumentos repentinos de actividad
        score, df_result = calcular_riesgo_indicador_15(df_global)
        global_valores['15'] = score
        df_result = df_result.copy()
        df_result['Indicador'] = '15'
        if not df_result.empty:
            if "GLOBAL" not in operaciones_sospechosas:
                operaciones_sospechosas["GLOBAL"] = pd.DataFrame()
            operaciones_sospechosas["GLOBAL"] = pd.concat([operaciones_sospechosas["GLOBAL"], df_result], ignore_index=True)

        # Indicador 16: Importes mayores para ciertos destinos
        score, df_result = calcular_riesgo_indicador_16(df_global)
        global_valores['16'] = score
        df_result = df_result.copy()
        df_result['Indicador'] = '16'
        if not df_result.empty:
            if "GLOBAL" not in operaciones_sospechosas:
                operaciones_sospechosas["GLOBAL"] = pd.DataFrame()
            operaciones_sospechosas["GLOBAL"] = pd.concat([operaciones_sospechosas["GLOBAL"], df_result], ignore_index=True)

        # Indicador 17: Concentración temporal de operaciones
        score, df_result = calcular_riesgo_indicador_17(df_global)
        global_valores['17'] = score
        df_result = df_result.copy()
        df_result['Indicador'] = '17'
        if not df_result.empty:
            if "GLOBAL" not in operaciones_sospechosas:
                operaciones_sospechosas["GLOBAL"] = pd.DataFrame()
            operaciones_sospechosas["GLOBAL"] = pd.concat([operaciones_sospechosas["GLOBAL"], df_result], ignore_index=True)

        # Indicador 18: Un mismo remitente a varios países
        score, df_result = calcular_riesgo_indicador_18(df_global)
        global_valores['18'] = score
        df_result = df_result.copy()
        df_result['Indicador'] = '18'
        if not df_result.empty:
            if "GLOBAL" not in operaciones_sospechosas:
                operaciones_sospechosas["GLOBAL"] = pd.DataFrame()
            operaciones_sospechosas["GLOBAL"] = pd.concat([operaciones_sospechosas["GLOBAL"], df_result], ignore_index=True)

        # Indicador 19: Remitentes de nacionalidades distintas al país destino
        score, df_result = calcular_riesgo_indicador_19(df_global)
        global_valores['19'] = score
        df_result = df_result.copy()
        df_result['Indicador'] = '19'
        if not df_result.empty:
            if "GLOBAL" not in operaciones_sospechosas:
                operaciones_sospechosas["GLOBAL"] = pd.DataFrame()
            operaciones_sospechosas["GLOBAL"] = pd.concat([operaciones_sospechosas["GLOBAL"], df_result], ignore_index=True)

        # Indicador 20: Datos genéricos o repetitivos
        score, df_result = calcular_riesgo_indicador_20(df_global)
        global_valores['20'] = score
        df_result = df_result.copy()
        df_result['Indicador'] = '20'
        if not df_result.empty:
            if "GLOBAL" not in operaciones_sospechosas:
                operaciones_sospechosas["GLOBAL"] = pd.DataFrame()
            operaciones_sospechosas["GLOBAL"] = pd.concat([operaciones_sospechosas["GLOBAL"], df_result], ignore_index=True)

        # Agregar valores globales al resultado
        resultados_por_agente["GLOBAL"] = global_valores

        # Calcular promedios por tipo de indicador para el conjunto global
        try:
            from utils.umbral_definitions import TIPOS_INDICADORES

            tipos_valores = {}
            for tipo in set(TIPOS_INDICADORES.values()):
                if tipo != 'No clasificado':
                    indicadores_tipo = [k for k, v in TIPOS_INDICADORES.items() if v == tipo]
                    valores_tipo = [global_valores.get(ind, 1) for ind in indicadores_tipo if ind in global_valores]
                    if valores_tipo:
                        tipos_valores[tipo] = sum(valores_tipo) / len(valores_tipo)
                    else:
                        tipos_valores[tipo] = 1.0

            resultados_por_tipo["GLOBAL"] = tipos_valores
        except Exception as e:
            print(f"Error al calcular promedios por tipo para el conjunto global: {str(e)}")

    except Exception as e:
        print(f"Error al calcular indicadores para el conjunto global: {str(e)}")


    return resultados_por_agente, resultados_por_tipo, operaciones_sospechosas


def calcular_riesgo_promedio(riesgos_por_entidad):
    """
    Calcula el promedio de riesgo para cada indicador a partir de los valores de cada entidad.

    Args:
        riesgos_por_entidad: Diccionario {entidad: {indicador: valor, ...}, ...}

    Returns:
        Diccionario con promedios por indicador
    """
    if not riesgos_por_entidad:
        return {}

    promedios = {}

    # Iterar sobre todos los posibles indicadores (1-20)
    for i in range(1, 21):
        ind_id = str(i)
        valores = []

        # Recopilar valores de todas las entidades para este indicador
        for entidad, indicadores in riesgos_por_entidad.items():
            if entidad != "GLOBAL" and ind_id in indicadores:
                valor = indicadores[ind_id]
                if isinstance(valor, (int, float)) and not pd.isna(valor):
                    valores.append(valor)

        # Calcular promedio si hay valores
        if valores:
            promedios[ind_id] = sum(valores) / len(valores)
        else:
            promedios[ind_id] = 1.0  # Valor predeterminado si no hay datos

    return promedios


def formatear_valor_riesgo(score):
    """
    Formatea un valor de riesgo: entero si es aproximadamente un número entero,
    o con máximo 2 decimales si no lo es.

    Args:
        score: Valor numérico de riesgo

    Returns:
        Valor formateado (entero o con máximo 2 decimales)
    """
    if pd.isna(score):
        return 1.0  # Valor predeterminado para NaN

    try:
        # Convertir a float para manejo consistente
        valor = float(score)

        # Verificar si es aproximadamente un entero (diferencia < 0.01)
        if abs(valor - round(valor)) < 0.01:
            return int(round(valor))
        else:
            # Redondear a 2 decimales
            return round(valor * 100) / 100
    except (ValueError, TypeError):
        # En caso de error, devolver el valor original
        return score


def obtener_nivel_riesgo(score):
    """
    Convierte una puntuación numérica de riesgo a un nivel cualitativo.

    Args:
        score: Puntuación numérica (1-4)

    Returns:
        Nivel de riesgo como texto ("BAJO", "MEDIO", "ALTO", "MUY ALTO")
    """
    try:
        valor = float(score)
        if valor < 1.5:
            return "BAJO"
        elif valor < 2.5:
            return "MEDIO"
        elif valor < 3.5:
            return "ALTO"
        else:
            return "MUY ALTO"
    except (ValueError, TypeError):
        return "BAJO"  # Valor predeterminado en caso de error

def get_indicator_descriptions():
    """
    Get descriptions and weights for risk indicators.

    Returns:
        Dictionary mapping indicator IDs to their descriptions and weights
    """
    return {
        "1": {
            "description": "Uso de la misma documentación en corto espacio de tiempo",
            "weight": "5%"
        },
        "2": {
            "description": "Documento repetido con nombres diferentes",
            "weight": "10%"
        },
        "3": {
            "description": "Documentación con formato alfanumérico erróneo",
            "weight": "2.5%"
        },
        "4": {
            "description": "Operaciones para eludir umbrales (3.000€)",
            "weight": "5.0%"
        },
        "5": {
            "description": "Operaciones fragmentadas por grupo de clientes",
            "weight": "2.5%"
        },
        "6": {
            "description": "Uso sistemático de importes redondos",
            "weight": "5%"
        },
        "7": {
            "description": "Numerosas cancelaciones de operaciones",
            "weight": "5%"
        },
        "8": {
            "description": "Transferencias a países de alto riesgo",
            "weight": "10%"
        },
        "9": {
            "description": "Operaciones no correspondientes al perfil habitual",
            "weight": "5.0%"
        },
        "10": {
            "description": "Clientes que son personas políticamente expuestas",
            "weight": "10%"
        },
        "11": {
            "description": "Variaciones en corredores del agente",
            "weight": "5%"
        },
        "12": {
            "description": "Agente con volumen de operaciones mucho mayor",
            "weight": "2.5%"
        },
        "13": {
            "description": "Agente no completa información correctamente",
            "weight": "2.5%"
        },
        "14": {
            "description": "Agente con operaciones sobre media del municipio",
            "weight": "5%"
        },
        "15": {
            "description": "Agente con aumento repentino de operaciones",
            "weight": "5.0%"
        },
        "16": {
            "description": "Agente con operaciones sustanciales a destino",
            "weight": "5.0%"
        },
        "17": {
            "description": "Agente concentrando operaciones en fechas/horas",
            "weight": "2.5%"
        },
        "18": {
            "description": "Agente aparece como remitente de dinero",
            "weight": "5.0%"
        },
        "19": {
            "description": "Agentes con remitentes de nacionalidad distinta",
            "weight": "5.0%"
        },
        "20": {
            "description": "Agentes con datos repetitivos de cliente",
            "weight": "2.5%" 
        }
    }

def get_indicator_types():
    """
    Get types for risk indicators.

    Returns:
        Dictionary mapping indicator IDs to their types
    """
    return {
        "1": "DOCUMENTACIÓN",
        "2": "DOCUMENTACIÓN",
        "3": "DOCUMENTACIÓN",
        "4": "UMBRALES",
        "5": "UMBRALES",
        "6": "UMBRALES",
        "7": "UMBRALES",
        "8": "GEOGRÁFICO",
        "9": "OUTLIERS",
        "10": "GEOGRÁFICO",
        "11": "GEOGRÁFICO",
        "12": "OUTLIERS",
        "13": "DOCUMENTACIÓN",
        "14": "OUTLIERS",
        "15": "OUTLIERS",
        "16": "GEOGRÁFICO",
        "17": "OUTLIERS",
        "18": "OUTLIERS",
        "19": "GEOGRÁFICO",
        "20": "DOCUMENTACIÓN"
    }

def get_indicator_names():
    """
    Get short names for risk indicators.

    Returns:
        Dictionary mapping indicator IDs to their short names
    """
    descriptions = get_indicator_descriptions()
    names = {}
    for ind_id, ind_desc in descriptions.items():
        names[ind_id] = ind_desc["description"]
    return names



def calculate_total_risk_score(risk_scores):
    """
    Calculate total risk score from individual indicator scores.

    Args:
        risk_scores: Dictionary mapping indicator IDs to their scores

    Returns:
        Total risk score (weighted average) formateado con máximo 2 decimales
    """
    if not risk_scores:
        return 1.0  # Default: riesgo bajo si no hay puntuaciones

    # Obtener pesos de los indicadores
    indicator_weights = {}
    descriptions = get_indicator_descriptions()

    for ind_id, desc in descriptions.items():
        try:
            weight_str = desc.get('weight', '1.0%')
            # Convertir a float, quitando el símbolo % si existe
            weight = float(weight_str.strip('%')) / 100 if '%' in weight_str else float(weight_str)
            indicator_weights[ind_id] = weight
        except (ValueError, TypeError):
            indicator_weights[ind_id] = 0.05  # 5% por defecto

    # Calcular promedio ponderado
    total_weight = 0
    weighted_sum = 0

    for ind_id, score in risk_scores.items():
        # Asegurarse de que el score sea un número
        if ind_id in indicator_weights:
            weight = indicator_weights[ind_id]

            # Convertir score a float si es posible
            try:
                # Si es una lista, tupla u otra secuencia, tomar el primer elemento
                if isinstance(score, (list, tuple)):
                    if len(score) > 0:
                        numeric_score = float(score[0])
                    else:
                        numeric_score = 1.0  # Valor predeterminado si la lista está vacía
                else:
                    numeric_score = float(score)

                total_weight += weight
                weighted_sum += numeric_score * weight
            except (ValueError, TypeError):
                # Si no se puede convertir, usamos 1.0 como valor predeterminado (riesgo bajo)
                print(f"Error al convertir score '{score}' del indicador {ind_id} a número. Usando valor predeterminado.")
                total_weight += weight
                weighted_sum += 1.0 * weight

    # Normalizar resultado
    if total_weight > 0:
        total_score = weighted_sum / total_weight
    else:
        total_score = 1.0

    # Asegurar que esté en el rango 1-4
    total_score = max(1.0, min(4.0, total_score))

    # Formatear valor de riesgo directamente
    return round(total_score) if total_score == int(total_score) else round(total_score, 2)

def calculate_risk_indicators(df: pd.DataFrame, thresholds: Dict[str, Dict[str, float]] = None) -> Tuple[Dict[str, int], Dict[str, Any]]:
    """
    Calcula los indicadores de riesgo para un DataFrame dado.

    Args:
        df: DataFrame con datos a analizar
        thresholds: Diccionario opcional con umbrales específicos

    Returns:
        Tuple con dos elementos:
        - Diccionario con indicadores y sus valores calculados
        - Diccionario con detalles adicionales por indicador
    """
    indicators: Dict[str, int] = {}
    details: Dict[str, pd.DataFrame] = {}


    try:
        # Validar si hay datos suficientes
        if df.empty:
            return {str(i): 1 for i in range(1, 21)}, {}

        # Añadir ID_Agente como copia de ENT_NAT_REF_COD si existe y viceversa
        if 'ENT_NAT_REF_COD' in df.columns and 'ID_Agente' not in df.columns:
            df['ID_Agente'] = df['ENT_NAT_REF_COD']
        elif 'ID_Agente' in df.columns and 'ENT_NAT_REF_COD' not in df.columns:
            df['ENT_NAT_REF_COD'] = df['ID_Agente']

        # Calcular riesgos globales (sin filtro de agente)
        resultados_riesgos, resultados_por_tipo, operaciones_sospechosas = calcular_riesgos_por_agente(df)

        # Convertir el formato de resultados_riesgos["GLOBAL"] a indicators
        global_scores = resultados_riesgos.get("GLOBAL", {})
        for ind_id, score in global_scores.items():
            indicators[ind_id] = score

        # Asegurar que todos los indicadores del 1 al 20 están presentes
        for i in range(1, 21):
            key = str(i)
            indicators.setdefault(key, 1)

        # Crear DataFrames vacíos para todos los indicadores
        df_global_ops = operaciones_sospechosas.get("GLOBAL", pd.DataFrame())



    # Preparamos un dict vacío con todas las claves 1–20
        cols = [c for c in df_global_ops.columns if c != 'Indicador']
        details = { str(i): pd.DataFrame(columns=cols) for i in range(1, 21) }

    # Agrupar cada fila según la columna 'Indicador' que hemos anotado antes ***
        if not df_global_ops.empty and 'Indicador' in df_global_ops.columns:
            for ind_id, grupo in df_global_ops.groupby('Indicador'):
                if ind_id in details:
                    details[ind_id] = grupo.drop(columns=['Indicador'])

    except Exception as e:
        print(f"Error al calcular indicadores: {str(e)}")
        # En caso de error, retornar indicadores con valor predeterminado (1 = riesgo bajo)
        indicators = {str(i): 1 for i in range(1, 21)}
        details    = {str(i): pd.DataFrame() for i in range(1, 21)}

    return indicators, details

def calculate_risk_scores(indicators: Dict[str, int], indicator_weights: Dict[str, float] = None) -> Dict[str, float]:
    """
    Calcula las puntuaciones de riesgo normalizadas para cada indicador.

    Args:
        indicators: Diccionario con valores crudos de indicadores
        indicator_weights: Pesos para cada indicador (opcional)

    Returns:
        Diccionario con puntuaciones de riesgo
    """
    if not indicators:
        return {}

    # Si no se proporcionan pesos, usar pesos predeterminados
    if not indicator_weights:
        indicator_weights = {}
        descriptions = get_indicator_descriptions()
        for ind_id, desc in descriptions.items():
            try:
                weight_str = desc.get('weight', '1.0%')
                # Convertir a float, quitando el símbolo % si existe
                weight = float(weight_str.strip('%')) / 100 if '%' in weight_str else float(weight_str)
                indicator_weights[ind_id] = weight
            except (ValueError, TypeError):
                indicator_weights[ind_id] = 0.05  # 5% por defecto

    # Función auxiliar interna para formatear valores de riesgo
    def formatear_valor_riesgo(valor):
        # Mantiene enteros como enteros, y decimales con máximo 2 posiciones
        return round(valor) if valor == int(valor) else round(valor, 2)
    risk_scores = {}
    for ind_id, value in indicators.items():
        # Asegurarse de que los valores estén en el rango 1-4
        if value > 4:
            normalized_value = 4.0
        elif value < 1 and value > 0:
            normalized_value = 1.0
        elif value == 0:
            normalized_value = 1.0  # Valor mínimo para indicadores no aplicables
        else:
            normalized_value = float(value)

        # Formatear el valor para consistencia (enteros o máximo 2 decimales)    
        risk_scores[ind_id] = formatear_valor_riesgo(normalized_value)

    return risk_scores

def run_risk_analysis(df: pd.DataFrame) -> Tuple[Dict[str, int], Dict[str, Any]]:
    """
    Run all risk indicators on the provided DataFrame.

    Args:
        df: DataFrame with transaction data

    Returns:
        Tuple containing:
        - Dictionary mapping indicator IDs to their risk scores
        - Dictionary mapping indicator IDs to their detailed results
    """
    indicators, details = calculate_risk_indicators(df)
    return indicators, details