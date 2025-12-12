"""tools/convert_to_pdfa.py

Utility to convert a PDF file to PDF/A‑1b compliance using Ghostscript.

Ghostscript must be installed and available on the system PATH (or provide the full path
via the `gs_executable` argument). The function runs the following command:

    gs -dPDFA -dBATCH -dNOPAUSE -dNOOUTERSAVE -sProcessColorModel=DeviceRGB \
       -sDEVICE=pdfwrite -sOutputFile=<output> <input>

The command produces a PDF/A‑1b file suitable for archiving and long‑term preservation.

Typical usage:

```python
from tools.convert_to_pdfa import convert_to_pdfa

convert_to_pdfa('input.pdf', 'output_pdfa.pdf')
```

If Ghostscript is not found, a `FileNotFoundError` is raised.
"""

import subprocess
import shutil
from pathlib import Path
from typing import Union

def convert_to_pdfa(
    input_pdf: Union[str, Path],
    output_pdf: Union[str, Path],
    *,
    gs_executable: str = "gs",
    timeout: int = 60,
) -> Path:
    """Convert *input_pdf* to PDF/A‑1b and write to *output_pdf*.

    Parameters
    ----------
    input_pdf: str or Path
        Path to the source PDF file.
    output_pdf: str or Path
        Destination path for the PDF/A file. Parent directories are created if needed.
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
    subprocess.CalledProcessError
        If Ghostscript returns a non‑zero exit status.
    """
    input_path = Path(input_pdf).expanduser().resolve()
    output_path = Path(output_pdf).expanduser().resolve()

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

    # Ghostscript command for PDF/A‑1b conversion
    cmd = [
        gs_executable,
        "-dPDFA",
        "-dBATCH",
        "-dNOPAUSE",
        "-dNOOUTERSAVE",
        "-sProcessColorModel=DeviceRGB",
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
        "--gs",
        dest="gs_executable",
        default="gs",
        help="Ghostscript executable (default: gs)",
    )
    args = parser.parse_args()

    try:
        result = convert_to_pdfa(args.input, args.output, gs_executable=args.gs_executable)
        print(f"PDF/A created at: {result}")
    except Exception as e:
        print(f"Error: {e}")
        raise
