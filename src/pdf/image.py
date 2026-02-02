import fitz  # PyMuPDF
from PIL import Image
import uuid
import io
import mimetypes
from lxml import etree
import base64
import hashlib
from service.storage import LocalStorage

def image_hash(image_bytes):
    """Generates an MD5 hash of image bytes to identify duplicates."""
    return hashlib.md5(image_bytes).hexdigest()

class PDFTemplateProcessor:
    """Processes PDF pages to extract portrait and inline images."""
    
    def __init__(self, storage: LocalStorage):
        self.storage = storage

    def get_portrait_image(self, pdf_path, page_n):
        """Extracts images from a specific PDF page and saves them to local storage."""
        try:
            doc = fitz.open(pdf_path)
        except Exception as e:
            # Error handling for opening PDF
            return [], []

        if page_n < 1 or page_n > len(doc):
            raise ValueError(f"The PDF has only {len(doc)} pages. 'page_n' must be between 1 and {len(doc)}.")

        page = doc[page_n - 1]
        page_width = page.rect.width
        page_height = page.rect.height

        xref_images_1 = []
        xref_images_2 = []
        fallback_images = []  # Placeholder for potential fallback logic

        info_blocks = page.get_image_info(xrefs=True)
        images = page.get_images(full=True)
        
        # Iterate all images in page
        for img_idx, img_info in enumerate(images):
            xref = img_info[0]
            smask = img_info[1]  # mask if exists

            if not xref or xref == 0:
                continue  # skip fallback images

            try:
                base_pix = fitz.Pixmap(doc, xref)

                masked = False
                if smask and smask != 0:
                    # Apply mask as alpha channel
                    mask_pix = fitz.Pixmap(doc, smask)
                    rgba_pix = fitz.Pixmap(base_pix, 1)  # clone as RGBA
                    rgba_pix.set_alpha(mask_pix.samples)
                    final_pix = rgba_pix
                    mask_pix = None
                    masked = True
                else:
                    if base_pix.alpha:  # already has alpha -> preserve it
                        final_pix = base_pix
                    else:
                        # force RGBA so PNG will have transparent background instead of black
                        final_pix = fitz.Pixmap(base_pix, 1)

                # Filter info_blocks for this xref
                blocks = [ib for ib in info_blocks if ib.get("xref") == xref]
                for _, block in enumerate(blocks):
                    bbox = block.get("bbox")
                    transform = block.get("transform")

                    # Convert Pixmap to PIL.Image
                    img_bytes = final_pix.tobytes("png")
                    imageData = Image.open(io.BytesIO(img_bytes))

                    img = imageData.convert("RGBA")  # Ensure RGBA
                    alpha = img.getchannel("A")
                    if all(pixel == 0 for pixel in alpha.getdata()):
                        continue

                    new_width, new_height = imageData.size
                    resized_image = imageData
                    if transform:
                        new_width = int(transform[0])
                        new_height = int(transform[3])
                        resized_image = imageData.resize((new_width, new_height), Image.LANCZOS)

                    # Size and position
                    left, top = int(bbox[0]), int(bbox[1])

                    # Save image locally
                    buffer = io.BytesIO()
                    resized_image.save(buffer, format="PNG")
                    buffer.seek(0)
                    mime_type, _ = mimetypes.guess_type("file.png")
                    content_type = mime_type or "application/octet-stream"
                    local_path = f"resized_images/{uuid.uuid4()}.png"
                    url = self.storage.upload_bytes(buffer, local_path, content_type)

                    # Append result with metadata
                    xref_images_1.append({
                        "type": "image",
                        "url": url,
                        "width": new_width,
                        "height": new_height,
                        "left": left,
                        "top": top,
                        "transform": list(block.get("transform") or []),
                        "metadata": {
                            "masked": masked,
                            "xref": xref,
                        }
                    })

                final_pix = None
                base_pix = None

            except Exception:
                continue  # Continue to next image if this fails

        # Extract xref hashes for inline image comparison
        xref_zero = [ib for ib in info_blocks if ib.get("xref") and ib.get("xref") > 0]
        xref_hashes = set()
        for xref_info in xref_zero:
            xref = xref_info.get("xref")
            try:
                base_image = doc.extract_image(xref)
                img_bytes = base_image["image"]
                xref_hashes.add(image_hash(img_bytes))
            except Exception:
                continue

        # Get SVG
        svg = page.get_svg_image()
        # Parse SVG
        root = etree.fromstring(svg.encode("utf-8"))
        ns = {
            'svg': 'http://www.w3.org/2000/svg',
            'xlink': 'http://www.w3.org/1999/xlink'
        }
        svg_width = root.attrib.get("width", "unknown")
        svg_height = root.attrib.get("height", "unknown")

        # Find all images inside <mask>
        masked_images = set()
        for mask in root.xpath(".//svg:mask", namespaces=ns):
            for image in mask.xpath(".//svg:image", namespaces=ns):
                href = image.get('{http://www.w3.org/1999/xlink}href')
                if href and href.startswith("data:image"):
                    masked_images.add(href.split(",")[1])

        # Iterate all inline images in SVG
        for i, image in enumerate(root.xpath(".//svg:image", namespaces=ns)):
            href = image.get('{http://www.w3.org/1999/xlink}href')
            if not href or not href.startswith("data:image"):
                continue

            img_b64 = href.split(",")[1]
            if img_b64 in masked_images:
                continue

            try:
                img_bytes = base64.b64decode(img_b64.strip())
            except Exception:
                continue

            if image_hash(img_bytes) in xref_hashes:
                continue

            # Get width/height from SVG
            img_width = image.attrib.get("width", "unknown")
            img_height = image.attrib.get("height", "unknown")
            left = image.attrib.get("x", 0)
            top = image.attrib.get("y", 0)

            try:
                img_width = float(img_width)
                img_height = float(img_height)
                left = float(left)
                top = float(top)
            except Exception:
                continue  # Skip this image

            # Scale proportionally if SVG width != page width
            try:
                svg_width_float = float(svg_width)
                scale = page_width / svg_width_float if svg_width_float != 0 else 1.0
                img_width = int(img_width * scale)
                img_height = int(img_height * scale)
            except Exception:
                continue  # Skip this image

            # Save image locally
            try:
                buffer = io.BytesIO()
                Image.open(io.BytesIO(img_bytes)).save(buffer, format="PNG")
                buffer.seek(0)
                local_path = f"resized_images/{uuid.uuid4()}.png"
                url = self.storage.upload_bytes(buffer, local_path, "image/png")
            except Exception:
                continue

            # Append image to xref_images
            xref_images_2.append({  
                "type": "image",
                "url": url,
                "width": img_width,
                "height": img_height,
                "left": left,
                "top": top,
                "transform": [],  # empty if no info
                "metadata": {}    # empty object
            })

        xref_images = xref_images_2 + xref_images_1
        doc.close()

        return xref_images, fallback_images