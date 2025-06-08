"""Scene summarization functionality using LLM."""
import logging
from typing import List, Dict, Optional
import json
import requests
import os
from pathlib import Path

logger = logging.getLogger(__name__)


def get_api_token() -> str:
    """Get the OpenRouter API token from environment or file."""
    try:
        return (os.environ.get("API_TOKEN") or
                os.environ.get("OPENROUTER_API_KEY") or
                Path('.API_TOKEN').read_text().strip())
    except FileNotFoundError:
        raise ValueError("OpenRouter API token not found")


def summarize_scene(scene: str, model_id: Optional[str] = None) -> str:
    """
    Summarize a single scene using LLM.

    Args:
        scene: Scene text to summarize
        model_id: OpenAI model to use (defaults to gpt-4o-mini)

    Returns:
        Scene summary (≤25 words)

    Raises:
        ValueError: If API call fails or response is invalid
    """
    if model_id is None:
        model_id = "openai/gpt-4o-mini"

    api_token = get_api_token()

    # Prepare prompt for concise summarization
    prompt = f"""Summarize the following scene in exactly 25 words or fewer. Focus on the key action, characters, and narrative elements. Be precise and concise.

Scene text:
{scene[:2000]}{"..." if len(scene) > 2000 else ""}

Summary (≤25 words):"""

    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_token}"},
            json={
                "model": model_id,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
                "max_tokens": 50,  # Limit tokens to ensure concise output
            },
            timeout=30,
        )
        response.raise_for_status()

        result = response.json()
        summary = result['choices'][0]['message']['content'].strip()

        # Validate word count
        word_count = len(summary.split())
        if word_count > 25:
            logger.warning(f"Summary has {word_count} words (>25): {summary}")
            # Truncate to first 25 words if needed
            summary = ' '.join(summary.split()[:25])

        return summary

    except requests.RequestException as e:
        logger.error(f"OpenRouter API request failed: {e}")
        raise ValueError("Failed to call OpenRouter API") from e


def summarize_scenes(scenes: List[str], model_id: Optional[str] = None) -> List[Dict[str, str]]:
    """
    Summarize multiple scenes using LLM.

    Args:
        scenes: List of scene texts to summarize
        model_id: OpenAI model to use (defaults to gpt-4o-mini)

    Returns:
        List of dictionaries with 'text' and 'summary' keys for each scene

    Raises:
        ValueError: If API call fails or response is invalid
    """
    summarized_scenes = []

    for i, scene in enumerate(scenes):
        logger.info(f"Summarizing scene {i+1}/{len(scenes)}")
        try:
            summary = summarize_scene(scene, model_id)
            summarized_scenes.append({
                'text': scene,
                'summary': summary,
                'id': f"scene_{i+1}"
            })
        except ValueError as e:
            logger.error(f"Failed to summarize scene {i+1}: {e}")
            # Use fallback summary if LLM fails
            fallback = scene[:100].replace('\n', ' ') + ('...' if len(scene) > 100 else '')
            summarized_scenes.append({
                'text': scene,
                'summary': fallback,
                'id': f"scene_{i+1}"
            })

    logger.info(f"Successfully summarized {len(summarized_scenes)} scenes")
    return summarized_scenes
