"""Tests for pdf2twine segmenter module."""
import pytest
from pdf2twine.segmenter import split_heuristic, split_llm, split_auto


def test_split_heuristic_basic():
    """Test basic heuristic splitting functionality."""
    text = """This is the first scene. It has multiple sentences and is quite long to meet the minimum length requirement.

This is the second scene. It also has multiple sentences and meets the length requirement for being a proper scene.

This is the third scene. Like the others, it contains enough text to be considered a valid scene by our heuristic splitter."""
    
    scenes = split_heuristic(text, min_length=50)
    
    assert len(scenes) == 3
    assert all(len(scene) >= 50 for scene in scenes)
    assert "first scene" in scenes[0]
    assert "second scene" in scenes[1] 
    assert "third scene" in scenes[2]


def test_split_heuristic_capital_letters():
    """Test that most scenes start with capital letters."""
    text = """Chapter One begins here. This is a proper narrative scene with good structure.

Another scene starts here. This one also follows proper capitalization rules.

Yet another scene begins. This maintains the pattern of starting with capitals.

A final scene concludes. This completes our test with proper formatting."""
    
    scenes = split_heuristic(text, min_length=50)
    
    capital_starts = sum(1 for scene in scenes if scene and scene[0].isupper())
    capital_percentage = (capital_starts / len(scenes)) * 100
    
    # Should meet the 90% target for well-formatted text
    assert capital_percentage >= 90


def test_split_heuristic_filters_short_blocks():
    """Test that short blocks are filtered out."""
    text = """This is a long scene that meets the minimum length requirement for inclusion.

Short.

Another long scene that definitely meets the minimum length requirement and should be included."""
    
    scenes = split_heuristic(text, min_length=50)
    
    assert len(scenes) == 2  # Short block should be filtered out
    assert all(len(scene) >= 50 for scene in scenes)


def test_split_auto_defaults_to_heuristic():
    """Test that split_auto uses heuristic method by default."""
    text = """First scene with sufficient length.

Second scene with sufficient length."""
    
    heuristic_result = split_heuristic(text, min_length=20)
    auto_result = split_auto(text, min_length=20)
    
    assert heuristic_result == auto_result


def test_split_auto_force_llm_flag():
    """Test that split_auto respects force_llm flag."""
    text = """First scene with sufficient length.

Second scene with sufficient length."""
    
    # This test will be skipped if no API token is available
    try:
        llm_result = split_auto(text, force_llm=True, max_scenes=10)
        assert isinstance(llm_result, list)
    except ValueError as e:
        if "API token not found" in str(e):
            pytest.skip("No API token available for LLM testing")
        else:
            raise


def test_split_heuristic_empty_text():
    """Test handling of empty text."""
    scenes = split_heuristic("", min_length=50)
    assert scenes == []


def test_split_heuristic_no_valid_scenes():
    """Test when no scenes meet minimum length."""
    text = "Short.\n\nAlso short.\n\nToo short."
    scenes = split_heuristic(text, min_length=100)
    assert scenes == [] 