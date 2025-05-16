import pandas as pd
import numpy as np
from typing import Tuple, List, Dict, Any
import re
from datetime import datetime, timedelta, date
import pytz
import pycountry
from babel.core import Locale
from fuzzywuzzy import process, fuzz
import warnings
from rapidfuzz import process, fuzz
from babel import Locale
warnings.filterwarnings("ignore", message="Boolean Series key will be reindexed to match DataFrame index.")


def validoDNI(dni):
    """
    Valida un DNI/NIE español.
    Retorna True si el DNI es válido, False en caso contrario.
    """
    if not isinstance(dni, str):
        return False

    tabla = "TRWAGMYFPDXBNJZSQVHLCKE"
    dig_ext = "XYZ"
    reemp_dig_ext = {'X':'0', 'Y':'1', 'Z':'2'}
    numeros = "1234567890"
    dni = dni.upper()

    if len(dni) == 9:
        dig_control = dni[8]
        dni = dni[:8]
        if dni[0] in dig_ext:
            dni = dni.replace(dni[0], reemp_dig_ext[dni[0]])
        try:
            return len(dni) == len([n for n in dni if n in numeros]) and tabla[int(dni) % 23] == dig_control
        except (ValueError, IndexError):
            return False
    return False



def es_importe_redondo_multiplo_100(importe: float) -> bool:
    """
    Verifica si un importe es un múltiplo de 100.
    """
    return importe % 100 == 0


territorios = Locale('es').territories
paises_validos = [nombre for codigo, nombre in territorios.items() if len(codigo) == 2]

# Función para validar y corregir el nombre del país mediante búsqueda fuzzy.
def validar_pais_fuzzy(nombre_pais: str, umbral: int = 80) -> str:
    if pd.isna(nombre_pais) or not isinstance(nombre_pais, str):
        return None
    try:
        # Algunas versiones de fuzzywuzzy devuelven 2 valores, otras 3
        resultado = process.extractOne(
            nombre_pais, paises_validos, scorer=fuzz.token_sort_ratio
        )

        # Manejar diferentes versiones de extractOne
        if isinstance(resultado, tuple):
            if len(resultado) >= 2:
                mejor_coincidencia = resultado[0]
                puntuacion = resultado[1]
            else:
                return None  # Si no hay suficientes elementos en la tupla
        else:
            return None  # Si el resultado no es una tupla

        if puntuacion >= umbral:
            return mejor_coincidencia
        else:
            return None
    except Exception as e:
        print(f"Error al validar país '{nombre_pais}': {str(e)}")
        return None


def calcular_riesgo_indicador_1(df: pd.DataFrame) -> Tuple[int, pd.DataFrame]:
    """
 Calcula el riesgo según el indicador 1: Uso de la misma documentación
    del mismo sujeto obligado en un corto espacio de tiempo.
    Se consideran de riesgo los clientes que:
      1. Tienen operaciones consecutivas cada 3 días o menos.
      2. Tienen más de 10 operaciones en total.
      3. Tienen más de 5 operaciones en total (umbral basado en la imagen).
    Retorna un risk score (1, 2, 3 o 4) y un DataFrame con la primera transacción representativa
    de cada cliente en riesgo, junto con el motivo.
    """
    # Comprobar columnas mínimas
    required_cols = ['FECHA', 'NUM_DOC_ORDENANTE']
    if not all(col in df.columns for col in required_cols):
        columnas_resultado = df.columns.tolist() + ['Motivo_Riesgo']
        return 1, pd.DataFrame(columns=columnas_resultado)

    # Convertir FECHA a formato datetime.date si no lo está
    if df['FECHA'].dtype != 'datetime64[ns]':
        df_copy = df.copy()
        df_copy['FECHA'] = pd.to_datetime(df_copy['FECHA'], dayfirst=True, errors='coerce').dt.date
    else:
        df_copy = df.copy()
        df_copy['FECHA'] = df_copy['FECHA'].dt.date

    conteo_riesgo = 0
    clientes_alto_riesgo_ids = set()
    clientes_alto_riesgo_data = []

    # Crear un identificador de cliente basado en columnas disponibles
    columnas_cliente = ['NOMBRE_ORDENANTE', 'APELLIDO_ORDENANTE', 'SEGUNDO_APELLIDO_ORDENANTE', 'NUM_DOC_ORDENANTE']
    columnas_existentes = [col for col in columnas_cliente if col in df.columns]

    if not columnas_existentes:
        columnas_resultado = df.columns.tolist() + ['Motivo_Riesgo']
        return 1, pd.DataFrame(columns=columnas_resultado)

    df['CLIENTE_ID'] = df[columnas_existentes].apply(lambda row: tuple(row.values), axis=1)

    clientes_unicos = df['CLIENTE_ID'].dropna().unique()
    total_clientes_unicos = len(clientes_unicos)

    for cliente_id in clientes_unicos:
        transacciones_cliente = df[df['CLIENTE_ID'] == cliente_id].sort_values(by='FECHA')
        motivos = []
        es_alto_riesgo = False

        # Criterio 1: operaciones consecutivas cada 3 días o menos
        if len(transacciones_cliente) > 1:
            for i in range(len(transacciones_cliente) - 1):
                fecha_actual = transacciones_cliente.iloc[i]['FECHA']
                fecha_siguiente = transacciones_cliente.iloc[i + 1]['FECHA']
                if pd.notna(fecha_actual) and pd.notna(fecha_siguiente):
                    dias_diferencia = (fecha_siguiente - fecha_actual).days
                    if dias_diferencia <= 3:
                        clientes_alto_riesgo_ids.add(cliente_id)
                        motivos.append("Operaciones frecuentes (≤ 3 días)")
                        es_alto_riesgo = True
                        break

        # Criterio 2: más de 10 operaciones
        if len(transacciones_cliente) > 10 and cliente_id not in clientes_alto_riesgo_ids:
            clientes_alto_riesgo_ids.add(cliente_id)
            motivos.append("Más de 10 operaciones")
            es_alto_riesgo = True

        # Criterio 3: más de 5 operaciones
        if len(transacciones_cliente) > 5 and cliente_id not in clientes_alto_riesgo_ids:
            clientes_alto_riesgo_ids.add(cliente_id)
            motivos.append("Más de 5 operaciones (umbral medio)")
            es_alto_riesgo = True

        if es_alto_riesgo:
            conteo_riesgo += 1
            cliente_data = transacciones_cliente.iloc[0].to_dict()
            cliente_data['Motivo_Riesgo'] = ", ".join(motivos)
            cliente_data.pop('CLIENTE_ID', None)
            clientes_alto_riesgo_data.append(cliente_data)

    porcentaje_riesgo = (conteo_riesgo / total_clientes_unicos) * 100 if total_clientes_unicos > 0 else 0

    if porcentaje_riesgo > 27.5:
        risk_score = 4
    elif porcentaje_riesgo > 20:
        risk_score = 3
    elif porcentaje_riesgo > 12.5:
        risk_score = 2
    else:
        risk_score = 1

    columnas_resultado = df.columns.tolist() + ['Motivo_Riesgo']

    df_result = pd.DataFrame(clientes_alto_riesgo_data)
    if df_result.empty:
        df_result = pd.DataFrame(columns=columnas_resultado)
    else:
        if 'FECHA' in df_result.columns:
            df_result['FECHA'] = pd.to_datetime(df_result['FECHA'], errors='coerce').dt.strftime('%d/%m/%Y')

    return risk_score, df_result

def calcular_riesgo_indicador_2(df: pd.DataFrame) -> Tuple[int, pd.DataFrame]:
    """
    Calcula el riesgo según el indicador 2: Documento repetido con diferentes nombres.

    Se detecta que un mismo NUM_DOC_ORDENANTE (documento) aparece con nombres
    (NOMBRE_ORDENANTE, APELLIDO_ORDENANTE, SEGUNDO_APELLIDO_ORDENANTE) diferentes.
    Retorna un risk score (1, 2, 3 o 4) y un DataFrame con las transacciones en riesgo, junto con el motivo.
    """
    # Verificar que existan las columnas necesarias
    required_columns = ['NUM_DOC_ORDENANTE', 'NOMBRE_ORDENANTE', 'APELLIDO_ORDENANTE']
    if not all(col in df.columns for col in required_columns):
        return 1, pd.DataFrame()  # No hay suficientes datos para el análisis

    # Asegurarnos de que exista la columna 'Motivo_Riesgo' en df
    df_copy = df.copy()
    if 'Motivo_Riesgo' not in df_copy.columns:
        df_copy['Motivo_Riesgo'] = ''

    # Crear una columna auxiliar para el "nombre completo"
    df_copy['NOMBRE_COMPLETO'] = df_copy['NOMBRE_ORDENANTE'].astype(str).str.strip() + ' ' + \
                         df_copy['APELLIDO_ORDENANTE'].astype(str).str.strip()

    # Añadir segundo apellido si existe
    if 'SEGUNDO_APELLIDO_ORDENANTE' in df_copy.columns:
        df_copy['NOMBRE_COMPLETO'] += ' ' + df_copy['SEGUNDO_APELLIDO_ORDENANTE'].astype(str).str.strip()

    # Agrupar por NUM_DOC_ORDENANTE para detectar cuántos nombres distintos existen para cada doc
    df_nombres_por_doc = df_copy.groupby('NUM_DOC_ORDENANTE')['NOMBRE_COMPLETO'].nunique().reset_index(name='nombres_distintos')

    # Determinar cuáles documentos tienen >1 nombre distinto
    documentos_riesgo = df_nombres_por_doc[df_nombres_por_doc['nombres_distintos'] > 1]['NUM_DOC_ORDENANTE'].tolist()
    total_documentos_unicos = len(df_nombres_por_doc)
    total_documentos_riesgo = len(documentos_riesgo)

    # Marcar en df las filas que correspondan a estos documentos de riesgo
    indices_riesgo = df_copy.index[df_copy['NUM_DOC_ORDENANTE'].isin(documentos_riesgo)]
    df_copy.loc[indices_riesgo, 'Motivo_Riesgo'] = "Documento repetido con nombre(s) distinto(s)"

    # Calcular el porcentaje de documentos en riesgo
    porcentaje_riesgo = (total_documentos_riesgo / total_documentos_unicos) * 100 if total_documentos_unicos > 0 else 0

    # Asignar la puntuación de riesgo
    if porcentaje_riesgo > 20:
        risk_score = 4
    elif porcentaje_riesgo > 15:
        risk_score = 3
    elif porcentaje_riesgo > 10:
        risk_score = 2
    else:
        risk_score = 1

    # Filtrar solo las transacciones marcadas como de riesgo
    df_result = df_copy[df_copy['Motivo_Riesgo'] == "Documento repetido con nombre(s) distinto(s)"]

    # Eliminar la columna auxiliar 'NOMBRE_COMPLETO'
    df_result = df_result.drop(columns=['NOMBRE_COMPLETO'], errors='ignore')

    return risk_score, df_result

