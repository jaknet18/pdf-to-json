import fitz  # PyMuPDF
import re
import json
import os
from difflib import get_close_matches

class PDFTextExtractor:
    """
    Extracts text blocks from PDF pages and matches them with available font styles.
    """

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.default_font = {
            "fontFamily": "Arial",
            "fullFontName": "Arial",
            "postScriptName": "Arial",
            "fontUrl": "https://code-test-ai.s3.us-east-1.amazonaws.com/fonts/BCDGEE_ArialMT.ttf",
        }
        self.common_fonts = self._load_common_fonts()

    def _load_common_fonts(self):
        """Loads common fonts from the resources directory."""
        resource_path = os.path.join(os.path.dirname(__file__), "..", "resources", "fonts.json")
        try:
            if os.path.exists(resource_path):
                with open(resource_path, "r") as f:
                    return json.load(f)
        except Exception:
            pass
        return []

    def extract(self, font_styles: list):
        """
        Extracts text from the PDF and returns a structured list of pages.
        """
        pdf_document = fitz.open(self.file_path)
        pdf_data = []
        
        # Combine provided styles with pre-defined common fonts
        all_styles = font_styles + self.common_fonts
        
        for page_index, page in enumerate(pdf_document, start=1):
            text_dict = page.get_text("dict")
            blocks = text_dict.get("blocks", [])
            pdf_items = []

            for block in blocks:
                if block.get("type") != 0:  # Only process text blocks
                    continue

                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        font_info = self._match_font(span.get("font", ""), all_styles)
                        
                        pdf_items.append({
                            "type": "text",
                            "text": span.get("text", ""),
                            "left": span["bbox"][0],
                            "top": span["bbox"][3] - span["size"],
                            "width": span["bbox"][2] - span["bbox"][0],
                            "height": span["bbox"][3] - span["bbox"][1],
                            "fontWeight": "bold" if "bold" in span.get("font", "").lower() else "normal",
                            "fontSize": span["size"],
                            "fontFamily": font_info.get("fullFontName", "Arial"),
                            "fontUrl": font_info.get("fontUrl", self.default_font["fontUrl"]),
                            "fill": "#{:06x}".format(span["color"] & 0xFFFFFF),
                            "opacity": span["alpha"] / 255.0
                        })

            pdf_data.append({
                "number": page_index,
                "size": {
                    "width": text_dict.get("width", 0),
                    "height": text_dict.get("height", 0)
                },
                "pdf_items": pdf_items
            })

        pdf_document.close()
        return pdf_data

    def _clean_font_name(self, font_name: str) -> str:
        """Removes common PDF font prefixes and suffixes."""
        name = re.sub(r'^[A-Z]{3,6}\+', '', font_name)
        name = re.sub(r'-?MT$', '', name)
        return name.strip()

    def _match_font(self, raw_font_name: str, font_styles: list) -> dict:
        """Attempts to match a raw font name with the best available font style."""
        clean_name = self._clean_font_name(raw_font_name)
        known_names = [font['fullFontName'] for font in font_styles]

        matches = get_close_matches(clean_name, known_names, n=1, cutoff=0.6)
        if matches:
            for font in font_styles:
                if font['fullFontName'] == matches[0]:
                    return font

        return self.default_font