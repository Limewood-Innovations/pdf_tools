# PDF Normalization Workflow

## Overview

The PDF normalization workflow uses Ghostscript to optimize PDF files for specific use cases (screen, print, prepress) while ensuring PDF 1.4 compatibility and reduced file sizes.

## What It Does

1. **Normalizes PDFs** - Runs Ghostscript with quality profiles
2. **Optimizes Size** - Compresses images and fonts
3. **Ensures Compatibility** - Converts to PDF 1.4 format
4. **Archives Originals** - Optionally moves processed files to archive directory

## Directory Structure

```
03_cleaned/        # Input PDFs (typically from batch workflow)
04_normalized/     # Optimized PDFs
99_archived/       # Original PDFs (optional)
logs/              # Optional log files
```

## Usage

### Basic Usage

```bash
python workflows/pdf_normalizer_new.py \
    ./03_cleaned \
    ./04_normalized
```

### With Quality Profile

```bash
python workflows/pdf_normalizer_new.py \
    ./03_cleaned \
    ./04_normalized \
    --profile prepress
```

### With Archiving and Custom PDF Version

```bash
python workflows/pdf_normalizer_new.py \
    ./03_cleaned \
    ./04_normalized \
    --profile printer \
    --compat 1.4 \
    --archive-dir ./99_archived
```

### With Logging

```bash
python workflows/pdf_normalizer_new.py \
    ./03_cleaned \
    ./04_normalized \
    --profile printer \
    --log-file ./logs/normalize.log \
    --log-max-bytes 10485760 \
    --log-backup-count 10
```

## CLI Options

### Required (Positional)
| Argument | Description |
|----------|-------------|
| `input_dir` | Directory containing PDF files to normalize |
| `output_dir` | Directory for normalized PDFs |

### Optional
| Option | Default | Description |
|--------|---------|-------------|
| `--profile` | `printer` | Ghostscript quality profile |
| `--compat` | `1.4` | PDF compatibility level |
| `--archive-dir` | _(none)_ | Archive originals after processing |
| `--log-file` | _(console)_ | Path to log file |
| `--log-max-bytes` | `5242880` | Max log file size (5 MB) |
| `--log-backup-count` | `5` | Number of rotated logs to keep |
| `--pdfa` | `false` | If set, convert normalized PDFs to PDF/A‑1b after processing |


## Ghostscript Quality Profiles

| Profile | Use Case | File Size | Quality |
|---------|----------|-----------|---------|
| `screen` | Screen viewing (72 dpi) | Smallest | Low |
| `ebook` | E-readers (150 dpi) | Small | Medium |
| `printer` | **Default** - Office printing (300 dpi) | Medium | Good |
| `prepress` | Professional printing (300 dpi) | Larger | High |
| `default` | Ghostscript default | Varies | Varies |

## Dependencies

### Required
```bash
# Ghostscript must be installed
# macOS
brew install ghostscript

# Ubuntu/Debian  
sudo apt-get install ghostscript

# Windows
# Download from: https://www.ghostscript.com/download/gsdnld.html
```

### Python Packages
```bash
pip install pypdf
```

## Workflow Steps

For each PDF in input directory:

1. **Detect Ghostscript** - Locate `gs` executable in system PATH
2. **Run Ghostscript** - Execute with selected profile and compatibility level
   ```bash
   gs -sDEVICE=pdfwrite \
      -dCompatibilityLevel=1.4 \
      -dPDFSETTINGS=/printer \
      -dNOPAUSE -dQUIET -dBATCH \
      -sOutputFile=output.pdf \
      input.pdf
   ```
3. **Validate Output** - Check for successful generation
4. **Archive Original** - Move original to archive directory (if specified)
5. **Convert to PDF/A** - Optionally convert the normalized PDF to PDF/A-1b using `convert_to_pdfa` tool.
   ```bash
   python tools/convert_to_pdfa.py \
       --input-pdf output.pdf \
       --output-pdf output_pdfa.pdf \
       --pdfa-level 1b
   ```
6. **Log Results** - Record processing status

## Output

### Console/Log Output
```
2025-11-24 23:50:00 [INFO] Found 10 PDF(s) in ./03_cleaned. Output dir: ./04_normalized
2025-11-24 23:50:01 [INFO] Normalizing document1.pdf
2025-11-24 23:50:02 [INFO]   -> document1.pdf (profile: printer, size: 1.2 MB)
2025-11-24 23:50:02 [INFO] Archived original: ./99_archived/document1.pdf
2025-11-24 23:50:03 [INFO] All PDFs processed.
```

### File Size Comparison

```
Before (03_cleaned):
document1.pdf    5.2 MB

After (04_normalized, printer profile):
document1.pdf    1.8 MB  (65% reduction)
```

## Error Handling

Errors are logged but processing continues for remaining files:
- **Ghostscript not found** - Script exits with error
- **Individual PDF fails** - Logged, processing continues
- **Output dir creation fails** - Script exits with error

## Examples

### Example 1: Optimize for Web (Smallest Size)
```bash
python workflows/pdf_normalizer_new.py \
    ./pdfs \
    ./web_pdfs \
    --profile screen
# Suitable for web viewing, smallest file sizes
```

### Example 2: High-Quality Print
```bash
python workflows/pdf_normalizer_new.py \
    ./pdfs \
    ./print_pdfs \
    --profile prepress \
    --compat 1.4
# Professional printing quality
```

### Example 3: Batch Normalize with Archiving
```bash
python workflows/pdf_normalizer_new.py \
    ./03_cleaned \
    ./04_normalized \
    --profile printer \
    --archive-dir ./99_archived \
    --log-file ./logs/normalize_$(date +%Y%m%d).log
# Standard workflow with archiving and logging
```

## Integration with Batch Workflow

Typical pipeline:

```bash
# Step 1: Split and clean
python workflows/pdf_batch_tools_new.py \
    --in-dir ./01_input \
    --out-dir-split ./02_processed \
    --out-dir-clean ./03_cleaned \
    --every 2

# Step 2: Normalize
python workflows/pdf_normalizer_new.py \
    ./03_cleaned \
    ./04_normalized \
    --profile printer \
    --archive-dir ./99_archived
```

## Troubleshooting

### Ghostscript Not Found
```bash
# Check if Ghostscript is installed
which gs  # macOS/Linux
where gs  # Windows

# Install if missing
brew install ghostscript  # macOS
```

### Normalization Fails
- Check input PDF is valid: `gs -dNODISPLAY -dBATCH input.pdf`
- Try different profile: `--profile default`
- Check disk space

### Files Too Large
- Use more aggressive profile: `--profile screen`
- Check if images can be downsampled

### Files Too Small (Quality Loss)
- Use less aggressive profile: `--profile prepress`
- Increase compatibility level: `--compat 1.7`

## Performance

Processing speed depends on:
- PDF size and complexity
- Ghostscript profile (screen = fastest, prepress = slowest)
- CPU speed
- Disk I/O

Typical: 1-2 seconds per MB on modern hardware with `printer` profile.

## Related Tools

- [`tools/find_ghostscript.py`](../tools/find_ghostscript.py) - Ghostscript detection
- [`tools/normalize.py`](../tools/normalize.py) - Normalization logic
- [`tools/setup_logging.py`](../tools/setup_logging.py) - Logging configuration
