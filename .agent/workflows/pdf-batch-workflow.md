---
description: PDF batch processing workflow - split, clean, and normalize
---

# PDF Batch Processing Workflow

This workflow orchestrates the complete PDF processing pipeline using the modular tools.

## Steps

### 1. Complete batch workflow

For a complete automated workflow, use the refactored `pdf_batch_tools.py`:

// turbo
```bash
python pdf_batch_tools.py \
    --in-dir ./01_input \
    --out-dir-split ./02_processed \
    --out-dir-clean ./03_cleaned \
    --every 2 \
    --archive-dir ./99_archived \
    --log-file ./logs/batch_processing.log
```

### 2. Normalize PDFs only

To normalize PDFs using Ghostscript:

// turbo
```bash
python pdf_normalizer.py ./03_cleaned ./04_normalized --profile printer --archive-dir ./99_archived
```

## Tool Modules

The workflow uses these modular tools located in the `tools/` directory:

- `configure_logging.py` - Logging configuration
- `split_pages.py` - PDF splitting functionality
- `blank_page.py` - Blank page detection and removal
- `move_to_archive.py` - File archiving utilities
- `find_ghostscript.py` - Ghostscript executable detection
- `setup_logging.py` - Normalizer logging setup
- `normalize.py` - PDF normalization with Ghostscript
- `utils.py` - Shared utility functions

## Configuration Options

### Split Options
- `--every N`: Split every N pages (0 to disable splitting)
- `--no-clean`: Skip blank page removal

### Blank Page Detection
- `--min-alnum N`: Minimum alphanumeric characters (default: 5)
- `--min-alnum-ratio R`: Minimum ratio of alphanumeric chars (default: 0.2)
- `--min-bytes N`: Minimum content stream bytes (default: 40)
- `--image-nonblank`: Treat pages with images as non-blank (default: on)

### Normalization
- `--profile`: Ghostscript profile (screen, ebook, printer, prepress, default)
- `--compat`: PDF compatibility level (default: 1.4)

### Archiving
- `--archive-dir`: Directory to move processed originals

### Logging
- `--log-file`: Path to log file with rotation support
- `--debug-pages`: Enable detailed per-page debug output
