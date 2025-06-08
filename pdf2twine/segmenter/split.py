"""Text splitting functionality for scene segmentation."""
import re
import logging
from typing import List, Optional
import json
import requests
import os
from pathlib import Path

logger = logging.getLogger(__name__)


def split_heuristic(text: str, min_length: int = 200) -> List[str]:
    """
    Split text into scenes using heuristic rules.

    Splits on blank lines and filters blocks to be >min_length characters.
    Acceptance criteria: ≥90% of blocks should start with capital letter.

    Args:
        text: Input text to split
        min_length: Minimum length for a scene block

    Returns:
        List of scene text blocks
    """
    # Split on double newlines (blank lines)
    raw_blocks = re.split(r'\n\s*\n', text)

    # Filter blocks by minimum length and clean whitespace
    scenes = []
    for block in raw_blocks:
        cleaned = block.strip()
        if len(cleaned) >= min_length:
            scenes.append(cleaned)

    # Log statistics for validation
    if scenes:
        capital_starts = sum(1 for scene in scenes if scene and scene[0].isupper())
        capital_percentage = (capital_starts / len(scenes)) * 100
        logger.info(f"Heuristic split: {len(scenes)} scenes, {capital_percentage:.1f}% start with capital")

        if capital_percentage < 90:
            logger.warning(f"Only {capital_percentage:.1f}% of scenes start with capital (target: ≥90%)")

    return scenes


def split_llm(text: str, max_scenes: int = 200, model_id: Optional[str] = None) -> List[str]:
    """
    Split text into scenes using LLM analysis.

    Uses OpenAI API to intelligently segment text into narrative scenes.
    Acceptance criteria: Returns JSON list with ≤max_scenes scenes.

    Args:
        text: Input text to split
        max_scenes: Maximum number of scenes to return
        model_id: OpenAI model to use (defaults to gpt-4o-mini)

    Returns:
        List of scene text blocks
    """
    if model_id is None:
        model_id = "openai/gpt-4o-mini"

    # Get API token
    try:
        api_token = os.environ.get("API_TOKEN") or os.environ.get("OPENROUTER_API_KEY") or Path('.API_TOKEN').read_text().strip()
    except Exception as e:
        logger.warning(f"Failed to get API token: {e}")
        raise ValueError("OpenRouter API token not found") from e

    # Prepare prompt
    prompt = f"""Analyze the following text and split it into narrative scenes. Each scene should be a coherent unit of action or dialogue.

Return your response as a JSON array where each element is the text of one scene. Do not include any other text or formatting.

Requirements:
- Maximum {max_scenes} scenes
- Each scene should be substantial (at least 100 characters)
- Preserve the original text exactly - do not summarize or modify
- Focus on natural narrative breaks

Text to analyze:
{text[:10000]}{"..." if len(text) > 10000 else ""}"""

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
            scenes = json.loads(llm_output)
            if not isinstance(scenes, list):
                raise ValueError("LLM response is not a JSON array")

            # Validate scene count
            if len(scenes) > max_scenes:
                logger.warning(f"LLM returned {len(scenes)} scenes, truncating to {max_scenes}")
                scenes = scenes[:max_scenes]

            # Filter out very short scenes
            scenes = [scene for scene in scenes if isinstance(scene, str) and len(scene.strip()) >= 50]

            logger.info(f"LLM split: {len(scenes)} scenes")
            return scenes

        # except json.JSONDecodeError as e:
        #     logger.error(f"Failed to parse LLM JSON response: {e}")
        #     logger.debug(f"LLM output: {llm_output[:500]}...")
        #     raise ValueError("LLM did not return valid JSON") from e
        except json.JSONDecodeError:
            # Attempt to extract JSON array from output
            logger.warning("LLM output not valid JSON, attempting substring extraction")
            first = llm_output.find('[')
            last = llm_output.rfind(']')
            if first != -1 and last != -1 and last > first:
                snippet = llm_output[first:last+1]
                try:
                    scenes = json.loads(snippet)
                    if not isinstance(scenes, list):
                        raise ValueError
                except Exception:
                    logger.error("Failed to parse extracted JSON snippet")
                    scenes = None
            else:
                scenes = None
            if not isinstance(scenes, list):
                logger.error(f"Final LLM output extract: {snippet if 'snippet' in locals() else llm_output[:200]}...")
                raise ValueError("LLM did not return valid JSON")

    except Exception as e:
        logger.warning(f"OpenRouter API request failed: {e}")
        raise ValueError("Failed to call OpenRouter API") from e


def split_auto(text: str, force_llm: bool = False, **kwargs) -> List[str]:
    """
    Automatically choose the best splitting method.

    Uses heuristic method by default, unless force_llm=True.
    In the future, this could benchmark both methods and choose the faster one.

    Args:
        text: Input text to split
        force_llm: If True, force use of LLM method
        **kwargs: Additional arguments passed to the chosen method

    Returns:
        List of scene text blocks
    """
    if force_llm:
        try:
            return split_llm(text, **kwargs)
        except Exception as e:
            logger.warning(f"LLM split failed, falling back to heuristic: {e}")
            # Fallback: ignore LLM-specific kwargs for heuristic
            return split_heuristic(text)
    # Default to heuristic split; allow min_length override if provided
    min_len = kwargs.get('min_length', None)
    return split_heuristic(text, min_length=min_len) if min_len is not None else split_heuristic(text)