def calcular_riesgo_indicador_3(df: pd.DataFrame) -> Tuple[int, pd.DataFrame]:
    """
    Calcula el riesgo según el indicador 3: Documentación errónea (NIE/NIF).

    Detecta documentos de identidad con formato incorrecto.
    Retorna un risk score (1, 2, 3 o 4) y un DataFrame con las transacciones en riesgo, junto con el motivo.
    """

    # Verificar que existan las columnas necesarias
    required_columns = ['NUM_DOC_ORDENANTE', 'ENT_NAT_REF_COD']
    if not all(col in df.columns for col in required_columns):
        columnas_resultado = df.columns.tolist() + ['Motivo_Riesgo']
        return 1, pd.DataFrame(columns=columnas_resultado)

    # Crear una copia del DataFrame para evitar modificaciones en el origin
    df_copy = df.copy()

     # Inicializar la columna 'Motivo_Riesgo' si no existe
    if 'Motivo_Riesgo' not in df_copy.columns:
        df_copy['Motivo_Riesgo'] = ''
    # Lista para almacenar las transacciones con documentos erróneos
    lista_detalle = []
    # Score predeterminado
    risk_score_general = 1
    risk_score = 1  # Inicializar risk_score para evitar error de variable no definida

    # Agrupar por agente
    for agente, df_agente in df_copy.groupby('ENT_NAT_REF_COD'):
        # Obtener los documentos de identidad únicos para el agente actual
        # eliminando los valores nulos
        docs_unicos = df_agente['NUM_DOC_ORDENANTE'].dropna().unique()
        # Calcular el número total de documentos únicos para el agente
        total_docs = len(docs_unicos)
 # Inicializar el contador de documentos erróneos para este agente
        count_err = 0
         # Iterar sobre cada documento de identidad único del agente
        for doc in docs_unicos:
            # Validar el formato del documento utilizando la función `validoDNI
            if not validoDNI(str(doc)):
                # Si el formato no es válido incrementamos el contador de e
                count_err += 1
                # Identificar todas las filas del DataFrame del agente que
                # corresponden a este documento erróneo
                filas_erroneas = df_agente[df_agente['NUM_DOC_ORDENANTE'] == doc]
                 # Iterar sobre las filas erróneas encontradas (aunque solo 
                for _, row in filas_erroneas.iterrows():
                     # Crear una copia de la fila (transacción) errónea
                    transaccion = row.copy()
                    # Asignar el motivo del riesgo a la columna 'Motivo_Rie
                    transaccion['Motivo_Riesgo'] = "Documentación errónea (NIE/NIF)"
                    # Añadir esta transacción a la lista de detalles
                    lista_detalle.append(transaccion)

 # Calcular el porcentaje de documentos erróneos para el agente actual
        porcentaje_error = (count_err / total_docs * 100) if total_docs > 0 else 0

 # Determinar el score de riesgo para este agente basado en el porcentaje de documentos erróneos
        if porcentaje_error > 5:
            risk_score = 4
        elif porcentaje_error > 4:
            risk_score = 3
        elif porcentaje_error > 3:
            risk_score = 2
        else:
            risk_score = 1

# Definir las columnas que debe tener el DataFrame de resultados
    columnas_resultado = df.columns.tolist() + ['Motivo_Riesgo']

 # Crear el DataFrame de resultados a partir de la lista de detalles
    df_result = pd.DataFrame(lista_detalle)
# Si no se encontraron documentos erróneos crear un DataFrame vacío con las columnas correctas
    if df_result.empty:
        df_result = pd.DataFrame(columns=columnas_resultado)
    else:
        if 'FECHA' in df_result.columns:
            df_result['FECHA'] = pd.to_datetime(df_result['FECHA'], errors='coerce').dt.strftime('%d/%m/%Y')

# Devolver el score de riesgo general y el DataFrame de motibvos de riesgo
    return risk_score, df_result


def calcular_riesgo_indicador_4(df: pd.DataFrame) -> Tuple[int, pd.DataFrame]:
    """
    Calcula el riesgo según el indicador 4: Operaciones para eludir umbrales (3.000€).

    Identifica patrones de operaciones ligeramente por debajo del umbral de reporting (3.000€).

    Retorna un risk score (1, 2, 3 o 4) y un DataFrame con las transacciones en riesgo, junto con el motivo.
    """
    # Verificar que existan las columnas necesarias
    required_columns = ['IMPORTE', 'FECHA', 'NUM_DOC_ORDENANTE']
    if not all(col in df.columns for col in required_columns):
        return 1, pd.DataFrame()  # No hay suficientes datos para el análisis

    # Copiar el dataframe para no modificar el original
    df_copy = df.copy()
    if 'Motivo_Riesgo' not in df_copy.columns:
        df_copy['Motivo_Riesgo'] = ''

    # Definir el umbral de reporting
    UMBRAL = 3000
    MIN_UMBRAL = UMBRAL * 0.85  # 85% del umbral

    # Marcar operaciones cercanas al umbral
    mask_cerca = df_copy['IMPORTE'].ge(MIN_UMBRAL) & df_copy['IMPORTE'].lt(UMBRAL)

    # Agrupar operaciones cerca del umbral por cliente
    ops_por_cliente = df_copy[mask_cerca].groupby('NUM_DOC_ORDENANTE').size() # Corrección: aplicar el filtro antes de agrupar

    # Calcular % de operaciones cercanas por cliente
    total_ops_cliente = df_copy.groupby('NUM_DOC_ORDENANTE').size()
    porcentaje_cerca = (ops_por_cliente / total_ops_cliente) * 100

    # Definir clientes en riesgo (porcentaje de operaciones cercanas > 5%)
    clientes_riesgo = porcentaje_cerca[porcentaje_cerca > 35].index

    # Marcar motivo de riesgo sólo en operaciones que cumplen (cliente de riesgo y operación cercana)
    mask_final = mask_cerca & df_copy['NUM_DOC_ORDENANTE'].isin(clientes_riesgo)
    df_copy.loc[mask_final, 'Motivo_Riesgo'] = "Múltiples operaciones cercanas al umbral (≥5% operaciones cerca)"

    # Construir df_result solo con transacciones en riesgo
    orig_cols = list(df.columns) + ['Motivo_Riesgo']
    df_result = df_copy[df_copy['Motivo_Riesgo'].astype(bool)].copy() # Corrección: usar el filtro booleano

    # Calcular porcentaje global de clientes en riesgo
    total_clientes = df_copy['NUM_DOC_ORDENANTE'].nunique()
    porcentaje_cliente_riesgo = (len(clientes_riesgo) / total_clientes * 100) if total_clientes else 0

    # Asignar risk_score
    if porcentaje_cliente_riesgo > 18:
        risk_score = 4
    elif porcentaje_cliente_riesgo > 15:
        risk_score = 3
    elif porcentaje_cliente_riesgo > 10:
        risk_score = 2
    else:
        risk_score = 1

    return risk_score, df_result

def calcular_riesgo_indicador_5(df: pd.DataFrame) -> Tuple[int, pd.DataFrame]:
    """
    Calcula el riesgo según el indicador 5: Operaciones fragmentadas por grupo de clientes a mismo beneficiario.

    Identifica múltiples remitentes enviando dinero al mismo beneficiario en operaciones
    que podrían estar fragmentadas para eludir controles.
    Retorna un risk score (1, 2, 3 o 4) y un DataFrame con las transacciones en riesgo, junto con el motivo.
    """
    # Verificar que existan las columnas necesarias
    req = ['IMPORTE', 'NUM_DOC_ORDENANTE', 'NOMBRE_BENEFICIARIO', 'APELLIDO_BENEFICIARIO', 'FECHA']
    if not all(col in df.columns for col in req):
        return 1, pd.DataFrame(columns=list(df.columns) + ['Motivo_Riesgo'])

     # Crear una copia del DataFrame para no modificar el original
    df_copy = df.copy()
    # Inicializar la columna para el motivo de riesgo
    df_copy['Motivo_Riesgo'] = ''
    # Convertir la columna de fecha a tipo datetime, ignorando errores
    df_copy['FECHA'] = pd.to_datetime(df_copy['FECHA'], errors='coerce')
    # Convertir la columna de importe a tipo numérico, ignorando errores
    df_copy['IMPORTE'] = pd.to_numeric(df_copy['IMPORTE'], errors='coerce')

    # Crear un identificador único para cada beneficiario combinando nombre y apellidos
    df_copy['ID_BENEFICIARIO'] = (
        df_copy['NOMBRE_BENEFICIARIO'].str.strip() + ' ' +
        df_copy['APELLIDO_BENEFICIARIO'].str.strip()
    )
    # Incluir el segundo apellido si la columna existe
    if 'SEGUNDO_APELLIDO_BENEFICIARIO' in df_copy.columns:
        df_copy['ID_BENEFICIARIO'] += ' ' + df_copy['SEGUNDO_APELLIDO_BENEFICIARIO'].str.strip()

    # Calcular estadísticas de fragmentación por beneficiario
    stats = (
        df_copy.groupby('ID_BENEFICIARIO')
        .agg(
            TotalRemitentes=('NUM_DOC_ORDENANTE', 'nunique'), # Contar el número de remitentes únicos
            MinFecha=('FECHA', 'min'),                     # Obtener la fecha de la primera operación
            MaxFecha=('FECHA', 'max')                      # Obtener la fecha de la última operación
        )
        .reset_index()
    )
    # Calcular la diferencia en días entre la primera y la última operación
    stats['DiasTotales'] = (stats['MaxFecha'] - stats['MinFecha']).dt.days.fillna(9999).astype(int)

    # Identificar beneficiarios sospechosos que recibieron dinero de >=3 remitentes en <=180 días
    frag = stats[(stats['TotalRemitentes'] >= 3) & (stats['DiasTotales'] <= 180)]

    # Inicializar el DataFrame de resultados
    orig_cols = list(df.columns) + ['Motivo_Riesgo']
    df_result = pd.DataFrame(columns=list(df.columns) + ['Motivo_Riesgo'])

    # Si se encontraron beneficiarios sospechosos
    if not frag.empty:
        # Crear un diccionario para mapear el ID del beneficiario con el motivo de riesgo
        msg_map = {
            row['ID_BENEFICIARIO']: f"Operaciones fragmentadas: {row['TotalRemitentes']} remitentes en {row['DiasTotales']} días"
            for _, row in frag.iterrows()
        }
        # Crear una máscara para identificar las transacciones de los beneficiarios sospechosos
        mask = df_copy['ID_BENEFICIARIO'].isin(msg_map)
        # Asignar el motivo de riesgo a las transacciones correspondientes en la copia del DataFrame
        df_copy.loc[mask, 'Motivo_Riesgo'] = df_copy.loc[mask, 'ID_BENEFICIARIO'].map(msg_map)
        # Crear el DataFrame de resultados con las transacciones marcadas
        df_result = df_copy.loc[mask, list(df.columns) + ['Motivo_Riesgo']].copy()

    # Calcular el porcentaje de operaciones marcadas como riesgo
    total_ops = len(df_copy)
    marked_ops = len(df_result)
    porcentaje_cliente_riesgo = (marked_ops / total_ops * 100) if total_ops > 0 else 0

    # Asignar un score de riesgo basado en el número de operaciones marcadas
    if marked_ops == 0:
        risk_score = 1
    else:
        if porcentaje_cliente_riesgo > 1:
            risk_score = 4
        elif porcentaje_cliente_riesgo > 0.50:
            risk_score = 3
        elif porcentaje_cliente_riesgo > 0.25:
            risk_score = 2
        else:
            risk_score = 1

    # Eliminar la columna temporal del ID del beneficiario del DataFrame de resultados
    df_result.drop(columns=['ID_BENEFICIARIO'], errors='ignore', inplace=True)
    # Volver a filtrar el df_copy para obtener solo las filas con motivo de riesgo (CORRECCIÓN)
    orig_cols = list(df.columns) + ['Motivo_Riesgo']
    df_result = df_copy.loc[
        df_copy['Motivo_Riesgo'].astype(str).str.strip() != '',
        orig_cols
    ].copy()

    return risk_score, df_result

