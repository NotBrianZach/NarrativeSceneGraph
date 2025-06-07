"""Tests for the exporter module."""
import pytest
from pathlib import Path
import tempfile
from pdf2twine.exporter import write_twee, assign_random_coordinates, assign_flow_coordinates


def test_assign_random_coordinates():
    """Test random coordinate assignment."""
    graph = {
        'nodes': [
            {'id': 'scene_1', 'label': 'First scene'},
            {'id': 'scene_2', 'label': 'Second scene'},
        ],
        'edges': []
    }
    
    result = assign_random_coordinates(graph, seed=42)  # Use seed for reproducibility
    
    assert 'nodes' in result
    assert len(result['nodes']) == 2
    
    for node in result['nodes']:
        assert 'position' in node
        assert 'x' in node['position']
        assert 'y' in node['position']
        assert 100 <= node['position']['x'] <= 3900  # Within canvas bounds
        assert 100 <= node['position']['y'] <= 2900


def test_assign_flow_coordinates():
    """Test flow-based coordinate assignment."""
    graph = {
        'nodes': [
            {'id': 'scene_1', 'label': 'First scene'},
            {'id': 'scene_2', 'label': 'Second scene'},
        ],
        'edges': [
            {'source': 'scene_1', 'target': 'scene_2'}
        ]
    }
    
    result = assign_flow_coordinates(graph)
    
    assert 'nodes' in result
    assert len(result['nodes']) == 2
    
    # Should arrange nodes in layers
    node1 = next(n for n in result['nodes'] if n['id'] == 'scene_1')
    node2 = next(n for n in result['nodes'] if n['id'] == 'scene_2')
    
    # First scene should be higher (lower y value) than second scene
    assert node1['position']['y'] < node2['position']['y']


def test_write_twee_basic():
    """Test basic Twee file generation."""
    graph = {
        'nodes': [
            {
                'id': 'scene_1', 
                'label': 'Opening scene',
                'text': 'This is the opening of our story.',
                'position': {'x': 100, 'y': 200}
            },
            {
                'id': 'scene_2',
                'label': 'Second scene', 
                'text': 'The story continues here.',
                'position': {'x': 300, 'y': 400}
            }
        ],
        'edges': [
            {'source': 'scene_1', 'target': 'scene_2', 'label': 'Continue'}
        ]
    }
    
    with tempfile.NamedTemporaryFile(mode='w+', suffix='.twee', delete=False) as f:
        temp_path = f.name
    
    try:
        write_twee(graph, temp_path, "Test Story")
        
        # Read the generated content
        content = Path(temp_path).read_text()
        
        # Check basic passages without JSON header
        assert ':: Opening scene <100,200>' in content
        assert ':: Second scene <300,400>' in content
        assert 'This is the opening of our story.' in content
        assert '[[Continue|Second scene]]' in content
        
    finally:
        Path(temp_path).unlink()


def test_write_twee_sanitizes_passage_names():
    """Test that passage names are properly sanitized."""
    graph = {
        'nodes': [
            {
                'id': 'scene_1',
                'label': 'Scene with "quotes" and special chars!@#',
                'text': 'Content here.'
            }
        ],
        'edges': []
    }
    
    with tempfile.NamedTemporaryFile(mode='w+', suffix='.twee', delete=False) as f:
        temp_path = f.name
    
    try:
        write_twee(graph, temp_path, "Test Story")
        content = Path(temp_path).read_text()
        
        # Should sanitize the passage name, preserving spaces
        assert ':: Scene with quotes and special chars___' in content
        assert '"' not in content.split('\n')[0]  # No quotes in passage header
        
    finally:
        Path(temp_path).unlink()


def test_write_twee_escapes_content():
    """Test that content is properly escaped."""
    graph = {
        'nodes': [
            {
                'id': 'scene_1',
                'label': 'Test scene',
                'text': 'Content with [[existing links]] and more text.'
            }
        ],
        'edges': []
    }
    
    with tempfile.NamedTemporaryFile(mode='w+', suffix='.twee', delete=False) as f:
        temp_path = f.name
    
    try:
        write_twee(graph, temp_path, "Test Story")
        content = Path(temp_path).read_text()
        
        # Should escape existing Twee links
        assert '\\[\\[existing links\\]\\]' in content
        
    finally:
        Path(temp_path).unlink()


def test_write_twee_no_nodes():
    """Test error handling when graph has no nodes."""
    graph = {'nodes': [], 'edges': []}
    
    with tempfile.NamedTemporaryFile(mode='w+', suffix='.twee', delete=False) as f:
        temp_path = f.name
    
    try:
        with pytest.raises(ValueError, match="Graph contains no nodes"):
            write_twee(graph, temp_path, "Test Story")
            
    finally:
        # Clean up if file was created
        if Path(temp_path).exists():
            Path(temp_path).unlink()


def test_coordinates_empty_graph():
    """Test coordinate assignment with empty graph."""
    graph = {'nodes': [], 'edges': []}
    
    result_random = assign_random_coordinates(graph)
    result_flow = assign_flow_coordinates(graph)
    
    assert result_random == graph
    assert result_flow == graph 