"""Quiz generation helpers for narrative graphs."""
from __future__ import annotations

import logging
from typing import Dict, Optional

try:  # pragma: no cover - optional dependency for offline tests
    import requests  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    from types import SimpleNamespace

    requests = SimpleNamespace(post=None)  # type: ignore

from pdf2twine.services import (
    APITokenError,
    DependencyError,
    OpenRouterRequest,
    ensure_dict,
    ensure_list,
    extract_json_value,
    load_api_token,
    perform_openrouter_completion,
)

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "openai/gpt-4o-mini"


def get_api_token() -> str:
    """Expose token retrieval for compatibility with tests."""

    return load_api_token()


def _call_llm(prompt: str, model_id: str) -> str:
    try:
        token = get_api_token()
        return perform_openrouter_completion(
            request=OpenRouterRequest(
                prompt=prompt,
                model_id=model_id,
                timeout=30,
                temperature=0.2,
            ),
            requests_module=requests,
            token=token,
        )
    except (DependencyError, APITokenError) as exc:
        raise ValueError(str(exc)) from exc


def make_quiz(scene: str, model_id: Optional[str] = None) -> Dict:
    """Generate a quiz question for a scene using an LLM."""

    model = model_id or DEFAULT_MODEL
    prompt = (
        "Generate a multiple choice quiz question based on the following scene. The question should test comprehension of key "
        "events, characters, or details.\n\n"
        "Return your response as a JSON object with this exact format:\n"
        "{\n  \"question\": \"What happened in this scene?\",\n"
        "  \"options\": [\"A) Option 1\", \"B) Option 2\", \"C) Option 3\", \"D) Option 4\"],\n"
        "  \"answer\": \"A\",\n  \"explanation\": \"Brief explanation of the correct answer\"\n}\n\n"
        "Requirements:\n"
        "- Question should be clear and specific to the scene\n"
        "- Provide exactly 4 options (A, B, C, D)\n"
        "- One option should be clearly correct\n"
        "- Other options should be plausible but wrong\n"
        "- Keep question and options concise\n\n"
        f"Scene text:\n{scene[:1500]}"
    )
    if len(scene) > 1500:
        prompt += "..."
    prompt += "\n\nQuiz JSON:"

    try:
        llm_output = _call_llm(prompt, model)
        quiz_raw = extract_json_value(
            llm_output,
            validator=lambda value: isinstance(value, dict),
            error_message="LLM did not return valid JSON",
        )
        quiz = ensure_dict(quiz_raw)

        required_keys = {"question", "options", "answer"}
        if not required_keys.issubset(quiz):
            raise ValueError("Quiz missing required keys")

        options = ensure_list(
            quiz["options"],
            item_validator=lambda item: isinstance(item, str),
            allow_empty=False,
        )
        if len(options) != 4:
            raise ValueError("Quiz must have exactly 4 options")
        if quiz["answer"] not in {"A", "B", "C", "D"}:
            raise ValueError("Answer must be A, B, C, or D")

        quiz["options"] = list(options)
        return quiz
    except ValueError:
        raise
    except Exception as exc:  # pragma: no cover - network errors mocked in tests
        logger.warning("OpenRouter API request failed: %s", exc)
        raise ValueError("Failed to call OpenRouter API") from exc


def make_quiz_fallback(scene: str) -> Dict:
    """Generate a simple fallback quiz when LLM fails."""

    sentences = scene.split('.')
    key_detail = sentences[0].strip() if sentences else scene[:100]

    return {
        "question": "What is mentioned in this scene?",
        "options": [
            f"A) {key_detail[:50]}...",
            "B) Something completely different",
            "C) Another unrelated event",
            "D) None of the above",
        ],
        "answer": "A",
        "explanation": "This detail is directly mentioned in the scene.",
    }


def format_quiz_content(quiz_data: Dict) -> str:
    """Format quiz data into Twine-compatible content."""

    question = quiz_data["question"]
    options = quiz_data["options"]
    answer = quiz_data["answer"]
    explanation = quiz_data.get("explanation", "")

    content = f"## Quiz Time!\n\n{question}\n\n"
    for option in options:
        content += f"{option}\n"
    content += "\n---\n\n"
    content += f"**Correct Answer: {answer}**\n\n"
    if explanation:
        content += f"*{explanation}*\n\n"
    content += "Ready to continue the story?"

    return content


def add_quizzes_to_graph(graph: Dict, model_id: Optional[str] = None) -> Dict:
    """Add quiz passages to a narrative graph."""

    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])
    if not nodes:
        return graph

    enhanced_nodes = list(nodes)
    enhanced_edges = list(edges)

    for node in nodes:
        scene_id = node["id"]
        scene_text = node["text"]
        logger.info("Generating quiz for %s", scene_id)

        try:
            quiz_data = make_quiz(scene_text, model_id)
        except ValueError as exc:
            logger.warning("LLM quiz generation failed for %s: %s", scene_id, exc)
            quiz_data = make_quiz_fallback(scene_text)

        quiz_id = f"{scene_id}_quiz"
        quiz_node = {
            "id": quiz_id,
            "label": f"Quiz: {node['label'][:30]}...",
            "text": format_quiz_content(quiz_data),
            "tags": ["quiz"],
            "quiz_data": quiz_data,
        }

        if "position" in node:
            pos = node["position"]
            quiz_node["position"] = {"x": pos["x"] + 200, "y": pos["y"] + 50}

        enhanced_nodes.append(quiz_node)

        enhanced_edges.append({"source": scene_id, "target": quiz_id, "label": "Take Quiz"})
        for original_edge in edges:
            if original_edge["source"] == scene_id:
                enhanced_edges.append(
                    {
                        "source": quiz_id,
                        "target": original_edge["target"],
                        "label": "Continue Story",
                    }
                )

    enhanced_graph = dict(graph)
    enhanced_graph["nodes"] = enhanced_nodes
    enhanced_graph["edges"] = enhanced_edges
    metadata = dict(graph.get("metadata", {}))
    metadata["quiz_nodes_added"] = len(nodes)
    enhanced_graph["metadata"] = metadata

    logger.info("Added %s quiz nodes to graph", len(nodes))
    return enhanced_graph


def extract_quiz_statistics(graph: Dict) -> Dict:
    """Extract statistics about quizzes in the graph."""

    nodes = graph.get("nodes", [])
    quiz_nodes = [n for n in nodes if "quiz" in n.get("tags", [])]
    scene_nodes = [n for n in nodes if "quiz" not in n.get("tags", [])]

    return {
        "total_nodes": len(nodes),
        "scene_nodes": len(scene_nodes),
        "quiz_nodes": len(quiz_nodes),
        "quiz_coverage": len(quiz_nodes) / len(scene_nodes) if scene_nodes else 0,
    }


__all__ = [
    "make_quiz",
    "make_quiz_fallback",
    "add_quizzes_to_graph",
    "format_quiz_content",
    "extract_quiz_statistics",
    "get_api_token",
]