def calcular_riesgo_indicador_6(df: pd.DataFrame) -> Tuple[int, pd.DataFrame]:
    """
    Calcula el riesgo según el indicador 6: Uso sistemático de importes redondos para valores altos.

    Identifica transacciones con valores redondos (terminados en 00) especialmente
    para importes altos o cercanos al umbral de reporting.
    Retorna un risk score (1, 2, 3 o 4) y un DataFrame con las transacciones en riesgo, junto con el motivo.
    """
    # Verificar que existan las columnas necesarias
    required_columns = ['NUM_DOC_ORDENANTE', 'IMPORTE']
    if not all(col in df.columns for col in required_columns):
        return 1, pd.DataFrame(columns=list(df.columns) + ['Motivo_Riesgo'])

    df_copy = df.copy()
    if 'Motivo_Riesgo' not in df_copy.columns:
        df_copy['Motivo_Riesgo'] = ''

    UMBRAL_REPORTING = 3000
    importe_p85 = df_copy['IMPORTE'].quantile(0.85)  # Definimos importe alto como P85

    # Condiciones de riesgo
    mask_redondo = df_copy['IMPORTE'].apply(es_importe_redondo_multiplo_100)
    mask_alto = df_copy['IMPORTE'] >= importe_p85
    mask_cercano = (df_copy['IMPORTE'] >= 0.85 * UMBRAL_REPORTING) & (df_copy['IMPORTE'] < UMBRAL_REPORTING)

    # Combinar máscaras
    mask_riesgo = mask_redondo & (mask_alto | mask_cercano)

    # Añadir flag de riesgo
    df_copy['flag_riesgo'] = mask_riesgo

    # Calcular porcentaje de operaciones de riesgo por cliente
    stats = df_copy.groupby('NUM_DOC_ORDENANTE').agg(
        total=('IMPORTE', 'count'),
        riesgo=('flag_riesgo', 'sum')
    )
    stats['porcentaje_riesgo'] = (stats['riesgo'] / stats['total']) * 100

    # Definir clientes en riesgo alto
    clientes_riesgo = stats[
        (stats['porcentaje_riesgo'] > 0.5)  # Ajustamos para score >=3 o 4
    ].index

    # Marcar motivo en transacciones de clientes en riesgo
    mask_final = mask_riesgo & df_copy['NUM_DOC_ORDENANTE'].isin(clientes_riesgo)
    df_copy.loc[mask_final, 'Motivo_Riesgo'] = "Cliente con uso sistemático de importes redondos elevados o cercanos a 3.000€"

    # Calcular porcentaje global de clientes en riesgo
    total_clientes = df_copy['NUM_DOC_ORDENANTE'].nunique()
    porcentaje_clientes_riesgo = (len(clientes_riesgo) / total_clientes * 100) if total_clientes > 0 else 0

    # Asignar risk_score global
    if porcentaje_clientes_riesgo > 1:
        risk_score = 4
    elif porcentaje_clientes_riesgo > 0.5:
        risk_score = 3
    elif porcentaje_clientes_riesgo > 0:
        risk_score = 2
    else:
        risk_score = 1

    # df_result solo con transacciones relevantes
    orig_cols = list(df.columns) + ['Motivo_Riesgo']
    df_result = df_copy.loc[
        df_copy['Motivo_Riesgo'].astype(str).str.strip() != '',
        orig_cols
    ].copy()

    return risk_score, df_result

def calcular_riesgo_indicador_7(df: pd.DataFrame) -> Tuple[int, pd.DataFrame]:
    """
    Calcula el riesgo según el indicador7: Numerosas cancelaciones, especialmente para importes cercanos al umbral.

    Identifica clientes con múltiples operaciones canceladas, especialmente aquellas
    con importes cercanos al umbral de reporting.
    Retorna un risk score (1, 2, 3 o 4) y un DataFrame con las transacciones en riesgo, junto con el motivo.
    """
    # Verificar que existan las columnas necesarias
    required = ['IMPORTE', 'ESTADO_OPERACION', 'NUM_DOC_ORDENANTE']
    if not all(col in df.columns for col in required):
        cols = list(df.columns) + ['Motivo_Riesgo']
        return 1, pd.DataFrame(columns=cols)

    # Copia y normalización
    df_copy = df.copy()
    df_copy['Motivo_Riesgo']    = ''
    df_copy['IMPORTE']          = pd.to_numeric(df_copy['IMPORTE'], errors='coerce')
    df_copy['ESTADO_OPERACION'] = df_copy['ESTADO_OPERACION'].astype(str).str.upper()

    # Máscaras
    UMBRAL     = 3000
    MARGEN     = 500
    mask_cancel = df_copy['ESTADO_OPERACION'] == 'CANCELADA'
    mask_cerca  = mask_cancel & df_copy['IMPORTE'].between(UMBRAL - MARGEN, UMBRAL + MARGEN)

    # Estadísticas por cliente
    # – total_cancel: cuántas canceladas
    # – cerca_umbral: cuántas de esas están cerca del umbral
    stats_cancel = (
        df_copy.loc[mask_cancel]
        .groupby('NUM_DOC_ORDENANTE')
        .size()
        .rename('total_cancel')
    )
    stats_cerca = (
        df_copy.loc[mask_cerca]
        .groupby('NUM_DOC_ORDENANTE')
        .size()
        .rename('cerca_umbral')
    )
    stats = pd.concat([stats_cancel, stats_cerca], axis=1).fillna(0).astype(int)

    # Detectar clientes sospechosos
    sospechosos = stats[
        (stats['total_cancel'] >= 3) |
        (stats['cerca_umbral'] >= 2)
    ].reset_index()

    # Preparar df_result vacío siempre con columnas
    orig_cols = list(df.columns) + ['Motivo_Riesgo']
    df_result = pd.DataFrame(columns=orig_cols)
    if not sospechosos.empty:
        # Mapear motivos
        reason_map = {
            row['NUM_DOC_ORDENANTE']:
                f"Cliente con {row['total_cancel']} cancelaciones, "
                f"{row['cerca_umbral']} cerca del umbral"
            for _, row in sospechosos.iterrows()
        }
        mask_sus = mask_cancel & df_copy['NUM_DOC_ORDENANTE'].isin(reason_map)
        df_copy.loc[mask_sus, 'Motivo_Riesgo'] = df_copy.loc[mask_sus, 'NUM_DOC_ORDENANTE'].map(reason_map)
        df_result = df_copy.loc[mask_sus, orig_cols].copy()

    # 8) Calcular porcentaje_cliente_riesgo y risk_score
    total_clientes = df_copy['NUM_DOC_ORDENANTE'].nunique()
    clientes_sos   = len(sospechosos)
    pct_clientes   = (clientes_sos / total_clientes * 100) if total_clientes else 0

    if pct_clientes > 1:
        risk_score = 4
    elif pct_clientes > 0.5:
        risk_score = 3
    elif pct_clientes > 0:
        risk_score = 2
    else:
        risk_score = 1

    orig_cols = list(df.columns) + ['Motivo_Riesgo']
    df_result = df_copy.loc[
    df_copy['Motivo_Riesgo'].astype(str).str.strip() != '',
    orig_cols
    ].copy()   


    return risk_score, df_result

