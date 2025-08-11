# app/pdf_utils.py
# Utilities for rendering and scaling PDFs (server-side helpers)
from typing import Tuple
import fitz  # PyMuPDF
from PIL import Image
import io

def render_pdf_page_to_png(pdf_bytes: bytes, page_number: int = 0, zoom: float = 1.5) -> Tuple[bytes, int, int]:
    """Render pdf page to PNG bytes, return (png_bytes, width_px, height_px)."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page = doc.load_page(page_number)
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    png = pix.tobytes("png")
    return png, pix.width, pix.height
