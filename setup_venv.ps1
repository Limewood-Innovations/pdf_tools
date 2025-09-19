# Einmalige Einrichtung auf Windows
param(
  [string]$Base = $PSScriptRoot
)

if (!(Test-Path $Base)) { New-Item -ItemType Directory -Force -Path $Base | Out-Null }
Set-Location $Base

# Python prüfen
$py = (Get-Command python -ErrorAction SilentlyContinue)
if (!$py) {
  Write-Host "Python nicht gefunden. Bitte Python 3.12 installieren und PATH setzen."
  exit 1
}

python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt

# Standardordner im Projekt
New-Item -ItemType Directory -Force -Path (Join-Path $Base '01_input') | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $Base '02_processed') | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $Base '03_cleand') | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $Base '99_archived') | Out-Null

Write-Host "Setup fertig. Skript-Test:"
python .\pdf_batch_tools.py --in-dir (Join-Path $Base '01_input') --out-dir-split (Join-Path $Base '02_processed') --out-dir-clean (Join-Path $Base '03_cleand')
