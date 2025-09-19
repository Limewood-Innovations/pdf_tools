param(
  [string]$Base = $PSScriptRoot,
  [string]$InDir = (Join-Path $PSScriptRoot "01_input")
)

$venvPy = Join-Path $Base ".venv\Scripts\python.exe"
$script = Join-Path $Base "pdf_batch_tools.py"

$outSplit = Join-Path $Base "02_processed"
$outClean = Join-Path $Base "03_cleand"

$fsw = New-Object System.IO.FileSystemWatcher $InDir, "*.pdf"
$fsw.IncludeSubdirectories = $false
$fsw.EnableRaisingEvents = $true

Write-Host "Watching $InDir for new PDFs..."

$action = {
  Start-Sleep -Milliseconds 800
  & $using:venvPy $using:script --in-dir $using:InDir --out-dir-split $using:outSplit --out-dir-clean $using:outClean | Out-Host
}

Register-ObjectEvent $fsw Created -Action $action | Out-Null
Register-ObjectEvent $fsw Changed -Action $action | Out-Null

while ($true) { Start-Sleep -Seconds 5 }
