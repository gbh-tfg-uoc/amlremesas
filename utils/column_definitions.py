"""
Definiciones centralizadas de columnas para garantizar la coherencia en toda la aplicación.
Esto ayuda a mantener un uso consistente de los nombres de columnas en todos los módulos.
"""

# Lista de todas las columnas esperadas en los archivos CSV
EXPECTED_COLUMNS = [
    'NUMERO_TRANSACCION',      # Número único de cada transacción
    'FECHA',                   # Fecha de la operación
    'HORA',                    # Hora de la operación
    'IMPORTE',                 # Importe de la operación en euros
    'ESTADO_OPERACION',        # Si la operación es exitosa, fallida o cancelada
    'PAIS_ORIGEN',             # País de origen (todos serán España)
    'NOMBRE_ORDENANTE',        # Nombre de la persona que envía el importe
    'APELLIDO_ORDENANTE',      # Primer apellido de la persona que envía el importe
    'SEGUNDO_APELLIDO_ORDENANTE', # Segundo apellido de la persona que envía el importe
    'PAIS_DOC_ORDENANTE',      # País del documento de identidad de la persona que envía
    'NUM_DOC_ORDENANTE',       # Número de documento de identidad del ordenante
    'PAIS_NAC_ORDENANTE',      # País de nacimiento de la persona que envía el importe
    'FECHA_NAC_ORDENANTE',     # Fecha de nacimiento de la persona que envía el importe
    'es_Agente',               # Identifica si una persona que realiza envíos es además agente
    'es_PEP',                  # Identifica si la persona que envía es una PEP
    'NOMBRE_BENEFICIARIO',     # Nombre de la persona que recibe el importe
    'APELLIDO_BENEFICIARIO',   # Primer apellido de la persona que recibe el importe
    'SEGUNDO_APELLIDO_BENEFICIARIO', # Segundo apellido de la persona que recibe el importe
    'PAIS_DESTINO',            # País donde se remite el importe
    'ENT_TOW_CIT_RES',         # Ciudad donde se localiza el agente
    'ENT_COD_PAR_ENT',         # Número que identifica al sujeto obligado
    'ENT_NAT_REF_COD',         # Número que identifica al agente
]

# Agrupaciones de columnas por categoría
SENDER_COLUMNS = [
    'NOMBRE_ORDENANTE',
    'APELLIDO_ORDENANTE',
    'SEGUNDO_APELLIDO_ORDENANTE',
    'PAIS_DOC_ORDENANTE',
    'NUM_DOC_ORDENANTE',
    'PAIS_NAC_ORDENANTE',
    'FECHA_NAC_ORDENANTE',
    'es_PEP'
]

RECEIVER_COLUMNS = [
    'NOMBRE_BENEFICIARIO',
    'APELLIDO_BENEFICIARIO',
    'SEGUNDO_APELLIDO_BENEFICIARIO',
    'PAIS_DESTINO'
]

TRANSACTION_COLUMNS = [
    'NUMERO_TRANSACCION',
    'FECHA',
    'HORA',
    'IMPORTE',
    'ESTADO_OPERACION',
    'PAIS_ORIGEN'
]

AGENT_COLUMNS = [
    'ENT_TOW_CIT_RES',
    'ENT_COD_PAR_ENT',
    'ENT_NAT_REF_COD',
    'es_Agente'
]

# Mapeo de alias para columnas (por si se encuentran diferentes nombres para la misma información)
COLUMN_ALIASES = {
    'PAIS_NAC_ORDENANTE': ['PAIS_NACIMIENTO_ORDENANTE'],
    'NUM_DOC_ORDENANTE': ['DOCUMENTO_ORDENANTE', 'DOC_ORDENANTE'],
    'FECHA_NAC_ORDENANTE': ['FECHA_NACIMIENTO_ORDENANTE'],
    'PAIS_DOC_ORDENANTE': ['PAIS_DOCUMENTO_ORDENANTE'],
    'ENT_NAT_REF_COD': ['CODIGO_AGENTE', 'AGENT_ID'],
    'ENT_COD_PAR_ENT': ['CODIGO_ENTIDAD', 'SUBJECT_ID']
}

# Función para normalizar nombres de columnas
def normalize_column_name(column_name):
    """
    Normaliza el nombre de una columna según los alias definidos.
    
    Args:
        column_name: Nombre de columna a normalizar
        
    Returns:
        Nombre de columna normalizado
    """
    # Convertir a mayúsculas
    column_name = column_name.upper()
    
    # Verificar si es un nombre estándar
    if column_name in EXPECTED_COLUMNS:
        return column_name
        
    # Verificar si es un alias
    for standard_name, aliases in COLUMN_ALIASES.items():
        if column_name in aliases:
            return standard_name
            
    # Si no es reconocido, devolver el nombre original
    return column_name