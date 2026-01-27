# Documentation Overview

This repository contains a set of **workflow scripts** and their corresponding **markdown documentation**. Each workflow is self‑contained and can be executed independently, while the documentation provides detailed usage, parameters, and integration examples.

---

## 📂 Directory Structure

```
workflows/
├── README.md                     # High‑level overview (this file)
├── IBAN_EXTRACTION.md            # IBAN extraction workflow documentation
├── PDF_BATCH_PROCESSING.md       # Batch processing (split/clean) documentation
├── PDF_NORMALIZATION.md          # PDF normalization documentation
├── SHAREPOINT_COPY.md            # SharePoint → local copy documentation
├── YAML_WORKFLOW_EXECUTOR.md     # YAML executor documentation
├── DOCUMENTATION_README.md       # **This** file – summary of all docs
├── iban_extraction.py            # IBAN extraction script
├── pdf_batch_tools_new.py        # Batch processing script
├── pdf_normalizer_new.py         # Normalization script
├── copy-sharepoint-to-local.ps1  # PowerShell SharePoint download script
└── run_workflow.py               # YAML workflow runner
```

---

## 📖 Available Documentation

| Document | Description | Quick Link |
|----------|-------------|------------|
| **IBAN_EXTRACTION.md** | Extract IBAN/BIC from PDFs using Ollama vision model. Includes CLI flags, logging, and the new `--no-pushover` option. | [IBAN Extraction](IBAN_EXTRACTION.md) |
| **PDF_BATCH_PROCESSING.md** | Split PDFs into chunks, remove blank pages, and archive originals. | [Batch Processing](PDF_BATCH_PROCESSING.md) |
| **PDF_NORMALIZATION.md** | Optimize PDFs with Ghostscript, choose quality profiles, and archive originals. | [Normalization](PDF_NORMALIZATION.md) |
| **SHAREPOINT_COPY.md** | Download files from SharePoint Online to local storage with multiple authentication methods. | [SharePoint Copy](SHAREPOINT_COPY.md) |
| **YAML_WORKFLOW_EXECUTOR.md** | Run a YAML‑defined workflow that strings together the above scripts. | [YAML Executor](YAML_WORKFLOW_EXECUTOR.md) |

---

## 🚀 Getting Started

1. **Install dependencies** (see each doc for specifics). A common set is:
   ```bash
   pip install pypdf requests pyyaml pdf2image Pillow
   # PowerShell side (SharePoint)
   Install-Module PnP.PowerShell -Scope CurrentUser
   ```
2. **Run a workflow** – pick the script you need and follow the usage examples in its markdown file.
   ```bash
   # Example: Download PDFs from SharePoint then extract IBANs
   .\workflows\copy-sharepoint-to-local.ps1 -SiteUrl "https://tenant.sharepoint.com/sites/Team" -LibraryName "Documents" -LocalPath ".\01_input"
   python workflows/iban_extraction.py --input-dir .\01_input --log-file ./logs/iban.log
   ```
3. **Customize** – all scripts accept optional arguments for input/output directories, logging, and flags like `--no-pushover`.

---

## 🛠️ Extending the Workflows

- **Add new scripts** to the `workflows/` folder.
- **Create a markdown file** following the same template (overview, CLI options, examples).
- **Update this README** to include the new entry in the table above.

---

## 📚 Further Reading

- **Implementation Plan** – see `../.gemini/antigravity/brain/.../implementation_plan.md`
- **Task Checklist** – see `../.gemini/antigravity/brain/.../task.md`
- **Walkthrough** – see `../.gemini/antigravity/brain/.../walkthrough.md`

---

*All documentation is kept in sync with the codebase. If you notice any mismatches, please open an issue or update the relevant markdown file.*
