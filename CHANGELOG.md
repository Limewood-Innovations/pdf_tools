# Changelog

All notable changes to this project are documented here.

## 2026-04-17

### Added
- **Ghostscript cidfmap drop-in for Arial/Times/Calibri** (f9d8003): `deploy/95-arial-liberation.conf` maps `ArialMT`, `TimesNewRomanPSMT`, `Calibri` (and PostScript-name variants) to local TrueType files. Without it Ghostscript silently substitutes embedded Arial subset fonts with `DroidSansFallback`, dropping lowercase `h`/`i` glyphs and corrupting Sonderzeichen in normalized output (incident `2026_04_17_pdf_error/`).
- **Idempotent server font provisioning script** (f9d8003): `deploy/install_server_fonts.sh` installs `fonts-liberation`, `ttf-mscorefonts-installer`, `fonts-crosextra-carlito`, drops the cidfmap into `/etc/ghostscript/cidfmap.d/`, and runs `update-gsfontmap`. Calibri uses Carlito (metric-compat OSS clone) which renders Western glyphs but may shift Sonderzeichen — real Calibri must be supplied separately if exact fidelity is required.

### Changed
- **README**: add Linux Server-Setup section pointing at `deploy/install_server_fonts.sh` (f9d8003).

## 2026-04-02

### Fixed
- `tools/normalize.py`: pre-repair PDFs via pikepdf before Ghostscript normalization. List & Label generated PDFs with broken object references caused GS to hang indefinitely or produce ~6KB stub files. pikepdf rewrites the PDF structure, fixing the references before GS processes them.
- `tools/normalize.py`: escape `%` characters in output filenames. Ghostscript interprets `%` in `-sOutputFile` as printf format specifiers, causing failures for files like `...17,81%_mit Anlagen.pdf`.
- `tools/normalize.py`: add missing `timeout=300` for Ghostscript subprocess (was documented in March incident but absent from code). Add output size validation to detect and reject stub files.
- `workflows/copy-sharepoint-to-local.ps1`: stop renaming files on SharePoint before download. Previous behavior caused cascading timestamp stacking when downloads failed, making files unrecoverable without manual cleanup. Timestamps are now only applied to local filenames.
- `workflows/copy-sharepoint-to-local.ps1`: add per-file error handling so one failed download no longer aborts the entire batch.
- `workflows/copy-sharepoint-to-local.ps1`: fix missing `-LibraryName` and `-SourceFolder` parameters in recursive folder calls.

### Changed
- `tools/convert_to_pdfa.py` now accepts explicit PDF/A levels (`1b`, `2b`, `2u`, `3b`, `3u`, `3a`) and defaults to `3a`.
- `workflows/pdf_normalizer.py` now supports `--pdfa-level` and defaults to `3a` when `--pdfa` is enabled.
- PDF/A conversion uses the discovered Ghostscript executable from the normalizer workflow.

## 2025-09-16

### Added
- Core Python tool `pdf_batch_tools.py`:
  - Split input PDF into parts every N pages (`--every`, default 2).
  - Optional removal of blank pages with robust heuristics (text ratio, min bytes, image detection).
  - CLI flags to tune behavior: `--min-alnum`, `--min-alnum-ratio`, `--min-bytes`, `--image-nonblank`/`--no-image-nonblank`, `--no-clean`.
- Windows helper scripts:
  - `run_split.bat` to run splitting/cleaning against `C:\\pdf-in` → `C:\\pdf-2pages`/`C:\\pdf-clean`.
  - `watch-and-run.ps1` to watch a folder for new PDFs and auto-run the tool.
  - `setup_venv.ps1` to create a virtualenv and install dependencies, plus bootstrap folders.
- Containerization:
  - `Dockerfile` to build a minimal image running the PDF split/clean tool with `pypdf`.
  - `Dockerfile.sharepoint` and `entrypoint-sharepoint.ps1` to run the SharePoint copy utility in a container via environment variables (mount target to `/data`).
  - `docker-compose.yml` to run the PDF split/clean container with project folders mounted (01_input → 02_processed/03_cleaned) and default arguments.
- Dependencies:
  - `requirements.txt` with `pypdf>=4.2.0`.
- Documentation:
  - `README.md` with Windows quickstart, manual usage, Task Scheduler notes, and Docker usage for both the Python tool and the SharePoint copy container.
- SharePoint copy utility:
  - PowerShell script `copy-sharepoint-to-local.ps1` to copy files from SharePoint Online libraries/folders to a local/UNC path. Supports Interactive/Device/Credentials auth, recursion, overwrite, and `-ModifiedSince`. README updated with usage examples.

### Changed
- PDF outputs are now untagged by default: `pdf_batch_tools.py` strips PDF tagging metadata before writing files. Removes catalog keys (`/StructTreeRoot`, `/MarkInfo`, `/RoleMap`) and page-level keys (`/Tabs`, `/StructParents`).
 - Default folder layout updated to project-relative names: `01_input`, `02_processed`, `03_cleand`, `99_archived`. Scripts (`run_split.bat`, `watch-and-run.ps1`, `setup_venv.ps1`) now resolve paths relative to the script directory.
