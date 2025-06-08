"""Twine/Twee export functionality for narrative graphs."""
import logging
from typing import Dict, TextIO
from pathlib import Path
import json
import uuid

logger = logging.getLogger(__name__)


def sanitize_passage_name(name: str) -> str:
    """
    Sanitize passage name for Twee format, preserving spaces.
    
    Args:
        name: Raw passage name
    Returns:
        Sanitized passage name safe for Twee
    """
    # Replace newlines and tabs with spaces and remove quotes
    cleaned = name.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
    cleaned = cleaned.replace('"', '').replace("'", '')

    # Remove characters Twine cannot handle
    # Allow letters, digits, spaces, hyphens, underscores
    import re
    sanitized = re.sub(r'[^a-zA-Z0-9 \-_]', '_', cleaned)
    
    # Collapse multiple spaces
    sanitized = re.sub(r' {2,}', ' ', sanitized).strip()
    
    # Truncate overly long names
    if len(sanitized) > 50:
        sanitized = sanitized[:47] + '...'
    
    return sanitized or 'unnamed_passage'


def escape_twee_content(content: str) -> str:
    """
    Escape content for Twee format.
    
    Args:
        content: Raw text content
        
    Returns:
        Escaped content safe for Twee
    """
    # Basic escaping - Twee is fairly permissive
    # but we should handle some edge cases
    escaped = content.replace('[[', '\\[\\[').replace(']]', '\\]\\]')
    
    # Clean up excessive whitespace
    lines = escaped.split('\n')
    cleaned_lines = []
    for line in lines:
        cleaned_line = line.strip()
        if cleaned_line:
            cleaned_lines.append(cleaned_line)
    
    return '\n'.join(cleaned_lines)


def write_twee(graph: Dict, output_path: str, story_title: str = "Generated Story") -> None:
    """
    Write a narrative graph to Twee 3 format.
    
    Args:
        graph: Graph dictionary with 'nodes' and 'edges'
        output_path: Path to write the .twee file
        story_title: Title for the Twine story
    """
    nodes = graph.get('nodes', [])
    edges = graph.get('edges', [])
    
    if not nodes:
        raise ValueError("Graph contains no nodes")
    
    # Build outgoing edge lookup
    outgoing_edges = {}
    for edge in edges:
        source = edge['source']
        if source not in outgoing_edges:
            outgoing_edges[source] = []
        outgoing_edges[source].append(edge)
    
    # Start writing the Twee file
    with open(output_path, 'w', encoding='utf-8') as f:
        # (Removed JSON header for direct Twine GUI import)
        # First passage will be the starting passage by default
        pass
        
        # Write each passage (no metadata header)
        for node in nodes:
            node_id = node['id']
            passage_name = sanitize_passage_name(node['label'])
            content = escape_twee_content(node['text'])
            
            # Add position metadata if available
            position_data = ""
            if 'position' in node:
                pos = node['position']
                position_data = f' <{pos["x"]},{pos["y"]}>'
            
            # Write passage header
            f.write(f":: {passage_name}{position_data}\n\n")
            
            # Write passage content
            f.write(content)
            f.write("\n\n")
            
            # Add links to connected passages
            connected_edges = outgoing_edges.get(node_id, [])
            if connected_edges:
                f.write("---\n\n")
                for edge in connected_edges:
                    target_node = next((n for n in nodes if n['id'] == edge['target']), None)
                    if target_node:
                        target_name = sanitize_passage_name(target_node['label'])
                        link_text = edge.get('label', 'Continue')
                        f.write(f"[[{link_text}|{target_name}]]\n")
                
                f.write("\n")
            
            # Add spacing between passages
            f.write("\n")
    
    logger.info(f"Wrote Twee file with {len(nodes)} passages to {output_path}")


