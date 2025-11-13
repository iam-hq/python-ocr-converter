import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import queue
import os
from pathlib import Path
from plyer import notification

from pdf_ocr_cli import (
    process_single_pdf,
    check_dependencies,
    list_input_files,
    DEFAULT_DPI,
    DEFAULT_LANG,
)

import logging
import sys
import time


class PDFOCRGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF OCR Converter")
        self.root.geometry("800x700")
        self.root.resizable(False, False)

        # State variables
        self.input_path = tk.StringVar()
        self.output_path = tk.StringVar()
        self.tesseract_path = tk.StringVar()
        self.poppler_path = tk.StringVar()
        self.dpi = tk.IntVar(value=DEFAULT_DPI)
        self.lang = tk.StringVar(value=DEFAULT_LANG)
        self.batch_mode = tk.BooleanVar(value=False)
        self.output_txt = tk.BooleanVar(value=False)
        self.skip_text = tk.BooleanVar(value=True)
        self.log_to_file = tk.StringVar(value="")

        # Log queue for thread-safe GUI updates
        self.log_queue = queue.Queue()

        # Build UI
        self.create_widgets()

        # Poll log queue periodically
        self.root.after(100, self.process_log_queue)

    def create_widgets(self):
        # Input selection frame
        frm_input = ttk.LabelFrame(self.root, text="Input Settings", padding=10)
        frm_input.pack(fill="x", padx=10, pady=5)

        ttk.Label(frm_input, text="Select File or Folder:").grid(row=0, column=0, sticky="w")
        ttk.Entry(frm_input, textvariable=self.input_path, width=60).grid(row=0, column=1, padx=5)
        ttk.Button(frm_input, text="Browse", command=self.browse_input).grid(row=0, column=2)

        ttk.Radiobutton(frm_input, text="Single File", variable=self.batch_mode, value=False).grid(row=1, column=0, sticky="w")
        ttk.Radiobutton(frm_input, text="Batch (Folder)", variable=self.batch_mode, value=True).grid(row=1, column=1, sticky="w")

        # Output settings
        frm_output = ttk.LabelFrame(self.root, text="Output Settings", padding=10)
        frm_output.pack(fill="x", padx=10, pady=5)

        ttk.Label(frm_output, text="Output Directory:").grid(row=0, column=0, sticky="w")
        ttk.Entry(frm_output, textvariable=self.output_path, width=60).grid(row=0, column=1, padx=5)
        ttk.Button(frm_output, text="Browse", command=self.browse_output).grid(row=0, column=2)

        ttk.Checkbutton(frm_output, text="Generate Text File (.txt)", variable=self.output_txt).grid(row=1, column=0, sticky="w")
        ttk.Checkbutton(frm_output, text="Skip pages with existing text", variable=self.skip_text).grid(row=1, column=1, sticky="w")

        # OCR Configuration
        frm_config = ttk.LabelFrame(self.root, text="OCR Configuration", padding=10)
        frm_config.pack(fill="x", padx=10, pady=5)

        ttk.Label(frm_config, text="DPI:").grid(row=0, column=0, sticky="w")
        dpi_entry = ttk.Entry(frm_config, textvariable=self.dpi, width=10)
        dpi_entry.grid(row=0, column=1, sticky="w")
        ttk.Button(frm_config, text="Reset", command=lambda: self.dpi.set(DEFAULT_DPI)).grid(row=0, column=2)

        ttk.Label(frm_config, text="Language(s):").grid(row=1, column=0, sticky="w")
        ttk.Entry(frm_config, textvariable=self.lang, width=20).grid(row=1, column=1, sticky="w")
        ttk.Label(frm_config, text='(e.g. "eng" or "eng+fra")').grid(row=1, column=2, sticky="w")

        ttk.Label(frm_config, text="Tesseract Path:").grid(row=2, column=0, sticky="w")
        ttk.Entry(frm_config, textvariable=self.tesseract_path, width=60).grid(row=2, column=1, padx=5)
        ttk.Button(frm_config, text="Browse", command=self.browse_tesseract).grid(row=2, column=2)

        ttk.Label(frm_config, text="Poppler Path:").grid(row=3, column=0, sticky="w")
        ttk.Entry(frm_config, textvariable=self.poppler_path, width=60).grid(row=3, column=1, padx=5)
        ttk.Button(frm_config, text="Browse", command=self.browse_poppler).grid(row=3, column=2)

        # Logging options
        frm_log = ttk.LabelFrame(self.root, text="Logging", padding=10)
        frm_log.pack(fill="x", padx=10, pady=5)

        ttk.Label(frm_log, text="Log File (optional):").grid(row=0, column=0, sticky="w")
        ttk.Entry(frm_log, textvariable=self.log_to_file, width=60).grid(row=0, column=1, padx=5)
        ttk.Button(frm_log, text="Browse", command=self.browse_log).grid(row=0, column=2)

        # Progress bar and start
        frm_run = ttk.Frame(self.root, padding=10)
        frm_run.pack(fill="x")

        ttk.Button(frm_run, text="Start OCR", command=self.start_ocr_thread).grid(row=0, column=0, padx=5)
        self.progress = ttk.Progressbar(frm_run, length=400, mode="determinate")
        self.progress.grid(row=0, column=1, padx=5)

        # Log output (console)
        frm_console = ttk.LabelFrame(self.root, text="Log Output", padding=10)
        frm_console.pack(fill="both", expand=True, padx=10, pady=5)

        self.console = scrolledtext.ScrolledText(frm_console, wrap=tk.WORD, height=15, state="disabled")
        self.console.pack(fill="both", expand=True)

    # Browse functions
    def browse_input(self):
        if self.batch_mode.get():
            path = filedialog.askdirectory(title="Select Folder Containing PDFs")
        else:
            path = filedialog.askopenfilename(title="Select PDF File", filetypes=[("PDF Files", "*.pdf")])
        if path:
            self.input_path.set(path)

    def browse_output(self):
        path = filedialog.askdirectory(title="Select Output Directory")
        if path:
            self.output_path.set(path)

    def browse_tesseract(self):
        path = filedialog.askopenfilename(title="Select Tesseract Executable")
        if path:
            self.tesseract_path.set(path)

    def browse_poppler(self):
        path = filedialog.askdirectory(title="Select Poppler 'bin' Folder")
        if path:
            self.poppler_path.set(path)

    def browse_log(self):
        path = filedialog.asksaveasfilename(title="Select Log File", defaultextension=".log", filetypes=[("Log Files", "*.log")])
        if path:
            self.log_to_file.set(path)

    # Logging utility
    def gui_log(self, msg):
        self.log_queue.put(msg)

    def process_log_queue(self):
        while not self.log_queue.empty():
            msg = self.log_queue.get_nowait()
            self.console.configure(state="normal")
            self.console.insert(tk.END, msg + "\n")
            self.console.configure(state="disabled")
            self.console.see(tk.END)
        self.root.after(100, self.process_log_queue)

    def start_ocr_thread(self):
        thread = threading.Thread(target=self.run_ocr, daemon=True)
        thread.start()

    def run_ocr(self):
        input_path = Path(self.input_path.get())
        if not input_path.exists():
            messagebox.showerror("Error", "Input path does not exist.")
            return

        out_dir = Path(self.output_path.get()) if self.output_path.get() else None
        tesseract_cmd = self.tesseract_path.get() or None
        poppler_path = self.poppler_path.get() or None
        log_file = self.log_to_file.get() or None

        # Logging setup
        handlers = [logging.StreamHandler(sys.stdout)]
        if log_file:
            handlers.append(logging.FileHandler(log_file, mode='w', encoding='utf-8'))

        logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s", handlers=handlers)

        self.gui_log("Checking dependencies...")
        try:
            check_dependencies(tesseract_cmd)
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return

        files = list_input_files(input_path)
        total_files = len(files)
        self.progress["maximum"] = total_files
        self.progress["value"] = 0

        self.gui_log(f"Processing {total_files} file(s)...")

        for i, f in enumerate(files, start=1):
            try:
                res = process_single_pdf(
                    f,
                    output_pdf=True,
                    output_txt=self.output_txt.get(),
                    dpi=self.dpi.get(),
                    lang=self.lang.get(),
                    skip_if_text=self.skip_text.get(),
                    poppler_path=poppler_path,
                    tesseract_config=None,
                    out_dir=out_dir
                )
                self.gui_log(f"✅ Done: {res['input']}")
            except Exception as e:
                self.gui_log(f"❌ Failed: {f} ({e})")

            self.progress["value"] = i
            self.root.update_idletasks()

        # Notify user
        notification.notify(
            title="PDF OCR Converter",
            message=f"OCR processing complete! {total_files} file(s) processed.",
            timeout=5,
        )

        messagebox.showinfo("Done", f"OCR processing complete! {total_files} file(s) processed.")

        self.gui_log("All tasks complete.\n")


if __name__ == "__main__":
    root = tk.Tk()
    app = PDFOCRGUI(root)
    root.mainloop()
