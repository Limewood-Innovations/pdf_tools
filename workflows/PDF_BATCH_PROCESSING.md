# PDF Batch Processing Workflow

## Overview

The PDF batch processing workflow splits PDFs into smaller chunks, removes blank pages, and ensures PDF 1.4 compatibility. Designed for bulk processing of scanned documents with OCR noise.

## What It Does

1. **Splits PDFs** - Divides PDFs into N-page chunks (configurable)
2. **Removes Blank Pages** - Detects and removes blank/noise pages using multiple heuristics
3. **Ensures PDF 1.4** - Converts to PDF 1.4 format for maximum compatibility
4. **Archives** - Optionally moves processed originals to archive directory

## Directory Structure

```
01_input/          # Input PDFs to process
02_processed/      # Split PDF parts
03_cleaned/        # PDFs with blank pages removed
99_archived/       # Original PDFs (if archiving enabled)
logs/              # Optional log files
```

## Usage

### Split Only (No Cleaning)

```bash
python workflows/pdf_batch_tools_new.py \
    --in-dir ./01_input \
    --out-dir-split ./02_processed \
    --every 2 \
    --no-clean
```

### Split + Clean Blank Pages

```bash
python workflows/pdf_batch_tools_new.py \
    --in-dir ./01_input \
    --out-dir-split ./02_processed \
    --out-dir-clean ./03_cleaned \
    --every 2
```

### With Archiving and Logging

```bash
python workflows/pdf_batch_tools_new.py \
    --in-dir ./01_input \
    --out-dir-split ./02_processed \
    --out-dir-clean ./03_cleaned \
    --every 2 \
    --archive-dir ./99_archived \
    --log-file ./logs/batch_$(date +%Y%m%d).log
```

### Skip Splitting (Clean Only)

```bash
python workflows/pdf_batch_tools_new.py \
    --in-dir ./01_input \
    --out-dir-split ./02_processed \
    --out-dir-clean ./03_cleaned \
    --every 0
```

## CLI Options

### Required
| Option | Description |
|--------|-------------|
| `--in-dir` | Input directory containing PDFs |
| `--out-dir-split` | Output directory for split parts |

### Optional
| Option | Default | Description |
|--------|---------|-------------|
| `--out-dir-clean` | _(none)_ | Output directory for cleaned PDFs |
| `--every` | `0` | Split every N pages (0 = no splitting) |
| `--no-clean` | _(off)_ | Skip blank page removal |
| `--archive-dir` | _(none)_ | Archive processed originals here |
| `--log-file` | _(console)_ | Path to log file |

### Blank Page Detection
| Option | Default | Description |
|--------|---------|-------------|
| `--min-alnum` | `5` | Min alphanumeric chars for non-blank |
| `--min-alnum-ratio` | `0.2` | Min ratio of alnum/total chars |
| `--min-bytes` | `40` | Min content stream bytes |
| `--image-nonblank` | _(on)_ | Treat image pages as non-blank |
| `--no-image-nonblank` | _(off)_ | Don't auto-mark image pages |
| `--debug-pages` | _(off)_ | Log per-page decisions |
| `--no-fallback-empty` | _(off)_ | Don't copy original if all blank |

## Dependencies

```bash
pip install pypdf
```

The `convert` module (for PDF 1.4 conversion) should be available in the project.

## Workflow Steps

### Phase 1: Splitting (if `--every > 0`)
For each PDF in input directory:
1. Read PDF with pypdf
2. Split into N-page chunks
3. Remove structure tags
4. Convert to PDF 1.4
5. Save to `{original}_part_{NNN}.pdf`

### Phase 2: Cleaning (if `--out-dir-clean` specified and not `--no-clean`)
For each split part (or original if no splitting):
1. Analyze each page:
   - Extract text content
   - Count alphanumeric characters
   - Check content stream size
   - Detect images