def write_twine_story(graph: Dict, output_path: str, story_title: str = "Generated Story") -> None:
    """
    Write a narrative graph to Twine 2 HTML format.
    
    This creates a standalone HTML file that can be opened directly in a browser.
    
    Args:
        graph: Graph dictionary with 'nodes' and 'edges'  
        output_path: Path to write the .html file
        story_title: Title for the Twine story
    """
    nodes = graph.get('nodes', [])
    edges = graph.get('edges', [])
    
    if not nodes:
        raise ValueError("Graph contains no nodes")
    
    # Build outgoing edge lookup
    outgoing_edges = {}
    for edge in edges:
        source = edge['source']
        if source not in outgoing_edges:
            outgoing_edges[source] = []
        outgoing_edges[source].append(edge)
    
    # Prepare story data
    passages = []
    for i, node in enumerate(nodes):
        node_id = node['id']
        passage_name = sanitize_passage_name(node['label'])
        content = escape_twee_content(node['text'])
        
        # Add links to connected passages
        connected_edges = outgoing_edges.get(node_id, [])
        if connected_edges:
            content += "\n\n---\n\n"
            for edge in connected_edges:
                target_node = next((n for n in nodes if n['id'] == edge['target']), None)
                if target_node:
                    target_name = sanitize_passage_name(target_node['label'])
                    link_text = edge.get('label', 'Continue')
                    content += f"[[{link_text}|{target_name}]]\n"
        
        # Get position or assign default
        position = node.get('position', {'x': 100 + (i % 10) * 300, 'y': 100 + (i // 10) * 200})
        
        passage_data = {
            "text": content,
            "links": [],  # Twine will parse these from the text
            "name": passage_name,
            "pid": str(i + 1),
            "position": position,
            "tags": []
        }
        passages.append(passage_data)
    
    # Create Twine story data structure
    story_data = {
        "passages": passages,
        "name": story_title,
        "startnode": "1",
        "creator": "pdf2twine",
        "creator-version": "1.0.0",
        "ifid": str(uuid.uuid4()).upper()
    }
    
    # Generate HTML
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>{story_title}</title>
    <meta charset="utf-8">
</head>
<body>
    <tw-storydata name="{story_title}" 
                   startnode="1" 
                   creator="pdf2twine" 
                   creator-version="1.0.0" 
                   ifid="{story_data['ifid']}" 
                   zoom="1" 
                   format="Harlowe" 
                   format-version="3.3.0">
        
        <style role="stylesheet" id="twine-user-stylesheet" type="text/twine-css">
        </style>
        
        <script role="script" id="twine-user-script" type="text/twine-javascript">
        </script>
"""
    
    # Add passages
    for passage in passages:
        position = passage['position']
        html_content += f'''
        <tw-passagedata pid="{passage['pid']}" 
                       name="{passage['name']}" 
                       tags="" 
                       position="{position['x']},{position['y']}" 
                       size="100,100">{passage['text']}</tw-passagedata>'''
    
    html_content += """
    </tw-storydata>
    
    <script title="Twine engine code" data-main="harlowe">
    // Twine/Harlowe engine would go here in a real implementation
    // For now, this creates a basic story structure
    console.log("Story data loaded");
    </script>
</body>
</html>"""
    
    # Write HTML file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    logger.info(f"Wrote Twine HTML file with {len(nodes)} passages to {output_path}")


def convert_graph_to_twine(graph: Dict, output_dir: str, story_title: str = "Generated Story") -> Dict[str, str]:
    """
    Convert a narrative graph to both Twee and HTML formats.
    
    Args:
        graph: Graph dictionary with 'nodes' and 'edges'
        output_dir: Directory to write output files
        story_title: Title for the Twine story
        
    Returns:
        Dictionary with paths to generated files
    """
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # Generate file names
    safe_title = sanitize_passage_name(story_title.replace(' ', '_'))
    twee_path = output_path / f"{safe_title}.twee"
    html_path = output_path / f"{safe_title}.html"
    
    # Write both formats
    write_twee(graph, str(twee_path), story_title)
    write_twine_story(graph, str(html_path), story_title)
    
    return {
        'twee': str(twee_path),
        'html': str(html_path),
        'title': story_title
    } 