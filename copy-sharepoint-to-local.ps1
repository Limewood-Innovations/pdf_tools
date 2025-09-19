#requires -Version 5.1
<#
.SYNOPSIS
  Copy files from SharePoint Online to a local/UNC folder.

.DESCRIPTION
  Uses the PnP.PowerShell module to connect to a SharePoint Online site and download
  files from a document library or a specific folder (server-relative URL).

.PARAMETER SiteUrl
  Full SharePoint site URL, e.g. https://tenant.sharepoint.com/sites/ProjectX

.PARAMETER LibraryName
  Name of the document library, e.g. "Shared Documents". Optional if ServerRelativeUrl is used.

.PARAMETER ServerRelativeUrl
  Server-relative URL of the folder to copy, e.g. "/sites/ProjectX/Shared Documents/Reports".
  If provided, overrides LibraryName/SourceFolder.

.PARAMETER SourceFolder
  Folder path under the library root, e.g. "Reports/2025". Optional.

.PARAMETER LocalPath
  Target local or UNC path, e.g. C:\\data\\sp-download or \\fileserver\\share\\sp

.PARAMETER Recursive
  Recurse into subfolders (default: on).

.PARAMETER Overwrite
  Overwrite existing local files.

.PARAMETER ModifiedSince
  Only download files modified on/after this date (UTC/local accepted). Example: "2025-01-01".

.PARAMETER Auth
  Authentication mode: Interactive | DeviceLogin | Credentials | AppSecret | Certificate (default: Interactive).

.PARAMETER Credential
  PSCredential to use when -Auth Credentials is selected.

.PARAMETER TenantId
  Directory (tenant) ID for app-only authentication (AppSecret/Certificate).

.PARAMETER ClientId
  Application (client) ID for app-only authentication (AppSecret/Certificate).

.PARAMETER ClientSecret
  Client secret (string) for app-only authentication (AppSecret).

.PARAMETER CertificatePath
  Path to a PFX certificate file for app-only authentication (Certificate).

.PARAMETER CertificatePassword
  Password for the PFX certificate (string) for app-only authentication (Certificate).

.EXAMPLE
  .\\copy-sharepoint-to-local.ps1 -SiteUrl https://tenant.sharepoint.com/sites/Team -LibraryName "Shared Documents" -SourceFolder Reports -LocalPath \\srv\\archive\\Reports -Recursive -Overwrite

.EXAMPLE
  .\\copy-sharepoint-to-local.ps1 -SiteUrl https://tenant.sharepoint.com/sites/Team -ServerRelativeUrl "/sites/Team/Shared Documents/Export" -LocalPath C:\\exports -ModifiedSince "2025-01-01"

