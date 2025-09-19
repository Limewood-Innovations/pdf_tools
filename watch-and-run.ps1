param(
  [string]$InDir = "C:\pdf-in",
  [string]$Base = "C:\pdf-tools"
)

$venvPy = Join-Path $Base ".venv\Scripts\python.exe"
$script = Join-Path $Base "pdf_batch_tools.py"

$fsw = New-Object System.IO.FileSystemWatcher $InDir, "*.pdf"
$fsw.IncludeSubdirectories = $false
$fsw.EnableRaisingEvents = $true

Write-Host "Watching $InDir for new PDFs..."

$action = {
  Start-Sleep -Milliseconds 800
  & $using:venvPy $using:script --in-dir $using:InDir --out-dir-split "C:\pdf-2pages" --out-dir-clean "C:\pdf-clean" | Out-Host
}

Register-ObjectEvent $fsw Created -Action $action | Out-Null
Register-ObjectEvent $fsw Changed -Action $action | Out-Null

while ($true) { Start-Sleep -Seconds 5 }
