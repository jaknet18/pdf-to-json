import os
import json

class LocalStorage:
    """Handles local file storage for images and JSON output."""
    
    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        self.images_dir = os.path.join(output_dir, "images")
        self.fonts_dir = os.path.join(output_dir, "fonts")
        
        # Ensure base project directories exist
        os.makedirs(self.images_dir, exist_ok=True)
        os.makedirs(self.fonts_dir, exist_ok=True)

    def save_bytes(self, buffer, relative_path: str, content_type: str = None) -> str:
        """Saves bytes to a file and returns the local file path."""
        target_path = os.path.join(self.output_dir, relative_path)
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        
        with open(target_path, "wb") as f:
            f.write(buffer.getvalue())
        
        return target_path

    def save_json(self, relative_path: str, data: any) -> str:
        """Saves data as a JSON file."""
        target_path = os.path.join(self.output_dir, relative_path)
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        
        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        return target_path

    def upload_bytes(self, buffer, relative_path: str, content_type: str = None) -> str:
        """Alias for save_bytes to maintain compatibility with original logic."""
        return self.save_bytes(buffer, relative_path, content_type)

    def upload_json(self, relative_path: str, data: any) -> str:
        """Alias for save_json to maintain compatibility with original logic."""
        return self.save_json(relative_path, data)
