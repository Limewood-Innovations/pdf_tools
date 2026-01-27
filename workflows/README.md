# Workflows Directory

This directory contains all workflow scripts and their documentation for the PDF tools project.

## Available Workflows

### 1. IBAN Extraction (`iban_extraction.py`)
**Purpose**: Extract IBAN and BIC from loan documents using AI vision models

**Documentation**: [IBAN_EXTRACTION.md](IBAN_EXTRACTION.md)

**Quick Start**:
```bash
python workflows/iban_extraction.py --log-file ./logs/iban.log
```

**Use Cases**:
- Automated bank account extraction from scanned documents
- Batch processing of loan applications
- IBAN validation and organization

---

### 2. PDF Batch Processing (`pdf_batch_tools_new.py`)
**Purpose**: Split PDFs and remove blank pages

**Documentation**: [PDF_BATCH_PROCESSING.md](PDF_BATCH_PROCESSING.md)

**Quick Start**:
```bash
python workflows/pdf_batch_tools_new.py \
    --in-dir ./01_input \
    --out-dir-split ./02_processed \
    --out-dir-clean ./03_cleaned \
    --every 2
```

**Use Cases**:
- Splitting large PDFs into manageable chunks
- Removing blank/noise pages from scanned documents
- Preparing PDFs for further processing

---

### 3. PDF Normalization (`pdf_normalizer_new.py`)
**Purpose**: Optimize PDFs using Ghostscript

**Documentation**: [PDF_NORMALIZATION.md](PDF_NORMALIZATION.md)

**Quick Start**:
```bash
python workflows/pdf_normalizer_new.py \
    ./03_cleaned \
    ./04_normalized \
    --profile printer
```

**Use Cases**:
- Reducing PDF file sizes
- Ensuring PDF 1.4 compatibility
- Optimizing for specific outputs (web, print, prepress)

---

### 4. YAML Workflow Executor (`run_workflow.py`)
**Purpose**: Execute automation workflows defined in YAML

**Documentation**: [YAML_WORKFLOW_EXECUTOR.md](YAML_WORKFLOW_EXECUTOR.md)

**Quick Start**:
```bash
python workflows/run_workflow.py path/to/workflow.yaml --dry-run
```

**Use Cases**:
- Creating custom multi-step workflows
- Automating complex PDF processing pipelines
- Orchestrating multiple tools

---

### 5. SharePoint to Local Copy (`copy-sharepoint-to-local.ps1`)
**Purpose**: Download files from SharePoint Online to local storage

**Documentation**: [SHAREPOINT_COPY.md](SHAREPOINT_COPY.md)

**Quick Start**:
```powershell
.\workflows\copy-sharepoint-to-local.ps1 `
    -SiteUrl "https://tenant.sharepoint.com/sites/Team" `
    -LibraryName "Shared Documents" `
    -LocalPath "C:\downloads"
```

**Use Cases**:
- Automated SharePoint file downloads
- Syncing SharePoint libraries to local/network storage
- Batch downloading PDFs for processing

---

## Typical Workflow Pipeline

A typical complete pipeline using all workflows:

```bash
# Step 0: Download from SharePoint (Windows PowerShell)
.\workflows\copy-sharepoint-to-local.ps1 `
    -SiteUrl "https://tenant.sharepoint.com/sites/Team" `
    -LibraryName "Documents" `
    -LocalPath ".\01_input" `
    -FileExtensions pdf

# Step 1: Split and clean PDFs
python workflows/pdf_batch_tools_new.py \
    --in-dir ./01_input \
    --out-dir-split ./02_processed \
    --out-dir-clean ./03_cleaned \
    --every 2 \
    --archive-dir ./99_archived

# Step 2: Normalize PDFs
python workflows/pdf_normalizer_new.py \
    ./03_cleaned \
    ./04_normalized \
    --profile printer \
    --archive-dir ./99_archived

# Step 3: Extract IBANs
python workflows/iban_extraction.py \
    --input-dir ./04_normalized \
    --output-dir ./05_final \
    --error-dir ./98_error \
    --archive-dir ./99_archived \
    --log-file ./logs/iban.log
```

## Directory Structure

```
workflows/
├── README.md                          # This file
├── iban_extraction.py                 # IBAN extraction script
├── pdf_batch_tools_new.py             # Batch processing script
├── pdf_normalizer_new.py              # Normalization script
├── run_workflow.py                    # YAML executor
├── copy-sharepoint-to-local.ps1       # SharePoint download script
├── IBAN_EXTRACTION.md                 # IBAN documentation
├── PDF_BATCH_PROCESSING.md            # Batch processing documentation
├── PDF_NORMALIZATION.md               # Normalization documentation
├── YAML_WORKFLOW_EXECUTOR.md          # YAML executor documentation
└── SHAREPOINT_COPY.md                 # SharePoint copy documentation
```

## Common Options

All workflows support these common patterns:

### Logging
```bash
--log-file ./logs/workflow_$(date +%Y%m%d).log
```

### Archiving
```bash
--archive-dir ./99_archived
```

### Custom Directories
```bash
--input-dir /custom/input \
--output-dir /custom/output \
--error-dir /custom/errors
```

## Dependencies

### Global
```bash
pip install pypdf requests pyyaml pdf2image Pillow
```

### PowerShell (for SharePoint workflow)
```powershell
Install-Module PnP.PowerShell -Scope CurrentUser
```

### System
- **Ghostscript** (for normalization)
- **Poppler** (for IBAN extraction with vision models)
- **Ollama** (for IBAN extraction)

### Installation
```bash
# macOS
brew install ghostscript poppler

# Ubuntu/Debian
sudo apt-get install ghostscript poppler-utils

# Ollama
curl https://ollama.ai/install.sh | sh
ollama pull qwen3-vl:30b
```

## Environment Variables

```bash
# Ollama configuration
export OLLAMA_URL="http://localhost:11434"
export OLLAMA_MODEL="qwen3-vl:30b"

# Pushover notifications (optional)
export PUSHOVER_USER_KEY="your-user-key"
export PUSHOVER_TOKEN="your-app-token"

# SharePoint (optional)
export SP_SITE_URL="https://yourtenant.sharepoint.com/sites/..."
export SP_FOLDER_PATH="Shared Documents/PDFs"
```

## Getting Help

Each workflow has comprehensive help:

```bash
python workflows/iban_extraction.py --help
python workflows/pdf_batch_tools_new.py --help
python workflows/pdf_normalizer_new.py --help
python workflows/run_workflow.py --help
```

## See Also

- [YAML_WORKFLOW_GUIDE.md](../YAML_WORKFLOW_GUIDE.md) - Complete YAML syntax guide
- [tools/](../tools/) - Modular tool library documentation
- [.agent/workflows/](../.agent/workflows/) - Example workflow definitions
