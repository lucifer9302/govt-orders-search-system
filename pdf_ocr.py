# pdf_ocr.py

import pytesseract
from pdf2image import convert_from_path
import unicodedata
import re

def extract_text_from_pdf(pdf_path: str) -> str:
    """
    OCR a PDF using Tesseract with Malayalam + English
    """
    pages = convert_from_path(
        pdf_path,
        dpi=300
    )

    all_text = []

    for i, page in enumerate(pages):
        text = pytesseract.image_to_string(
            page,
            lang="mal+eng",
            config="--oem 1 --psm 6"
        )

        text = unicodedata.normalize("NFC", text)
        text = re.sub(r"\s+", " ", text)

        all_text.append(text)

    return "\n".join(all_text)
