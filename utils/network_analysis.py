import pandas as pd
import networkx as nx
from typing import Dict, List, Any, Optional, Set, Tuple, Union
import random
import colorsys
from collections import Counter


# Función para asignar color a un país
COUNTRY_COLORS = {}

def get_country_color(country_name):
    """
    Asigna un color aleatorio (pero fijo) a cada país.
    """
    if not country_name or pd.isna(country_name):
        return "#CCCCCC"  # Gris para países sin dato
    
    country_upper = str(country_name).strip().upper()
    if country_upper not in COUNTRY_COLORS:
        # Generar colores agradables, no completamente aleatorios
        hue = random.random()  # Entre 0 y 1
        saturation = 0.6 + random.random() * 0.3  # Entre 0.6 y 0.9
        value = 0.5 + random.random() * 0.3  # Entre 0.5 y 0.8
        
        # Convertir HSV a RGB
        h = hue * 6
        i = int(h)
        f = h - i
        p = value * (1 - saturation)
        q = value * (1 - f * saturation)
        t = value * (1 - (1 - f) * saturation)
        
        if i % 6 == 0:
            r, g, b = value, t, p
        elif i % 6 == 1:
            r, g, b = q, value, p
        elif i % 6 == 2:
            r, g, b = p, value, t
        elif i % 6 == 3:
            r, g, b = p, q, value
        elif i % 6 == 4:
            r, g, b = t, p, value
        else:
            r, g, b = value, p, q
        
        # Convertir a hexadecimal
        rgb = (int(r * 255), int(g * 255), int(b * 255))
        COUNTRY_COLORS[country_upper] = "#{:02x}{:02x}{:02x}".format(*rgb)
    
    return COUNTRY_COLORS[country_upper]


def get_community_name(community_id: int, nodes_in_community: List[Dict[str, Any]]) -> str:
    """
    Genera un nombre significativo para una comunidad basado en sus nodos.
    
    Args:
        community_id: ID de la comunidad
        nodes_in_community: Lista de nodos (como diccionarios) en esta comunidad
        
    Returns:
        Nombre descriptivo de la comunidad
    """
    # Si no hay nodos, usa un nombre genérico
    if not nodes_in_community:
        return f"Comunidad {community_id}"
    
    # Verificar que los elementos sean diccionarios, no strings
    if isinstance(nodes_in_community[0], str):
        return f"Comunidad {community_id} ({len(nodes_in_community)} participantes)"
    
    try:
        # Contar países en la comunidad con manejo de errores seguro
        country_counts = Counter()
        for node in nodes_in_community:
            if isinstance(node, dict) and 'country' in node:
                country_counts[node['country']] += 1
            else:
                country_counts['Desconocido'] += 1
        
        # Si hay un país predominante, úsalo en el nombre
        if country_counts:
            main_country = country_counts.most_common(1)[0][0]
            country_proportion = country_counts[main_country] / len(nodes_in_community)
            
            # Si más del 60% son del mismo país, nombra la comunidad por ese país
            if country_proportion > 0.6:
                return f"Comunidad {community_id}: {main_country} ({len(nodes_in_community)} participantes)"
        
        # Contar tipos de nodos (remitentes vs beneficiarios) con manejo de errores
        type_counts = Counter()
        for node in nodes_in_community:
            if isinstance(node, dict) and 'type' in node:
                type_counts[node['type']] += 1
            else:
                type_counts['unknown'] += 1
        
        # Nombrar según la composición de tipos
        senders = type_counts.get('sender', 0)
        beneficiaries = type_counts.get('beneficiary', 0)
        
        if senders > 0 and beneficiaries > 0:
            return f"Comunidad {community_id}: {senders} remitentes y {beneficiaries} beneficiarios"
        elif senders > 0:
            return f"Comunidad {community_id}: {senders} remitentes"
        elif beneficiaries > 0:
            return f"Comunidad {community_id}: {beneficiaries} beneficiarios"
    
    except Exception as e:
        print(f"Error al generar nombre de comunidad {community_id}: {e}")
    
    # Nombre por defecto en caso de error
    return f"Comunidad {community_id} ({len(nodes_in_community)} participantes)"


