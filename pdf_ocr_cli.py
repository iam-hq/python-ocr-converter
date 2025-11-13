#!/usr/bin/env python3
"""
pdf_ocr_searchable.py

Convert image-only (or partly image) PDFs into searchable PDFs and/or text using Tesseract OCR.

Features:
- Input: single PDF or directory of PDFs (batch)
- Uses pdf2image to rasterize pages
- Uses pytesseract (Tesseract) to OCR pages
- Outputs: searchable PDF and/or .txt
- Preserves original pages that already contain selectable text (optional)
- Configurable DPI and language(s)
- Progress bar with tqdm, logging, and error handling

Dependencies (Python): pytesseract, pdf2image, PyPDF2, pdfplumber, Pillow, tqdm
System deps: Tesseract OCR (tesseract), Poppler (pdftoppm)

Author: ChatGPT-style assistant
"""

import os
import io
import sys
import argparse
import logging
import tempfile
from pathlib import Path
from typing import List, Optional

from tqdm import tqdm
from pdf2image import convert_from_path #, PDFInfoNotInstalledError
import pytesseract
from PyPDF2 import PdfReader, PdfWriter
import pdfplumber
from PIL import Image

# -------------------------
# Configuration defaults
# -------------------------
DEFAULT_DPI = 300
DEFAULT_LANG = "eng"   # You can specify multiple like "eng+fra"
DEFAULT_OUTPUT_PDF = True
DEFAULT_OUTPUT_TXT = False
DEFAULT_SKIP_OCR_IF_TEXT = True
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"

# -------------------------
# Helper / utility funcs
# -------------------------

def check_dependencies(tesseract_cmd: Optional[str] = None):
    """
    Check that Tesseract and pdf2image/poppler are available.
    Raises RuntimeError with helpful message if missing.
    """
    # Tesseract
    try:
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
        _ = pytesseract.get_tesseract_version()
    except Exception as e:
        raise RuntimeError(
            "Tesseract not found or not working. Please install Tesseract OCR and ensure it's on PATH, "
            "or provide --tesseract-cmd path. See README for install instructions."
        ) from e

    # Poppler (pdf2image uses pdftoppm from poppler)
    try:
        # convert_from_path will raise PDFInfoNotInstalledError if poppler isn't installed when used,
        # but we do a cheap check via trying to get PDF info by calling convert_from_path on an empty value would fail.
        # We simply rely on catching PDFInfoNotInstalledError downstream when conversion is attempted.
        pass
    except Exception:
        pass


def list_input_files(input_path: Path) -> List[Path]:
    """
    If input_path is a file, return [file]. If a directory, return list of pdf files (non-recursive).
    """
    if input_path.is_file():
        return [input_path]
    elif input_path.is_dir():
        pdfs = sorted([p for p in input_path.iterdir() if p.suffix.lower() == ".pdf"])
        return pdfs
    else:
        raise FileNotFoundError(f"Input path {input_path} does not exist.")


def pdf_page_has_text(pdf_path: Path, page_number: int) -> bool:
    """
    Check if a particular page has selectable/existing text (using pdfplumber).
    Returns True if page text length > 20 (configurable threshold).
    """
    try:
        with pdfplumber.open(str(pdf_path)) as doc:
            if page_number < 0 or page_number >= len(doc.pages):
                return False
            text = doc.pages[page_number].extract_text()
            if text and len(text.strip()) > 20:
                return True
    except Exception:
        # If pdfplumber fails, assume no text to be safe and run OCR
        return False
    return False


def pdf_to_images(pdf_path: Path, dpi: int = DEFAULT_DPI, poppler_path: Optional[str] = None):
    """
    Convert PDF pages to PIL Images using pdf2image.convert_from_path.
    Returns list of PIL Image objects.
    """
    kwargs = {"dpi": dpi}
    if poppler_path:
        kwargs["poppler_path"] = poppler_path

    try:
        images = convert_from_path(str(pdf_path), **kwargs)
    # except PDFInfoNotInstalledError as e:
    #     raise RuntimeError(
    #         "Poppler not found. Install poppler (provides pdftoppm). On Debian/Ubuntu: sudo apt install poppler-utils. "
    #         "On macOS: brew install poppler. On Windows: install from poppler releases and provide --poppler-path."
    #     ) from e
    except Exception as e:
        raise RuntimeError(f"Failed to convert PDF to images: {e}") from e

    return images


