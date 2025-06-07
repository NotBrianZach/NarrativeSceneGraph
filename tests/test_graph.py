"""Tests for the graph generation module."""
import pytest
from unittest.mock import Mock, patch
from pdf2twine.graph import summarize_scenes, extract_narrative_graph, to_dot


def test_summarize_scenes_empty_list():
    """Test summarizing an empty list of scenes."""
    result = summarize_scenes([])
    assert result == []


def test_summarize_scenes_fallback():
    """Test scene summarization with fallback when LLM fails."""
    scenes = ["This is a test scene with some content."]
    
    # Mock the LLM call to fail
    with patch('pdf2twine.graph.summarize.get_api_token', side_effect=ValueError("No token")):
        result = summarize_scenes(scenes)
    
    assert len(result) == 1
    assert result[0]['id'] == 'scene_1'
    assert result[0]['text'] == scenes[0]
    assert 'summary' in result[0]
    # Should fallback to truncated text
    assert len(result[0]['summary']) <= 103  # 100 chars + "..."


@patch('pdf2twine.graph.summarize.requests.post')
@patch('pdf2twine.graph.summarize.get_api_token')
def test_summarize_scenes_llm_success(mock_get_token, mock_post):
    """Test successful scene summarization with LLM."""
    mock_get_token.return_value = "test_token"
    
    # Mock successful API response
    mock_response = Mock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {
        'choices': [{'message': {'content': 'A brief scene summary'}}]
    }
    mock_post.return_value = mock_response
    
    scenes = ["This is a test scene with some content."]
    result = summarize_scenes(scenes)
    
    assert len(result) == 1
    assert result[0]['summary'] == 'A brief scene summary'
    assert mock_post.called


def test_extract_narrative_graph_empty():
    """Test extracting graph from empty scenes."""
    with pytest.raises(Exception):
        extract_narrative_graph([])


@patch('pdf2twine.graph.extract.requests.post')
@patch('pdf2twine.graph.extract.get_api_token')
def test_extract_narrative_graph_basic(mock_get_token, mock_post):
    """Test basic narrative graph extraction."""
    mock_get_token.return_value = "test_token"
    
    # Mock successful API response
    mock_response = Mock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {
        'choices': [{'message': {'content': '[["scene_1", "leads_to", "scene_2"]]'}}]
    }
    mock_post.return_value = mock_response
    
    summarized_scenes = [
        {'id': 'scene_1', 'summary': 'First scene', 'text': 'Scene 1 content'},
        {'id': 'scene_2', 'summary': 'Second scene', 'text': 'Scene 2 content'}
    ]
    
    result = extract_narrative_graph(summarized_scenes)
    
    assert 'nodes' in result
    assert 'edges' in result
    assert len(result['nodes']) == 2
    assert len(result['edges']) >= 1  # At least the LLM-generated edge


def test_to_dot_basic():
    """Test basic DOT generation."""
    graph = {
        'nodes': [
            {'id': 'scene_1', 'label': 'First scene'},
            {'id': 'scene_2', 'label': 'Second scene'}
        ],
        'edges': [
            {'source': 'scene_1', 'target': 'scene_2', 'label': 'leads_to'}
        ]
    }
    
    dot_content = to_dot(graph, "TestGraph")
    
    assert dot_content.startswith('digraph TestGraph {')
    assert 'scene_1' in dot_content
    assert 'scene_2' in dot_content
    assert 'leads_to' in dot_content
    assert dot_content.endswith('}')


def test_to_dot_sanitizes_ids():
    """Test that DOT generation sanitizes node IDs."""
    graph = {
        'nodes': [
            {'id': 'scene-1!@#', 'label': 'First scene'},
        ],
        'edges': []
    }
    
    dot_content = to_dot(graph, "TestGraph")
    
    # Should sanitize the problematic ID
    assert 'scene_1___' in dot_content or 'scene_' in dot_content
    assert '!@#' not in dot_content


def test_to_dot_escapes_labels():
    """Test that DOT generation escapes labels properly."""
    graph = {
        'nodes': [
            {'id': 'scene_1', 'label': 'Scene with "quotes" and \n newlines'},
        ],
        'edges': []
    }
    
    dot_content = to_dot(graph, "TestGraph")
    
    # Should escape quotes and newlines
    assert '\\"' in dot_content  # Escaped quotes
    assert '\\n' in dot_content  # Escaped newlines 