.EXAMPLE
  # App-only with client secret
  .\\copy-sharepoint-to-local.ps1 -SiteUrl https://tenant.sharepoint.com/sites/Team `
    -Auth AppSecret -TenantId <TENANT_ID> -ClientId <CLIENT_ID> -ClientSecret '<CLIENT_SECRET>' `
    -ServerRelativeUrl "/sites/Team/Shared Documents/Export" -LocalPath C:\\exports

.EXAMPLE
  # App-only with certificate
  .\\copy-sharepoint-to-local.ps1 -SiteUrl https://tenant.sharepoint.com/sites/Team `
    -Auth Certificate -TenantId <TENANT_ID> -ClientId <CLIENT_ID> -CertificatePath .\\app.pfx -CertificatePassword 'PfxPassword' `
    -LibraryName "Shared Documents" -SourceFolder Export -LocalPath C:\\exports

.NOTES
  Requires: PnP.PowerShell
#>

[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)]  [string]$SiteUrl,
  [Parameter(Mandatory=$false)] [string]$LibraryName,
  [Parameter(Mandatory=$false)] [string]$ServerRelativeUrl,
  [Parameter(Mandatory=$false)] [string]$SourceFolder = "",
  [Parameter(Mandatory=$true)]  [string]$LocalPath,
  [Parameter(Mandatory=$false)] [switch]$Recursive = $true,
  [Parameter(Mandatory=$false)] [switch]$Overwrite,
  [Parameter(Mandatory=$false)] [datetime]$ModifiedSince,
  [Parameter(Mandatory=$false)] [ValidateSet('Interactive','DeviceLogin','Credentials','AppSecret','Certificate')] [string]$Auth = 'Interactive',
  [Parameter(Mandatory=$false)] [System.Management.Automation.PSCredential]$Credential,
  # App-only auth parameters
  [Parameter(Mandatory=$false)] [string]$TenantId,
  [Parameter(Mandatory=$false)] [string]$ClientId,
  [Parameter(Mandatory=$false)] [string]$ClientSecret,
  [Parameter(Mandatory=$false)] [string]$CertificatePath,
  [Parameter(Mandatory=$false)] [string]$CertificatePassword
)

function Ensure-Module {
  param([string]$Name)
  if (-not (Get-Module -ListAvailable -Name $Name)) {
    Write-Error "Required module '$Name' is not installed. Install via: Install-Module PnP.PowerShell -Scope CurrentUser" -ErrorAction Stop
  }
}

function Join-Url {
  param([string]$a,[string]$b)
  $a = ($a -replace '/+$','')
  $b = ($b -replace '^/+','')
  if ([string]::IsNullOrWhiteSpace($a)) { return '/' + $b }
  if ([string]::IsNullOrWhiteSpace($b)) { return $a }
  return "$a/$b"
}

function Get-SiteRelativePath {
  param([string]$ServerRelativeUrl,[string]$SiteServerRelative)
  if ($SiteServerRelative -eq '/') { $SiteServerRelative = '' }
  if ($ServerRelativeUrl.StartsWith($SiteServerRelative)) {
    return ($ServerRelativeUrl.Substring($SiteServerRelative.Length)).TrimStart('/')
  }
  return $ServerRelativeUrl.TrimStart('/')
}

function Resolve-ServerRelativeFolderUrl {
  param([string]$LibraryName,[string]$SourceFolder,[string]$ServerRelativeUrl)
  if ($ServerRelativeUrl) { return $ServerRelativeUrl }
  if (-not $LibraryName) {
    throw "Either -ServerRelativeUrl or -LibraryName must be provided."
  }
  $list = Get-PnPList -Identity $LibraryName -Includes RootFolder | Select-Object -First 1
  if (-not $list) { throw "Library not found: $LibraryName" }
  $root = $list.RootFolder.ServerRelativeUrl
  if ([string]::IsNullOrWhiteSpace($SourceFolder)) { return $root }
  return (Join-Url -a $root -b $SourceFolder)
}

function Ensure-Directory {
  param([string]$Path)
  if (-not (Test-Path -LiteralPath $Path)) { New-Item -ItemType Directory -Path $Path | Out-Null }
}

function Download-File {
  param(
    [string]$ServerRelativeUrl,
    [string]$TargetDirectory,
    [string]$TargetFileName,
    [switch]$Overwrite,
    [datetime]$ModifiedSince
  )

  Ensure-Directory -Path $TargetDirectory
  $target = Join-Path -Path $TargetDirectory -ChildPath $TargetFileName

  $shouldDownload = $true
  if ($ModifiedSince -or (Test-Path -LiteralPath $target)) {
    try {
      $li = Get-PnPFile -Url $ServerRelativeUrl -AsListItem -ErrorAction Stop
      $remoteModified = [datetime]$li.FieldValues['Modified']
      if ($ModifiedSince -and ($remoteModified -lt $ModifiedSince)) {
        $shouldDownload = $false
      }
      if (-not $Overwrite -and (Test-Path -LiteralPath $target)) {
        $localModified = (Get-Item -LiteralPath $target).LastWriteTime
        if ($remoteModified -le $localModified) {
          $shouldDownload = $false
        }
      }
    } catch {
      Write-Warning "Could not read metadata for $ServerRelativeUrl. Proceeding to download. $_"
    }
  }

  if ($shouldDownload) {
    Write-Host "Downloading: $ServerRelativeUrl -> $target" -ForegroundColor Cyan
    Get-PnPFile -Url $ServerRelativeUrl -Path $TargetDirectory -FileName $TargetFileName -AsFile -Force:$Overwrite.IsPresent -ErrorAction Stop | Out-Null
  } else {
    Write-Host "Skip (up-to-date): $ServerRelativeUrl" -ForegroundColor DarkGray
  }
}

function Copy-SharePointFolder {
  param(
    [string]$FolderServerRelative,
    [string]$LocalPath,
    [switch]$Recursive,
    [switch]$Overwrite,
    [datetime]$ModifiedSince
  )

  $web = Get-PnPWeb -Includes ServerRelativeUrl
  $sitePrefix = $web.ServerRelativeUrl
  if ($sitePrefix -eq '/') { $sitePrefix = '' }
  $siteRelative = Get-SiteRelativePath -ServerRelativeUrl $FolderServerRelative -SiteServerRelative $sitePrefix

  # Files in current folder
  $files = @()
  try {
    $files = Get-PnPFolderItem -FolderSiteRelativeUrl $siteRelative -ItemType File -ErrorAction Stop
  } catch {
    throw "Folder not found or not accessible: $FolderServerRelative ($_ )"
  }

  foreach ($f in $files) {
    $serverRel = if ($f.ServerRelativeUrl) { $f.ServerRelativeUrl } else { (Join-Url -a $FolderServerRelative -b $f.Name) }
    Download-File -ServerRelativeUrl $serverRel -TargetDirectory $LocalPath -TargetFileName $f.Name -Overwrite:$Overwrite -ModifiedSince:$ModifiedSince
  }

  if ($Recursive) {
    $subFolders = Get-PnPFolderItem -FolderSiteRelativeUrl $siteRelative -ItemType Folder | Where-Object { $_.Name -ne 'Forms' }
    foreach ($sf in $subFolders) {
      $subServerRel = if ($sf.ServerRelativeUrl) { $sf.ServerRelativeUrl } else { (Join-Url -a $FolderServerRelative -b $sf.Name) }
      $localSub = Join-Path -Path $LocalPath -ChildPath $sf.Name
      Ensure-Directory -Path $localSub
      Copy-SharePointFolder -FolderServerRelative $subServerRel -LocalPath $localSub -Recursive:$Recursive -Overwrite:$Overwrite -ModifiedSince:$ModifiedSince
    }
  }
}

# --- Main ---

try {
  Ensure-Module -Name 'PnP.PowerShell'
  switch ($Auth) {
    'Interactive' { Connect-PnPOnline -Url $SiteUrl -Interactive -ErrorAction Stop }
    'DeviceLogin' { Connect-PnPOnline -Url $SiteUrl -DeviceLogin -ErrorAction Stop }
    'Credentials' {
      if (-not $Credential) { $Credential = Get-Credential -Message "Enter SharePoint credentials" }
      Connect-PnPOnline -Url $SiteUrl -Credentials $Credential -ErrorAction Stop
    }
    'AppSecret' {
      if (-not $TenantId -or -not $ClientId -or -not $ClientSecret) {
        throw "Auth=AppSecret requires -TenantId, -ClientId and -ClientSecret"
      }
      $sec = ConvertTo-SecureString -AsPlainText $ClientSecret -Force
      Connect-PnPOnline -Url $SiteUrl -Tenant $TenantId -ClientId $ClientId -ClientSecret $sec -ErrorAction Stop
    }
    'Certificate' {
      if (-not $TenantId -or -not $ClientId -or -not $CertificatePath) {
        throw "Auth=Certificate requires -TenantId, -ClientId and -CertificatePath"
      }
      if ($CertificatePassword) {
        $pfx = ConvertTo-SecureString -AsPlainText $CertificatePassword -Force
        Connect-PnPOnline -Url $SiteUrl -Tenant $TenantId -ClientId $ClientId -CertificatePath $CertificatePath -CertificatePassword $pfx -ErrorAction Stop
      } else {
        Connect-PnPOnline -Url $SiteUrl -Tenant $TenantId -ClientId $ClientId -CertificatePath $CertificatePath -ErrorAction Stop
      }
    }
  }

  Ensure-Directory -Path $LocalPath
  $folderServerRel = Resolve-ServerRelativeFolderUrl -LibraryName $LibraryName -SourceFolder $SourceFolder -ServerRelativeUrl $ServerRelativeUrl
  Write-Host "Source: $folderServerRel`nTarget: $LocalPath" -ForegroundColor Green
  if ($ModifiedSince) { Write-Host ("Only files modified since: {0:u}" -f $ModifiedSince) -ForegroundColor Yellow }

  Copy-SharePointFolder -FolderServerRelative $folderServerRel -LocalPath $LocalPath -Recursive:$Recursive -Overwrite:$Overwrite -ModifiedSince:$ModifiedSince

  Write-Host "Completed." -ForegroundColor Green
}
catch {
  Write-Error $_
  exit 1
}
