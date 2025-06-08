"""Narrative graph extraction functionality using LLM."""
import logging
from typing import List, Dict, Tuple, Optional
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


def extract_scene_relationships(summarized_scenes: List[Dict[str, str]], 
                               model_id: Optional[str] = None) -> List[Tuple[str, str, str]]:
    """
    Extract narrative relationships between scenes using LLM.
    
    Args:
        summarized_scenes: List of scene dictionaries with 'id', 'summary', and 'text'
        model_id: OpenAI model to use (defaults to gpt-4o-mini)
        
    Returns:
        List of triples (source_id, relationship, target_id) representing edges
        
    Raises:
        ValueError: If API call fails or response is invalid
    """
    if model_id is None:
        model_id = "openai/gpt-4o-mini"
    
    api_token = get_api_token()
    
    # Prepare scene summaries for analysis
    scene_list = []
    for scene in summarized_scenes:
        scene_list.append(f"ID: {scene['id']}\nSummary: {scene['summary']}")
    
    scenes_text = "\n\n".join(scene_list)
    
    # Prepare prompt for relationship extraction
    prompt = f"""Analyze the following narrative scenes and identify the relationships between them. 

Return your response as a JSON array where each element is a triple [source_id, relationship, target_id].

Requirements:
- Each scene must have at least one outgoing edge (except possibly the last scene)
- Use relationship types like "leads_to", "causes", "parallels", "resolves", "conflicts_with"
- Ensure the graph represents the narrative flow
- Scene IDs must match exactly from the list below

Scenes:
{scenes_text}

Expected JSON format:
[
  ["scene_1", "leads_to", "scene_2"],
  ["scene_2", "causes", "scene_3"],
  ...
]

Relationships:"""

    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_token}"},
            json={
                "model": model_id,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
            },
            timeout=60,
        )
        response.raise_for_status()
        
        result = response.json()
        llm_output = result['choices'][0]['message']['content']
        
        # Try to parse JSON response
        try:
            relationships = json.loads(llm_output)
            if not isinstance(relationships, list):
                raise ValueError("LLM response is not a JSON array")
            
            # Validate and filter relationships
            valid_scene_ids = {scene['id'] for scene in summarized_scenes}
            valid_relationships = []
            
            for rel in relationships:
                if (isinstance(rel, list) and len(rel) == 3 and 
                    rel[0] in valid_scene_ids and rel[2] in valid_scene_ids):
                    valid_relationships.append(tuple(rel))
                else:
                    logger.warning(f"Invalid relationship: {rel}")
            
            logger.info(f"Extracted {len(valid_relationships)} valid relationships")
            return valid_relationships
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM JSON response: {e}")
            logger.debug(f"LLM output: {llm_output[:500]}...")
            raise ValueError("LLM did not return valid JSON") from e
            
    except requests.RequestException as e:
        logger.error(f"OpenRouter API request failed: {e}")
        raise ValueError("Failed to call OpenRouter API") from e


def ensure_connectivity(summarized_scenes: List[Dict[str, str]], 
                       relationships: List[Tuple[str, str, str]]) -> List[Tuple[str, str, str]]:
    """
    Ensure each scene has at least one outgoing edge (except the last).
    
    Args:
        summarized_scenes: List of scene dictionaries
        relationships: List of relationship triples
        
    Returns:
        Modified list of relationships ensuring connectivity
    """
    # Create adjacency list for outgoing edges
    outgoing_edges = {}
    for source, rel, target in relationships:
        if source not in outgoing_edges:
            outgoing_edges[source] = []
        outgoing_edges[source].append((rel, target))
    
    # Check each scene for outgoing edges
    enhanced_relationships = list(relationships)
    scene_ids = [scene['id'] for scene in summarized_scenes]
    
    for i, scene in enumerate(summarized_scenes):
        scene_id = scene['id']
        
        # Skip the last scene - it's okay if it has no outgoing edges
        if i == len(summarized_scenes) - 1:
            continue
            
        # If no outgoing edges, create a sequential connection
        if scene_id not in outgoing_edges:
            if i + 1 < len(scene_ids):
                next_scene_id = scene_ids[i + 1]
                enhanced_relationships.append((scene_id, "leads_to", next_scene_id))
                logger.info(f"Added sequential connection: {scene_id} -> {next_scene_id}")
    
    return enhanced_relationships


def extract_narrative_graph(summarized_scenes: List[Dict[str, str]], 
                           model_id: Optional[str] = None) -> Dict:
    """
    Extract a complete narrative graph from summarized scenes.
    
    Args:
        summarized_scenes: List of scene dictionaries with 'id', 'summary', and 'text'
        model_id: OpenAI model to use (defaults to gpt-4o-mini)
        
    Returns:
        Dictionary containing nodes and edges for the narrative graph
        
    Raises:
        ValueError: If extraction fails
    """
    # Extract relationships using LLM
    relationships = extract_scene_relationships(summarized_scenes, model_id)
    
    # Ensure connectivity
    enhanced_relationships = ensure_connectivity(summarized_scenes, relationships)
    
    # Build graph structure
    nodes = []
    for scene in summarized_scenes:
        nodes.append({
            'id': scene['id'],
            'label': scene['summary'],
            'text': scene['text']
        })
    
    edges = []
    for source, relationship, target in enhanced_relationships:
        edges.append({
            'source': source,
            'target': target,
            'label': relationship
        })
    
    graph = {
        'nodes': nodes,
        'edges': edges,
        'metadata': {
            'total_nodes': len(nodes),
            'total_edges': len(edges),
            'connectivity_ensured': True
        }
    }
    
    logger.info(f"Created narrative graph with {len(nodes)} nodes and {len(edges)} edges")
    return graph 