2. Mark page as blank if ALL conditions met:
   - Text length < threshold
   - Alnum chars < minimum
   - Alnum ratio < minimum  
   - Content bytes < minimum
   - No images (unless `--no-image-nonblank`)
3. Keep only non-blank pages
4. Convert to PDF 1.4
5. Save cleaned PDF

### Phase 3: Archiving (if `--archive-dir` specified)
Move original PDFs to archive directory with timestamp handling for name conflicts.

## Blank Page Detection

Pages are considered blank if they meet ALL criteria:

```python
is_blank = (
    text_length <= 1 AND
    alnum_chars < 5 AND
    alnum_ratio < 0.2 AND
    content_bytes < 40 AND
    has_no_images
)
```

### Heuristics

1. **Text Length** - Raw extracted text must be ≤ 1 character
2. **Alphanumeric Count** - Must have < 5 alphanumeric chars
3. **Alphanumeric Ratio** - Must have < 20% alphanumeric content
4. **Content Bytes** - PDF content stream must be < 40 bytes
5. **Image Detection** - Pages with images treated as non-blank (configurable)

### OCR Noise Tolerance

The multi-criteria approach handles OCR artifacts:
- Scattered dots/noise (fails alnum ratio)
- Single stray characters (fails text length)
- Formatting marks (fails alnum count)
- Minimal content (fails bytes threshold)

## Output

### Console/Log Output
```
2025-11-24 23:40:00 [INFO] Processing: document1.pdf
2025-11-24 23:40:00 [INFO] Split document1.pdf into 10 parts
2025-11-24 23:40:01 [INFO] Cleaning document1_part_001.pdf
2025-11-24 23:40:01 [INFO]   Kept 1/2 pages
2025-11-24 23:40:02 [INFO] Moved to archive: ./99_archived/document1.pdf
```

### File Output
```
02_processed/
├── document1_part_001.pdf    # 2-page chunk
├── document1_part_002.pdf
└── ...

03_cleaned/
├── document1_part_001.pdf    # 1 page (blank removed)
├── document1_part_002.pdf
└── ...
```

## Examples

### Example 1: Split 100-page PDF into 2-page chunks
```bash
python workflows/pdf_batch_tools_new.py \
    --in-dir ./scans \
    --out-dir-split ./parts \
    --every 2 \
    --no-clean
# Output: 50 files of 2 pages each
```

### Example 2: Remove blank pages without splitting
```bash
python workflows/pdf_batch_tools_new.py \
    --in-dir ./dirty \
    --out-dir-split ./dirty \
    --out-dir-clean ./clean \
    --every 0
# Output: Cleaned PDFs with blanks removed
```

### Example 3: Aggressive blank detection (strict)
```bash
python workflows/pdf_batch_tools_new.py \
    --in-dir ./input \
    --out-dir-split ./split \
    --out-dir-clean ./clean \
    --every 2 \
    --min-alnum 10 \
    --min-alnum-ratio 0.3 \
    --min-bytes 100 \
    --no-image-nonblank \
    --debug-pages
# More strict blank detection + debug logging
```

## Troubleshooting

### Too Many Pages Removed
- Decrease thresholds: `--min-alnum 3 --min-bytes 20`
- Enable image protection: `--image-nonblank`
- Use `--debug-pages` to see decisions

### Not Enough Pages Removed
- Increase thresholds: `--min-alnum 10 --min-bytes 100`
- Disable image protection: `--no-image-nonblank`

### PDF 1.4 Conversion Errors
- Check `convert` module is available
- Review temp file permissions
- Check disk space

## Related Tools

- [`tools/split_pages.py`](../tools/split_pages.py) - PDF splitting logic
- [`tools/blank_page.py`](../tools/blank_page.py) - Blank page detection
- [`tools/move_to_archive.py`](../tools/move_to_archive.py) - Archiving
- [`tools/configure_logging.py`](../tools/configure_logging.py) - Logging setup
