@echo off
setlocal ENABLEDELAYEDEXPANSION
rem Base directory is the folder of this script
set "BASE=%~dp0"
rem remove trailing backslash if present
if "%BASE:~-1%"=="\" set "BASE=%BASE:~0,-1%"

set "PY=%BASE%\.venv\Scripts\python.exe"
set "IN_DIR=%BASE%\01_input"
set "OUT_SPLIT=%BASE%\02_processed"
set "OUT_CLEAN=%BASE%\03_cleand"

"%PY%" "%BASE%\pdf_batch_tools.py" --in-dir "%IN_DIR%" --out-dir-split "%OUT_SPLIT%" --out-dir-clean "%OUT_CLEAN%"
endlocal
