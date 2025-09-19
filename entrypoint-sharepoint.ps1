[CmdletBinding()]
param()

function Get-Bool([string]$val, [bool]$default=$true) {
  if ([string]::IsNullOrWhiteSpace($val)) { return $default }
  switch ($val.ToLowerInvariant()) {
    'true'|'1'|'yes'|'y'|'on' { return $true }
    'false'|'0'|'no'|'n'|'off' { return $false }
    default { return $default }
  }
}

$siteUrl = $env:SITE_URL
if ([string]::IsNullOrWhiteSpace($siteUrl)) {
  Write-Error "SITE_URL environment variable is required"; exit 2
}

$argsList = @('-SiteUrl', $siteUrl, '-LocalPath', ($env:LOCAL_PATH ?? '/data'))

if ($env:SERVER_RELATIVE_URL) { $argsList += @('-ServerRelativeUrl', $env:SERVER_RELATIVE_URL) }
elseif ($env:LIBRARY_NAME) {
  $argsList += @('-LibraryName', $env:LIBRARY_NAME)
  if ($env:SOURCE_FOLDER) { $argsList += @('-SourceFolder', $env:SOURCE_FOLDER) }
}

if ($env:AUTH) { $argsList += @('-Auth', $env:AUTH) }

if ($env:MODIFIED_SINCE) {
  try { [datetime]::Parse($env:MODIFIED_SINCE) | Out-Null; $argsList += @('-ModifiedSince', $env:MODIFIED_SINCE) } catch { }
}

if (Get-Bool $env:OVERWRITE $false) { $argsList += '-Overwrite' }
if (Get-Bool $env:RECURSIVE $true) { $argsList += '-Recursive' }

Write-Host "Running copy-sharepoint-to-local.ps1 with args: $($argsList -join ' ')" -ForegroundColor Cyan

& pwsh -File /app/copy-sharepoint-to-local.ps1 @argsList
exit $LASTEXITCODE