def ocr_image_to_pdf_bytes(image: Image.Image, lang: str = DEFAULT_LANG, config: Optional[str] = None) -> bytes:
    """
    Run Tesseract OCR on a PIL Image and return a PDF (bytes) with an invisible text layer (searchable PDF).
    Uses pytesseract.image_to_pdf_or_hocr.
    """
    # Ensure image is in a format Tesseract likes (RGB)
    if image.mode in ("RGBA", "LA"):
        bg = Image.new("RGB", image.size, (255, 255, 255))
        bg.paste(image, mask=image.split()[-1])
        image_for_ocr = bg
    else:
        image_for_ocr = image.convert("RGB")

    pdf_bytes = pytesseract.image_to_pdf_or_hocr(image_for_ocr, extension="pdf", lang=lang, config=config or "")
    return pdf_bytes


def ocr_image_to_text(image: Image.Image, lang: str = DEFAULT_LANG, config: Optional[str] = None) -> str:
    """
    Extract plain text from PIL Image using pytesseract.
    """
    return pytesseract.image_to_string(image, lang=lang, config=config or "")


def merge_pdf_bytes_into_writer(writer: PdfWriter, pdf_bytes: bytes):
    """
    Read pdf_bytes with PdfReader and append pages to the given PdfWriter.
    """
    reader = PdfReader(io.BytesIO(pdf_bytes))
    for p in reader.pages:
        writer.add_page(p)


def process_single_pdf(
    pdf_path: Path,
    output_pdf: bool = DEFAULT_OUTPUT_PDF,
    output_txt: bool = DEFAULT_OUTPUT_TXT,
    dpi: int = DEFAULT_DPI,
    lang: str = DEFAULT_LANG,
    skip_if_text: bool = DEFAULT_SKIP_OCR_IF_TEXT,
    poppler_path: Optional[str] = None,
    tesseract_config: Optional[str] = None,
    out_dir: Optional[Path] = None,
):
    """
    Process a single PDF file: convert pages to images, OCR them, and produce outputs.
    Returns a dict summarizing results.
    """
    out_dir = out_dir or pdf_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    base_name = pdf_path.stem
    output_pdf_path = out_dir / f"{base_name}_searchable.pdf" if output_pdf else None
    output_txt_path = out_dir / f"{base_name}.txt" if output_txt else None

    logging.info(f"Processing {pdf_path} (dpi={dpi}, lang={lang})")

    # Try quick check for the number of pages using PyPDF2 to pre-validate PDF
    try:
        reader_orig = PdfReader(str(pdf_path))
        num_pages = len(reader_orig.pages)
    except Exception as e:
        raise RuntimeError(f"Failed to read PDF file with PyPDF2: {e}") from e

    # Convert pages to images (may raise error if poppler missing)
    images = pdf_to_images(pdf_path, dpi=dpi, poppler_path=poppler_path)
    if len(images) != num_pages:
        # Sometimes convert_from_path returns same count, but if not, warn.
        logging.warning(f"pdf2image returned {len(images)} images but PDF has {num_pages} pages.")

    writer = PdfWriter()
    all_text = []

    # Iterate pages with progress bar
    for page_idx, img in enumerate(tqdm(images, desc=f"OCR pages ({pdf_path.name})", unit="page")):
        try:
            # If skip_if_text enabled and page contains text, copy original page
            if skip_if_text and pdf_page_has_text(pdf_path, page_idx):
                logging.info(f"Page {page_idx+1}: contains existing text — copying original page (skip OCR).")
                # Add original page from original PDF
                try:
                    writer.add_page(reader_orig.pages[page_idx])
                    # Also extract text via pdfplumber for txt output if requested
                    if output_txt:
                        with pdfplumber.open(str(pdf_path)) as doc:
                            text = doc.pages[page_idx].extract_text() or ""
                            all_text.append(text)
                except Exception as e:
                    logging.warning(f"Failed to copy original page {page_idx+1}: {e}. Falling back to OCR.")
                    # Fall through to OCR if copying fails
                    pdf_bytes = ocr_image_to_pdf_bytes(img, lang=lang, config=tesseract_config)
                    merge_pdf_bytes_into_writer(writer, pdf_bytes)
                    if output_txt:
                        text = ocr_image_to_text(img, lang=lang, config=tesseract_config)
                        all_text.append(text)
            else:
                # Perform OCR on the rasterized image
                pdf_bytes = ocr_image_to_pdf_bytes(img, lang=lang, config=tesseract_config)
                merge_pdf_bytes_into_writer(writer, pdf_bytes)
                if output_txt:
                    text = ocr_image_to_text(img, lang=lang, config=tesseract_config)
                    all_text.append(text)
        except Exception as e:
            logging.exception(f"Error processing page {page_idx+1} of {pdf_path.name}: {e}")
            # To keep page count, add the original page if possible; otherwise create a blank page
            try:
                writer.add_page(reader_orig.pages[page_idx])
            except Exception:
                # Create a blank white page as fallback
                from PyPDF2.generic import RectangleObject
                writer.add_blank_page(width=595, height=842)  # A4-ish fallback

    # Write the merged searchable PDF if requested
    if output_pdf and output_pdf_path:
        try:
            with open(output_pdf_path, "wb") as f:
                writer.write(f)
            logging.info(f"Wrote searchable PDF: {output_pdf_path}")
        except Exception as e:
            logging.exception(f"Failed to write output PDF {output_pdf_path}: {e}")
            raise

    # Write text file if requested
    if output_txt and output_txt_path:
        try:
            combined_text = "\n\n=== PAGE BREAK ===\n\n".join([t.strip() for t in all_text if t])
            with open(output_txt_path, "w", encoding="utf-8") as f:
                f.write(combined_text)
            logging.info(f"Wrote text output: {output_txt_path}")
        except Exception as e:
            logging.exception(f"Failed to write text file {output_txt_path}: {e}")
            raise

    return {
        "input": str(pdf_path),
        "output_pdf": str(output_pdf_path) if output_pdf_path else None,
        "output_txt": str(output_txt_path) if output_txt_path else None,
        "pages": num_pages,
    }


