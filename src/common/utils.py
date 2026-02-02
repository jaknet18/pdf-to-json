def compute_overlap_area(rect1, rect2):
    """Computes intersection area between two rectangles."""
    x1 = max(rect1['left'], rect2['left'])
    y1 = max(rect1['top'], rect2['top'])
    x2 = min(rect1['left'] + rect1['width'], rect2['left'] + rect2['width'])
    y2 = min(rect1['top'] + rect1['height'], rect2['top'] + rect2['height'])

    overlap_width = max(0, x2 - x1)
    overlap_height = max(0, y2 - y1)
    return overlap_width * overlap_height

def area(rect):
    """Calculates the area of a rectangle."""
    return float(rect['width']) * float(rect['height'])

def intersection_area(a, b):
    """Calculates the area of intersection between two rectangles."""
    a_left = float(a['left'])
    a_top = float(a['top'])
    a_right = a_left + float(a['width'])
    a_bottom = a_top + float(a['height'])

    b_left = float(b['left'])
    b_top = float(b['top'])
    b_right = b_left + float(b['width'])
    b_bottom = b_top + float(b['height'])

    x_left = max(a_left, b_left)
    y_top = max(a_top, b_top)
    x_right = min(a_right, b_right)
    y_bottom = min(a_bottom, b_bottom)

    if x_right <= x_left or y_bottom <= y_top:
        return 0

    return (x_right - x_left) * (y_bottom - y_top)

def line_bbox(line):
    """Converts a line object into a bounding box."""
    x0 = min(line["points"]["x0"], line["points"]["x1"])
    x1 = max(line["points"]["x0"], line["points"]["x1"])
    y0 = min(line["points"]["y0"], line["points"]["y1"])
    y1 = max(line["points"]["y0"], line["points"]["y1"])
    return {"left": x0, "top": y0, "width": x1 - x0, "height": y1 - y0}

def remove_overlaps_from_items(base_images, items, page_data, threshold=0.4):
    """Filters out images that are largely covered by other images."""
    page_size = page_data.get("size", {})
    page_width = page_size.get("width")
    page_height = page_size.get("height")

    filtered_items = []
    
    for item in items:
        if item.get("type") != "image":
            filtered_items.append(item)
            continue

        item_area = area(item)
        is_covered = False
        
        for base in base_images:
            if base.get("type") == "image":
                width = base.get("width")
                height = base.get("height")
                
                # Skip comparison if base matches page size closely
                if (width is not None and height is not None
                    and abs(width - page_width) <= 2
                    and abs(height - page_height) <= 2):
                    continue

            inter_area = intersection_area(base, item)
            coverage = inter_area / item_area if item_area else 0
            if coverage >= threshold:
                is_covered = True
                break
        
        if not is_covered:
            filtered_items.append(item)
    
    return filtered_items

def filter_images_removing_if_covering_multiple_texts(data, overlap_threshold=0.8):
    """Removes images that cover multiple text blocks (likely backgrounds)."""
    texts = [item for item in data if item['type'] == 'text']

    result = []
    for item in data:
        if item['type'] != 'image':
            result.append(item)
            continue

        covered_texts_count = 0
        for txt in texts:
            if 'width' not in txt or 'height' not in txt:
                continue
            text_area = txt['width'] * txt['height']
            if text_area == 0:
                continue

            overlap = compute_overlap_area(item, txt)
            overlap_ratio = overlap / text_area

            if overlap_ratio >= overlap_threshold:
                covered_texts_count += 1
                if covered_texts_count >= 2:
                    break

        if covered_texts_count < 2:
            result.append(item)

    return result

def remove_covered_lines(items, images, threshold=0.8):
    """Removes lines that are covered by images."""
    result = []
    for item in items:
        if item["type"] != "line":
            result.append(item)
            continue

        bbox = line_bbox(item)
        bbox_area = area(bbox)

        is_covered = False
        for img in images:
            img_bbox = {
                "left": img["left"],
                "top": img["top"],
                "width": img["width"],
                "height": img["height"]
            }

            if bbox_area == 0:
                result.append(item)
                continue

            inter_area = intersection_area(bbox, img_bbox)
            if inter_area / bbox_area >= threshold:
                is_covered = True
                break

        if not is_covered:
            result.append(item)

    return result

