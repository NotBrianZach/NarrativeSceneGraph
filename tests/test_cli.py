"""Tests for pdf2twine CLI module."""
import pytest
from unittest.mock import patch
from pathlib import Path
import tempfile


def test_cli_module_imports():
    """Test that the CLI module can be imported."""
    from pdf2twine import cli
    assert hasattr(cli, 'main')
    assert hasattr(cli, 'setup_logging')


def test_cli_help():
    """Test that CLI shows help when no arguments provided."""
    from pdf2twine.cli import main
    
    with patch('sys.argv', ['pdf2twine']):
        with pytest.raises(SystemExit) as exc_info:
            main()
        # argparse exits with code 2 for missing required arguments
        assert exc_info.value.code == 2


def test_cli_dry_run():
    """Test CLI dry run functionality."""
    from pdf2twine.cli import main
    
    with tempfile.NamedTemporaryFile(suffix='.pdf') as temp_pdf:
        temp_pdf.write(b'dummy pdf content')
        temp_pdf.flush()
        
        with patch('sys.argv', [
            'pdf2twine', 
            temp_pdf.name, 
            'output.twee', 
            '--dry-run'
        ]):
            result = main()
            assert result == 0  # Should succeed in dry run


def test_cli_invalid_input_file():
    """Test CLI with non-existent input file."""
    from pdf2twine.cli import main
    
    with patch('sys.argv', ['pdf2twine', 'nonexistent.pdf', 'output.twee']):
        result = main()
        assert result == 1  # Should fail with error code 1


def test_cli_non_pdf_input():
    """Test CLI with non-PDF input file."""
    from pdf2twine.cli import main
    
    with tempfile.NamedTemporaryFile(suffix='.txt') as temp_file:
        temp_file.write(b'not a pdf')
        temp_file.flush()
        
        with patch('sys.argv', ['pdf2twine', temp_file.name, 'output.twee']):
            result = main()
            assert result == 1  # Should fail with error code 1 