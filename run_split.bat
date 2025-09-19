@echo off
setlocal
set BASE=C:\pdf-tools
set PY=%BASE%\.venv\Scripts\python.exe
"%PY%" "%BASE%\pdf_batch_tools.py" --in-dir C:\pdf-in --out-dir-split C:\pdf-2pages --out-dir-clean C:\pdf-clean
endlocal