def remove_covered_texts(items, images, threshold=0.6):
    """Removes text elements that are substantially covered by an image."""
    result = []
    for item in items:
        if item.get("type") != "text":
            result.append(item)
            continue

        text_area = area(item)
        covered = False

        for image in images:
            inter_area = intersection_area(item, image)
            coverage = inter_area / text_area if text_area else 0

            if coverage >= threshold:
                covered = True
                break

        if not covered:
            result.append(item)

    return result

def remove_items_covered_by_images(data, images, threshold=0.8):
    """Generic helper to remove items covered by a list of images."""
    def get_bbox(obj):
        if obj['type'] == 'line':
            return line_bbox(obj)
        elif obj['type'] in ('rect', 'text', 'image'):
            return {
                'left': obj['left'],
                'top': obj['top'],
                'width': obj['width'],
                'height': obj['height']
            }
        return None

    result = []
    for item in data:
        if item['type'] not in ['line', 'rect', 'text', 'image']:
            result.append(item)
            continue

        item_bbox = get_bbox(item)
        if not item_bbox:
            result.append(item)
            continue

        item_area = area(item_bbox)
        if item_area == 0:
            result.append(item)
            continue

        is_covered = False
        for img in images:
            inter_area = intersection_area(item_bbox, img)
            overlap_ratio = inter_area / item_area

            if overlap_ratio >= threshold:
                is_covered = True
                break

        if not is_covered:
            result.append(item)

    return result

def remove_full_page_rects(items, page_data):
    """Removes white rectangles that match the exact size of the page."""
    page_size = page_data.get("size", {})
    page_width = page_size.get("width")
    page_height = page_size.get("height")

    if page_width is None or page_height is None:
        return items

    filtered_items = []
    for el in items:
        is_full_page_white_rect = (
            el.get("type") == "rect" and
            el.get("color", "").lower() == "#ffffff" and
            el.get("width") == page_width and
            el.get("height") == page_height
        )
        if not is_full_page_white_rect:
            filtered_items.append(el)

    return filtered_items

def move_full_page_rects_first(items, page_data, tolerance=20):
    """Moves rectangles that approximately match page size to the beginning of the list."""
    page_size = page_data.get("size", {})
    page_width = page_size.get("width")
    page_height = page_size.get("height")

    if page_width is None or page_height is None:
        return items

    full_page_rects = []
    other_items = []

    for el in items:
        if el.get("type") == "rect":
            width = el.get("width")
            height = el.get("height")

            if (width is not None and height is not None
                and abs(width - page_width) <= tolerance
                and abs(height - page_height) <= tolerance):
                full_page_rects.append(el)
                continue

        other_items.append(el)

    return full_page_rects + other_items

def add_underline_and_strikethrough(items):
    """Identifies and adds underline/linethrough flags to text based on nearby rectangles."""
    used_rects = set()

    def rect_signature(r):
        return (round(r["left"], 3), round(r["top"], 3), round(r["width"], 3), round(r["height"], 3))

    underline_margin = 0.5
    linethrough_margin = 1.0

    texts = [el for el in items if el.get("type") == "text"]
    rects = [el for el in items if el.get("type") == "rect"]

    for text_item in texts:
        text_top = text_item["top"]
        text_bottom = text_top + text_item["height"]
        text_center = text_top + text_item["height"] / 2
        text_left = text_item["left"]
        text_right = text_left + text_item["width"]

        for rect in rects:
            if rect.get("height", 0) >= 1:
                continue

            rect_top = rect["top"]
            rect_left = rect["left"]
            rect_right = rect_left + rect["width"]

            if rect_left >= text_left and rect_right <= text_right:
                if text_center <= rect_top <= text_bottom + underline_margin:
                    text_item["underline"] = True
                    used_rects.add(rect_signature(rect))
                    break
                elif abs(rect_top - text_center) <= linethrough_margin:
                    text_item["linethrough"] = True
                    used_rects.add(rect_signature(rect))
                    break

    # Filter out rects that were used as text decorations
    final_items = []
    for el in items:
        if el.get("type") == "rect" and rect_signature(el) in used_rects:
            continue
        final_items.append(el)

    return final_items
