import re
import os
from io import BytesIO
import fitz  # PyMuPDF
from fontTools.ttLib import TTFont
from service.storage import LocalStorage

class FontStylePDF:
    """
    Extracts embedded fonts from PDF files and saves them to local storage.
    """
    
    def __init__(self, storage: LocalStorage):
        self.storage = storage

    def extract_fonts_from_pdf(self, pdf_path):
        """
        Extract embedded fonts from a PDF using PyMuPDF.
        Returns a list of dictionaries with font metadata and local URLs.
        """
        fonts = []
        seen_font_ids = set()
        seen_font_names = set()

        doc = fitz.open(pdf_path)
        try:
            for page_num in range(len(doc)):
                page = doc[page_num]
                try:
                    font_list = page.get_fonts(full=True)
                except Exception:
                    font_list = []

                for font_entry in font_list:
                    xref = None
                    fontname = None
                    for part in font_entry:
                        if isinstance(part, int) and xref is None:
                            xref = part
                        elif isinstance(part, str) and fontname is None:
                            fontname = part

                    font_id = xref if xref is not None else str(font_entry)
                    if font_id in seen_font_ids:
                        continue

                    # Attempt to extract font bytes
                    font_bytes = None
                    ext = None
                    try:
                        if xref is not None:
                            info = doc.extract_font(xref)
                            if isinstance(info, tuple) and len(info) == 4:
                                _, font_ext, _, font_data = info
                                font_bytes = font_data
                                ext = font_ext
                                if isinstance(ext, str):
                                    ext = ext.lower()
                                    if not ext.startswith("."):
                                        ext = "." + ext
                            elif isinstance(info, dict):
                                font_bytes = info.get("file") or info.get("fontfile") or info.get("font")
                                ext = info.get("ext") or info.get("type")
                                if isinstance(ext, str):
                                    ext = ext.lower()
                                    if not ext.startswith("."):
                                        ext = "." + ext
                    except Exception:
                        pass

                    # Fallback extraction method
                    if not font_bytes and xref is not None:
                        try:
                            xobj = doc.xref_stream(xref)
                            if xobj:
                                font_bytes = xobj
                                ext = ext or ".ttf"
                        except Exception:
                            pass

                    if not font_bytes:
                        seen_font_ids.add(font_id)
                        continue

                    ext = ext or ".ttf"

                    # Extract metadata from font bytes
                    family_name, postscript_name, full_font_name = self._get_font_names_from_bytes(
                        font_bytes, ext
                    )

                    if (family_name == "Unknown" or postscript_name == "Unknown" or full_font_name == "Unknown"):
                        seen_font_ids.add(font_id)
                        continue

                    # Avoid duplicates
                    if postscript_name in seen_font_names:
                        seen_font_ids.add(font_id)
                        continue

                    clean_name = re.sub(r"[^a-zA-Z0-9_]", "_", postscript_name or family_name)
                    filename = f"{clean_name}{ext}"
                    local_path = f"fonts/{filename}"

                    try:
                        url = self.storage.upload_bytes(BytesIO(font_bytes), local_path, "font/ttf")
                    except Exception:
                        url = None

                    fonts.append({
                        "fontFamily": family_name,
                        "fullFontName": full_font_name,
                        "postScriptName": postscript_name,
                        "fontUrl": url,
                    })

                    seen_font_names.add(postscript_name)
                    seen_font_ids.add(font_id)
        finally:
            doc.close()

        return fonts

    @staticmethod
    def _get_font_names_from_bytes(data: bytes, ext: str):
        """
        Extracts font names using FontTools from raw bytes.
        """
        try:
            font = TTFont(BytesIO(data))
            name_table = font["name"]
            family_name = None
            subfamily_name = None
            full_name = None
            postscript_name = None

            for record in name_table.names:
                try:
                    name_str = record.string.decode(record.getEncoding(), errors="ignore")
                except Exception:
                    continue

                if record.nameID == 1 and not family_name:
                    family_name = name_str
                elif record.nameID == 2 and not subfamily_name:
                    subfamily_name = name_str
                elif record.nameID == 4 and not full_name:
                    full_name = name_str
                elif record.nameID == 6 and not postscript_name:
                    postscript_name = name_str

            if not full_name and family_name and subfamily_name:
                full_name = f"{family_name} {subfamily_name}"
            elif not full_name and family_name:
                full_name = family_name

            return family_name or "Unknown", postscript_name or "Unknown", full_name or "Unknown"

        except Exception:
            return "Unknown", "Unknown", "Unknown"