def calcular_riesgo_indicador_8(df: pd.DataFrame) -> Tuple[int, pd.DataFrame]:
    """
    Calcula el riesgo según el indicador 8: Transferencias a países de alto riesgo o beneficiarios no identificables.

    Identifica transferencias a países considerados de alto riesgo según listas oficiales
    o con beneficiarios con datos incompletos o sospechosos.
    Retorna un risk score (1, 2, 3 o 4) y un DataFrame con las transacciones en riesgo, junto con el motivo.
    """
    # Verificar que existan las columnas necesarias
    required_columns = ['PAIS_DESTINO', 'NOMBRE_BENEFICIARIO', 'APELLIDO_BENEFICIARIO']
    if not all(col in df.columns for col in required_columns):
        return 1, pd.DataFrame()  # No hay suficientes datos para el análisis

    # Inicializar
    df_copy = df.copy()
    if 'Motivo_Riesgo' not in df_copy.columns:
        df_copy['Motivo_Riesgo'] = ''

    # Lista de países de alto riesgo
    paises_alto_riesgo = [
        "República Popular Democrática de Corea", "Irán", "Myanmar", "África del Sur", "Bulgaria",
        "Burkina Faso", "Camerún", "Croacia", "Filipinas", "Haití", "Kenia", "Mali", "Mozambique",
        "Namibia", "Nigeria", "República Democrática del Congo", "Senegal", "Siria", "Sudán del Sur",
        "Tanzania", "Turquía", "Vietnam", "Yemen", "Venezuela", "Mónaco", "Anguila", "Bahrein",
        "Barbados", "Bermudas", "Dominica", "Fiji", "Gibraltar", "Guam", "Guernsey", "Isla de Man",
        "Islas Caimán", "Islas Malvinas", "Islas Marianas", "Islas Salomón", "Islas Turcas y Caicos",
        "Islas Vírgenes Británicas", "Islas Vírgenes de Estados Unidos de América", "Jersey", "Palaos",
        "Samoa", "Samoa Americana", "Seychelles", "Trinidad y Tobago", "Vanuatu"
    ]

    # Convertir a mayúsculas para comparación
    paises_alto_riesgo = [p.upper() for p in paises_alto_riesgo]
    df_copy['PAIS_DESTINO'] = df_copy['PAIS_DESTINO'].astype(str).str.upper()

    # Identificar transacciones a países de alto riesgo
    transacciones_pais_riesgo = df_copy[df_copy['PAIS_DESTINO'].isin(paises_alto_riesgo)].copy()
    for idx, row in transacciones_pais_riesgo.iterrows():
        transacciones_pais_riesgo.loc[idx, 'Motivo_Riesgo'] = f"Transferencia a país de alto riesgo: {row['PAIS_DESTINO']}"

    # Identificar beneficiarios con datos incompletos o sospechosos
    transacciones_beneficiario_sospechoso = df_copy[
        (df_copy['NOMBRE_BENEFICIARIO'].astype(str).str.strip() == '') | 
        (df_copy['APELLIDO_BENEFICIARIO'].astype(str).str.strip() == '') |
        # Nombres sospechosamente cortos
        (df_copy['NOMBRE_BENEFICIARIO'].astype(str).str.len() < 3) |
        (df_copy['APELLIDO_BENEFICIARIO'].astype(str).str.len() < 3)
    ].copy()

    for idx, row in transacciones_beneficiario_sospechoso.iterrows():
        transacciones_beneficiario_sospechoso.loc[idx, 'Motivo_Riesgo'] = "Beneficiario con datos incompletos o sospechosos"

    # Combinar resultados
    transacciones_riesgo = pd.concat([transacciones_pais_riesgo, transacciones_beneficiario_sospechoso]).drop_duplicates()

    # Calcular porcentaje de transacciones de riesgo
    porcentaje_riesgo = (len(transacciones_riesgo) / len(df_copy)) * 100 if len(df_copy) > 0 else 0

    # Determinar nivel de riesgo
    if porcentaje_riesgo > 15:
        risk_score = 4
    elif porcentaje_riesgo >14:
        risk_score = 3
    elif porcentaje_riesgo > 13:
        risk_score = 2
    else:
        risk_score = 1


    orig_cols = list(df.columns) + ['Motivo_Riesgo']   
    df_result = df_copy.loc[
    df_copy['Motivo_Riesgo'].astype(str).str.strip() != '',
    orig_cols
    ].copy() 

    return risk_score, df_result

def calcular_riesgo_indicador_9(df: pd.DataFrame) -> Tuple[int, pd.DataFrame]:
    """
    Calcula el riesgo según el indicador 9: Operaciones que no corresponden con el perfil habitual del cliente.

    Identifica transacciones con características inusuales para un cliente específico,
    como importes anormalmente altos o destinos inusuales.
    Retorna la puntuación de riesgo y el DataFrame original con una columna 'Motivo_Riesgo'
    indicando las transacciones de riesgo.
    """
    # Verificar que existan las columnas necesarias
    required_columns = ['IMPORTE', 'NUM_DOC_ORDENANTE', 'PAIS_DESTINO']
    if not all(col in df.columns for col in required_columns):
        return 1, pd.DataFrame()  # No hay suficientes datos para el análisis

    # Inicializar
    df_copy = df.copy()
    if 'Motivo_Riesgo' not in df_copy.columns:
        df_copy['Motivo_Riesgo'] = ''

    # Analizar el perfil habitual de cada cliente

    # Estadísticas por cliente
    stats = df_copy.groupby('NUM_DOC_ORDENANTE').agg(
        total_ops=('IMPORTE', 'count'),
        mean_imp=('IMPORTE', 'mean'),
        std_imp =('IMPORTE', 'std'),
        max_imp =('IMPORTE', 'max'),
        # destino más frecuente y su cuenta
        habitual_destino=('PAIS_DESTINO', lambda x: x.mode().iloc[0] if len(x.mode())>0 else None),
        habitual_count  =('PAIS_DESTINO', lambda x: x.value_counts().iloc[0] if len(x)>0 else 0)
    ).reset_index()

    # Unir stats de vuelta
    df_copy = df_copy.merge(stats, on='NUM_DOC_ORDENANTE', how='left')

    # Calcular umbral alto
    df_copy['umbral_alto'] = df_copy.apply(
        lambda r: (r['mean_imp'] + 2*r['std_imp']) if pd.notna(r['std_imp']) and r['std_imp']>0
                  else 1.5 * r['max_imp'],
        axis=1
    )

    # Máscaras de inusual
    mask_clientes_suf = df_copy['total_ops'] >= 3
    mask_high  = mask_clientes_suf & (df_copy['IMPORTE'] > df_copy['umbral_alto'])
    mask_dest  = mask_clientes_suf & \
                 (df_copy['habitual_count'] > 3) & \
                 (df_copy['PAIS_DESTINO'] != df_copy['habitual_destino'])
    mask_inus  = mask_high | mask_dest

    # Crear flag de operaciones inusuales
    df_copy['flag_inusual'] = mask_inus

    # Resumen por cliente
    resumen_clientes = df_copy.groupby('NUM_DOC_ORDENANTE').agg(
        total_ops=('IMPORTE', 'count'),
        inusuales=('flag_inusual', 'sum')
    )
    resumen_clientes['porcentaje_inusuales'] = (resumen_clientes['inusuales'] / resumen_clientes['total_ops']) * 100

    # Clientes con % de inusuales relevantes
    clientes_riesgo = resumen_clientes[
        resumen_clientes['porcentaje_inusuales'] > 0.75
    ].index

    # Marcar motivo de riesgo en operaciones inusuales de esos clientes
    mask_final = mask_inus & df_copy['NUM_DOC_ORDENANTE'].isin(clientes_riesgo)
    df_copy.loc[mask_final, 'Motivo_Riesgo'] = df_copy.loc[mask_final].apply(
        lambda row: " | ".join([
            f"Importe atípico ({row['IMPORTE']:.2f}€), media: {row['mean_imp']:.2f}€" if mask_high.loc[row.name] else "",
            f"Destino inusual ({row['PAIS_DESTINO']}), habitual: {row['habitual_destino']}" if mask_dest.loc[row.name] else ""
        ]).strip(' | '),
        axis=1
    )

    # Calcular porcentaje global
    total_clientes = df_copy['NUM_DOC_ORDENANTE'].nunique()
    porcentaje_clientes_riesgo = (len(clientes_riesgo) / total_clientes * 100) if total_clientes > 0 else 0

    # Asignar risk_score global
    if porcentaje_clientes_riesgo > 2:
        risk_score = 4
    elif porcentaje_clientes_riesgo > 1:
        risk_score = 3
    elif porcentaje_clientes_riesgo > 0.5:
        risk_score = 2
    else:
        risk_score = 1

    # Construir df_result
    orig_cols = list(df.columns) + ['Motivo_Riesgo']
    df_result = df_copy.loc[
        df_copy['Motivo_Riesgo'].astype(str).str.strip() != '',
        orig_cols
    ].copy()

    return risk_score, df_result

def calcular_riesgo_indicador_10(df: pd.DataFrame) -> Tuple[int, pd.DataFrame]:
    """
    Calcula el riesgo según el indicador  10: Clientes que son personas políticamente expuestas.

    Identifica transacciones de personas políticamente expuestas (PEPs) que requieren
    un escrutinio adicional por su mayor riesgo potencial.
    Se considera el campo 'es_PEP' del CSV (True/False) para identificar estas personas.
    Retorna la puntuación de riesgo y el DataFrame original con una columna 'Motivo_Riesgo'
    indicando las transacciones de riesgo.
    """
    # Verificar que exista la columna necesaria
    required_columns = ['NUM_DOC_ORDENANTE', 'ES_PEP']
    if not all(col in df.columns for col in required_columns):
        columnas_resultado = list(df.columns) + ['Motivo_Riesgo']
        return 1, pd.DataFrame(columns=columnas_resultado)

    df_copy = df.copy()
    if 'Motivo_Riesgo' not in df_copy.columns:
        df_copy['Motivo_Riesgo'] = ''

    # Normalizar es_PEP a booleano
    df_copy['es_PEP'] = df_copy['ES_PEP'].apply(lambda x:
        True if isinstance(x, bool) and x else
        True if isinstance(x, str) and x.lower() == 'true' else
        True if isinstance(x, (int, float)) and x == 1 else
        False
    )

    # Agrupar por cliente único
    resumen_peps = df_copy.groupby('NUM_DOC_ORDENANTE')['ES_PEP'].max().reset_index()
    total_clientes = resumen_peps.shape[0]
    clientes_pep = resumen_peps[resumen_peps['ES_PEP'] == True].shape[0]

    porcentaje_peps = (clientes_pep / total_clientes * 100) if total_clientes > 0 else 0

    # Asignar risk_score
    if porcentaje_peps > 2:
        risk_score = 4
    elif porcentaje_peps > 1.5:
        risk_score = 3
    elif porcentaje_peps > 1:
        risk_score = 2
    else:
        risk_score = 1

    # Marcar motivo de riesgo solo si el cliente es PEP
    clientes_pep_ids = resumen_peps[resumen_peps['ES_PEP'] == True]['NUM_DOC_ORDENANTE']

    df_copy.loc[
        df_copy['NUM_DOC_ORDENANTE'].isin(clientes_pep_ids),
        'Motivo_Riesgo'
    ] = "Cliente identificado como Persona Políticamente Expuesta (PEP)"

    # Construir df_result
    orig_cols = list(df.columns) + ['Motivo_Riesgo']
    df_result = df_copy.loc[
        df_copy['Motivo_Riesgo'].astype(str).str.strip() != '',
        orig_cols
    ].copy()

    return risk_score, df_result

