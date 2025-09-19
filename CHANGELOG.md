# Changelog

All notable changes to this project are documented here.

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
- Dependencies:
  - `requirements.txt` with `pypdf>=4.2.0`.
- Documentation:
  - `README.md` with Windows quickstart, manual usage, Task Scheduler notes, and Docker usage for both the Python tool and the SharePoint copy container.
- SharePoint copy utility:
  - PowerShell script `copy-sharepoint-to-local.ps1` to copy files from SharePoint Online libraries/folders to a local/UNC path. Supports Interactive/Device/Credentials auth, recursion, overwrite, and `-ModifiedSince`. README updated with usage examples.

### Changed
- PDF outputs are now untagged by default: `pdf_batch_tools.py` strips PDF tagging metadata before writing files. Removes catalog keys (`/StructTreeRoot`, `/MarkInfo`, `/RoleMap`) and page-level keys (`/Tabs`, `/StructParents`).
