"""Shared helpers for interacting with external LLM services."""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Optional, Sequence

logger = logging.getLogger(__name__)


class DependencyError(RuntimeError):
    """Raised when an optional dependency required for LLM features is missing."""


class APITokenError(RuntimeError):
    """Raised when an OpenRouter API token cannot be located."""


@dataclass(frozen=True)
class OpenRouterRequest:
    """Configuration for an OpenRouter completion request."""

    prompt: str
    model_id: str
    temperature: float = 0.1
    timeout: int = 60
    max_tokens: Optional[int] = None


def ensure_requests_available(requests_module: Any) -> Any:
    """Ensure the optional ``requests`` dependency is available."""

    if requests_module is None:  # pragma: no cover - exercised via tests
        raise DependencyError(
            "The 'requests' package is required for LLM features. Install "
            "it or run with force_llm=False to use offline heuristics."
        )
    return requests_module


def load_api_token() -> str:
    """Retrieve the OpenRouter API token from the environment or a file."""

    token = os.environ.get("API_TOKEN") or os.environ.get("OPENROUTER_API_KEY")
    if token:
        return token.strip()

    token_path = Path(".API_TOKEN")
    if token_path.exists():
        content = token_path.read_text(encoding="utf-8").strip()
        if content:
            return content

    raise APITokenError("OpenRouter API token not found")


def perform_openrouter_completion(
    *,
    request: OpenRouterRequest,
    requests_module: Any,
    token: Optional[str] = None,
) -> str:
    """Execute a completion request against the OpenRouter API."""

    requests_impl = ensure_requests_available(requests_module)
    token = token or load_api_token()

    payload: dict[str, Any] = {
        "model": request.model_id,
        "messages": [{"role": "user", "content": request.prompt}],
        "temperature": request.temperature,
    }
    if request.max_tokens is not None:
        payload["max_tokens"] = request.max_tokens

    response = requests_impl.post(
        url="https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
        timeout=request.timeout,
    )
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"]


def extract_json_value(
    raw: str,
    *,
    validator: Callable[[Any], bool],
    error_message: str,
) -> Any:
    """Parse JSON content from a raw LLM response."""

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = None

    if parsed is None or not validator(parsed):
        start = raw.find("[")
        end = raw.rfind("]")
        if start == -1 or end <= start:
            start = raw.find("{")
            end = raw.rfind("}")
        if start != -1 and end > start:
            snippet = raw[start : end + 1]
            try:
                parsed = json.loads(snippet)
            except Exception:  # pragma: no cover - defensive
                parsed = None
        else:
            parsed = None

    if parsed is None or not validator(parsed):
        logger.error("Failed to parse JSON from LLM response: %s", raw[:200])
        raise ValueError(error_message)

    return parsed


def ensure_list(
    value: Any,
    *,
    item_validator: Callable[[Any], bool],
    allow_empty: bool = True,
) -> Sequence[Any]:
    """Ensure a parsed JSON value is a list meeting validation criteria."""

    if not isinstance(value, list):
        raise ValueError("LLM response is not a JSON array")
    if not allow_empty and not value:
        raise ValueError("LLM response returned an empty array")
    if not all(item_validator(item) for item in value):
        raise ValueError("LLM response contains invalid elements")
    return value


def ensure_dict(value: Any) -> dict[str, Any]:
    """Ensure a parsed JSON value is a dictionary."""

    if not isinstance(value, dict):
        raise ValueError("LLM response is not a JSON object")
    return value

