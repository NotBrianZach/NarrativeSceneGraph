"""Coordinate generation for Twine node positioning."""
import random
import math
from typing import Dict, List, Tuple


def assign_random_coordinates(graph: Dict, 
                            canvas_width: int = 4000, 
                            canvas_height: int = 3000,
                            min_distance: int = 200,
                            seed: int = None) -> Dict:
    """
    Assign random 2D coordinates to graph nodes for Twine visualization.
    
    Args:
        graph: Graph dictionary with 'nodes' and 'edges'
        canvas_width: Width of the Twine canvas
        canvas_height: Height of the Twine canvas  
        min_distance: Minimum distance between nodes
        seed: Random seed for reproducible layouts
        
    Returns:
        Modified graph with coordinates added to nodes
    """
    if seed is not None:
        random.seed(seed)
    
    nodes = graph.get('nodes', [])
    if not nodes:
        return graph
    
    # Generate coordinates with collision avoidance
    coordinates = []
    max_attempts = 1000
    
    for i, node in enumerate(nodes):
        attempts = 0
        while attempts < max_attempts:
            x = random.randint(100, canvas_width - 100)
            y = random.randint(100, canvas_height - 100)
            
            # Check distance from existing coordinates
            valid = True
            for existing_x, existing_y in coordinates:
                distance = math.sqrt((x - existing_x) ** 2 + (y - existing_y) ** 2)
                if distance < min_distance:
                    valid = False
                    break
            
            if valid:
                coordinates.append((x, y))
                break
                
            attempts += 1
        
        # Fallback: use grid placement if random placement fails
        if attempts >= max_attempts:
            grid_size = math.ceil(math.sqrt(len(nodes)))
            grid_x = (i % grid_size) * (canvas_width // grid_size)
            grid_y = (i // grid_size) * (canvas_height // grid_size)
            coordinates.append((grid_x + 100, grid_y + 100))
    
    # Add coordinates to nodes
    enhanced_nodes = []
    for i, node in enumerate(nodes):
        enhanced_node = dict(node)
        enhanced_node['position'] = {
            'x': coordinates[i][0],
            'y': coordinates[i][1]
        }
        enhanced_nodes.append(enhanced_node)
    
    # Return enhanced graph
    enhanced_graph = dict(graph)
    enhanced_graph['nodes'] = enhanced_nodes
    
    return enhanced_graph


def assign_flow_coordinates(graph: Dict,
                           canvas_width: int = 4000,
                           canvas_height: int = 3000) -> Dict:
    """
    Assign coordinates based on narrative flow for better readability.
    
    Arranges nodes in a top-to-bottom flow following the story progression.
    
    Args:
        graph: Graph dictionary with 'nodes' and 'edges'
        canvas_width: Width of the Twine canvas
        canvas_height: Height of the Twine canvas
        
    Returns:
        Modified graph with flow-based coordinates
    """
    nodes = graph.get('nodes', [])
    edges = graph.get('edges', [])
    
    if not nodes:
        return graph
    
    # Build adjacency information
    incoming = {node['id']: [] for node in nodes}
    outgoing = {node['id']: [] for node in nodes}
    
    for edge in edges:
        source, target = edge['source'], edge['target']
        if source in outgoing and target in incoming:
            outgoing[source].append(target)
            incoming[target].append(source)
    
    # Find start nodes (no incoming edges)
    start_nodes = [node_id for node_id in incoming if not incoming[node_id]]
    if not start_nodes:
        start_nodes = [nodes[0]['id']]  # Fallback to first node
    
    # Assign layers using BFS
    layers = []
    visited = set()
    current_layer = start_nodes[:]
    
    while current_layer:
        layers.append(current_layer)
        next_layer = []
        
        for node_id in current_layer:
            visited.add(node_id)
            for target in outgoing.get(node_id, []):
                if target not in visited and target not in next_layer:
                    next_layer.append(target)
        
        current_layer = next_layer
    
    # Add any unvisited nodes to final layer
    unvisited = [node['id'] for node in nodes if node['id'] not in visited]
    if unvisited:
        layers.append(unvisited)
    
    # Calculate positions
    enhanced_nodes = []
    node_lookup = {node['id']: node for node in nodes}
    
    for layer_idx, layer in enumerate(layers):
        y = (layer_idx + 1) * (canvas_height // (len(layers) + 1))
        
        for node_idx, node_id in enumerate(layer):
            x = (node_idx + 1) * (canvas_width // (len(layer) + 1))
            
            enhanced_node = dict(node_lookup[node_id])
            enhanced_node['position'] = {'x': x, 'y': y}
            enhanced_nodes.append(enhanced_node)
    
    # Return enhanced graph
    enhanced_graph = dict(graph)
    enhanced_graph['nodes'] = enhanced_nodes
    
    return enhanced_graph 