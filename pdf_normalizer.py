#!/usr/bin/env python3
"""
normalize_pdf_with_ghostscript.py

Normalizes ALL PDFs in a source directory using Ghostscript
and writes the results into a target directory.

Usage:
    python normalize_pdf_with_ghostscript.py input_dir output_dir
    python normalize_pdf_with_ghostscript.py input_dir output_dir --profile printer
"""

import argparse
import subprocess
import shutil
from pathlib import Path

# Common Ghostscript binary names on different platforms
GS_CANDIDATES = [
    "gswin64c.exe",  # Windows 64-bit
    "gswin32c.exe",  # Windows 32-bit
    "gs"             # Linux/macOS
]

def find_ghostscript() -> str:
    """Find Ghostscript executable on PATH."""
    for name in GS_CANDIDATES:
        path = shutil.which(name)
        if path:
            return path
    raise RuntimeError(
        "Ghostscript executable not found. "
        "Install Ghostscript 10.06.0 and ensure 'gs' or 'gswin64c' is on PATH."
    )

def normalize_pdf(
    input_pdf: Path,
    output_pdf: Path,
    profile: str = "printer",
    compatibility: str = "1.4",
) -> None:
    """Normalize a single PDF via Ghostscript pdfwrite."""
    gs_bin = find_ghostscript()

    profile_map = {
        "screen": "/screen",
        "ebook": "/ebook",
        "printer": "/printer",
        "prepress": "/prepress",
        "default": "/default",
    }

    if profile not in profile_map:
        raise ValueError(
            f"Unknown profile '{profile}'. "
            f"Use one of: {', '.join(profile_map.keys())}"
        )

    pdf_settings = profile_map[profile]

    cmd = [
        gs_bin,
        "-dSAFER",
        "-dBATCH",
        "-dNOPAUSE",
        "-sDEVICE=pdfwrite",
        "-sColorConversionStrategy=LeaveColorUnchanged",
        f"-dCompatibilityLevel={compatibility}",
        f"-dPDFSETTINGS={pdf_settings}",
        "-dDetectDuplicateImages=true",
        "-dCompressFonts=true",
        "-dSubsetFonts=true",
        f"-sOutputFile={str(output_pdf)}",
        str(input_pdf),
    ]

    print(f"➡️  Normalizing: {input_pdf.name}")
    subprocess.run(cmd, check=True)
    print(f"   ✅ Output: {output_pdf.name}")

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Normalize all PDFs in a directory using Ghostscript."
    )
    parser.add_argument("input_dir", type=Path, help="Directory containing PDF files.")
    parser.add_argument("output_dir", type=Path, help="Directory for normalized PDFs.")
    parser.add_argument(
        "--profile",
        choices=["screen", "ebook", "printer", "prepress", "default"],
        default="printer",
        help="Ghostscript quality profile (default: printer)"
    )
    parser.add_argument(
        "--compat",
        default="1.4",
        help="PDF compatibility level (default: 1.4).",
    )

    args = parser.parse_args()

    if not args.input_dir.is_dir():
        raise SystemExit(f"Input directory not found: {args.input_dir}")

    # Create output folder if missing
    args.output_dir.mkdir(parents=True, exist_ok=True)

    pdf_files = list(args.input_dir.glob("*.pdf"))
    if not pdf_files:
        raise SystemExit("No PDF files found in input directory.")

    print(f"Found {len(pdf_files)} PDFs to process.\n")

    for pdf in pdf_files:
        output_pdf = args.output_dir / pdf.name
        normalize_pdf(
            input_pdf=pdf,
            output_pdf=output_pdf,
            profile=args.profile,
            compatibility=args.compat,
        )

    print("\n🎉 All PDFs processed successfully!")

if __name__ == "__main__":
    main()