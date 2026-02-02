
class PDFProcessingError(Exception):
    """Custom exception for PDF processing issues."""
    def __init__(self, message):
        super().__init__(message)

class FontExtractionError(PDFProcessingError):
    """Raised when font extraction fails."""
    pass

class ImageProcessingError(PDFProcessingError):
    """Raised when image extraction or processing fails."""
    pass