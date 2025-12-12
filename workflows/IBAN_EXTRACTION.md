# IBAN Extraction Workflow

## Overview

The IBAN extraction workflow processes loan documents (Darlehen PDFs) to automatically extract and validate Austrian IBAN and BIC banking information using AI vision models.

## What It Does

1. **Splits PDFs** - Divides multi-page PDFs into 2-page chunks
2. **Vision Analysis** - Uses Ollama vision models (e.g., qwen3-vl:30b) to extract IBAN/BIC from all pages
3. **Validates** - Checks Austrian IBAN format and derives bank code/account number
4. **Organizes Files** - Moves processed files by account number, errors to separate directory
5. **Archives** - Stores original PDFs after successful processing
6. **Notifies** - Optional Pushover notifications for results

## Directory Structure

```
01_input/          # Input PDFs to process
02_processed/      # Successfully extracted (renamed: {account_number}.pdf)
98_error/          # Failed extractions for manual review
99_archived/       # Original PDFs after successful processing
logs/              # Optional log files
```

## Usage

### Basic Usage

```bash
# Process all PDFs in default input directory
python workflows/iban_extraction.py

# With custom directories
python workflows/iban_extraction.py \
    --input-dir ./documents \
    --output-dir ./success \
    --error-dir ./failed \
    --archive-dir ./archive
```

### With Logging

```bash
python workflows/iban_extraction.py \
    --log-file ./logs/iban_$(date +%Y%m%d).log
```

### Full Example

```bash
python workflows/iban_extraction.py \
    --input-dir ./01_input \
    --output-dir ./02_processed \
    --error-dir ./98_error \
    --archive-dir ./99_archived \
    --log-file ./logs/iban.log
```

### Silent Mode (No Notifications)

```bash
python workflows/iban_extraction.py \
    --no-pushover \
    --log-file ./logs/iban.log
```

## CLI Options

| Option | Default | Description |
|--------|---------|-------------|
| `--input-dir` | `./01_input` | Directory containing input PDF files |
| `--output-dir` | `./02_processed` | Where to save successfully processed files |
| `--error-dir` | `./98_error` | Where to save failed extractions |
| `--archive-dir` | `./99_archived` | Where to archive original PDFs |
| `--log-file` | _(console only)_ | Optional path to log file |
| `--no-pushover` | _(off)_ | Disable Pushover notifications |

## Dependencies

### Required
```bash
pip install pypdf pdf2image Pillow requests
```

### System Requirements
- **Ollama** - Running locally with a vision model (e.g., qwen3-vl:30b)
- **Poppler** - For PDF to image conversion
  ```bash
  # macOS
  brew install poppler
  
  # Ubuntu/Debian
  sudo apt-get install poppler-utils
  ```

### Optional
- **Pushover** - For push notifications (set env vars `PUSHOVER_USER_KEY`, `PUSHOVER_TOKEN`)

## Environment Variables

```bash
# Ollama configuration
export OLLAMA_URL="http://localhost:11434"
export OLLAMA_MODEL="qwen3-vl:30b"

# Optional: Pushover notifications
export PUSHOVER_USER_KEY="your-user-key"
export PUSHOVER_TOKEN="your-app-token"
```

**Note:** Pushover notifications can be completely disabled using the `--no-pushover` flag, regardless of environment variable configuration.

## Workflow Steps

For each PDF in the input directory:

1. **Split** - Divide into 2-page chunks
2. **Extract** - Send all pages to Ollama vision model
3. **Parse** - Extract IBAN/BIC from JSON response
4. **Validate** - Check Austrian IBAN format (AT + 18 digits)
5. **Derive** - Extract bank code (chars 5-9) and account number (chars 10-20)
6. **Move** - Save to `{account_number}.pdf` in output directory
7. **Archive** - Move original to archive directory
8. **Notify** - Send Pushover notification (if configured)

On failure at any step, the chunk is moved to the error directory.

## Output

### Console/Log Output
```
2025-11-24 23:30:00 [INFO] Found 3 PDF(s) in ./01_input
2025-11-24 23:30:00 [INFO] Output directory: ./02_processed
============================================================

[1/3] Processing: document1.pdf
------------------------------------------------------------
2025-11-24 23:30:01 [INFO] Split into 10 parts
2025-11-24 23:30:05 [INFO] Processing file: document1_part_001.pdf
2025-11-24 23:30:08 [INFO] ✓ Extracted IBAN: AT771234567890123456
2025-11-24 23:30:08 [INFO]   Bank code: 12345
2025-11-24 23:30:08 [INFO]   Account number: 67890123456
2025-11-24 23:30:08 [INFO]   Confidence: 0.95
2025-11-24 23:30:08 [INFO] Moved to: ./02_processed/67890123456.pdf
2025-11-24 23:30:10 [INFO] Parts processed: 8 success, 2 errors
2025-11-24 23:30:10 [INFO] Archived original to: ./99_archived/document1.pdf

============================================================
[SUMMARY] Total parts processed: 24 success, 6 errors
[SUMMARY] Error files location: ./98_error
[SUMMARY] Success files location: ./02_processed
```

### File Organization
```
02_processed/
├── 67890123456.pdf    # Extracted part with IBAN AT77...
├── 11223344556.pdf    # Another extracted part
└── ...

98_error/
├── document1_part_003.pdf    # Failed extraction
└── ...

99_archived/
├── document1.pdf    # Original after processing
└── ...
```

## Error Handling

Files are moved to `98_error/` when:
- Ollama vision model fails (timeout, 500 error, etc.)
- No IBAN found in document
- Invalid Austrian IBAN format
- Account info extraction fails

Check the log file for detailed error messages.

## Tips

1. **Model Selection** - Use vision models optimized for OCR (e.g., qwen3-vl, llava)
2. **GPU Acceleration** - Run Ollama with GPU for faster processing
3. **Batch Size** - Process in small batches to avoid memory issues
4. **Error Review** - Check `98_error/` directory regularly for failed extractions
5. **Log Rotation** - Use dated log files: `--log-file ./logs/iban_$(date +%Y%m%d).log`
6. **Silent Processing** - Use `--no-pushover` for batch jobs to avoid notification spam

## Troubleshooting

### No IBANs Found
- Check if Ollama is running: `curl http://localhost:11434/api/tags`
- Verify vision model is installed: `ollama list`
- Review PDF quality - ensure text is readable

### Slow Processing
- Use GPU-accelerated Ollama
- Reduce DPI in `tools/ollama_client.py` (default: 200)
- Process smaller batches

### Import Errors
```bash
# Missing pdf2image
pip install pdf2image Pillow

# Missing poppler
brew install poppler  # macOS
```

## Related Tools

- [`tools/ollama_client.py`](../tools/ollama_client.py) - Vision model integration
- [`tools/iban_validator.py`](../tools/iban_validator.py) - IBAN validation
- [`tools/split_pages.py`](../tools/split_pages.py) - PDF splitting
