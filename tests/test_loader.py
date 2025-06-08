"""Tests for pdf2twine loader module."""
import pytest
from pathlib import Path
from pdf2twine.loader import extract


def test_extract_mobydick():
    """Test extraction with the mobydick.pdf fixture."""
    text = extract('mobydick.pdf')
    
    # Should return more than 100 characters as specified in acceptance criteria
    assert len(text) > 100
    
    # Should contain expected content
    assert 'HERMAN MELVILLE' in text
    assert 'MOBY' in text
    

def test_extract_nonexistent_file():
    """Test extraction with non-existent file."""
    with pytest.raises(FileNotFoundError):
        extract('nonexistent.pdf')


def test_extract_non_pdf_file(tmp_path):
    """Test extraction with non-PDF file."""
    # Create a temporary text file
    text_file = tmp_path / "test.txt"
    text_file.write_text("This is not a PDF")
    
    with pytest.raises(ValueError, match="File must be a PDF"):
        extract(str(text_file))


def test_extract_with_pathlib_path():
    """Test extraction using pathlib.Path object."""
    path = Path('mobydick.pdf')
    text = extract(path)
    
    assert len(text) > 100
    assert 'HERMAN MELVILLE' in text 