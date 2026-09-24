import io
import os
import random

import pymupdf as fitz
from PIL import Image, ImageDraw


def make_digital_pdf(path: str, pages: int = 5, keywords=None) -> str:
    """PDF with pure digital text (no images)."""
    doc = fitz.open()
    keywords = keywords or ["NIT 900.123.456-7", "FACTURA", "ANDREH"]
    for i in range(pages):
        page = doc.new_page(width=595, height=842)
        line = f"Página {i+1}\n"
        line += "\n".join(keywords)
        line += f"\nReporte financiero trimestral NIT de auditoría {i}.\n"
        page.insert_text((50, 70), line, fontsize=11)
    doc.save(path)
    doc.close()
    return path


def make_image_bytes(text_lines, width=900, height=400, bg=(255, 255, 255)) -> bytes:
    img = Image.new("RGB", (width, height), color=bg)
    draw = ImageDraw.Draw(img)
    y = 40
    for t in text_lines:
        draw.text((40, y), t, fill=(20, 20, 20))
        y += 50
    out = io.BytesIO()
    img.save(out, format="PNG")
    return out.getvalue()


def make_scanned_pdf(path: str, pages: int = 2) -> str:
    """PDF whose pages are pure images (scanned), no digital text."""
    doc = fitz.open()
    for i in range(pages):
        page = doc.new_page(width=595, height=842)
        # Image with the SAME aspect ratio as the page, covering it fully.
        img_bytes = make_image_bytes(
            [f"DOCUMENTO ESCANEADO {i+1}", "FACTURA", "NIT 900123456"],
            width=595, height=842,
        )
        page.insert_image(fitz.Rect(0, 0, 595, 842), stream=img_bytes)
    doc.save(path)
    doc.close()
    return path


def make_corrupt_pdf(path: str) -> str:
    with open(path, "wb") as f:
        f.write(b"%PDF-1.4\n garbage not a valid pdf structure")
    return path


def make_mixed_pdf(path: str, digital_pages: int = 3, image_pages: int = 2) -> str:
    """Mixed: some digital pages, some pages with large embedded images."""
    doc = fitz.open()
    for i in range(digital_pages):
        page = doc.new_page(width=595, height=842)
        page.insert_text((50, 70), f"Texto digital página {i+1} con keyword NIT_999_TEST", fontsize=11)
    for j in range(image_pages):
        page = doc.new_page(width=595, height=842)
        img_bytes = make_image_bytes([f"RECIBO EMBEBIDO {j}", "keywordNIT_EMB"] )
        page.insert_image(fitz.Rect(50, 100, 545, 400), stream=img_bytes)
    doc.save(path)
    doc.close()
    return path