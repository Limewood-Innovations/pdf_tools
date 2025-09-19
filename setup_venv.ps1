# Einmalige Einrichtung auf Windows
param(
  [string]$Base = "C:\pdf-tools"
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

# Standardordner
New-Item -ItemType Directory -Force -Path C:\pdf-in | Out-Null
New-Item -ItemType Directory -Force -Path C:\pdf-2pages | Out-Null
New-Item -ItemType Directory -Force -Path C:\pdf-clean | Out-Null

Write-Host "Setup fertig. Skript-Test:"
python .\pdf_batch_tools.py --in-dir C:\pdf-in --out-dir-split C:\pdf-2pages --out-dir-clean C:\pdf-clean
