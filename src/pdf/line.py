import fitz  # PyMuPDF
import math

class PDFGraphicExtractor:
    """
    Extracts vector graphics, rectangles, and paths from PDF pages.
    """
    
    def __init__(self, file_path: str, sensitivity: int = 3):
        self.file_path = file_path
        self.sensitivity = sensitivity

    def _get_distance(self, p1, p2):
        """Calculates distance between two points."""
        return math.hypot(p1.x - p2.x, p1.y - p2.y)

    def extract(self):
        """
        Iterates through the PDF to extract vector drawings.
        """
        doc = fitz.open(self.file_path)
        pages_data = []

        for page_index, page in enumerate(doc, start=1):
            elements = []
            page_width = page.rect.width
            page_height = page.rect.height

            drawings = page.get_drawings()
            for path in drawings:
                fill = path.get("fill", (0, 0, 0))
                hex_fill = None
                if fill:
                    hex_fill = "#{:02x}{:02x}{:02x}".format(
                        int(fill[0]*255), int(fill[1]*255), int(fill[2]*255)
                    )

                color = path.get("color", (0, 0, 0))
                hex_color = None
                if color:
                    hex_color = "#{:02x}{:02x}{:02x}".format(
                        int(color[0]*255), int(color[1]*255), int(color[2]*255)
                    )

                path_str = ""
                started = False
                last_point = None
                num_items = len(path["items"])
                
                for i, item in enumerate(path["items"]):
                    item_type = item[0]
                    is_last = (i == num_items - 1)
                    
                    if item_type == "l" or item_type == "c":  # line or curve
                        if item_type == "l":
                            p0, p1 = item[1], item[2]

                            # Ignore last if coordinates are identical
                            if is_last and int(p0.x) == int(p1.x) and int(p0.y) == int(p1.y):
                                continue

                            # If a subpath was already started and new p0 != last point, close previous subpath
                            if last_point and (int(last_point.x) != int(p0.x) or int(last_point.y) != int(p0.y)):
                                path_str += " Z "
                                path_str += f"M {p0.x:.2f} {p0.y:.2f} "
                                started = True
                            elif not started:
                                path_str += f"M {p0.x:.2f} {p0.y:.2f} "
                                started = True

                            path_str += f"L {p1.x:.2f} {p1.y:.2f} "
                            last_point = p1

                        elif item_type == "c":
                            p0, p1, p2, p3 = item[1:]

                            # Handle subpath transitions for curves
                            if last_point and (int(last_point.x) != int(p0.x) or int(last_point.y) != int(p0.y)):
                                path_str += " Z "
                                path_str += f"M {p0.x:.2f} {p0.y:.2f} "
                                started = True
                            elif not started:
                                path_str += f"M {p0.x:.2f} {p0.y:.2f} "
                                started = True

                            path_str += f"C {p1.x:.2f} {p1.y:.2f}, {p2.x:.2f} {p2.y:.2f}, {p3.x:.2f} {p3.y:.2f} "
                            last_point = p3

                    elif item_type == "re":  # rectangle
                        rect = item[1]
                        elements.append({
                            "type": "rect",
                            "left": rect.x0,
                            "top": rect.y0,
                            "width": rect.width,
                            "height": rect.height,
                            "stroke": hex_color,
                            "fill": hex_fill,
                            "strokeWidth": path.get("width", 1) or 1,
                            "strokeLineCap": (
                                ["butt", "round", "square"][path["lineCap"][0]]
                                if path.get("lineCap") and isinstance(path["lineCap"], (list, tuple))
                                else "butt"
                            ),
                            "strokeLineJoin": (
                                ["miter", "round", "bevel"][int(path["lineJoin"])]
                                if path.get("lineJoin") is not None
                                else "miter"
                            ),
                            "strokeDashArray": (
                                [float(x) for x in path.get("dashes", "").strip("[] 0").split() if x]
                                if path.get("dashes")
                                else []
                            ),
                            "opacity": path.get("stroke_opacity") if path.get("stroke_opacity") is not None else (
                                path.get("fill_opacity") if path.get("fill_opacity") is not None else 1
                            ),
                            "fillRule": "evenodd" if path.get("even_odd") else "nonzero",
                        })

                if path_str:
                    elements.append({
                        "type": "path",
                        "d": path_str.strip() + " Z",
                        "stroke": hex_color,
                        "fill": hex_fill,
                        "strokeWidth": path.get("width", 1) or 1,
                        "strokeLineCap": (
                            ["butt", "round", "square"][path["lineCap"][0]]
                            if path.get("lineCap") and isinstance(path["lineCap"], (list, tuple))
                            else "butt"
                        ),
                        "strokeLineJoin": (
                            ["miter", "round", "bevel"][int(path["lineJoin"])]
                            if path.get("lineJoin") is not None
                            else "miter"
                        ),
                        "strokeDashArray": (
                            [float(x) for x in path.get("dashes", "").strip("[] 0").split() if x]
                            if path.get("dashes")
                            else []
                        ),
                        "opacity": path.get("stroke_opacity") if path.get("stroke_opacity") is not None else (
                            path.get("fill_opacity") if path.get("fill_opacity") is not None else 1
                        ),
                        "fillRule": "evenodd" if path.get("even_odd") else "nonzero",
                        "closed": path.get("closePath", False),
                    })

            pages_data.append({
                "number": page_index,
                "size": {
                    "width": page_width,
                    "height": page_height
                },
                "pdf_items": elements
            })

        doc.close()
        return pages_data