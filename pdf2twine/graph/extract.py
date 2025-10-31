"""Narrative graph extraction powered by optional LLM calls."""
from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple

try:  # pragma: no cover - exercised indirectly in tests
    import requests  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - dependency optional for offline mode
    from types import SimpleNamespace

    requests = SimpleNamespace(post=None)  # type: ignore

from pdf2twine.services import (
    DependencyError,
    OpenRouterRequest,
    ensure_list,
    extract_json_value,
    load_api_token,
    perform_openrouter_completion,
)

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "openai/gpt-4o-mini"


def get_api_token() -> str:
    """Public helper kept for backwards compatibility and tests."""

    return load_api_token()


def _call_llm(prompt: str, model_id: str, *, timeout: int = 60) -> str:
    """Execute the OpenRouter request and return the raw payload."""

    try:
        token = get_api_token()
        return perform_openrouter_completion(
            request=OpenRouterRequest(
                prompt=prompt,
                model_id=model_id,
                timeout=timeout,
                temperature=0.1,
            ),
            requests_module=requests,
            token=token,
        )
    except DependencyError as exc:
        raise ValueError(str(exc)) from exc


def extract_scene_relationships(
    summarized_scenes: List[Dict[str, str]],
    model_id: Optional[str] = None,
) -> List[Tuple[str, str, str]]:
    """Extract narrative relationships between scenes using an LLM."""

    if not summarized_scenes:
        return []

    model = model_id or DEFAULT_MODEL
    scene_descriptions = "\n\n".join(
        f"ID: {scene['id']}\nSummary: {scene['summary']}"
        for scene in summarized_scenes
    )
    prompt = (
        "Analyze the following narrative scenes and identify the relationships between them.\n\n"
        "Return your response as a JSON array where each element is a triple "
        "[source_id, relationship, target_id].\n\n"
        "Requirements:\n"
        "- Each scene must have at least one outgoing edge (except possibly the last scene)\n"
        "- Use relationship types like \"leads_to\", \"causes\", \"parallels\", \"resolves\", \"conflicts_with\"\n"
        "- Ensure the graph represents the narrative flow\n"
        "- Scene IDs must match exactly from the list below\n\n"
        f"Scenes:\n{scene_descriptions}\n\n"
        "Expected JSON format:\n"
        "[[\"scene_1\", \"leads_to\", \"scene_2\"], ...]\n\nRelationships:"
    )

    try:
        llm_output = _call_llm(prompt, model)
        relationships_raw = extract_json_value(
            llm_output,
            validator=lambda value: isinstance(value, list),
            error_message="LLM did not return valid JSON",
        )
        valid_scene_ids = {scene["id"] for scene in summarized_scenes}
        relationships: List[Tuple[str, str, str]] = []

        for rel in ensure_list(
            relationships_raw,
            item_validator=lambda item: isinstance(item, (list, tuple)) and len(item) == 3,
        ):
            source, relation, target = rel
            if source in valid_scene_ids and target in valid_scene_ids:
                relationships.append((str(source), str(relation), str(target)))
            else:
                logger.warning("Invalid relationship ignored: %s", rel)

        logger.info("Extracted %s valid relationships", len(relationships))
        return relationships
    except ValueError:
        raise
    except Exception as exc:  # pragma: no cover - network errors mocked in tests
        logger.warning("OpenRouter API request failed: %s", exc)
        raise ValueError("Failed to call OpenRouter API") from exc


def ensure_connectivity(
    summarized_scenes: List[Dict[str, str]],
    relationships: List[Tuple[str, str, str]],
) -> List[Tuple[str, str, str]]:
    """Ensure each scene has at least one outgoing edge (except the last)."""

    outgoing_edges: Dict[str, List[Tuple[str, str]]] = {}
    for source, relation, target in relationships:
        outgoing_edges.setdefault(source, []).append((relation, target))

    enhanced_relationships = list(relationships)
    scene_ids = [scene["id"] for scene in summarized_scenes]

    for index, scene in enumerate(summarized_scenes):
        scene_id = scene["id"]
        if index == len(summarized_scenes) - 1:
            continue
        if scene_id not in outgoing_edges and index + 1 < len(scene_ids):
            next_scene_id = scene_ids[index + 1]
            enhanced_relationships.append((scene_id, "leads_to", next_scene_id))
            logger.info("Added sequential connection: %s -> %s", scene_id, next_scene_id)

    return enhanced_relationships


def extract_narrative_graph(
    summarized_scenes: List[Dict[str, str]],
    model_id: Optional[str] = None,
) -> Dict:
    """Extract a complete narrative graph from summarised scenes."""

    if not summarized_scenes:
        raise ValueError("No scenes available for graph extraction")

    try:
        relationships = extract_scene_relationships(summarized_scenes, model_id)
    except ValueError as exc:
        logger.warning("Failed to extract relationships via LLM: %s", exc)
        relationships = []

    if not relationships:
        for index in range(len(summarized_scenes) - 1):
            source_id = summarized_scenes[index]["id"]
            target_id = summarized_scenes[index + 1]["id"]
            relationships.append((source_id, "leads_to", target_id))
        logger.info("Using fallback sequential relationships: %s edges", len(relationships))

    enhanced_relationships = ensure_connectivity(summarized_scenes, relationships)

    nodes = [
        {
            "id": scene["id"],
            "label": scene["summary"],
            "text": scene["text"],
        }
        for scene in summarized_scenes
    ]

    edges = [
        {
            "source": source,
            "target": target,
            "label": relation,
        }
        for source, relation, target in enhanced_relationships
    ]

    graph = {
        "nodes": nodes,
        "edges": edges,
        "metadata": {
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "connectivity_ensured": True,
        },
    }

    logger.info(
        "Created narrative graph with %s nodes and %s edges",
        len(nodes),
        len(edges),
    )
    return graph


__all__ = [
    "extract_scene_relationships",
    "ensure_connectivity",
    "extract_narrative_graph",
    "get_api_token",
]
