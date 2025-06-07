"""Quiz generation functionality using LLM."""
import logging
from typing import Dict, List, Optional
import json
import requests
import os
from pathlib import Path

logger = logging.getLogger(__name__)


def get_api_token() -> str:
    """Get the OpenRouter API token from environment or file."""
    try:
        return os.environ.get("API_TOKEN") or Path('.API_TOKEN').read_text().strip()
    except FileNotFoundError:
        raise ValueError("OpenRouter API token not found")


def make_quiz(scene: str, model_id: Optional[str] = None) -> Dict:
    """
    Generate a quiz question for a scene using LLM.
    
    Args:
        scene: Scene text to create quiz for
        model_id: OpenAI model to use (defaults to gpt-4o-mini)
        
    Returns:
        Dictionary with 'question', 'options', and 'answer' keys
        
    Raises:
        ValueError: If API call fails or response is invalid
    """
    if model_id is None:
        model_id = "openai/gpt-4o-mini"
    
    api_token = get_api_token()
    
    # Prepare prompt for quiz generation
    prompt = f"""Generate a multiple choice quiz question based on the following scene. The question should test comprehension of key events, characters, or details.

Return your response as a JSON object with this exact format:
{{
  "question": "What happened in this scene?",
  "options": ["A) Option 1", "B) Option 2", "C) Option 3", "D) Option 4"],
  "answer": "A",
  "explanation": "Brief explanation of the correct answer"
}}

Requirements:
- Question should be clear and specific to the scene
- Provide exactly 4 options (A, B, C, D)
- One option should be clearly correct
- Other options should be plausible but wrong
- Keep question and options concise

Scene text:
{scene[:1500]}{"..." if len(scene) > 1500 else ""}

Quiz JSON:"""

    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_token}"},
            json={
                "model": model_id,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2,
            },
            timeout=30,
        )
        response.raise_for_status()
        
        result = response.json()
        llm_output = result['choices'][0]['message']['content']
        
        # Try to parse JSON response
        try:
            quiz_data = json.loads(llm_output)
            
            # Validate structure
            required_keys = ['question', 'options', 'answer']
            if not all(key in quiz_data for key in required_keys):
                raise ValueError("Quiz missing required keys")
            
            if not isinstance(quiz_data['options'], list) or len(quiz_data['options']) != 4:
                raise ValueError("Quiz must have exactly 4 options")
            
            if quiz_data['answer'] not in ['A', 'B', 'C', 'D']:
                raise ValueError("Answer must be A, B, C, or D")
            
            return quiz_data
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse quiz JSON response: {e}")
            logger.debug(f"LLM output: {llm_output[:500]}...")
            raise ValueError("LLM did not return valid JSON") from e
            
    except requests.RequestException as e:
        logger.error(f"OpenRouter API request failed: {e}")
        raise ValueError("Failed to call OpenRouter API") from e


def make_quiz_fallback(scene: str) -> Dict:
    """
    Generate a simple fallback quiz when LLM fails.
    
    Args:
        scene: Scene text to create quiz for
        
    Returns:
        Basic quiz dictionary
    """
    # Extract first sentence or key detail
    sentences = scene.split('.')
    key_detail = sentences[0].strip() if sentences else scene[:100]
    
    return {
        "question": "What is mentioned in this scene?",
        "options": [
            f"A) {key_detail[:50]}...",
            "B) Something completely different",
            "C) Another unrelated event",
            "D) None of the above"
        ],
        "answer": "A",
        "explanation": "This detail is directly mentioned in the scene."
    }