def calcular_riesgo_indicador_11(df: pd.DataFrame) -> Tuple[int, pd.DataFrame]:
    """
    Calcula el riesgo según el indicador 11: Variaciones en corredores del agente hacia destinos de mayor riesgo.

    Identifica cuando un agente comienza a enviar más dinero a países de alto riesgo,
    lo que podría indicar un cambio sospechoso en sus patrones de operación.
    Retorna la puntuación de riesgo y el DataFrame original con una columna 'Motivo_Riesgo'
    indicando las transacciones de riesgo.
    """
    # Verificar que existan las columnas necesarias
    required_columns = ['PAIS_DESTINO', 'NUM_DOC_ORDENANTE']

    if not all(col in df.columns for col in required_columns):
        return 1, pd.DataFrame()  # No hay suficientes datos para el análisis

    # Inicializar
    df_copy = df.copy()
    if 'Motivo_Riesgo' not in df_copy.columns:
        df_copy['Motivo_Riesgo'] = ''

    # Lista de países de alto riesgo
    paises_alto_riesgo = [
        "República Popular Democrática de Corea", "Irán", "Myanmar", "África del Sur", "Bulgaria",
        "Burkina Faso", "Camerún", "Croacia", "Filipinas", "Haití", "Kenia", "Mali", "Mozambique",
        "Namibia", "Nigeria", "República Democrática del Congo", "Senegal", "Siria", "Sudán del Sur",
        "Tanzania", "Turquía", "Vietnam", "Yemen", "Venezuela", "Mónaco", "Anguila", "Bahrein",
        "Barbados", "Bermudas", "Dominica", "Fiji", "Gibraltar", "Guam", "Guernsey", "Isla de Man",
        "Islas Caimán", "Islas Turcas y Caicos", "Jersey", "Jordania", "Líbano", "Malasia", "Maldivas",
        "Marruecos", "Pakistán", "Panamá", "Puerto Rico", "Samoa Americana", "San Bartolomé",
        "San Cristóbal y Nieves", "Santa Lucía", "San Vicente y las Granadinas", "Tailandia",
        "Trinidad y Tobago", "Emiratos Árabes Unidos", "Vanuatu", "Zimbabue", "Albania", "Armenia",
        "Bosnia y Herzegovina", "Colombia", "Jamaica", "Kosovo", "Líbano", "Macedonia del Norte",
        "Montenegro", "Serbia"
    ]

    # Convertir a mayúsculas para comparación
    alto_set = set(p.upper() for p in paises_alto_riesgo)
    df_copy['PAIS_DESTINO'] = df_copy['PAIS_DESTINO'].astype(str).str.upper()

    clientes_riesgo = df_copy.loc[df_copy['PAIS_DESTINO'].isin(alto_set), 'NUM_DOC_ORDENANTE'].unique()

    total_clientes = df_copy['NUM_DOC_ORDENANTE'].nunique()
    total_riesgo = len(clientes_riesgo)

    porcentaje_riesgo = (total_riesgo / total_clientes * 100) if total_clientes > 0 else 0

        # Asignar risk_score
    if porcentaje_riesgo > 22:
        risk_score = 4
    elif porcentaje_riesgo > 21:
        risk_score = 3
    elif porcentaje_riesgo > 20:
        risk_score = 2
    else:
        risk_score = 1

        # Marcar motivo de riesgo en las transacciones de clientes afectados

    df_copy.loc[df_copy['NUM_DOC_ORDENANTE'].isin(clientes_riesgo) & df_copy['PAIS_DESTINO'].isin(alto_set), 'Motivo_Riesgo'] = (
            "Cliente que realiza envíos a país de alto riesgo"
        )

        # Construir df_result
    orig_cols = list(df.columns) + ['Motivo_Riesgo']
    df_result = df_copy.loc[
            df_copy['Motivo_Riesgo'].astype(str).str.strip() != '',
            orig_cols
        ].copy()


    # Calcular risk_score global como máximo de agente
    return risk_score, df_result

def calcular_riesgo_indicador_12(df: pd.DataFrame) -> Tuple[int, pd.DataFrame]:
    """
    Calcula el riesgo según el indicador  12: Agente con volumen de operaciones mucho mayor al promedio.

    Riesgo de agentes cuyo volumen de operaciones es significativamente mayor
    que el promedio, lo que podría indicar actividad sospechosa o concentración
    de operaciones de riesgo.
    Retorna la puntuación de riesgo y el DataFrame original con una columna 'Motivo_Riesgo'
    indicando las transacciones de riesgo.
    """
    # Verificar que existan las columnas necesarias
    required_columns = ['ENT_NAT_REF_COD', 'IMPORTE']
    if not all(col in df.columns for col in required_columns):
        return 1, pd.DataFrame()  # No hay suficientes datos para el análisis

    # Inicializar
    df_copy = df.copy()
    if 'Motivo_Riesgo' not in df_copy.columns:
        df_copy['Motivo_Riesgo'] = ''

    # Definir umbral
    UMBRAL_REPORTING = 3000
    importe_p75 = df_copy['IMPORTE'].quantile(0.75)  # Percentil 75 de todos los importes

    def es_redondo(importe):
        importe_str = f"{importe:.2f}"
        return importe_str.endswith('.00')

    agentes = df_copy['ENT_NAT_REF_COD'].unique()
    porcentaje_max = 0
    risk_score_max = 1

    for agente in agentes:
        df_agente = df_copy[df_copy['ENT_NAT_REF_COD'] == agente]
        if df_agente.empty:
            continue

        # Condiciones de riesgo:
        mask_redondo = df_agente['IMPORTE'].apply(es_importe_redondo_multiplo_100)
        mask_alto = df_agente['IMPORTE'] >= importe_p75
        mask_cercano = (df_agente['IMPORTE'] >= 0.85 * UMBRAL_REPORTING) & (df_agente['IMPORTE'] < UMBRAL_REPORTING)

        mask_riesgo = mask_redondo & (mask_alto | mask_cercano)

        total = len(df_agente)
        riesgo = mask_riesgo.sum()
        porcentaje = (riesgo / total * 100) if total > 0 else 0

        if riesgo > 0:
            df_copy.loc[df_agente.index[mask_riesgo], 'Motivo_Riesgo'] = (
                f"Importes redondos (>P75 o ~3.000€) en {porcentaje:.2f}% de las operaciones del agente {agente}"
            )

        # Evaluar risk score por agente
        if porcentaje > 0.5:
            risk_score = 4
        elif porcentaje > 0.25:
            risk_score = 3
        elif porcentaje > 0.125:
            risk_score = 2
        else:
            risk_score = 1

    orig_cols = list(df.columns) + ['Motivo_Riesgo']

    df_result = df_copy.loc[
        df_copy['Motivo_Riesgo'].astype(str).str.strip() != '',
        orig_cols
    ].copy()

    return risk_score, df_result

def calcular_riesgo_indicador_13(df: pd.DataFrame) -> Tuple[int, pd.DataFrame]:
    """
    Calcula el riesgo según el indicador 13: Agente que no completa adecuadamente la información de los clientes
    o lo hace de manera errónea.

    Para cada cliente (NUM_DOC_ORDENANTE):
      - Se comprueba si falta alguna información obligatoria.
      - Se valida la fecha de nacimiento (edad entre 12 y 100 años).
      - Se valida país de nacimiento y destino con validar_pais_fuzzy(..., umbral=80).

    Si un cliente tiene cualquier error o falta, todas sus transacciones se marcan con
    Motivo_Riesgo. Luego se calcula el porcentaje de clientes y se asigna risk_score,

Retorna la puntuación de riesgo y el DataFrame original con una columna 'Motivo_Riesgo'
    indicando las transacciones de riesgo.
    """
    # Definir las columnas requeridas para este indicador
    required_columns = [
        'ENT_NAT_REF_COD', 'NUM_DOC_ORDENANTE', 'NOMBRE_ORDENANTE', 'APELLIDO_ORDENANTE',
        'NOMBRE_BENEFICIARIO', 'APELLIDO_BENEFICIARIO', 'PAIS_DOC_ORDENANTE',
        'PAIS_NAC_ORDENANTE', 'PAIS_DESTINO', 'FECHA_NAC_ORDENANTE'
    ]
    # Verificar si todas las columnas requeridas existen en el DataFrame
    if not all(col in df.columns for col in required_columns):
        # Si falta alguna columna, retornar un riesgo bajo y un DataFrame vacío con la columna 'Motivo_Riesgo'
        return 1, pd.DataFrame(columns=list(df.columns) + ['Motivo_Riesgo'])

    # Crear una copia del DataFrame para trabajar sin modificar el original
    df_copy = df.copy()
    # Inicializar la columna 'Motivo_Riesgo' con cadenas vacías si no existe
    if 'Motivo_Riesgo' not in df_copy.columns:
        df_copy['Motivo_Riesgo'] = ''

    # Obtener la lista de clientes únicos (identificados por 'NUM_DOC_ORDENANTE'), eliminando valores nulos
    clientes_unicos = df_copy['NUM_DOC_ORDENANTE'].dropna().unique()
    # Calcular el número total de clientes únicos
    total_clientes = len(clientes_unicos)
    # Inicializar el contador de clientes con información errónea
    clientes_erroneos = 0

    # Obtener la fecha actual para cálculos de edad
    fecha_actual = datetime.now().date()

    # Iterar sobre cada cliente único
    for cliente_id in clientes_unicos:
        # Filtrar el DataFrame para obtener solo las transacciones del cliente actual
        df_cliente = df_copy[df_copy['NUM_DOC_ORDENANTE'] == cliente_id]
        # Tomar la primera fila del DataFrame del cliente para verificar la información del cliente
        first = df_cliente.iloc[0]

        # Verificar si falta información en alguna de las columnas clave para el cliente
        falta_info = any(
            pd.isna(first.get(col)) or str(first.get(col)).strip() == ''
            for col in [
                'NOMBRE_ORDENANTE', 'APELLIDO_ORDENANTE', 'NOMBRE_BENEFICIARIO',
                'APELLIDO_BENEFICIARIO', 'PAIS_DOC_ORDENANTE', 'NUM_DOC_ORDENANTE',
                'PAIS_NAC_ORDENANTE', 'PAIS_DESTINO', 'FECHA_NAC_ORDENANTE'
            ]
        )

        # Inicializar una bandera para indicar si se encontraron errores adicionales para el cliente
        errores = False
        fecha_nac_raw = first['FECHA_NAC_ORDENANTE']
        # Si no falta información básica, realizar verificaciones adicionales
        if not falta_info:
            # Validar la fecha de nacimiento del ordenante
            try:
                # Intentar parsear la fecha de nacimiento desde la cadena
                if isinstance(fecha_nac_raw, (pd.Timestamp, datetime)):
                    fecha_nac = fecha_nac_raw.date()
                # Calcular la edad del ordenante
                else:
                    # Verificar si la edad está fuera de un rango razonable (12 a 100 años)
                    fecha_nac = pd.to_datetime(fecha_nac_raw, dayfirst=True, errors='raise').date()
                    edad = fecha_actual.year - fecha_nac.year - (
                        (fecha_actual.month, fecha_actual.day) < (fecha_nac.month, fecha_nac.day)
                    )
                    if edad < 12 or edad > 100:
                        errores = True 
            except Exception:
                errores = True
            # Validar el país de nacimiento del ordenante utilizando fuzzy matching
            if not validar_pais_fuzzy(str(first['PAIS_NAC_ORDENANTE']), umbral=70):
                errores = True
            # Validar el país de destino utilizando fuzzy matching
            if not validar_pais_fuzzy(str(first['PAIS_DESTINO']), umbral=70):
                errores = True

        # Si se encontró falta de información o errores adicionales para el cliente
        if falta_info or errores:
            # Incrementar el contador de clientes con errores
            clientes_erroneos += 1
            # Marcar todas las transacciones de este cliente con un motivo de riesgo
            df_copy.loc[df_copy['NUM_DOC_ORDENANTE'] == cliente_id, 'Motivo_Riesgo'] = (
                f"Cliente {cliente_id} con datos incompletos o erróneos."
            )

    # Calcular el porcentaje de clientes con información errónea
    porcentaje = (clientes_erroneos / total_clientes * 100) if total_clientes > 0 else 0.0

    # Asignar un score de riesgo basado en el porcentaje de clientes con errores
    if porcentaje > 37:
        risk_score = 4
    elif porcentaje > 35.5:
        risk_score = 3
    elif porcentaje > 34:
        risk_score = 2
    else:
        risk_score = 1

    # Crear el DataFrame de resultados con las filas donde se ha asignado un motivo de riesgo
    orig_cols = list(df.columns) + ['Motivo_Riesgo']
    df_result = df_copy.loc[
    df_copy['Motivo_Riesgo'].astype(str).str.strip() != '',
    orig_cols
    ].copy()

    # Retornar el score de riesgo, el DataFrame de resultados y el porcentaje de clientes afectados
    return risk_score, df_result


