# PDF OCR Converter

A Python application that converts image-only or scanned PDFs into searchable PDFs and/or text files using Tesseract OCR. The project includes both a command-line interface and a user-friendly graphical interface.

## Features

- **Dual Interface**: Command-line tool and GUI application
- **Batch Processing**: Process single files or entire directories
- **Smart Text Detection**: Skip OCR on pages that already contain selectable text
- **Multiple Output Formats**: Generate searchable PDFs and/or plain text files
- **Configurable OCR**: Adjustable DPI, multiple language support
- **Progress Tracking**: Real-time progress bars and logging
- **Cross-platform**: Works on Windows, macOS, and Linux

## Screenshots

### GUI Interface
The application provides an intuitive graphical interface with:
- File/folder selection
- OCR configuration options
- Real-time progress tracking
- Logging output

## Requirements

### System Dependencies
- **Tesseract OCR**: The core OCR engine
- **Poppler**: For PDF to image conversion

### Python Dependencies
All Python dependencies are listed in `requirements.txt`:
```
cffi==2.0.0
charset-normalizer==3.4.4
colorama==0.4.6
cryptography==46.0.3
packaging==25.0
pdf2image==1.17.0
pdfminer.six==20250506
pdfplumber==0.11.7
pillow==12.0.0
plyer==2.1.0
pycparser==2.23
PyPDF2==3.0.1
pypdfium2==4.30.0
pytesseract==0.3.13
tk==0.1.0
tqdm==4.67.1
typing_extensions==4.15.0
```

## Installation

### 1. Install System Dependencies

#### Windows
1. **Tesseract OCR**:
   - Download from [GitHub releases](https://github.com/UB-Mannheim/tesseract/wiki)
   - Install and note the installation path (usually `C:\Program Files\Tesseract-OCR\tesseract.exe`)

2. **Poppler**:
   - Download from [poppler releases](https://github.com/oschwartz10612/poppler-windows/releases)
   - Extract and note the path to the `bin` folder

#### macOS
```bash
brew install tesseract poppler
```

#### Linux (Ubuntu/Debian)
```bash
sudo apt update
sudo apt install tesseract-ocr poppler-utils
```

### 2. Set Up Python Environment

1. **Clone or download** this repository
2. **Create a virtual environment**:
   ```bash
   python -m venv .venv
   ```

3. **Activate the virtual environment**:
   - Windows: `.venv\Scripts\activate`
   - macOS/Linux: `source .venv/bin/activate`

4. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### GUI Application

Run the graphical interface:
```bash
python pdf_ocr_gui.py
```

#### GUI Features:
- **Input Settings**: Choose single file or batch folder processing
- **Output Settings**: Select output directory and formats
- **OCR Configuration**: Adjust DPI, language, and dependency paths
- **Logging**: Optional log file output
- **Progress Tracking**: Real-time progress bar and console output

### Command Line Interface

Run the command-line version:
```bash
python pdf_ocr_cli.py input_file_or_folder [options]
```

#### Command Line Options:
```
positional arguments:
  input                 PDF file or directory containing PDFs

options:
  -h, --help            Show help message
  --out-dir, -o         Output directory (default: same as input)
  --dpi DPI             DPI for rasterizing PDF (default: 300)
  --lang LANG           Tesseract language(s), e.g. "eng" or "eng+fra"
  --txt                 Also output a .txt file with extracted text
  --no-pdf              Do not output searchable PDF (only with --txt)
  --skip-text-pages     Skip OCR on pages with existing selectable text
  --poppler-path        Path to poppler binaries (Windows)
  --tesseract-cmd       Full path to tesseract executable
  --config              Extra Tesseract config string
  --log                 Log to file (default: stdout)
  --batch               Process all PDFs in directory
```

#### Examples:

Process a single PDF:
```bash
python pdf_ocr_cli.py document.pdf
```

Batch process with text output:
```bash
python pdf_ocr_cli.py folder_with_pdfs --batch --txt
```

High-quality OCR with custom language:
```bash
python pdf_ocr_cli.py document.pdf --dpi 600 --lang eng+fra
```

## Configuration

### Language Support
Tesseract supports many languages. Common language codes:
- `eng` - English
- `fra` - French
- `deu` - German
- `spa` - Spanish
- `chi_sim` - Chinese Simplified
- `ara` - Arabic

Combine languages with `+`: `eng+fra+deu`

To install additional languages:
- **Windows**: Download language packs from Tesseract releases
- **macOS**: `brew install tesseract-lang`
- **Linux**: `sudo apt install tesseract-ocr-[lang-code]`

### DPI Settings
- **150 DPI**: Fast processing, lower quality
- **300 DPI**: Default, good balance of speed and quality
- **600 DPI**: High quality, slower processing

## Project Structure

```
PythonOCR/
├── pdf_ocr_gui.py              # GUI application
├── pdf_ocr_cli.py       # Command-line tool and core logic
├── requirements.txt            # Python dependencies
├── test.py                     # Simple test file
├── README.md                   # This file
├── files/                      # Sample/output files directory
│   ├── *.txt                   # Text outputs
│   ├── 300/                    # Organized outputs
│   ├── new/                    # New files
│   └── processing/             # Files being processed
└── __pycache__/               # Python cache files
```

## How It Works

1. **PDF Analysis**: Uses `pdfplumber` to detect existing text
2. **Image Conversion**: Converts PDF pages to images using `pdf2image`
3. **OCR Processing**: Applies Tesseract OCR to generate searchable text
4. **PDF Creation**: Combines original pages (if they have text) with OCR'd pages
5. **Output Generation**: Creates searchable PDFs and/or text files

## Troubleshooting

### Common Issues

**"Tesseract not found"**:
- Ensure Tesseract is installed and in PATH
- Use `--tesseract-cmd` to specify full path
- GUI users can browse for the executable

**"Poppler not found"**:
- Install Poppler utils
- On Windows, use `--poppler-path` to specify bin folder
- GUI users can browse for the poppler bin folder

**Out of memory errors**:
- Reduce DPI setting
- Process files individually instead of batch
- Close other applications

**Poor OCR quality**:
- Increase DPI (try 450-600)
- Ensure correct language is selected
- Check if source PDF has good image quality

### Performance Tips

- Use appropriate DPI (300 is usually sufficient)
- Enable "Skip pages with existing text" for mixed documents
- Process files in smaller batches for large datasets
- Use SSD storage for temporary files

## Contributing

Feel free to submit issues and pull requests. When contributing:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test with various PDF types
5. Submit a pull request

## License

This project is open source.

## Acknowledgments

- **Tesseract OCR**: Google's open-source OCR engine
- **pdf2image**: Python library for PDF to image conversion
- **PyPDF2**: PDF manipulation library
- **pdfplumber**: PDF text extraction library

---

**Note**: This tool works best with scanned documents and image-based PDFs. For PDFs that already contain selectable text, consider using the "skip text pages" option to preserve the original quality.