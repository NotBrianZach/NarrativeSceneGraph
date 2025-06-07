"""Serialization functionality for converting graphs to DOT format."""
import logging
from typing import Dict
import re

logger = logging.getLogger(__name__)


def sanitize_id(node_id: str) -> str:
    """
    Sanitize node ID to be valid in DOT format.
    
    Args:
        node_id: Raw node identifier
        
    Returns:
        Sanitized identifier safe for DOT
    """
    # Replace invalid characters with underscores
    sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', node_id)
    
    # Ensure it starts with a letter or underscore
    if sanitized and not (sanitized[0].isalpha() or sanitized[0] == '_'):
        sanitized = f"node_{sanitized}"
    
    return sanitized or "node_unknown"


def escape_label(label: str) -> str:
    """
    Escape label text for DOT format.
    
    Args:
        label: Raw label text
        
    Returns:
        Escaped label safe for DOT
    """
    # Escape quotes and backslashes
    escaped = label.replace('\\', '\\\\').replace('"', '\\"')
    
    # Replace newlines with \\n for DOT
    escaped = escaped.replace('\n', '\\n')
    
    # Truncate very long labels
    if len(escaped) > 100:
        escaped = escaped[:97] + "..."
    
    return escaped


def to_dot(graph: Dict, title: str = "NarrativeGraph") -> str:
    """
    Convert a narrative graph to DOT format.
    
    Args:
        graph: Graph dictionary with 'nodes' and 'edges' keys
        title: Title for the graph
        
    Returns:
        DOT format string representation of the graph
    """
    nodes = graph.get('nodes', [])
    edges = graph.get('edges', [])
    
    # Start DOT graph
    dot_lines = [
        f'digraph {sanitize_id(title)} {{',
        '    rankdir=TB;',
        '    node [shape=box, style=rounded];',
        '    edge [fontsize=10];',
        ''
    ]
    
    # Add nodes
    dot_lines.append('    // Nodes')
    for node in nodes:
        node_id = sanitize_id(node['id'])
        label = escape_label(node['label'])
        
        # Determine node shape based on position or content
        shape = 'ellipse'  # Default shape
        if 'scene_1' in node['id']:
            shape = 'doublecircle'  # Start node
        elif node == nodes[-1]:  # Last node
            shape = 'doublecircle'  # End node
        
        dot_lines.append(f'    {node_id} [label="{label}", shape={shape}];')
    
    dot_lines.append('')
    
    # Add edges
    dot_lines.append('    // Edges')
    for edge in edges:
        source_id = sanitize_id(edge['source'])
        target_id = sanitize_id(edge['target'])
        edge_label = escape_label(edge.get('label', ''))
        
        if edge_label:
            dot_lines.append(f'    {source_id} -> {target_id} [label="{edge_label}"];')
        else:
            dot_lines.append(f'    {source_id} -> {target_id};')
    
    # Close graph
    dot_lines.append('}')
    
    dot_content = '\n'.join(dot_lines)
    
    logger.info(f"Generated DOT graph with {len(nodes)} nodes and {len(edges)} edges")
    return dot_content


def to_dot_with_clustering(graph: Dict, title: str = "NarrativeGraph") -> str:
    """
    Convert a narrative graph to DOT format with scene clustering.
    
    This version groups related scenes into visual clusters for better readability.
    
    Args:
        graph: Graph dictionary with 'nodes' and 'edges' keys
        title: Title for the graph
        
    Returns:
        DOT format string representation with clustering
    """
    nodes = graph.get('nodes', [])
    edges = graph.get('edges', [])
    
    # Start DOT graph
    dot_lines = [
        f'digraph {sanitize_id(title)} {{',
        '    rankdir=TB;',
        '    compound=true;',
        '    node [shape=box, style=rounded];',
        '    edge [fontsize=10];',
        ''
    ]
    
    # Group nodes into clusters (every 3-5 scenes)
    cluster_size = 4
    clusters = [nodes[i:i + cluster_size] for i in range(0, len(nodes), cluster_size)]
    
    # Add clustered nodes
    for cluster_idx, cluster_nodes in enumerate(clusters):
        if len(clusters) > 1:  # Only create clusters if we have multiple groups
            dot_lines.append(f'    subgraph cluster_{cluster_idx} {{')
            dot_lines.append(f'        label="Chapter {cluster_idx + 1}";')
            dot_lines.append('        style=dashed;')
            dot_lines.append('')
        
        for node in cluster_nodes:
            node_id = sanitize_id(node['id'])
            label = escape_label(node['label'])
            
            # Determine node shape
            shape = 'ellipse'
            if 'scene_1' in node['id']:
                shape = 'doublecircle'
            elif node == nodes[-1]:
                shape = 'doublecircle'
            
            if len(clusters) > 1:
                dot_lines.append(f'        {node_id} [label="{label}", shape={shape}];')
            else:
                dot_lines.append(f'    {node_id} [label="{label}", shape={shape}];')
        
        if len(clusters) > 1:
            dot_lines.append('    }')
            dot_lines.append('')
    
    # Add edges
    dot_lines.append('    // Edges')
    for edge in edges:
        source_id = sanitize_id(edge['source'])
        target_id = sanitize_id(edge['target'])
        edge_label = escape_label(edge.get('label', ''))
        
        if edge_label:
            dot_lines.append(f'    {source_id} -> {target_id} [label="{edge_label}"];')
        else:
            dot_lines.append(f'    {source_id} -> {target_id};')
    
    # Close graph
    dot_lines.append('}')
    
    dot_content = '\n'.join(dot_lines)
    
    logger.info(f"Generated clustered DOT graph with {len(nodes)} nodes and {len(edges)} edges")
    return dot_content 