def calcular_riesgo_indicador_14(df: pd.DataFrame) -> Tuple[int, pd.DataFrame]:
    """
    Calcula el riesgo según el indicador  14: Agente con operaciones muy superiores a la media del municipio.

    Identifica agentes cuyo volumen de operaciones es significativamente mayor
    que otros agentes en el mismo municipio, lo que podría indicar actividad sospechosa.

    Retorna la puntuación de riesgo y el DataFrame original con una columna 'Motivo_Riesgo'
    indicando las transacciones de riesgo.
    """
    required_columns = ['ENT_NAT_REF_COD', 'IMPORTE']
    if not all(col in df.columns for col in required_columns):
        return 1, pd.DataFrame()

    df_copy = df.copy()
    if 'Motivo_Riesgo' not in df_copy.columns:
        df_copy['Motivo_Riesgo'] = ''

    media_global = df_copy['IMPORTE'].mean()
    umbral_alto = media_global * 1.5

    df_copy['Es_Operacion_De_Alto_Riesgo'] = df_copy['IMPORTE'] > umbral_alto

    # Marcar cada transacción individual con su motivo de riesgo
    df_copy['Motivo_Riesgo'] = df_copy.apply(lambda row: 
        f"Operación ({row['IMPORTE']:.2f}) de Agente {row['ENT_NAT_REF_COD']} excede 1.5x la media global ({media_global:.2f})" 
        if row['Es_Operacion_De_Alto_Riesgo'] 
        else '', axis=1)

    # Filtrar las transacciones de alto riesgo
    df_result = df_copy[df_copy['Es_Operacion_De_Alto_Riesgo']].copy()
    orig_cols = list(df.columns) + ['Motivo_Riesgo']
    df_result = df_copy.loc[
        df_copy['Motivo_Riesgo'].astype(str).str.strip() != '',
        orig_cols
    ].copy()

    # Calcular el porcentaje de operaciones de alto riesgo
    porcentaje_operaciones_alto_riesgo = (df_copy['Es_Operacion_De_Alto_Riesgo'].sum() / len(df_copy)) * 100 \
        if len(df_copy) > 0 else 0

    # Asignar el puntaje de riesgo basado en el porcentaje de operaciones de alto riesgo
    if porcentaje_operaciones_alto_riesgo > 24.5:
        risk_score = 4
    elif porcentaje_operaciones_alto_riesgo > 23:
        risk_score = 3
    elif porcentaje_operaciones_alto_riesgo > 21.5:
        risk_score = 2
    else:
        risk_score = 1

    return risk_score, df_result



def calcular_riesgo_indicador_15(df: pd.DataFrame) -> Tuple[int, pd.DataFrame]:
    """
    Calcula el riesgo según el indicador 15: Agente con aumento repentino en operaciones o clientes.

   Si un agente incrementa intermensualmente
    de manera notable el número de clientes  que tiene
    o los importe total enviado.
    Retorna la puntuación de riesgo y el DataFrame original con una columna 'Motivo_Riesgo'
    indicando las transacciones de riesgo.
    """
    # Verificar columnas necesarias
    required_columns = ['FECHA', 'NUM_DOC_ORDENANTE', 'IMPORTE']
    if not all(col in df.columns for col in required_columns):
        return 1, pd.DataFrame()

    df_copy = df.copy()
    if 'Motivo_Riesgo' not in df_copy.columns:
        df_copy['Motivo_Riesgo'] = ''

    # Convertir FECHA a formato datetime (por si acaso)
    df_copy['FECHA'] = pd.to_datetime(df_copy['FECHA'], errors='coerce')

    # Crear columna Año-Mes
    df_copy['AÑO_MES'] = df_copy['FECHA'].dt.to_period('M')

    # Agrupar número de clientes y suma de importes por mes
    resumen = df_copy.groupby('AÑO_MES').agg(
        num_clientes=('NUM_DOC_ORDENANTE', 'nunique'),
        importe_total=('IMPORTE', 'sum')
    ).sort_index()

    if len(resumen) < 2:
        # No hay suficiente información para comparar meses
        return 1, pd.DataFrame()

    # Calcular incrementos porcentuales intermensuales
    resumen['inc_clientes'] = resumen['num_clientes'].pct_change() * 100
    resumen['inc_importes'] = resumen['importe_total'].pct_change() * 100

    # Eliminar el primer mes que siempre tiene NaN
    resumen = resumen.dropna()

    # Calcular media de los incrementos (no el máximo)
    incremento_medio_clientes = resumen['inc_clientes'].mean()
    incremento_medio_importes = resumen['inc_importes'].mean()

    # Elegir el mayor de los dos incrementos medios
    porcentaje_riesgo = max(incremento_medio_clientes, incremento_medio_importes)

    # Asignar risk_score basado en el incremento medio
    if porcentaje_riesgo > 8:
        risk_score = 4
    elif porcentaje_riesgo > 4:
        risk_score = 3
    elif porcentaje_riesgo > 0:
        risk_score = 2
    else:
        risk_score = 1

    # Como df_result, devolvemos todas las operaciones que hemos analizado
    orig_cols = list(df.columns) + ['Motivo_Riesgo']
    df_result = df_copy.loc[
        df_copy['AÑO_MES'].isin(resumen.index),
        orig_cols
    ].copy()

    return risk_score, df_result

def calcular_riesgo_indicador_16(df: pd.DataFrame) -> Tuple[int, pd.DataFrame]:
    """
    Calcula el riesgo según el indicador 16: Agente con operaciones sustanciales a destino específico con promedio superior.
    Retorna la puntuación de riesgo y el DataFrame original con una columna 'Motivo_Riesgo'
    indicando las transacciones de riesgo.
    """
    # Verificar que existan las columnas necesarias
    required_columns = ['ENT_NAT_REF_COD', 'PAIS_DESTINO', 'IMPORTE']
    if not all(col in df.columns for col in required_columns):
        return 1, pd.DataFrame()

    df_copy = df.copy()
    if 'Motivo_Riesgo' not in df_copy.columns:
        df_copy['Motivo_Riesgo'] = ''

    # Calcular promedio de importes por país de destino
    promedio_destino = df_copy.groupby('PAIS_DESTINO')['IMPORTE'].mean().reset_index()
    promedio_destino.columns = ['PAIS_DESTINO', 'PROMEDIO_DESTINO']
    df_copy = pd.merge(df_copy, promedio_destino, on='PAIS_DESTINO', how='left')

    # Marcar transacciones por encima de la media del país destino
    df_copy['Encima_Global'] = df_copy['IMPORTE'] > df_copy['PROMEDIO_DESTINO']

    # Estadísticas por agente y país
    resumen = (
        df_copy.groupby(['ENT_NAT_REF_COD', 'PAIS_DESTINO'])
        .agg(total=('IMPORTE', 'count'), altas=('Encima_Global', 'sum'))
        .reset_index()
    )
    resumen['porcentaje_altas'] = (resumen['altas'] / resumen['total']) * 100

    # Asignar riesgo por agente
    agentes_riesgo = {}
    for _, row in resumen.iterrows():
        agente = row['ENT_NAT_REF_COD']
        porcentaje = row['porcentaje_altas']
        if porcentaje > 70:
            agentes_riesgo[agente] = 4
        elif porcentaje > 60:
            agentes_riesgo[agente] = 3
        elif porcentaje > 50:
            agentes_riesgo[agente] = 2
        else:
            agentes_riesgo[agente] = 1

    # Aplicar motivo de riesgo
    for _, row in resumen.iterrows():
        if row['porcentaje_altas'] > 10:
            agente = row['ENT_NAT_REF_COD']
            destino = row['PAIS_DESTINO']
            porcentaje = row['porcentaje_altas']
            mask = (
                (df_copy['ENT_NAT_REF_COD'] == agente) &
                (df_copy['PAIS_DESTINO'] == destino) &
                (df_copy['Encima_Global'])
            )
            df_copy.loc[mask, 'Motivo_Riesgo'] = (
                f"Agente con {porcentaje:.1f}% de transacciones por encima de la media global en {destino}"
            )

    # Preparar el df_result
    df_result = df_copy[df_copy['Motivo_Riesgo'].astype(bool)].copy()

    risk_score = agentes_riesgo[agente]
    orig_cols = list(df.columns) + ['Motivo_Riesgo']

    df_result = df_copy.loc[
        df_copy['Motivo_Riesgo'].astype(str).str.strip() != '',
        orig_cols
    ].copy()
    return risk_score, df_result



