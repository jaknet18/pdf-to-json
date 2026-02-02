import os
from service.storage import LocalStorage
from pdf.font_style import FontStylePDF
from pdf.image import PDFTemplateProcessor
from pdf.line import PDFGraphicExtractor
from pdf.txt import PDFTextExtractor
from common.utils import (
    move_full_page_rects_first,
    remove_overlaps_from_items,
    remove_full_page_rects,
    filter_images_removing_if_covering_multiple_texts,
    remove_covered_texts,
    add_underline_and_strikethrough,
)
from error.errors import PDFProcessingError

class PDFProcessor:
    """
    Core engine for converting PDF documents into structured JSON data.
    """
    
    def __init__(self, output_dir: str):
        self.storage = LocalStorage(output_dir)
        self.template_processor = PDFTemplateProcessor(self.storage)
        self.font_style_processor = FontStylePDF(self.storage)

    def process(self, pdf_path: str):
        """Processes a PDF file, extracts all components, and saves the output."""
        if not os.path.exists(pdf_path):
            raise PDFProcessingError(f"Input file not found: {pdf_path}")

        print(f"[*] Extracting PDF: {pdf_path}")
        
        try:
            # 1. Component Extraction
            line_extractor = PDFGraphicExtractor(pdf_path)
            lines = line_extractor.extract()
            
            styles = self.font_style_processor.extract_fonts_from_pdf(pdf_path)
            
            text_extractor = PDFTextExtractor(pdf_path)
            texts = text_extractor.extract(styles)
            
            # 2. Page Assembly
            merged_pages_dict = self._merge_items_by_page([lines, texts])
            final_pages = [merged_pages_dict[p] for p in sorted(merged_pages_dict)]
            
            # 3. Post-Processing & Refinement
            for page_data in final_pages:
                page_num = page_data["number"]
                
                # Extract media assets
                portrait_images, fallback_images = self.template_processor.get_portrait_image(pdf_path, page_num)
                
                items = page_data["pdf_items"]
                
                # Cleaning and layering
                items = filter_images_removing_if_covering_multiple_texts(items)
                items = add_underline_and_strikethrough(items)
                
                all_images = [el for el in items if el.get("type") == "image"]
                items = remove_covered_texts(items, all_images)
                items = remove_overlaps_from_items(portrait_images, items, page_data)
                items = remove_full_page_rects(items, page_data)
                
                # final assembly for the page
                enriched_items = portrait_images + items + fallback_images
                page_data["pdf_items"] = move_full_page_rects_first(enriched_items, page_data)

            # 4. Final Output Generation
            pdf_filename = os.path.basename(pdf_path)
            json_filename = f"{os.path.splitext(pdf_filename)[0]}.json"
            output_path = self.storage.upload_json(json_filename, final_pages)
            
            print(f"[+] Processing complete. Output saved to: {output_path}")
            return output_path

        except Exception as e:
            raise PDFProcessingError(f"Failed to process PDF: {str(e)}")

    def _merge_items_by_page(self, items_lists):
        """Helper to organize extracted components by page number."""
        merged = {}
        for item_list in items_lists:
            for page_entry in item_list:
                page_num = page_entry["number"]
                if page_num not in merged:
                    merged[page_num] = {
                        "number": page_num,
                        "size": page_entry["size"],
                        "pdf_items": list(page_entry["pdf_items"])
                    }
                else:
                    merged[page_num]["pdf_items"].extend(page_entry["pdf_items"])
        return merged