def add_quizzes_to_graph(graph: Dict, model_id: Optional[str] = None) -> Dict:
    """
    Add quiz passages to a narrative graph.
    
    Creates quiz nodes tagged as 'quiz' and links them to their corresponding scenes.
    
    Args:
        graph: Graph dictionary with 'nodes' and 'edges'
        model_id: OpenAI model to use for quiz generation
        
    Returns:
        Enhanced graph with quiz nodes added
    """
    nodes = graph.get('nodes', [])
    edges = graph.get('edges', [])
    
    if not nodes:
        return graph
    
    enhanced_nodes = list(nodes)  # Copy existing nodes
    enhanced_edges = list(edges)  # Copy existing edges
    
    # Generate quizzes for each scene
    for node in nodes:
        scene_id = node['id']
        scene_text = node['text']
        
        logger.info(f"Generating quiz for {scene_id}")
        
        try:
            quiz_data = make_quiz(scene_text, model_id)
        except ValueError as e:
            logger.warning(f"LLM quiz generation failed for {scene_id}: {e}")
            quiz_data = make_quiz_fallback(scene_text)
        
        # Create quiz node
        quiz_id = f"{scene_id}_quiz"
        quiz_content = format_quiz_content(quiz_data)
        
        quiz_node = {
            'id': quiz_id,
            'label': f"Quiz: {node['label'][:30]}...",
            'text': quiz_content,
            'tags': ['quiz'],
            'quiz_data': quiz_data
        }
        
        # Add position near the original node if available
        if 'position' in node:
            pos = node['position']
            quiz_node['position'] = {
                'x': pos['x'] + 200,  # Offset to the right
                'y': pos['y'] + 50    # Slight downward offset
            }
        
        enhanced_nodes.append(quiz_node)
        
        # Create edge from scene to quiz
        scene_to_quiz_edge = {
            'source': scene_id,
            'target': quiz_id,
            'label': 'Take Quiz'
        }
        enhanced_edges.append(scene_to_quiz_edge)
        
        # Find edges that originally came from this scene
        # and create return edges from quiz
        original_outgoing = [e for e in edges if e['source'] == scene_id]
        for orig_edge in original_outgoing:
            quiz_to_next_edge = {
                'source': quiz_id,
                'target': orig_edge['target'],
                'label': 'Continue Story'
            }
            enhanced_edges.append(quiz_to_next_edge)
    
    # Create enhanced graph
    enhanced_graph = dict(graph)
    enhanced_graph['nodes'] = enhanced_nodes
    enhanced_graph['edges'] = enhanced_edges
    enhanced_graph['metadata'] = dict(graph.get('metadata', {}))
    enhanced_graph['metadata']['quiz_nodes_added'] = len(nodes)
    
    logger.info(f"Added {len(nodes)} quiz nodes to graph")
    return enhanced_graph


def format_quiz_content(quiz_data: Dict) -> str:
    """
    Format quiz data into Twine-compatible content.
    
    Args:
        quiz_data: Quiz dictionary with question, options, answer, explanation
        
    Returns:
        Formatted content string for Twine passage
    """
    question = quiz_data['question']
    options = quiz_data['options']
    answer = quiz_data['answer']
    explanation = quiz_data.get('explanation', '')
    
    content = f"## Quiz Time!\n\n{question}\n\n"
    
    for option in options:
        content += f"{option}\n"
    
    content += "\n---\n\n"
    content += f"**Correct Answer: {answer}**\n\n"
    
    if explanation:
        content += f"*{explanation}*\n\n"
    
    content += "Ready to continue the story?"
    
    return content


def extract_quiz_statistics(graph: Dict) -> Dict:
    """
    Extract statistics about quizzes in the graph.
    
    Args:
        graph: Graph with quiz nodes
        
    Returns:
        Dictionary with quiz statistics
    """
    nodes = graph.get('nodes', [])
    
    quiz_nodes = [n for n in nodes if 'quiz' in n.get('tags', [])]
    scene_nodes = [n for n in nodes if 'quiz' not in n.get('tags', [])]
    
    return {
        'total_nodes': len(nodes),
        'scene_nodes': len(scene_nodes),
        'quiz_nodes': len(quiz_nodes),
        'quiz_coverage': len(quiz_nodes) / len(scene_nodes) if scene_nodes else 0
    } 