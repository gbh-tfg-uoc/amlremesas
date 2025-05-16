import pandas as pd
import numpy as np
import io
import re
from datetime import datetime
import os
from typing import List, Dict, Tuple, Set, Optional, Any, Union

# Importar definiciones de columnas
from utils.column_definitions import (
    normalize_column_name
)


def process_csv_files(uploaded_files: List) -> Tuple[pd.DataFrame, Dict[str, str]]:
    """
    Procesa archivos CSV subidos y extrae información de agente y sujeto de los nombres de archivo.

    Args:
        uploaded_files: Lista de objetos de archivos subidos

    Returns:
        Tupla que contiene:
        - DataFrame combinado con todas las transacciones
        - Diccionario que mapea códigos de agente a códigos de sujeto
    """
    all_dataframes = []
    agent_subject_mapping = {}

    for file in uploaded_files:
        try:
            # Extraer información de agente y sujeto del nombre del archivo
            filename = file.name
            print(f"Procesando archivo: {filename}")

            # Probar diferentes patrones de nombre de archivo
            # Patrón 1: Sujeto_ObligadoX__AgenteY (formato original)
            match1 = re.search(r'Sujeto_Obligado(\d+)__Agente(\d+)', filename)
            # Patrón 2: Sujeto_X / Agente_Y (formato alternativo)
            match2 = re.search(r'Sujeto_(\d+).*Agente(?:_)?(\d+)', filename)
            # Patrón 3: SujetoX / AgenteY (otro formato alternativo)
            match3 = re.search(r'Sujeto(\d+).*Agente(\d+)', filename)
            # Patrón 4: Con código numérico en el nombre
            match4 = re.search(r'(\d+).*(\d{4,})', filename)  # Busca cualquier número y luego un número de 4+ dígitos
            # Patrón 5: Extraer simplemente el último grupo numérico como ID de agente
            numeric_parts = re.findall(r'\d+', filename)

            # Determinar qué patrón coincidió
            if match1:
                subject_id = match1.group(1)
                agent_id = match1.group(2)
                print(f"Patrón 1 coincidió: Sujeto_{subject_id}, Agente_{agent_id}")
            elif match2:
                subject_id = match2.group(1)
                agent_id = match2.group(2)
                print(f"Patrón 2 coincidió: Sujeto_{subject_id}, Agente_{agent_id}")
            elif match3:
                subject_id = match3.group(1)
                agent_id = match3.group(2)
                print(f"Patrón 3 coincidió: Sujeto_{subject_id}, Agente_{agent_id}")
            elif match4:
                subject_id = match4.group(1)
                agent_id = match4.group(2)
                print(f"Patrón 4 coincidió: Sujeto_{subject_id}, Agente_{agent_id}")
            elif numeric_parts:
                # Usar el primer número como ID de sujeto y el último como ID de agente
                subject_id = numeric_parts[0]
                agent_id = numeric_parts[-1]
                print(f"Patrón 5 coincidió: Sujeto_{subject_id}, Agente_{agent_id}")
            else:
                # Valores por defecto si no hay coincidencia
                subject_id = "1"  # Valor por defecto
                agent_id = "1000"  # Valor por defecto
                print(f"Ningún patrón coincidió, usando valores por defecto: Sujeto_{subject_id}, Agente_{agent_id}")

            # Leer el archivo CSV
            try:
                file.seek(0)  # Restablecer el puntero del archivo
                df = pd.read_csv(file, sep=',', encoding='utf-8')
            except Exception as e1:
                try:
                    file.seek(0)
                    df = pd.read_csv(file, sep=';', encoding='utf-8')
                except Exception as e2:
                    try:
                        file.seek(0)
                        df = pd.read_csv(file, sep=',', encoding='latin1')
                    except Exception as e3:
                        file.seek(0)
                        # Último intento: probar todas las combinaciones
                        df = None
                        for sep in [',', ';', '\t']:
                            for enc in ['utf-8', 'latin1', 'ISO-8859-1']:
                                try:
                                    file.seek(0)
                                    df = pd.read_csv(file, sep=sep, encoding=enc)
                                    print(f"Archivo leído con separador '{sep}' y codificación '{enc}'")
                                    break
                                except:
                                    continue
                            if df is not None:
                                break

                        # Si aún no podemos leer el archivo, omitirlo
                        if df is None:
                            print(f"ERROR: No se pudo leer el archivo: {filename}")
                            continue

            # Comprobar si el DataFrame está vacío
            if df.empty:
                print(f"ADVERTENCIA: Archivo {filename} está vacío, omitiendo.")
                continue

            print(f"Columnas leídas: {df.columns.tolist()}")

            # Extraer el ID de agente de los datos si no se extrajo ya del nombre de archivo
            if 'ENT_NAT_REF_COD' in df.columns and not df['ENT_NAT_REF_COD'].isna().all():
                # Usar el valor más común en ENT_NAT_REF_COD
                extracted_agent_id = str(df['ENT_NAT_REF_COD'].mode()[0])
                print(f"Extraído ID de agente del contenido: {extracted_agent_id}")
                # Sólo usarlo si aún no tenemos un agent_id o es el valor por defecto
                if agent_id == "1000":
                    agent_id = extracted_agent_id
                    print(f"Usando ID de agente del contenido: {agent_id}")

            # Añadir información al DataFrame
            df['AGENT_ID'] = agent_id
            df['SUBJECT_ID'] = subject_id

            # Mapear agente a sujeto usando formato normalizado
            if 'ENT_NAT_REF_COD' in df.columns:
                # Usar el código de agente real de los datos si está disponible
                unique_agents = df['ENT_NAT_REF_COD'].unique()
                for agent_code in unique_agents:
                    if pd.notna(agent_code):  # Evitar valores NaN
                        # Normalizar el código del agente para evitar duplicados
                        agent_num = str(agent_code)
                        # Si ya tiene el prefijo "Agente", extraer solo el número
                        if agent_num.startswith("Agente"):
                            agent_num = agent_num[6:]

                        # Guardar en ambos formatos para garantizar coincidencia
                        agent_subject_mapping[agent_num] = f"Sujeto_{subject_id}"
                        agent_subject_mapping[f"Agente{agent_num}"] = f"Sujeto_{subject_id}"

            # También agregar el ID de agente del nombre de archivo al mapeo
            # Normalizar de la misma manera
            agent_num = str(agent_id)
            if agent_num.startswith("Agente"):
                agent_num = agent_num[6:]

            # Guardar en ambos formatos
            agent_subject_mapping[agent_num] = f"Sujeto_{subject_id}"
            agent_subject_mapping[f"Agente{agent_num}"] = f"Sujeto_{subject_id}"

            # Limpiar y estandarizar los datos
            df = clean_dataframe(df)

            # Rellenar valores NaN en ENT_NAT_REF_COD con agent_id
            if 'ENT_NAT_REF_COD' in df.columns:
                df['ENT_NAT_REF_COD'] = df['ENT_NAT_REF_COD'].fillna(agent_id)
            else:
                # Si la columna no existe, crearla
                df['ENT_NAT_REF_COD'] = agent_id

            # Añadir a la lista de DataFrames
            all_dataframes.append(df)
            print(f"Archivo {filename} procesado con éxito: {len(df)} filas")

        except Exception as e:
            import traceback
            print(f"Error al procesar el archivo {file.name}: {str(e)}")
            print(traceback.format_exc())

    # Combinar todos los DataFrames
    if all_dataframes:
        combined_df = pd.concat(all_dataframes, ignore_index=True)
        print(f"Datos combinados: {len(combined_df)} filas, {len(agent_subject_mapping)} agentes")
        return combined_df, agent_subject_mapping
    else:
        print("ADVERTENCIA: No se procesaron datos de ningún archivo.")
        return pd.DataFrame(), {}


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Limpia y estandariza un DataFrame con datos de transacciones.

    Args:
        df: DataFrame a limpiar

    Returns:
        DataFrame limpiado
    """
    # Hacer una copia para evitar advertencias SettingWithCopyWarning
    df = df.copy()

    # Normalizar nombres de columnas a mayúsculas
    df.columns = [col.upper() for col in df.columns]

    # Normalizar nombres de columnas usando el mapeo de alias definido
    new_columns = {}
    for col in df.columns:
        new_col = normalize_column_name(col)
        if new_col != col:
            new_columns[col] = new_col

    # Renombrar columnas si es necesario
    if new_columns:
        df = df.rename(columns=new_columns)

    # Procesamiento de fechas
    date_columns = ['FECHA', 'FECHA_NAC_ORDENANTE']
    for col in date_columns:
        if col in df.columns:
            try:
                df[col] = pd.to_datetime(df[col], dayfirst=True, errors='coerce')
            except:
                try:
                    # Intentar formato alternativo
                    df[col] = pd.to_datetime(df[col], format='%Y-%m-%d', errors='coerce')
                except:
                    pass

    # Procesar hora
    if 'HORA' in df.columns:
        # Mantener hora como string en formato estándar
        df['HORA'] = df['HORA'].astype(str)

    # Procesar importe
    if 'IMPORTE' in df.columns:
        df['IMPORTE'] = pd.to_numeric(df['IMPORTE'], errors='coerce')

    # Estandarizar campos categóricos
    if 'ESTADO_OPERACION' in df.columns:
        df['ESTADO_OPERACION'] = df['ESTADO_OPERACION'].str.upper()

    # Estandarizar campos de país
    country_columns = ['PAIS_ORIGEN', 'PAIS_DESTINO', 'PAIS_DOC_ORDENANTE', 'PAIS_NAC_ORDENANTE']
    for col in country_columns:
        if col in df.columns and df[col].dtype == 'object':
            df[col] = df[col].str.title()



    # Convertir códigos de agente y entidad a strings
    id_columns = ['ENT_NAT_REF_COD', 'ENT_COD_PAR_ENT', 'NUMERO_TRANSACCION']
    for col in id_columns:
        if col in df.columns:
            df[col] = df[col].astype(str)

    return df


def extract_agent_subject_info(agent_subject_mapping: Dict[str, str]) -> Tuple[List[str], List[str]]:
    """
    Extrae listas de agentes disponibles y sujetos a partir del mapeo.