def calcular_riesgo_indicador_17(df: pd.DataFrame) -> Tuple[int, pd.DataFrame]:
    """
     Calcula el riesgo según el indicador 17: Agente que concentra sus operaciones en fechas/horas específicas.

    Identifica agentes que muestran concentración de operaciones en intervalos
    de tiempo muy cortos o en horas inusuales (antes de las 9:00 o después de las 22:00),
    lo que podría indicar intención de evadir controles o supervisión.

    Se asigna un riesgo a nivel global según el porcentaje de clientes que presentan 
    una alta proporción de transacciones en condiciones inusuales.   Retorna la puntuación de riesgo y el DataFrame original con una columna 'Motivo_Riesgo'
    indicando las transacciones de riesgo.
    """
    import numpy as np  # Para operaciones vectorizadas

    # Verificar columnas necesarias
    required_columns = ['ENT_NAT_REF_COD', 'FECHA', 'HORA', 'IMPORTE', 'NUM_DOC_ORDENANTE']
    missing_cols = [col for col in required_columns if col not in df.columns]
    if missing_cols:
        print(f"Advertencia: Faltan columnas necesarias: {missing_cols}")
        return 1, pd.DataFrame()

    # Trabajar sobre copia y asegurarse de la columna de motivos
    df_copy = df.copy()
    if 'Motivo_Riesgo' not in df_copy.columns:
        df_copy['Motivo_Riesgo'] = ''

    # Preparar conversión a datetime usando la zona de Madrid
    madrid_tz = pytz.timezone('Europe/Madrid')
    try:
        # Primero convertir la fecha a cadena de texto si es un datetime
        if df_copy['FECHA'].dtype == 'datetime64[ns]' or (df_copy['FECHA'].dtype == 'object' and isinstance(df_copy['FECHA'].iloc[0], (pd.Timestamp, date, datetime))):
            df_copy['FECHA_STR'] = df_copy['FECHA'].dt.strftime('%d/%m/%Y') if hasattr(df_copy['FECHA'], 'dt') else df_copy['FECHA'].apply(lambda x: x.strftime('%d/%m/%Y') if hasattr(x, 'strftime') else str(x))
        else:
            df_copy['FECHA_STR'] = df_copy['FECHA'].astype(str)

        # Luego concatenar con la hora
        df_copy['TIMESTAMP'] = pd.to_datetime(df_copy['FECHA_STR'] + ' ' + df_copy['HORA'].astype(str), format='%d/%m/%Y %H:%M', errors='coerce')
    except Exception as e:
        print(f"Error al convertir FECHA y HORA a datetime: {e}")
        # En caso de error, intentamos otra forma de convertir
        try:
            # Intentamos convertir fecha y hora por separado
            if 'FECHA_STR' not in df_copy.columns:
                df_copy['FECHA_STR'] = df_copy['FECHA'].astype(str)
            df_copy['TIMESTAMP'] = pd.to_datetime(df_copy['FECHA_STR'], format='%d/%m/%Y', errors='coerce')
        except Exception as e2:
            print(f"Error al convertir solo FECHA a datetime: {e2}")
            return 1, pd.DataFrame()

    # Localizar cada registro en la zona horaria de Madrid
    df_copy['TIMESTAMP_MADRID'] = df_copy['TIMESTAMP'].dt.tz_localize(madrid_tz, ambiguous='infer', nonexistent='shift_forward')

    # Calcular la diferencia de tiempo entre transacciones consecutivas de cada cliente
    # Usamos groupby y shift para calcular 'delta' en minutos
    df_copy.sort_values(by=['NUM_DOC_ORDENANTE', 'TIMESTAMP_MADRID'], inplace=True)
    df_copy['delta'] = df_copy.groupby('NUM_DOC_ORDENANTE')['TIMESTAMP_MADRID'].diff()

    # Crear flag: operaciones muy cercanas (diferencia menor a 1 hora)
    operaciones_threshold = timedelta(hours=1)
    df_copy['operacion_cercana'] = df_copy['delta'] < operaciones_threshold

    # Flag para operaciones en horas inusuales: antes de las 9 o a las 22 o más
    df_copy['hora'] = df_copy['TIMESTAMP_MADRID'].dt.hour
    df_copy['hora_inusual'] = (df_copy['hora'] < 9) | (df_copy['hora'] >= 22)

    # Definir flag general de riesgo para cada transacción
    # Puede ser True si se cumple alguno de los criterios
    df_copy['transaccion_riesgo'] = df_copy['operacion_cercana'] | df_copy['hora_inusual']

    # Para cada cliente, calcular la proporción de transacciones en riesgo
    resumen_clientes = df_copy.groupby('NUM_DOC_ORDENANTE').agg(
        total_transacciones = ('IMPORTE', 'count'),
        transacciones_riesgo = ('transaccion_riesgo', 'sum')
    ).reset_index()
    resumen_clientes['porcentaje_riesgo'] = (resumen_clientes['transacciones_riesgo'] / resumen_clientes['total_transacciones']) * 100

    # Asignar riesgo a nivel global basado en el porcentaje de clientes que muestran alta concentración
    total_clientes = resumen_clientes.shape[0]
    # Consideramos "cliente riesgoso" si tiene >10% de sus transacciones en situaciones inusuales
    clientes_riesgosos = resumen_clientes[resumen_clientes['porcentaje_riesgo'] > 10]
    porcentaje_clientes_riesgo = (clientes_riesgosos.shape[0] / total_clientes) * 100 if total_clientes > 0 else 0

    if porcentaje_clientes_riesgo > 25:
        risk_score = 4
    elif porcentaje_clientes_riesgo > 20:
        risk_score = 3
    elif porcentaje_clientes_riesgo > 15:
        risk_score = 2
    else:
        risk_score = 1

    # Actualizar 'Motivo_Riesgo' para las transacciones de clientes que tienen alto porcentaje de riesgo
    # Se marca cada transacción que cumpla el criterio, y se añade el porcentaje de riesgo del cliente
    riesgo_dict = resumen_clientes.set_index('NUM_DOC_ORDENANTE')['porcentaje_riesgo'].to_dict()
    # Solo se marcarán las transacciones ya identificadas como riesgo
    df_copy.loc[df_copy['transaccion_riesgo'], 'Motivo_Riesgo'] = df_copy.loc[df_copy['transaccion_riesgo'], 'NUM_DOC_ORDENANTE'].map(
        lambda cli: f"Operación en intervalo corto o en hora inusual; riesgo cliente: {riesgo_dict.get(cli, 0):.1f}%"
    )

    # Eliminar columnas auxiliares
    df_result = df_copy.drop(columns=['TIMESTAMP', 'TIMESTAMP_MADRID', 'delta', 'operacion_cercana', 'hora', 'hora_inusual', 'transaccion_riesgo', 'FECHA_STR'])
    orig_cols = list(df.columns) + ['Motivo_Riesgo']

    df_result = df_copy.loc[
        df_copy['Motivo_Riesgo'].astype(str).str.strip() != '',
        orig_cols
    ].copy()

    return risk_score, df_result

def calcular_riesgo_indicador_18(df: pd.DataFrame) -> Tuple[float, pd.DataFrame]:
    """
    Calcula el riesgo según el indicador 18: Agente aparece como remitente de dinero a diferentes países/beneficiarios.
    Identifica agentes que también aparecen como clientes enviando dinero a múltiples
    destinos o beneficiarios, lo que podría indicar prácticas irregulares o uso
    de agentes como intermediarios en esquemas de lavado.
    Retorna la puntuación de riesgo y el DataFrame original con una columna 'Motivo_Riesgo'
    indicando las transacciones de riesgo.
    """
    # columnas necesarias
    cols_req = ['ENT_NAT_REF_COD', 'IMPORTE', 'ES_AGENTE']
    if not all(c in df.columns for c in cols_req):
        empty = pd.DataFrame(columns=list(df.columns) + ['Motivo_Riesgo'])
        return 1.0, empty

    # Preparar datos
    df_copy = df.copy()
    df_copy['Motivo_Riesgo'] = ''
    df_copy['IMPORTE'] = pd.to_numeric(df_copy['IMPORTE'], errors='coerce')
    df_num = df_copy.dropna(subset=['IMPORTE'])

    # Marcar agentes
    df_num['ES_AGENTE_bool'] = df_num['ES_AGENTE'].astype(str).str.strip().str.upper() == "TRUE"

    # Media y recuento de clientes (no agentes)
    df_clients = df_num[~df_num['ES_AGENTE_bool']]
    mean_clients_imp = df_clients['IMPORTE'].mean()
    count_clients = len(df_clients)
    if count_clients == 0 or mean_clients_imp == 0 or pd.isna(mean_clients_imp):
        empty = pd.DataFrame(columns=list(df.columns) + ['Motivo_Riesgo'])
        return 1.0, empty

    # Lista de agentes únicos
    agentes = df_num.loc[df_num['ES_AGENTE_bool'], 'ENT_NAT_REF_COD'].unique()
    if len(agentes) == 0:
        empty = pd.DataFrame(columns=list(df.columns) + ['Motivo_Riesgo'])
        return 1.0, empty

    scores = []
    ratios = []

    # Para cada agente calculamos ratios y score
    for agente in agentes:
        df_ag = df_num[(df_num['ES_AGENTE_bool']) & (df_num['ENT_NAT_REF_COD'] == agente)]
        mean_ag_imp = df_ag['IMPORTE'].mean()
        count_ag = len(df_ag)

        # evitar división por cero
        if count_ag == 0:
            continue

        ratio_imp = mean_ag_imp / mean_clients_imp
        ratio_cnt = count_ag / count_clients
        ratio_ag = (ratio_imp + ratio_cnt) / 2
        ratios.append(ratio_ag)

        if ratio_ag > 0.75:
            score = 4
        elif ratio_ag > 0.5:
            score = 3
        elif ratio_ag > 0.25:
            score = 2
        else:
            score = 1
        scores.append(score)

        # marcar alerta si score >= 3
        if score >= 3:
            motivo = (
                f"Agente {agente}: ratio medio {ratio_ag:.2f}× "
                "superior al resto de clientes"
            )
            df_copy.loc[df_copy['ENT_NAT_REF_COD'] == agente, 'Motivo_Riesgo'] = motivo

    # Construir DataFrame de alertas
    cols_out = list(df.columns) + ['Motivo_Riesgo']
    df_alertas = df_copy.loc[df_copy['Motivo_Riesgo'] != '', cols_out].copy()

    # Calcular medias finales
    risk_score = float(np.mean(scores)) if scores else 1.0
    ratio_mean = float(np.mean(ratios)) if ratios else 0.0

    return risk_score, df_alertas