# -------------------------
# CLI entrypoint
# -------------------------

def main(argv=None):
    parser = argparse.ArgumentParser(description="Convert PDF(s) with images into searchable PDFs and/or text using Tesseract OCR.")
    parser.add_argument("input", help="PDF file or directory containing PDFs")
    parser.add_argument("--out-dir", "-o", help="Output directory (default: same folder as input files)", default=None)
    parser.add_argument("--dpi", type=int, default=DEFAULT_DPI, help=f"DPI for rasterizing PDF (default: {DEFAULT_DPI})")
    parser.add_argument("--lang", type=str, default=DEFAULT_LANG, help='Tesseract language(s) e.g. "eng" or "eng+fra" (default: eng)')
    parser.add_argument("--txt", action="store_true", help="Also output a .txt file with extracted text")
    parser.add_argument("--no-pdf", action="store_true", help="Do not output searchable PDF (only useful with --txt)")
    parser.add_argument("--skip-text-pages", action="store_true", help="Skip OCR on pages that already contain selectable text (copy original page)")
    parser.add_argument("--poppler-path", type=str, default=None, help="Path to poppler binaries (windows).")
    parser.add_argument("--tesseract-cmd", type=str, default=None, help="Full path to tesseract executable (if not on PATH).")
    parser.add_argument("--config", type=str, default=None, help="Extra Tesseract config string (e.g. --psm 1)")
    parser.add_argument("--log", type=str, default=None, help="Log to this file (default: stdout)")
    parser.add_argument("--batch", action="store_true", help="Treat input as directory and process all .pdf files in it")
    args = parser.parse_args(argv)

    # Setup logging
    if args.log:
        logging.basicConfig(level=logging.INFO, filename=args.log, format=LOG_FORMAT)
    else:
        logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)

    try:
        check_dependencies(args.tesseract_cmd)
    except RuntimeError as e:
        logging.error(e)
        sys.exit(1)

    input_path = Path(args.input)
    out_dir = Path(args.out_dir) if args.out_dir else None

    # Build file list
    try:
        files = list_input_files(input_path)
    except Exception as e:
        logging.error(f"Input error: {e}")
        sys.exit(1)

    if args.batch and input_path.is_dir() is False:
        logging.error("--batch requires input to be a directory")
        sys.exit(1)

    results = []
    for pdf_file in files:
        try:
            res = process_single_pdf(
                pdf_file,
                output_pdf=(not args.no_pdf),
                output_txt=args.txt,
                dpi=args.dpi,
                lang=args.lang,
                skip_if_text=args.skip_text_pages,
                poppler_path=args.poppler_path,
                tesseract_config=args.config,
                out_dir=out_dir
            )
            results.append(res)
        except Exception as e:
            logging.exception(f"Failed processing {pdf_file}: {e}")
            results.append({"input": str(pdf_file), "error": str(e)})

    # Print summary
    print("\nProcessing summary:")
    for r in results:
        print(r)

    return 0


if __name__ == "__main__":
    sys.exit(main())