Normaliza los agentes para eliminar duplicados (por ejemplo, "Agente797" y "797").

Args:

    agent_subject_mapping: Diccionario que asigna códigos de agente a códigos de sujeto

Returns:
Tupla con:

    Lista de códigos de agente normalizados (todos con prefijo "Agente")

    Lista de códigos de sujetos obligados
    """
    # Normalizar los agentes y eliminar duplicados
    normalized_agents = set()
    agents_list = []

    for agent in agent_subject_mapping.keys():
        if agent is None:
            continue

        agent_str = str(agent)
        agent_num = agent_str

        # Si el agente ya tiene el prefijo "Agente", extraer solo el número
        if agent_str.startswith("Agente"):
            agent_num = agent_str[6:]

        # Normalizar al formato "AgenteX" y añadir si no es un duplicado
        normalized_agent = f"Agente{agent_num}"

        if agent_num not in normalized_agents:
            normalized_agents.add(agent_num)
            agents_list.append(normalized_agent)

    # Ordenar la lista de agentes para una presentación más clara
    agents_list.sort()

    # Obtener la lista de sujetos obligados únicos
    subjects = list(set(agent_subject_mapping.values()))

    return agents_list, subjects


def filter_dataframe(
    df: pd.DataFrame, 
    agent_subject_mapping: Dict[str, str],
    selected_agents: List[str],
    selected_subjects: List[str]
) -> pd.DataFrame:
    """
   Filtra un DataFrame según los agentes y sujetos seleccionados.

    Args:
        df: DataFrame a filtrar
        agent_subject_mapping: Diccionario que asigna códigos de agente a códigos de sujeto
        selected_agents: Lista de códigos de agente seleccionados
        selected_subjects: Lista de códigos de sujeto seleccionados

    Returns:
        DataFrame filtrado

    """
    print("Iniciando filtrado de DataFrame...")
    print(f"Agentes seleccionados: {selected_agents}")
    print(f"Sujetos seleccionados: {selected_subjects}")

    # Verificaciones de seguridad
    if df is None or df.empty:
        print("DataFrame vacío o None")
        # Devolver un DataFrame vacío con las mismas columnas si está disponible
        if isinstance(df, pd.DataFrame):
            return pd.DataFrame(columns=df.columns)
        return pd.DataFrame()

    # Normalizar agentes seleccionados de forma más estricta - VERSIÓN MEJORADA
    normalized_agent_ids = set()  # Usamos un set para garantizar unicidad
    normalized_selected_agents = []

    # Primero, extraer todos los ID numéricos de agente
    for agent in selected_agents:
        if agent is None:
            continue

        agent_str = str(agent)

        # Extraer el número de agente consistentemente
        if agent_str.startswith('Agente'):
            agent_num = agent_str[6:]  # Número después de "Agente"
        else:
            agent_num = agent_str

        # Solo agregar si no está ya en el conjunto
        if agent_num not in normalized_agent_ids:
            normalized_agent_ids.add(agent_num)
            # Siempre usar el formato con prefijo "Agente" de manera consistente
            normalized_selected_agents.append(f"Agente{agent_num}")

    # Actualizar la lista de agentes seleccionados con la versión normalizada
    selected_agents = normalized_selected_agents
    print(f"Agentes normalizados: {selected_agents}")

    try:
        # Manejar columnas duplicadas
        if df.columns.duplicated().any():
            print("ADVERTENCIA: Columnas duplicadas detectadas, renombrando...")
            # Renombrar columnas duplicadas para evitar problemas
            cols = pd.Series(df.columns)
            for dup in cols[cols.duplicated()].unique(): 
                cols[cols[cols == dup].index.values.tolist()] = [f"{dup}_{i}" if i != 0 else dup for i in range(sum(cols == dup))]
            df.columns = cols

        # Crear una copia con reset_index garantizado
        print("Creando copia limpia del DataFrame...")
        df_new = df.copy()
        df_new = df_new.reset_index(drop=True)

        # Si no hay filtros seleccionados, devolver todos los datos
        if not selected_agents and not selected_subjects:
            print("No hay filtros seleccionados, devolviendo todos los datos")
            return df_new

        # Determinar agentes que corresponden a los sujetos seleccionados
        agents_for_selected_subjects = set()
        if selected_subjects:
            for agent, subject in agent_subject_mapping.items():
                if subject in selected_subjects:
                    agents_for_selected_subjects.add(agent)
            print(f"Agentes correspondientes a sujetos seleccionados: {agents_for_selected_subjects}")

        # Combinar los agentes seleccionados explícitamente con los de los sujetos seleccionados
        all_agents_to_filter = set(selected_agents).union(agents_for_selected_subjects)
        print(f"Agentes totales para filtrar: {all_agents_to_filter}")

        # Filtrar el DataFrame solo si hay agentes para filtrar y la columna existe
        if all_agents_to_filter and 'ENT_NAT_REF_COD' in df_new.columns:
            print("Filtrando por agentes...")

            # Método de filtrado manual por valor (más seguro)
            matching_indices = []

            # Método mejorado de comparación de agentes
            for idx, val in enumerate(df_new['ENT_NAT_REF_COD']):
                if val is None:
                    continue

                # Normalizar valor actual para comparación
                val_str = str(val)

                # Comprobar coincidencias de tres maneras:
                # 1. Directamente con el valor
                # 2. Con el formato "AgenteX" si el valor no tiene el prefijo
                # 3. Con el número si el valor tiene el prefijo "Agente"
                matches = False

                for agent in all_agents_to_filter:
                    agent_str = str(agent)

                    # Verificar coincidencia directa
                    if agent_str == val_str:
                        matches = True
                        break

                    # Si val_str tiene el formato "AgenteX", extraer el número
                    if val_str.startswith("Agente"):
                        val_num = val_str[6:]
                        # Comparar con el agente sin prefijo
                        if agent_str == val_num:
                            matches = True
                            break
                    # Si val_str es solo un número, comparar con el formato "AgenteX"
                    elif val_str.isdigit():
                        if agent_str == f"Agente{val_str}":
                            matches = True
                            break

                if matches:
                    matching_indices.append(idx)

            if matching_indices:
                print(f"Se encontraron {len(matching_indices)} coincidencias")
                filtered_df = df_new.iloc[matching_indices].copy()
                filtered_df.reset_index(drop=True, inplace=True)
                return filtered_df
            else:
                print("No se encontraron coincidencias")
                # No se encontraron coincidencias - devolver DataFrame vacío
                return pd.DataFrame(columns=df_new.columns)

        elif not all_agents_to_filter and (selected_agents or selected_subjects):
            # Si se seleccionaron filtros pero no hay agentes correspondientes
            print("Se seleccionaron filtros pero no hay agentes correspondientes")
            return pd.DataFrame(columns=df_new.columns)

        # Si llegamos aquí, puede que la columna ENT_NAT_REF_COD no exista
        print("Devolviendo DataFrame sin filtrar")
        return df_new

    except Exception as e:
        # En caso de error, registrarlo y devolver un DataFrame vacío
        print(f"ERROR AL FILTRAR: {str(e)}")
        import traceback
        print(traceback.format_exc())

        # Intento de recuperación - mostrar información de diagnóstico
        try:
            print(f"Columnas disponibles: {df.columns.tolist()}")
            print(f"Tipos de datos: {df.dtypes}")
        except:
            print("No se pudo mostrar información de diagnóstico")

        # Devolver DataFrame vacío
        if isinstance(df, pd.DataFrame):
            return pd.DataFrame(columns=df.columns)
        return pd.DataFrame()