def calcular_riesgo_indicador_19(df: pd.DataFrame) -> Tuple[int, pd.DataFrame]:
    """
    Calcula el riesgo según el indicador 19: Agentes con alto número de remitentes cuya nacionalidad difiere del destino.

    Identifica agentes con un número elevado de remitentes que envían dinero a países
    distintos de su nacionalidad, lo que podría indicar patrones atípicos o sospechosos.
    Retorna la puntuación de riesgo y el DataFrame original con una columna 'Motivo_Riesgo'
    indicando las transacciones de riesgo.
    """
    # Verificar que existan las columnas necesarias
    required_cols = ['ENT_NAT_REF_COD', 'PAIS_NAC_ORDENANTE', 'PAIS_DOC_ORDENANTE', 'PAIS_DESTINO', 'NUM_DOC_ORDENANTE']
    if not all(col in df.columns for col in required_cols):
        return 1, pd.DataFrame(columns=list(df.columns) + ['Motivo_Riesgo'])

    df_copy = df.copy()
    if 'Motivo_Riesgo' not in df_copy.columns:
        df_copy['Motivo_Riesgo'] = ''


    clientes_unicos = df_copy['NUM_DOC_ORDENANTE'].dropna().unique()
    total_clientes = len(clientes_unicos)
    clientes_riesgo = []

    for cliente in clientes_unicos:
        df_cliente = df_copy[df_copy['NUM_DOC_ORDENANTE'] == cliente]

        nacionalidad = df_cliente['PAIS_NAC_ORDENANTE'].iloc[0]
        doc_pais = df_cliente['PAIS_DOC_ORDENANTE'].iloc[0]
        destinos = df_cliente['PAIS_DESTINO'].unique()

        for destino in destinos:
            if destino != nacionalidad and destino != doc_pais:
                clientes_riesgo.append(cliente)
                df_copy.loc[df_copy['NUM_DOC_ORDENANTE'] == cliente, 'Motivo_Riesgo'] = (
                    f"Cliente {cliente}: destino {destino} distinto de nacionalidad {nacionalidad} y país doc {doc_pais}"
                )
                break  # Si ya lo marcamos, no seguimos con más destinos de ese cliente

    porcentaje_riesgo = (len(clientes_riesgo) / total_clientes * 100) if total_clientes > 0 else 0.0

    # Asignar risk_score
    if porcentaje_riesgo > 8.5:
        risk_score = 4
    elif porcentaje_riesgo > 7:
        risk_score = 3
    elif porcentaje_riesgo > 6.5:
        risk_score = 2
    else:
        risk_score = 1

    orig_cols = list(df.columns) + ['Motivo_Riesgo']

    df_result = df_copy.loc[
        df_copy['Motivo_Riesgo'].astype(str).str.strip() != '',
        orig_cols
    ].copy()
    df_result = df_copy[df_copy['Motivo_Riesgo'].astype(bool)].copy()

    return risk_score, df_result

def calcular_riesgo_indicador_20(df: pd.DataFrame) -> Tuple[int, pd.DataFrame]:


    """
    Calcula el riesgo según el indicador 20: Agentes con datos repetitivos de cliente en distintos campos.

    Identifica agentes que introducen información del cliente de manera repetitiva
    en varios campos o con patrones sospechosos, lo que podría indicar prácticas
    irregulares en la captura de datos o intentos de ocultar la verdadera identidad
    Retorna la puntuación de riesgo y el DataFrame original con una columna 'Motivo_Riesgo'
    indicando las transacciones de riesgo.
    """
    # Verificar que existan las columnas necesarias
    required_cols = ['NUM_DOC_ORDENANTE', 'NOMBRE_BENEFICIARIO', 'APELLIDO_BENEFICIARIO', 'SEGUNDO_APELLIDO_BENEFICIARIO', 'PAIS_DESTINO']
    if not all(col in df.columns for col in required_cols):
        return 1, pd.DataFrame()

    df_copy = df.copy()
    if 'Motivo_Riesgo' not in df_copy.columns:
        df_copy['Motivo_Riesgo'] = ''

    def normalize_string(s):
        if pd.isna(s):
            return ''
        return str(s).strip().lower()

    # Crear clave única de beneficiario
    df_copy['clave_benef'] = df_copy.apply(
        lambda row: f"{normalize_string(row['NOMBRE_BENEFICIARIO'])}|"
                    f"{normalize_string(row['APELLIDO_BENEFICIARIO'])}|"
                    f"{normalize_string(row.get('SEGUNDO_APELLIDO_BENEFICIARIO', ''))}|"
                    f"{normalize_string(row['PAIS_DESTINO'])}",
        axis=1
    )

    # Agrupar por clave_benef y contar ordenantes únicos
    grupos = df_copy.groupby('clave_benef')['NUM_DOC_ORDENANTE'].nunique()

    # Detectar claves con más de un ordenante
    claves_repetitivas = grupos[grupos > 1].index.tolist()
    ordenantes_repetitivos = df_copy[df_copy['clave_benef'].isin(claves_repetitivas)]['NUM_DOC_ORDENANTE'].unique()

    total_ordenantes = df_copy['NUM_DOC_ORDENANTE'].nunique()
    porcentaje_repetitivos = (len(ordenantes_repetitivos) / total_ordenantes * 100) if total_ordenantes > 0 else 0

    # Asignar risk score
    if porcentaje_repetitivos > 30:
        risk_score = 4
    elif porcentaje_repetitivos > 25:
        risk_score = 3
    elif porcentaje_repetitivos > 20:
        risk_score = 2
    else:
        risk_score = 1

    # Marcar las transacciones sospechosas
    motivo = (
        f"Beneficiarios repetidos entre distintos ordenantes "
        f"({porcentaje_repetitivos:.1f}% de ordenantes afectados)"
    )
    df_copy.loc[df_copy['NUM_DOC_ORDENANTE'].isin(ordenantes_repetitivos), 'Motivo_Riesgo'] = motivo

    # Limpiar columna auxiliar
    df_copy.drop(columns=['clave_benef'], inplace=True)

    # Filtrar sólo transacciones con Motivo_Riesgo
    df_result = df_copy[df_copy['Motivo_Riesgo'].astype(bool)].copy()
    orig_cols = list(df.columns) + ['Motivo_Riesgo']

    df_result = df_copy.loc[
        df_copy['Motivo_Riesgo'].astype(str).str.strip() != '',
        orig_cols
    ].copy()
    return risk_score, df_result



# Definiciones de indicadores y umbrales

NOMBRES_INDICADORES = {
    '1': "Uso de la misma documentación en un corto espacio de tiempo",
    '2': "Documento repetido con diferentes nombres",
    '3': "Documentación errónea (NIE/NIF)",
    '4': "Operaciones para evitar umbrales de comunicación (3.000 euros)",
    '5': "Operaciones fraccionadas hacia un mismo beneficiario",
    '6': "Uso sistemático de importes redondos para valores altos",
    '7': "Cliente realiza numerosas cancelaciones",
    '8': "Transferencias a países de alto riesgo",
    '9': "Operaciones que no coinciden con el perfil habitual del cliente",
    '10': "Clientes que son personas políticamente expuestas (PEP)",
    '11': "Variaciones en los corredores hacia destinos de mayor riesgo",
    '12': "Agente con volumen mayor que la media",
    '13': "Agente que no completa adecuadamente la información de los clientes",
    '14': "Agente con operaciones muy por encima de su municipio",
    '15': "Agente con incremento repentino de operativa",
    '16': "Agente con volumen sustancial a un destino concreto",
    '17': "Agente que concentra operaciones en fechas/horas inusuales",
    '18': "Agente como ordenante de envíos a diferentes países",
    '19': "Remitentes con nacionalidad distinta del país de destino",
    '20': "Agentes que incluyen datos repetitivos en sus clientes"
}

TIPOS_INDICADORES = {
    '1': "DOCUMENTACIÓN",
    '2': "DOCUMENTACIÓN", 
    '3': "DOCUMENTACIÓN",
    '4': "UMBRALES",
    '5': "UMBRALES",
    '6': "UMBRALES", 
    '7': "UMBRALES",
    '8': "GEOGRÁFICO",
    '9': "OUTLIERS",
    '10': "OUTLIERS",
    '11': "GEOGRÁFICO",
    '12': "OUTLIERS",
    '13': "DOCUMENTACIÓN",
    '14': "OUTLIERS",
    '15': "OUTLIERS",
    '16': "OUTLIERS",
    '17': "OUTLIERS",
    '18': "OUTLIERS",
    '19': "GEOGRÁFICO",
    '20': "DOCUMENTACIÓN"
}

# Umbrales predeterminados usados en las funciones de análisis
UMBRALES_DEFAULT = {
    '1': {'descripcion': 'Nº de operaciones en 3 días', 'bajo': 12.5, 'medio': 20, 'alto': 27.5},
    '2': {'descripcion': '% de nombres diferentes', 'bajo': 10, 'medio': 15, 'alto': 20},
    '3': {'descripcion': '% documentos erróneos', 'bajo': 3, 'medio': 4, 'alto': 5},
    '4': {'descripcion': 'Importe total fraccionado (€)', 'bajo': 12, 'medio': 15, 'alto': 18},
    '5': {'descripcion': 'Nº remitentes a mismo beneficiario', 'bajo': 0.25, 'medio': 0.5, 'alto': 1},
    '6': {'descripcion': '% operaciones con importes redondos', 'bajo': 0, 'medio': 0.5, 'alto': 1},
    '7': {'descripcion': 'Nº cancelaciones en un periodo', 'bajo': 0, 'medio': 0.5, 'alto': 1},
    '8': {'descripcion': 'Nº transacciones a países de alto riesgo', 'bajo': 13, 'medio': 14, 'alto': 15},
    '9': {'descripcion': 'Desviación del perfil (desv. estándar)', 'bajo': 0.5, 'medio': 1, 'alto': 2},
    '10': {'descripcion': 'Nº transacciones de PEPs', 'bajo': 1, 'medio': 1.5, 'alto': 2},
    '11': {'descripcion': '% incremento a destinos de riesgo', 'bajo': 20, 'medio': 21, 'alto': 22},
    '12': {'descripcion': '% sobre volumen medio de agentes', 'bajo': 0.125, 'medio': 0.25, 'alto': 0.5},
    '13': {'descripcion': '% campos incompletos', 'bajo': 34, 'medio': 35.5, 'alto': 37},
    '14': {'descripcion': '% sobre media del municipio', 'bajo': 21.5, 'medio': 23, 'alto': 24.5},
    '15': {'descripcion': '% incremento repentino', 'bajo': 0, 'medio': 4, 'alto': 8},
    '16': {'descripcion': '% sobre media a ese destino', 'bajo': 50, 'medio': 60, 'alto': 70},
    '17': {'descripcion': '% operaciones en horario inusual', 'bajo': 15, 'medio': 20, 'alto': 25},
    '18': {'descripcion': 'Nº países/beneficiarios', 'bajo': 0.25, 'medio': 0.5, 'alto': 0.75},
    '19': {'descripcion': '% remitentes con nacionalidad diferente', 'bajo': 6.5, 'medio': 7, 'alto': 8.5},
    '20': {'descripcion': '% datos repetidos', 'bajo': 20, 'medio': 25, 'alto': 30}
}

def obtener_nivel_riesgo(score):
    """
    Convierte una puntuación numérica de riesgo a un nivel cualitativo.

    Args:
        score: Puntuación numérica (1-4)

    Returns:
        Nivel de riesgo como texto ("BAJO", "MEDIO", "ALTO", "MUY ALTO")
    """
    if score < 1.5:
        return "BAJO"
    elif score < 2.5:
        return "MEDIO"
    elif score < 3.5:
        return "ALTO"
    else:
        return "MUY ALTO"