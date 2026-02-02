# PDF-to-JSON Professional Extractor

A robust CLI tool for converting PDF documents into structured JSON data. This tool extracts text, layouts, font styles, and images with high precision using **PyMuPDF**.

## ✨ Features

- **Component-Level Extraction**: Extracts text, lines, rectangles, and images as individual JSON components.
- **Font Intelligence**: Identifies and extracts embedded font styles (Family, Full Name, PostScript) for accurate rendering.
- **Visual Accuracy**: Captures image positions, dimensions, and transformations.
- **Smart Cleanup**: Automatically removes overlaps, hidden texts, and redundant background elements.
- **Local Storage**: Completely standalone with local asset storage (no cloud dependencies).
- **Docker Ready**: Fully containerized for easy deployment and scaling.

## 🛠️ Installation

### Using Python
1. Clone the repository:
   ```bash
   git clone https://github.com/x-eight/pdf-to-json.git
   cd pdf-to-json
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Using Docker
```bash
docker build -t pdf-to-json .
```

## 🚀 Usage

### Basic Command
Run the CLI by providing the path to your PDF file:
```bash
python src/cli.py path/to/your/document.pdf
```

### Options
- `-o, --output-dir`: Specify where to save the JSON and extracted assets (default: `./output`).

Example with custom output:
```bash
python src/cli.py input.pdf --output-dir ./my_results
```

### Running with Docker
```bash
docker run -v $(pwd)/output:/app/output pdf-to-json input.pdf
```

## 📂 Output Structure
The tool generates a structured output in the designated folder:
```text
output/
├── input.json          # Structured data of the PDF
├── images/             # Extracted portrait and inline images
└── fonts/              # Extracted embedded fonts
```

## 📝 Technical Details
This project utilizes:
- **PyMuPDF (fitz)**: For core PDF parsing and SVG extraction.
- **Pillow**: For image processing and optimization.
- **FontTools**: For deep inspection of embedded font metadata.
- **Font Mapping**: Uses `src/resources/fonts.json` to accurately map embedded and standard fonts (Arial, Calibri, etc.) even when obfuscated.

## ⚖️ License
This project is licensed under the MIT License.
# pdf-to-json