def detect_communities(G: nx.Graph, method: str = 'modularity') -> Dict[str, int]:
    """
    Detecta comunidades dentro de un grafo utilizando diferentes métodos.
    
    Args:
        G: Grafo de NetworkX para analizar
        method: Método de detección de comunidades, opciones:
                - 'modularity': Maximiza la modularidad (por defecto)
                - 'louvain': Usa el algoritmo Louvain para optimizar modularidad
                - 'label_propagation': Usa propagación de etiquetas (rápido)
                - 'girvan_newman': Usa el algoritmo Girvan-Newman (lento)
    
    Returns:
        Diccionario que mapea IDs de nodos a números de comunidad
    """
    # Convertir a no dirigido para algoritmos que lo requieren
    if G.is_directed():
        G_undirected = G.to_undirected()
    else:
        G_undirected = G
    
    community_map = {}
    
    try:
        if method == 'modularity':
            # Usar el algoritmo de modularidad para detectar comunidades
            communities = list(nx.algorithms.community.greedy_modularity_communities(G_undirected))
            
            # Asignar comunidad a cada nodo
            for i, community in enumerate(communities):
                for node_id in community:
                    community_map[node_id] = i
        
        elif method == 'louvain':
            # Intentar usar el algoritmo Louvain
            try:
                from community import best_partition
                partition = best_partition(G_undirected)
                community_map = partition
            except ImportError:
                # Si no está disponible, caer a modularidad
                communities = list(nx.algorithms.community.greedy_modularity_communities(G_undirected))
                for i, community in enumerate(communities):
                    for node_id in community:
                        community_map[node_id] = i
        
        elif method == 'label_propagation':
            # Usar propagación de etiquetas
            communities = list(nx.algorithms.community.label_propagation_communities(G_undirected))
            
            # Asignar comunidad a cada nodo
            for i, community in enumerate(communities):
                for node_id in community:
                    community_map[node_id] = i
        
        elif method == 'girvan_newman':
            # Usar Girvan-Newman (puede ser muy lento para grafos grandes)
            if len(G.nodes) <= 100:  # Limitar a grafos pequeños
                # Tomar K particiones (ajustar según necesidad)
                k = min(5, len(G.nodes) // 5) if len(G.nodes) >= 10 else 2
                communities_generator = nx.algorithms.community.girvan_newman(G_undirected)
                communities = list(next(communities_generator) for _ in range(k))[-1]  # Tomar la última partición
                
                # Asignar comunidad a cada nodo
                for i, community in enumerate(communities):
                    for node_id in community:
                        community_map[node_id] = i
            else:
                # Para grafos grandes, usar modularidad
                communities = list(nx.algorithms.community.greedy_modularity_communities(G_undirected))
                for i, community in enumerate(communities):
                    for node_id in community:
                        community_map[node_id] = i
        
        else:
            # Método desconocido, usar modularidad por defecto
            communities = list(nx.algorithms.community.greedy_modularity_communities(G_undirected))
            for i, community in enumerate(communities):
                for node_id in community:
                    community_map[node_id] = i
    
    except Exception as e:
        print(f"Error en detección de comunidades con método {method}: {e}")
        # Si hay error, intentar el método más simple
        try:
            communities = list(nx.algorithms.community.label_propagation_communities(G_undirected))
            for i, community in enumerate(communities):
                for node_id in community:
                    community_map[node_id] = i
        except Exception:
            # Si todo falla, asignar una comunidad a cada nodo
            for i, node_id in enumerate(G.nodes()):
                community_map[node_id] = 0
    
    return community_map


def create_transaction_graph(
    df: pd.DataFrame, 
    min_amount: float = 0,
    destination_countries: List[str] = None,
    document_countries: List[str] = None,
    community_method: str = 'modularity'
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Create a network graph representation of transactions.
    
    Args:
        df: DataFrame with transaction data
        min_amount: Minimum transaction amount to include
        destination_countries: Optional list of countries to filter destination countries
        document_countries: Optional list of countries to filter document issuer countries
        community_method: Method for community detection ('modularity', 'louvain', 'label_propagation', 'girvan_newman')
        
    Returns:
        Dictionary with 'nodes' and 'edges' for visualization
    """
    if df.empty:
        return {'nodes': [], 'edges': []}
    
    # Create a copy of the dataframe
    df_graph = df.copy()
    
    # Ensure we have required columns
    required_cols = [
        'NUM_DOC_ORDENANTE', 'NOMBRE_ORDENANTE', 'APELLIDO_ORDENANTE',
        'NOMBRE_BENEFICIARIO', 'APELLIDO_BENEFICIARIO', 
        'IMPORTE', 'PAIS_DESTINO'
    ]
    
    missing_cols = [col for col in required_cols if col not in df_graph.columns]
    if missing_cols:
        print(f"Warning: Missing columns for graph analysis: {missing_cols}")
        return {'nodes': [], 'edges': []}
    
    # Filtrar por importe mínimo si se especifica
    if min_amount > 0:
        df_graph = df_graph[df_graph['IMPORTE'] >= min_amount]
        if df_graph.empty:
            return {'nodes': [], 'edges': []}
    
    # Aplicar filtros por país destino si se especifica
    if destination_countries and len(destination_countries) > 0:
        df_graph = df_graph[df_graph['PAIS_DESTINO'].isin(destination_countries)]
        if df_graph.empty:
            return {'nodes': [], 'edges': []}
    
    # Aplicar filtros por país documento ordenante si se especifica
    if document_countries and len(document_countries) > 0:
        df_graph = df_graph[df_graph['PAIS_DOC_ORDENANTE'].isin(document_countries)]
        if df_graph.empty:
            return {'nodes': [], 'edges': []}
    
    # Completar campos faltantes
    for col in ['SEGUNDO_APELLIDO_ORDENANTE', 'SEGUNDO_APELLIDO_BENEFICIARIO']:
        if col not in df_graph.columns:
            df_graph[col] = ""
    
    # Crear identificadores únicos asegurando que no haya valores nulos
    try:
        # Ordenantes: usar 'NUM_DOC_ORDENANTE' si está disponible
        if 'NUM_DOC_ORDENANTE' in df_graph.columns:
            # Asegurar que el documento no sea nulo
            df_graph['NUM_DOC_ORDENANTE'] = df_graph['NUM_DOC_ORDENANTE'].fillna('doc_desconocido')
            df_graph['ORDENANTE_ID'] = "O_" + df_graph['NUM_DOC_ORDENANTE'].astype(str)
        else:
            # Si no hay documento, usar nombre+apellido
            df_graph['ORDENANTE_ID'] = "O_" + df_graph['NOMBRE_ORDENANTE'].fillna('') + "_" + df_graph['APELLIDO_ORDENANTE'].fillna('')
    except Exception as e:
        print(f"Error al crear IDs de ordenantes: {e}")
        # ID de fallback
        df_graph['ORDENANTE_ID'] = ["O_" + str(i) for i in range(len(df_graph))]
    
    # Etiquetas para ordenantes (con manejo de errores)
    try:    
        df_graph['ORDENANTE_LABEL'] = df_graph['NOMBRE_ORDENANTE'].fillna('') + ' ' + df_graph['APELLIDO_ORDENANTE'].fillna('')
        if 'SEGUNDO_APELLIDO_ORDENANTE' in df_graph.columns:
            valid_segundo = df_graph['SEGUNDO_APELLIDO_ORDENANTE'].notna() & (df_graph['SEGUNDO_APELLIDO_ORDENANTE'] != "")
            df_graph.loc[valid_segundo, 'ORDENANTE_LABEL'] += ' ' + df_graph.loc[valid_segundo, 'SEGUNDO_APELLIDO_ORDENANTE']
    except Exception as e:
        print(f"Error al crear etiquetas de ordenantes: {e}")
        df_graph['ORDENANTE_LABEL'] = df_graph['ORDENANTE_ID']
    
    # Crear ID único para beneficiarios con manejo de errores
    try:
        # Asegurar que tengamos nombres y apellidos (incluso vacíos)
        for col in ['NOMBRE_BENEFICIARIO', 'APELLIDO_BENEFICIARIO', 'SEGUNDO_APELLIDO_BENEFICIARIO']:
            if col not in df_graph.columns:
                df_graph[col] = ""
                
        # Crear ID combinando nombre y apellidos
        df_graph['BENEFICIARIO_ID'] = df_graph.apply(
            lambda row: f"B_{row['NOMBRE_BENEFICIARIO']}_{row['APELLIDO_BENEFICIARIO']}_{row.get('SEGUNDO_APELLIDO_BENEFICIARIO', '')}",
            axis=1
        )
        
        # Limpiar IDs para asegurar que sean válidos
        df_graph['BENEFICIARIO_ID'] = df_graph['BENEFICIARIO_ID'].str.replace(r'[^\w\s]', '', regex=True)
        df_graph['BENEFICIARIO_ID'] = df_graph['BENEFICIARIO_ID'].str.replace(r'_+', '_', regex=True).str.strip('_')
        
        # Detectar y manejar beneficiarios vacíos
        beneficiario_vacio = (df_graph['BENEFICIARIO_ID'].isin(["B__", "B_"]) | 
                             df_graph['BENEFICIARIO_ID'].isna() | 
                             (df_graph['BENEFICIARIO_ID'] == ""))
        # Asignar ID único basado en el índice para los vacíos
        df_graph.loc[beneficiario_vacio, 'BENEFICIARIO_ID'] = ["B_" + str(i) for i in range(sum(beneficiario_vacio))]
    except Exception as e:
        print(f"Error al crear IDs de beneficiarios: {e}")
        # ID de fallback
        df_graph['BENEFICIARIO_ID'] = ["B_" + str(i) for i in range(len(df_graph))]
    
    # Crear etiquetas para beneficiarios con manejo de errores
    try:
        df_graph['BENEFICIARIO_LABEL'] = df_graph['NOMBRE_BENEFICIARIO'].fillna('') + ' ' + df_graph['APELLIDO_BENEFICIARIO'].fillna('')
        if 'SEGUNDO_APELLIDO_BENEFICIARIO' in df_graph.columns:
            valid_segundo = df_graph['SEGUNDO_APELLIDO_BENEFICIARIO'].notna() & (df_graph['SEGUNDO_APELLIDO_BENEFICIARIO'] != "")
            df_graph.loc[valid_segundo, 'BENEFICIARIO_LABEL'] += ' ' + df_graph.loc[valid_segundo, 'SEGUNDO_APELLIDO_BENEFICIARIO']
        # Si la etiqueta quedó vacía, usar el ID
        df_graph.loc[df_graph['BENEFICIARIO_LABEL'].str.strip() == '', 'BENEFICIARIO_LABEL'] = df_graph.loc[df_graph['BENEFICIARIO_LABEL'].str.strip() == '', 'BENEFICIARIO_ID']
    except Exception as e:
        print(f"Error al crear etiquetas de beneficiarios: {e}")
        df_graph['BENEFICIARIO_LABEL'] = df_graph['BENEFICIARIO_ID']
    
    # Calcular totales por ordenante y beneficiario
    total_enviado = df_graph.groupby('ORDENANTE_ID')['IMPORTE'].sum().to_dict()
    total_recibido = df_graph.groupby('BENEFICIARIO_ID')['IMPORTE'].sum().to_dict()
    
    # Crear grafo dirigido
    G = nx.DiGraph()
    
    # Añadir nodos de ordenantes
    for _, row in df_graph[['ORDENANTE_ID', 'ORDENANTE_LABEL', 'NUM_DOC_ORDENANTE', 'PAIS_DOC_ORDENANTE']].drop_duplicates().iterrows():
        ordenante_id = row['ORDENANTE_ID']
        pais = row.get('PAIS_DOC_ORDENANTE', 'Desconocido')
        G.add_node(
            ordenante_id,
            label=row['ORDENANTE_LABEL'],
            type='sender',
            value=float(total_enviado.get(ordenante_id, 0)),
            transactions=len(df_graph[df_graph['ORDENANTE_ID'] == ordenante_id]),
            country=pais,
            color=get_country_color(pais),
            documento=row['NUM_DOC_ORDENANTE']
        )
    
    # Añadir nodos de beneficiarios
    for _, row in df_graph[['BENEFICIARIO_ID', 'BENEFICIARIO_LABEL', 'PAIS_DESTINO']].drop_duplicates().iterrows():
        beneficiario_id = row['BENEFICIARIO_ID']
        pais = row.get('PAIS_DESTINO', 'Desconocido')
        G.add_node(
            beneficiario_id,
            label=row['BENEFICIARIO_LABEL'],
            type='beneficiary',
            value=float(total_recibido.get(beneficiario_id, 0)),
            transactions=len(df_graph[df_graph['BENEFICIARIO_ID'] == beneficiario_id]),
            country=pais,
            color=get_country_color(pais)
        )
    
    # Añadir aristas (agrupadas por ordenante-beneficiario)
    grouped = df_graph.groupby(['ORDENANTE_ID', 'BENEFICIARIO_ID']).agg({
        'IMPORTE': 'sum',
        'NUMERO_TRANSACCION': 'count'
    }).reset_index()
    
    for _, row in grouped.iterrows():
        G.add_edge(
            row['ORDENANTE_ID'],
            row['BENEFICIARIO_ID'],
            value=float(row['IMPORTE']),
            transactions=int(row['NUMERO_TRANSACCION']),
            title=f"Importe: {float(row['IMPORTE']):.2f} EUR, {int(row['NUMERO_TRANSACCION'])} transacciones"
        )
    
    # Aplicar detección de comunidades si hay suficientes nodos
    if len(G.nodes) > 3:
        try:
            # Usar el método de detección de comunidades especificado
            community_map = detect_communities(G, method=community_method)
            
            # Actualizar atributos de los nodos con verificación de tipos
            for node_id in G.nodes:
                if node_id in community_map and isinstance(community_map, dict):
                    G.nodes[node_id]['group'] = community_map[node_id]
            
            # Guardar el método usado para referencia
            for node_id in G.nodes:
                G.nodes[node_id]['community_method'] = community_method
                
        except Exception as e:
            print(f"Error en detección de comunidades con método {community_method}: {e}")
    
    # Generar listas para visualización
    nodes = []
    for node_id, attrs in G.nodes(data=True):
        node_data = attrs.copy()
        node_data['id'] = node_id
        nodes.append(node_data)
    
    # Verificar que cada comunidad tenga al menos un remitente y un beneficiario
    # Paso 1: Crear el diccionario de comunidades con información detallada
    community_dict = {}
    for node in nodes:
        # Verificar que node sea un diccionario y que tenga un atributo 'group'
        if not isinstance(node, dict):
            continue
            
        community_id = node.get('group')
        if community_id is not None:
            if community_id not in community_dict:
                community_dict[community_id] = {
                    'nodes': [],
                    'remitentes': [],
                    'beneficiarios': [],
                    'transacciones': 0,  # Contador de transacciones
                    'countries': set(),  # Países involucrados
                    'total_value': 0.0   # Valor total
                }
            
            # Añadir nodo a la lista correspondiente
            community_dict[community_id]['nodes'].append(node)
            
            # Clasificar por tipo y añadir información adicional
            # Verificación de tipo de nodo - asegurar que es un diccionario
            if isinstance(node, dict):
                node_type = node.get('type')
                if node_type == 'sender':
                    community_dict[community_id]['remitentes'].append(node)
                elif node_type == 'beneficiary':
                    community_dict[community_id]['beneficiarios'].append(node)
                
                # Añadir país a la colección si existe
                if isinstance(node, dict) and 'country' in node and node['country']:
                    community_dict[community_id]['countries'].add(node['country'])
            
            # Sumar el valor del nodo con verificación de tipo
            if isinstance(node, dict) and 'value' in node:
                try:
                    node_value = node['value']
                    if node_value is not None:
                        community_dict[community_id]['total_value'] += float(node_value)
                except (ValueError, TypeError):
                    pass
            
            # Contar transacciones con verificación de tipo
            if isinstance(node, dict) and 'transactions' in node:
                try:
                    node_transactions = node['transactions']
                    if node_transactions is not None:
                        community_dict[community_id]['transacciones'] += int(node_transactions)
                except (ValueError, TypeError):
                    pass
    
    # Generar la lista de aristas
    edges = []
    for source, target, attrs in G.edges(data=True):
        edge_data = attrs.copy()
        edge_data['source'] = source
        edge_data['target'] = target
        edges.append(edge_data)
    
    # Paso 2: Verificar aristas para contar transacciones entre nodos de la misma comunidad
    for edge in edges:
        # Verificar que edge sea un diccionario
        if not isinstance(edge, dict):
            continue
            
        source = edge.get('source')
        target = edge.get('target')
        
        # Verificar que source y target sean válidos
        if source is None or target is None:
            continue
            
        # Encontrar comunidad del origen y destino
        source_community = None
        target_community = None
        
        for node in nodes:
            # Verificar que node sea un diccionario
            if not isinstance(node, dict):
                continue
                
            node_id = node.get('id')
            
            if node_id == source:
                source_community = node.get('group')
            elif node_id == target:
                target_community = node.get('group')
                
            if source_community is not None and target_community is not None:
                break
        
        # Si ambos están en la misma comunidad, añadir las transacciones
        if (source_community is not None and 
            target_community is not None and 
            source_community == target_community and 
            source_community in community_dict):
            
            if 'transactions' in edge and edge['transactions'] is not None:
                try:
                    community_dict[source_community]['transacciones'] += int(edge['transactions'])
                except (ValueError, TypeError, KeyError):
                    pass
    
    # Paso 3: Reasignar nodos en comunidades que no cumplen los requisitos
    valid_communities = {}
    reassigned_nodes = []
    
    # Criterios completos para considerar válida a una comunidad:
    # 1. Debe tener al menos un remitente y un beneficiario
    # 2. Debe tener al menos una transacción registrada
    for community_id, community_data in community_dict.items():
        if (len(community_data['remitentes']) > 0 and 
            len(community_data['beneficiarios']) > 0 and
            community_data['transacciones'] > 0):
            # Comunidad válida - la mantenemos
            valid_communities[community_id] = community_data
        else:
            # Comunidad inválida - sus nodos serán reasignados
            for node in community_data['nodes']:
                # Marcar para reasignación
                node['needs_reassignment'] = True
                reassigned_nodes.append(node)
    
    # Paso 4: Reasignar nodos a comunidades válidas o crear nueva comunidad
    if reassigned_nodes:
        if valid_communities:
            # Si hay comunidades válidas, reasignar nodos a la más grande o más activa
            # Preferimos comunidades con más transacciones
            largest_community_id = max(valid_communities.keys(), 
                                     key=lambda k: valid_communities[k]['transacciones'] * 10 + len(valid_communities[k]['nodes']))
            
            for node in reassigned_nodes:
                node['group'] = largest_community_id
                valid_communities[largest_community_id]['nodes'].append(node)
                
                # Actualizar clasificación del nodo
                if node.get('type') == 'sender':
                    valid_communities[largest_community_id]['remitentes'].append(node)
                else:
                    valid_communities[largest_community_id]['beneficiarios'].append(node)
                
                # Eliminar marca de reasignación
                if 'needs_reassignment' in node:
                    del node['needs_reassignment']
        else:
            # Si no hay comunidades válidas, crear una nueva comunidad mixta
            # Esto es una situación extrema que no debería ocurrir si hay datos válidos
            new_community_id = 1  # Usar un ID numérico consistente
            
            # Crear la nueva comunidad
            valid_communities[new_community_id] = {
                'nodes': [],
                'remitentes': [],
                'beneficiarios': [],
                'transacciones': 1,  # Mínimo para ser válida
                'countries': set(),
                'total_value': 0.0
            }
            
            for node in reassigned_nodes:
                node['group'] = new_community_id
                valid_communities[new_community_id]['nodes'].append(node)
                
                # Actualizar clasificación del nodo
                if node.get('type') == 'sender':
                    valid_communities[new_community_id]['remitentes'].append(node)
                else:
                    valid_communities[new_community_id]['beneficiarios'].append(node)
                
                # Añadir país si existe
                if 'country' in node and node['country']:
                    valid_communities[new_community_id]['countries'].add(node['country'])
                
                # Actualizar valor total
                if 'value' in node:
                    try:
                        valid_communities[new_community_id]['total_value'] += float(node['value'])
                    except (ValueError, TypeError):
                        pass
                
                # Eliminar marca de reasignación
                if 'needs_reassignment' in node:
                    del node['needs_reassignment']
    
    # Asignar nombres descriptivos a cada comunidad
    community_names = {}
    for community_id, community_data in valid_communities.items():
        try:
            # Usar los nodos de la comunidad para generar el nombre
            nodes_in_community = community_data.get('nodes', [])
            
            # Verificar que haya nodos para nombrar la comunidad
            if not nodes_in_community:
                community_names[community_id] = f"Comunidad {community_id}"
                continue
                
            # Generar nombre usando los nodos válidos
            community_names[community_id] = get_community_name(community_id, nodes_in_community)
        except Exception as e:
            print(f"Error al nombrar comunidad {community_id}: {str(e)}")
            community_names[community_id] = f"Comunidad {community_id}"
    
    # Añadir nombres de comunidades a cada nodo
    for node in nodes:
        try:
            community_id = node.get('group')
            if community_id is not None and community_id in community_names:
                node['community_name'] = community_names[community_id]
            else:
                # Asignar nombre genérico si no tiene comunidad asignada
                node['community_name'] = "Sin comunidad"
        except Exception as e:
            print(f"Error al asignar nombre de comunidad al nodo: {str(e)}")
            node['community_name'] = "Sin comunidad"
    
    edges = []
    for source, target, attrs in G.edges(data=True):
        edge_data = attrs.copy()
        edge_data['source'] = source
        edge_data['target'] = target
        edges.append(edge_data)
    
    # Añadir IDs de transacciones a las aristas para mejor análisis
    df_txns = {}
    for _, row in df_graph.iterrows():
        # Generar identificadores para ordenante y beneficiario basados en nombres completos
        # Si no hay ORDENANTE_ID/BENEFICIARIO_ID, crear uno a partir del nombre completo
        if 'ORDENANTE_ID' not in row or pd.isna(row['ORDENANTE_ID']):
            ordenante_nombre = ' '.join([
                str(row.get('NOMBRE_ORDENANTE', '')), 
                str(row.get('APELLIDO_ORDENANTE', ''))
            ]).strip()
            ordenante_id = 'ord_' + ''.join(ordenante_nombre.split())[:20]  # ID basado en nombre
        else:
            ordenante_id = row['ORDENANTE_ID']
            
        if 'BENEFICIARIO_ID' not in row or pd.isna(row['BENEFICIARIO_ID']):
            beneficiario_nombre = ' '.join([
                str(row.get('NOMBRE_BENEFICIARIO', '')), 
                str(row.get('APELLIDO_BENEFICIARIO', ''))
            ]).strip()
            beneficiario_id = 'ben_' + ''.join(beneficiario_nombre.split())[:20]  # ID basado en nombre
        else:
            beneficiario_id = row['BENEFICIARIO_ID']
            
        # Usar los identificadores generados
        key = (str(ordenante_id), str(beneficiario_id))
        if key not in df_txns:
            df_txns[key] = []
        
        # Añadir ID de transacción si existe
        if 'NUMERO_TRANSACCION' in row and pd.notna(row['NUMERO_TRANSACCION']):
            df_txns[key].append(str(row['NUMERO_TRANSACCION']))
    
    # Actualizar las aristas con las IDs de transacciones
    for edge in edges:
        key = (str(edge['source']), str(edge['target']))
        if key in df_txns:
            edge['transaction_ids'] = df_txns[key]
    
    # Paso 6: Recopilar datos detallados de cada comunidad válida para la exportación
    community_list = []
    for community_id, community_data in valid_communities.items():
        # Convertir set de países a lista para JSON
        countries_list = list(community_data['countries']) if isinstance(community_data['countries'], set) else []
        
        # Recopilar todos los IDs de transacciones que pertenecen a esta comunidad
        transaction_ids = set()
        ordered_transactions = []
        
        # Recopilar ordenantes y beneficiarios para la exportación
        ordenantes_list = [node.get('label', 'Sin nombre') for node in community_data['remitentes']]
        beneficiarios_list = [node.get('label', 'Sin nombre') for node in community_data['beneficiarios']]
        
        # Recopilar datos de transacciones para esta comunidad
        community_transactions = []
        
        # Buscar en las aristas las transacciones entre nodos de esta comunidad
        for edge in edges:
            source = edge.get('source')
            target = edge.get('target')
            
            # Verificar si ambos nodos pertenecen a esta comunidad
            source_in_community = False
            target_in_community = False
            
            for node in community_data['nodes']:
                if node.get('id') == source:
                    source_in_community = True
                if node.get('id') == target:
                    target_in_community = True
            
            if source_in_community and target_in_community:
                # Añadir IDs de transacciones
                if 'transaction_ids' in edge:
                    for trans_id in edge['transaction_ids']:
                        transaction_ids.add(trans_id)
                        
                # Buscar datos completos de las transacciones en el DataFrame original
                source_rows = df_graph[(df_graph['ORDENANTE_ID'] == source) & 
                                       (df_graph['BENEFICIARIO_ID'] == target)]
                
                for _, row in source_rows.iterrows():
                    # Crear registro de transacción para exportación
                    trans_record = {
                        'Fecha': row.get('FECHA_OPERACION', ''),
                        'Importe': float(row.get('IMPORTE', 0)),
                        'ID_Transaccion': str(row.get('NUMERO_TRANSACCION', '')),
                        'Remitente': row.get('ORDENANTE_LABEL', ''),
                        'Beneficiario': row.get('BENEFICIARIO_LABEL', ''),
                        'Pais_Origen': row.get('PAIS_DOC_ORDENANTE', ''),
                        'Pais_Destino': row.get('PAIS_DESTINO', '')
                    }
                    community_transactions.append(trans_record)
                    ordered_transactions.append(str(row.get('NUMERO_TRANSACCION', '')))
        
        # Crear entrada de comunidad con datos completos
        community_entry = {
            'id': community_id,
            'name': community_names.get(community_id, f"Comunidad {community_id}"),
            'nodes': len(community_data['nodes']),
            'senders': len(community_data['remitentes']),
            'beneficiaries': len(community_data['beneficiarios']),
            'transactions': community_data['transacciones'],
            'total_value': community_data['total_value'],
            'countries': countries_list,
            'transaction_data': community_transactions,
            'trans_id_list': ", ".join(ordered_transactions) if ordered_transactions else "",
            'ordenantes_list': ", ".join(ordenantes_list) if ordenantes_list else "",
            'beneficiarios_list': ", ".join(beneficiarios_list) if beneficiarios_list else ""
        }
        
        community_list.append(community_entry)
    
    # Verificación final: no permitir comunidades sin transacciones o beneficiarios
    valid_community_list = [
        comm for comm in community_list 
        if comm['senders'] > 0 and comm['beneficiaries'] > 0 and comm['transactions'] > 0
    ]
    
    # Si todas las comunidades fueron filtradas, restaurar al menos una con datos mínimos
    if not valid_community_list and len(nodes) > 1:
        # Crear una comunidad general con todos los nodos
        sender_nodes = [n for n in nodes if n.get('type') == 'sender']
        beneficiary_nodes = [n for n in nodes if n.get('type') == 'beneficiary']
        
        if sender_nodes and beneficiary_nodes:
            # Obtener información básica de las transacciones
            transaction_count = sum(1 for e in edges if 'transactions' in e and e['transactions'] > 0)
            total_value = sum(float(e.get('value', 0)) for e in edges)
            
            # Crear comunidad general
            general_community = {
                'id': 1,
                'name': 'Comunidad general',
                'nodes': len(nodes),
                'senders': len(sender_nodes),
                'beneficiaries': len(beneficiary_nodes),
                'transactions': max(transaction_count, 1),  # Al menos 1 transacción
                'total_value': total_value,
                'countries': list(set(n.get('country', 'Desconocido') for n in nodes if 'country' in n)),
                'transaction_data': [{'Importe': total_value, 'Fecha': ''}],
                'trans_id_list': '',
                'ordenantes_list': ", ".join(n.get('label', '') for n in sender_nodes),
                'beneficiarios_list': ", ".join(n.get('label', '') for n in beneficiary_nodes)
            }
            valid_community_list.append(general_community)
    
    # Incluir toda la información en el resultado para facilitar la exportación
    return {
        'nodes': nodes,
        'edges': edges,
        'communities': [
            {'id': community_id, 'name': name}
            for community_id, name in community_names.items()
        ],
        'community_list': valid_community_list  # Lista completa de comunidades con datos detallados
    }