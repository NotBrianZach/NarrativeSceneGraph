"""Scene summarisation helpers powered by optional LLM calls."""
from __future__ import annotations

import logging
from typing import Dict, List, Optional

try:  # pragma: no cover - import fallback behaviour exercised indirectly
    import requests  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - dependency is optional for tests
    from types import SimpleNamespace

    requests = SimpleNamespace(post=None)  # type: ignore

from pdf2twine.services import (
    DependencyError,
    OpenRouterRequest,
    load_api_token,
    perform_openrouter_completion,
)

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "openai/gpt-4o-mini"


def get_api_token() -> str:
    """Public helper retained for backwards compatibility and tests."""

    return load_api_token()


def _call_llm(prompt: str, model_id: str) -> str:
    """Perform a completion request and return the raw text output."""

    try:
        token = get_api_token()
        return perform_openrouter_completion(
            request=OpenRouterRequest(
                prompt=prompt,
                model_id=model_id,
                temperature=0.1,
                timeout=30,
                max_tokens=50,
            ),
            requests_module=requests,
            token=token,
        )
    except DependencyError as exc:
        raise ValueError(str(exc)) from exc


def summarize_scene(scene: str, model_id: Optional[str] = None) -> str:
    """Summarise a single scene using the configured LLM."""

    if not scene:
        raise ValueError("Scene text must not be empty")

    model = model_id or DEFAULT_MODEL
    prompt = (
        "Summarize the following scene in exactly 25 words or fewer. "
        "Focus on the key action, characters, and narrative elements. "
        "Be precise and concise.\n\n"
        f"Scene text:\n{scene[:2000]}"
    )
    if len(scene) > 2000:
        prompt += "..."
    prompt += "\n\nSummary (≤25 words):"

    try:
        summary = _call_llm(prompt, model)
    except ValueError as exc:
        # Surface the original error so callers can choose a fallback strategy
        raise
    except Exception as exc:  # pragma: no cover - network errors mocked in tests
        logger.warning("OpenRouter API request failed: %s", exc)
        raise ValueError("Failed to call OpenRouter API") from exc

    summary = summary.strip()
    words = summary.split()
    if len(words) > 25:
        logger.warning("Summary has %s words (>25): %s", len(words), summary)
        summary = " ".join(words[:25])

    return summary


def summarize_scenes(scenes: List[str], model_id: Optional[str] = None) -> List[Dict[str, str]]:
    """Summarise a sequence of scenes using the configured model."""

    summarized_scenes: List[Dict[str, str]] = []
    if not scenes:
        return summarized_scenes

    for index, scene in enumerate(scenes, start=1):
        logger.info("Summarizing scene %s/%s", index, len(scenes))
        try:
            summary = summarize_scene(scene, model_id)
        except ValueError as exc:
            logger.warning("Failed to summarize scene %s: %s", index, exc)
            fallback = scene[:100].replace("\n", " ")
            if len(scene) > 100:
                fallback += "..."
            summary = fallback

        summarized_scenes.append(
            {
                "text": scene,
                "summary": summary,
                "id": f"scene_{index}",
            }
        )

    logger.info("Successfully processed %s scenes", len(summarized_scenes))
    return summarized_scenes


__all__ = ["summarize_scene", "summarize_scenes", "get_api_token"]
