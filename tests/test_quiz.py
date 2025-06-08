"""Tests for the quiz generation module."""
import pytest
from unittest.mock import Mock, patch
from pdf2twine.quiz import make_quiz, add_quizzes_to_graph


def test_make_quiz_fallback():
    """Test quiz generation fallback when LLM fails."""
    scene = "This is a test scene with some important content."
    
    # Mock the LLM call to fail
    with patch('pdf2twine.quiz.generate.get_api_token', side_effect=ValueError("No token")):
        with pytest.raises(ValueError):
            make_quiz(scene)


@patch('pdf2twine.quiz.generate.requests.post')
@patch('pdf2twine.quiz.generate.get_api_token')
def test_make_quiz_llm_success(mock_get_token, mock_post):
    """Test successful quiz generation with LLM."""
    mock_get_token.return_value = "test_token"
    
    # Mock successful API response
    quiz_response = {
        "question": "What is the main topic of this scene?",
        "options": ["A) Test content", "B) Other content", "C) Different content", "D) Random content"],
        "answer": "A",
        "explanation": "The scene mentions test content."
    }
    
    mock_response = Mock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {
        'choices': [{'message': {'content': f'{quiz_response}'}}]
    }
    mock_post.return_value = mock_response
    
    scene = "This is a test scene with some important content."
    
    # This will fail because the mock returns a string representation of dict, not JSON
    # Let's fix the mock to return proper JSON
    import json
    mock_response.json.return_value = {
        'choices': [{'message': {'content': json.dumps(quiz_response)}}]
    }
    
    result = make_quiz(scene)
    
    assert result['question'] == quiz_response['question']
    assert result['answer'] == quiz_response['answer']
    assert len(result['options']) == 4
    assert mock_post.called


def test_add_quizzes_to_graph():
    """Test adding quizzes to a narrative graph."""
    original_graph = {
        'nodes': [
            {'id': 'scene_1', 'label': 'First scene', 'text': 'Content of first scene'},
            {'id': 'scene_2', 'label': 'Second scene', 'text': 'Content of second scene'}
        ],
        'edges': [
            {'source': 'scene_1', 'target': 'scene_2', 'label': 'continue'}
        ]
    }
    
    # Mock the quiz generation to use fallback
    with patch('pdf2twine.quiz.generate.make_quiz', side_effect=ValueError("Mock failure")):
        result = add_quizzes_to_graph(original_graph)
    
    # Should have original nodes plus quiz nodes
    assert len(result['nodes']) == 4  # 2 original + 2 quiz nodes
    
    # Check that quiz nodes were added
    quiz_nodes = [n for n in result['nodes'] if 'quiz' in n.get('tags', [])]
    assert len(quiz_nodes) == 2
    
    # Check quiz node structure
    for quiz_node in quiz_nodes:
        assert quiz_node['id'].endswith('_quiz')
        assert 'quiz_data' in quiz_node
        assert quiz_node['label'].startswith('Quiz:')
    
    # Should have more edges (original + quiz connections)
    assert len(result['edges']) > len(original_graph['edges'])


def test_add_quizzes_empty_graph():
    """Test adding quizzes to an empty graph."""
    empty_graph = {'nodes': [], 'edges': []}
    result = add_quizzes_to_graph(empty_graph)
    
    assert result == empty_graph  # Should return unchanged


@patch('pdf2twine.quiz.generate.make_quiz')
def test_add_quizzes_with_positions(mock_make_quiz):
    """Test that quiz nodes get proper positioning."""
    mock_make_quiz.return_value = {
        "question": "Test question?",
        "options": ["A) Option 1", "B) Option 2", "C) Option 3", "D) Option 4"],
        "answer": "A",
        "explanation": "Test explanation"
    }
    
    graph = {
        'nodes': [
            {
                'id': 'scene_1', 
                'label': 'First scene', 
                'text': 'Content',
                'position': {'x': 100, 'y': 200}
            }
        ],
        'edges': []
    }
    
    result = add_quizzes_to_graph(graph)
    
    quiz_node = next(n for n in result['nodes'] if 'quiz' in n.get('tags', []))
    assert 'position' in quiz_node
    assert quiz_node['position']['x'] == 300  # Original x + 200
    assert quiz_node['position']['y'] == 250  # Original y + 50


def test_make_quiz_invalid_response():
    """Test handling of invalid LLM response."""
    with patch('pdf2twine.quiz.generate.get_api_token', return_value="test_token"):
        with patch('pdf2twine.quiz.generate.requests.post') as mock_post:
            # Mock invalid JSON response
            mock_response = Mock()
            mock_response.raise_for_status.return_value = None
            mock_response.json.return_value = {
                'choices': [{'message': {'content': 'not valid json'}}]
            }
            mock_post.return_value = mock_response
            
            scene = "Test scene content"
            
            with pytest.raises(ValueError, match="LLM did not return valid JSON"):
                make_quiz(scene)


def test_make_quiz_missing_keys():
    """Test handling of quiz response missing required keys."""
    with patch('pdf2twine.quiz.generate.get_api_token', return_value="test_token"):
        with patch('pdf2twine.quiz.generate.requests.post') as mock_post:
            # Mock response missing required keys
            import json
            invalid_quiz = {"question": "What?", "answer": "A"}  # Missing 'options'
            
            mock_response = Mock()
            mock_response.raise_for_status.return_value = None
            mock_response.json.return_value = {
                'choices': [{'message': {'content': json.dumps(invalid_quiz)}}]
            }
            mock_post.return_value = mock_response
            
            scene = "Test scene content"
            
            with pytest.raises(ValueError, match="Quiz missing required keys"):
                make_quiz(scene) 