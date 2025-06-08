"""PDF text extraction functionality."""
import logging
from pathlib import Path
from typing import Union

logger = logging.getLogger(__name__)


def extract(path: Union[str, Path]) -> str:
    """
    Extract text from a PDF file.
    
    Uses pdfminer.six as the primary extraction method, with pymupdf as fallback.
    
    Args:
        path: Path to the PDF file
        
    Returns:
        Extracted text as a string
        
    Raises:
        FileNotFoundError: If the PDF file doesn't exist
        ValueError: If the file is not a valid PDF or extraction fails
    """
    path = Path(path)
    
    if not path.exists():
        raise FileNotFoundError(f"PDF file not found: {path}")
    
    if not path.suffix.lower() == '.pdf':
        raise ValueError(f"File must be a PDF: {path}")
    
    # Try pdfminer.six first
    try:
        return _extract_with_pdfminer(path)
    except Exception as e:
        logger.warning(f"pdfminer.six extraction failed: {e}")
        
        # Fallback to pymupdf
        try:
            return _extract_with_pymupdf(path)
        except Exception as e2:
            logger.error(f"pymupdf extraction also failed: {e2}")
            raise ValueError(f"Failed to extract text from PDF: {path}") from e2


def _extract_with_pdfminer(path: Path) -> str:
    """Extract text using pdfminer.six."""
    from pdfminer.high_level import extract_text
    
    text = extract_text(str(path))
    
    if not text or len(text.strip()) < 10:
        raise ValueError("Extracted text is too short or empty")
    
    return text


def _extract_with_pymupdf(path: Path) -> str:
    """Extract text using pymupdf as fallback."""
    import fitz  # pymupdf
    
    doc = fitz.open(str(path))
    text_parts = []
    
    for page_num in range(doc.page_count):
        page = doc.load_page(page_num)
        text_parts.append(page.get_text())
    
    doc.close()
    
    text = '\n'.join(text_parts)
    
    if not text or len(text.strip()) < 10:
        raise ValueError("Extracted text is too short or empty")
    
    return text 