"""
Módulo para la detección de patrones y tramas sospechosas en las transacciones.
Implementa algoritmos de análisis para detectar esquemas de estructuración,
múltiples remitentes a un mismo beneficiario, y otros patrones de interés.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Tuple

def identify_smurfing_patterns(df: pd.DataFrame) -> Dict[str, List[Dict[str, any]]]:
    """
    Identifica patrones potenciales de "smurfing" (estructuración) en las transacciones.
    
    Parámetros:
    - df: DataFrame con los datos de transacciones
    
    Retorna:
    - Dict con patrones identificados
    """
    if df.empty:
        return {"error": "No hay datos para analizar"}
    
    # Verificar columnas necesarias
    required_cols = ['NUMERO_TRANSACCION', 'FECHA', 'IMPORTE', 'NUM_DOC_ORDENANTE', 'NOMBRE_BENEFICIARIO', 'APELLIDO_BENEFICIARIO']
    if not all(col in df.columns for col in required_cols):
        return {"error": "Faltan columnas necesarias para el análisis de smurfing"}
    
    # Preparar resultado
    results = {
        "multiple_senders_same_beneficiary": [],
        "structured_transactions": [],
        "frequent_small_amounts": []
    }
    
    # 1. Patrón: Múltiples remitentes enviando a un mismo beneficiario
    if 'NOMBRE_BENEFICIARIO' in df.columns and 'APELLIDO_BENEFICIARIO' in df.columns:
        df['BENEFICIARIO_ID'] = df.apply(
            lambda row: f"{row['NOMBRE_BENEFICIARIO']} {row['APELLIDO_BENEFICIARIO']}",
            axis=1
        )
        
        beneficiary_counts = df.groupby('BENEFICIARIO_ID')['NUM_DOC_ORDENANTE'].nunique().reset_index()
        beneficiary_counts.columns = ['BENEFICIARIO_ID', 'NUM_REMITENTES']
        
        # Filtrar beneficiarios con múltiples remitentes (al menos 3)
        suspicious_beneficiaries = beneficiary_counts[beneficiary_counts['NUM_REMITENTES'] >= 3]
        
        for _, row in suspicious_beneficiaries.iterrows():
            beneficiary_id = row['BENEFICIARIO_ID']
            num_senders = row['NUM_REMITENTES']
            
            # Obtener detalles de las transacciones
            transactions = df[df['BENEFICIARIO_ID'] == beneficiary_id]
            total_amount = transactions['IMPORTE'].sum()
            transaction_count = len(transactions)
            
            results["multiple_senders_same_beneficiary"].append({
                "beneficiary": beneficiary_id,
                "num_senders": num_senders,
                "total_amount": total_amount,
                "transaction_count": transaction_count,
                "transactions": transactions['NUMERO_TRANSACCION'].tolist()[:10]  # Limitar a 10 transacciones
            })
    
    # 2. Patrón: Transacciones estructuradas (múltiples transacciones pequeñas en lugar de una grande)
    if 'FECHA' in df.columns and 'IMPORTE' in df.columns and 'NUM_DOC_ORDENANTE' in df.columns:
        # Agrupar por remitente y fecha
        df_grouped = df.groupby(['NUM_DOC_ORDENANTE', 'FECHA'])
        
        for (sender, date), group in df_grouped:
            if len(group) >= 3:  # Al menos 3 transacciones el mismo día
                total_amount = group['IMPORTE'].sum()
                max_amount = group['IMPORTE'].max()
                
                # Si todas las transacciones son pequeñas y el total es significativo
                if max_amount < 1000 and total_amount > 3000:
                    results["structured_transactions"].append({
                        "sender": sender,
                        "date": date.strftime('%Y-%m-%d') if hasattr(date, 'strftime') else str(date),
                        "transaction_count": len(group),
                        "total_amount": total_amount,
                        "average_amount": total_amount / len(group),
                        "transactions": group['NUMERO_TRANSACCION'].tolist()
                    })
    
    # 3. Patrón: Transacciones frecuentes de pequeños importes
    if 'IMPORTE' in df.columns and 'FECHA' in df.columns and 'NUM_DOC_ORDENANTE' in df.columns:
        small_transactions = df[df['IMPORTE'] < 1000]
        sender_counts = small_transactions.groupby('NUM_DOC_ORDENANTE').size().reset_index(name='COUNT')
        
        # Remitentes con muchas transacciones pequeñas (al menos 5)
        frequent_senders = sender_counts[sender_counts['COUNT'] >= 5]
        
        for _, row in frequent_senders.iterrows():
            sender = row['NUM_DOC_ORDENANTE']
            count = row['COUNT']
            
            # Obtener detalles de las transacciones
            transactions = small_transactions[small_transactions['NUM_DOC_ORDENANTE'] == sender]
            total_amount = transactions['IMPORTE'].sum()
            date_range = (transactions['FECHA'].max() - transactions['FECHA'].min()).days if hasattr(transactions['FECHA'].max(), 'days') else None
            
            results["frequent_small_amounts"].append({
                "sender": sender,
                "small_transaction_count": count,
                "total_amount": total_amount,
                "average_amount": total_amount / count,
                "date_range_days": date_range,
                "transactions": transactions['NUMERO_TRANSACCION'].tolist()[:10]  # Limitar a 10 transacciones
            })
    
    return results

def format_pattern_for_display(patterns: Dict[str, List[Dict[str, Any]]]) -> Dict[str, pd.DataFrame]:
    """
    Convierte los patrones detectados a DataFrames para visualización.
    
    Args:
        patterns: Diccionario con patrones detectados
        
    Returns:
        Diccionario con DataFrames formateados por tipo de patrón
    """
    result = {}
    
    # Si hay un error en los patrones, devolver vacío
    if "error" in patterns:
        return {}
    
    # 1. Patrones de múltiples remitentes a un mismo beneficiario
    if patterns.get("multiple_senders_same_beneficiary"):
        df_multiple = pd.DataFrame(patterns["multiple_senders_same_beneficiary"])
        if not df_multiple.empty:
            # Formatear para visualización
            df_multiple = df_multiple.rename(columns={
                "beneficiary": "Beneficiario",
                "num_senders": "Número de Remitentes",
                "total_amount": "Importe Total (€)",
                "transaction_count": "Total Transacciones"
            })
            result["multiple_senders"] = df_multiple
    
    # 2. Patrones de transacciones estructuradas
    if patterns.get("structured_transactions"):
        df_structured = pd.DataFrame(patterns["structured_transactions"])
        if not df_structured.empty:
            # Formatear para visualización
            df_structured = df_structured.rename(columns={
                "sender": "Remitente (Doc)",
                "date": "Fecha",
                "transaction_count": "Núm. Transacciones",
                "total_amount": "Importe Total (€)",
                "average_amount": "Importe Promedio (€)"
            })
            result["structured"] = df_structured
    
    # 3. Patrones de transacciones frecuentes de pequeños importes
    if patterns.get("frequent_small_amounts"):
        df_small = pd.DataFrame(patterns["frequent_small_amounts"])
        if not df_small.empty:
            # Formatear para visualización
            df_small = df_small.rename(columns={
                "sender": "Remitente (Doc)", 
                "small_transaction_count": "Núm. Transacciones Pequeñas",
                "total_amount": "Importe Total (€)",
                "average_amount": "Importe Promedio (€)",
                "date_range_days": "Rango en Días"
            })
            result["small_frequent"] = df_small
    
    return result