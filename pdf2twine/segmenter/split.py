"""Text splitting functionality for scene segmentation."""
from __future__ import annotations

import logging
import re
from typing import List, Optional

try:  # pragma: no cover - dependency optional for offline tests
    import requests  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    from types import SimpleNamespace

    requests = SimpleNamespace(post=None)  # type: ignore

from pdf2twine.services import (
    APITokenError,
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
    """Expose token retrieval for compatibility with existing tests."""

    return load_api_token()


def split_heuristic(text: str, min_length: int = 200) -> List[str]:
    """Split text into scenes using heuristic rules."""

    raw_blocks = re.split(r"\n\s*\n", text)
    scenes: List[str] = []
    for block in raw_blocks:
        cleaned = block.strip()
        if len(cleaned) >= min_length:
            scenes.append(cleaned)

    if scenes:
        capital_starts = sum(1 for scene in scenes if scene and scene[0].isupper())
        capital_percentage = (capital_starts / len(scenes)) * 100
        logger.info(
            "Heuristic split: %s scenes, %.1f%% start with capital",
            len(scenes),
            capital_percentage,
        )
        if capital_percentage < 90:
            logger.warning(
                "Only %.1f%% of scenes start with capital (target: ≥90%%)",
                capital_percentage,
            )

    return scenes


def _call_llm(prompt: str, model_id: str) -> str:
    try:
        token = get_api_token()
        return perform_openrouter_completion(
            request=OpenRouterRequest(
                prompt=prompt,
                model_id=model_id,
                timeout=60,
                temperature=0.1,
            ),
            requests_module=requests,
            token=token,
        )
    except (DependencyError, APITokenError) as exc:
        raise ValueError(str(exc)) from exc


def split_llm(text: str, max_scenes: int = 200, model_id: Optional[str] = None) -> List[str]:
    """Split text into scenes using LLM analysis."""

    model = model_id or DEFAULT_MODEL
    prompt = (
        "Analyze the following text and split it into narrative scenes. Each scene should be a "
        "coherent unit of action or dialogue.\n\nReturn your response as a JSON array where each "
        "element is the text of one scene. Do not include any other text or formatting.\n\n"
        f"Requirements:\n- Maximum {max_scenes} scenes\n- Each scene should be substantial (at least 100 characters)\n"
        "- Preserve the original text exactly - do not summarize or modify\n- Focus on natural narrative breaks\n\n"
        "Text to analyze:\n"
        f"{text[:10000]}"
    )
    if len(text) > 10000:
        prompt += "..."

    try:
        llm_output = _call_llm(prompt, model)
        scenes_raw = extract_json_value(
            llm_output,
            validator=lambda value: isinstance(value, list),
            error_message="LLM did not return valid JSON",
        )
        scenes: List[str] = []
        for scene in ensure_list(
            scenes_raw,
            item_validator=lambda item: isinstance(item, str) and len(item.strip()) >= 50,
        ):
            scenes.append(scene)

        if len(scenes) > max_scenes:
            logger.warning("LLM returned %s scenes, truncating to %s", len(scenes), max_scenes)
            scenes = scenes[:max_scenes]

        logger.info("LLM split: %s scenes", len(scenes))
        return scenes
    except ValueError:
        raise
    except Exception as exc:  # pragma: no cover - network errors mocked in tests
        logger.warning("OpenRouter API request failed: %s", exc)
        raise ValueError("Failed to call OpenRouter API") from exc


def split_auto(text: str, force_llm: bool = False, **kwargs) -> List[str]:
    """Automatically choose the best splitting method."""

    if force_llm:
        try:
            return split_llm(text, **kwargs)
        except ValueError as exc:
            logger.warning("LLM split failed, falling back to heuristic: %s", exc)
            return split_heuristic(text)

    min_len = kwargs.get("min_length")
    if min_len is not None:
        return split_heuristic(text, min_length=min_len)
    return split_heuristic(text)


__all__ = ["split_heuristic", "split_llm", "split_auto", "get_api_token"]
