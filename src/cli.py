import argparse
import sys
import os

# Ensure src is in the system path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from processor import PDFProcessor
from error.errors import PDFProcessingError

def main():
    parser = argparse.ArgumentParser(
        description="Professional PDF-to-JSON Converter CLI Tool.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Usage Examples:
  python src/cli.py input.pdf
  python src/cli.py input.pdf --output-dir ./results
        """
    )
    
    parser.add_argument("input", help="Path to the source PDF file")
    parser.add_argument(
        "-o", "--output-dir", 
        default="output", 
        help="Directory to store the JSON and extracted assets (default: './output')"
    )

    args = parser.parse_args()

    if not os.path.isfile(args.input):
        print(f"Error: The input file '{args.input}' does not exist or is not a file.")
        sys.exit(1)

    try:
        processor = PDFProcessor(args.output_dir)
        processor.process(args.input)
    except PDFProcessingError as e:
        print(f"Error during processing: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
