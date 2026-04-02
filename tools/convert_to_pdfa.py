"""tools/convert_to_pdfa.py

Utility to convert a PDF file to PDF/A using Ghostscript.

Ghostscript must be installed and available on the system PATH (or provide
the full path via the ``gs_executable`` argument).
"""

import subprocess
import shutil
from pathlib import Path
from typing import Union


SUPPORTED_PDFA_LEVELS = {
    "1b": 1,
    "2b": 2,
    "2u": 2,
    "3b": 3,
    "3u": 3,
    "3a": 3,
}


def convert_to_pdfa(
    input_pdf: Union[str, Path],
    output_pdf: Union[str, Path],
    *,
    pdfa_level: str = "3a",
    gs_executable: str = "gs",
    timeout: int = 60,
) -> Path:
    """Convert *input_pdf* to PDF/A and write to *output_pdf*.

    Parameters
    ----------
    input_pdf: str or Path
        Path to the source PDF file.
    output_pdf: str or Path
        Destination path for the PDF/A file. Parent directories are created if needed.
    pdfa_level: str, optional
        PDF/A conformance target. Supported values:
        ``1b``, ``2b``, ``2u``, ``3b``, ``3u``, ``3a``.
        Defaults to ``3a``.
    gs_executable: str, optional
        Name or full path of the Ghostscript executable. Defaults to ``"gs"`` which
        relies on the executable being in the system ``PATH``.
    timeout: int, optional
        Maximum seconds to wait for the Ghostscript process. Defaults to 60 seconds.

    Returns
    -------
    Path
        The absolute path to the generated PDF/A file.

    Raises
    ------
    FileNotFoundError
        If the Ghostscript executable cannot be located.
    ValueError
        If ``pdfa_level`` is not supported.
    subprocess.CalledProcessError
        If Ghostscript returns a non-zero exit status.
    """
    input_path = Path(input_pdf).expanduser().resolve()
    output_path = Path(output_pdf).expanduser().resolve()
    normalized_level = pdfa_level.lower().strip()
    pdfa_version = SUPPORTED_PDFA_LEVELS.get(normalized_level)
    if pdfa_version is None:
        allowed_levels = ", ".join(sorted(SUPPORTED_PDFA_LEVELS))
        raise ValueError(
            f"Unsupported PDF/A level '{pdfa_level}'. Use one of: {allowed_levels}"
        )

    # Ensure input exists
    if not input_path.is_file():
        raise FileNotFoundError(f"Input PDF not found: {input_path}")

    # Ensure Ghostscript is available
    if shutil.which(gs_executable) is None:
        raise FileNotFoundError(
            f"Ghostscript executable '{gs_executable}' not found in PATH."
        )

    # Create parent directories for output if they don't exist
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Ghostscript command for PDF/A conversion.
    # Note: PDF/A-3A requires accessible/structured source content. If the source
    # document is not tagged, Ghostscript may fail or produce a lower conformance.
    cmd = [
        gs_executable,
        f"-dPDFA={pdfa_version}",
        "-dBATCH",
        "-dNOPAUSE",
        "-dNOOUTERSAVE",
        "-dSAFER",
        "-dPDFACompatibilityPolicy=1",
        "-sProcessColorModel=DeviceRGB",
        "-sColorConversionStrategy=RGB",
        "-dEmbedAllFonts=true",
        "-sDEVICE=pdfwrite",
        f"-sOutputFile={output_path}",
        str(input_path),
    ]

    # Run the command
    subprocess.run(cmd, check=True, timeout=timeout)

    return output_path

# Example usage when run as a script (not executed during import)
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Convert PDF to PDF/A using Ghostscript")
    parser.add_argument("input", help="Path to input PDF")
    parser.add_argument("output", help="Path to output PDF/A file")
    parser.add_argument(
        "--pdfa-level",
        default="3a",
        choices=sorted(SUPPORTED_PDFA_LEVELS),
        help="PDF/A level to generate (default: 3a)",
    )
    parser.add_argument(
        "--gs",
        dest="gs_executable",
        default="gs",
        help="Ghostscript executable (default: gs)",
    )
    args = parser.parse_args()

    try:
        result = convert_to_pdfa(
            args.input,
            args.output,
            pdfa_level=args.pdfa_level,
            gs_executable=args.gs_executable,
        )
        print(f"PDF/A created at: {result}")
    except Exception as e:
        print(f"Error: {e}")
        raise
