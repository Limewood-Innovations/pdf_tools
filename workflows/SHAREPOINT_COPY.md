# SharePoint to Local Copy Workflow

## Overview

The SharePoint copy workflow downloads files from SharePoint Online document libraries to local or network storage. It supports multiple authentication methods, selective file filtering, and automatic organization of processed files.

## What It Does

1. **Connects to SharePoint** - Supports multiple authentication methods (interactive, app-only, etc.)
2. **Downloads Files** - Copies files from SharePoint libraries to local/network paths
3. **Filters Files** - Downloads only specified file types (default: PDF)
4. **Checks Modifications** - Optionally downloads only recently modified files
5. **Organizes Files** - Automatically moves processed SharePoint files to "Fertig" (finished) folder
6. **Preserves Structure** - Optionally maintains folder hierarchy

## Directory Structure

```
SharePoint:
  Shared Documents/
    Reports/
      ├── file1.pdf
      ├── file2.pdf
      └── Fertig/          # Processed files moved here
          ├── file1.pdf
          └── file2.pdf

Local:
  C:\downloads\
    ├── file1.pdf
    └── file2.pdf
```

## Usage

### Basic Usage (Interactive Authentication)

```powershell
.\workflows\copy-sharepoint-to-local.ps1 `
    -SiteUrl "https://tenant.sharepoint.com/sites/Team" `
    -LibraryName "Shared Documents" `
    -LocalPath "C:\downloads"
```

### With Specific Folder

```powershell
.\workflows\copy-sharepoint-to-local.ps1 `
    -SiteUrl "https://tenant.sharepoint.com/sites/Team" `
    -LibraryName "Shared Documents" `
    -SourceFolder "Reports/2025" `
    -LocalPath "C:\downloads\reports" `
    -Recursive
```

### Using Server-Relative URL

```powershell
.\workflows\copy-sharepoint-to-local.ps1 `
    -SiteUrl "https://tenant.sharepoint.com/sites/Team" `
    -ServerRelativeUrl "/sites/Team/Shared Documents/Export" `
    -LocalPath "C:\exports"
```

### With Date Filter

```powershell
.\workflows\copy-sharepoint-to-local.ps1 `
    -SiteUrl "https://tenant.sharepoint.com/sites/Team" `
    -LibraryName "Shared Documents" `
    -LocalPath "C:\downloads" `
    -ModifiedSince "2025-01-01"
```

### Multiple File Types

```powershell
.\workflows\copy-sharepoint-to-local.ps1 `
    -SiteUrl "https://tenant.sharepoint.com/sites/Team" `
    -LibraryName "Documents" `
    -LocalPath "C:\downloads" `
    -FileExtensions pdf,docx,xlsx
```

### App-Only Authentication (Client Secret)

```powershell
.\workflows\copy-sharepoint-to-local.ps1 `
    -SiteUrl "https://tenant.sharepoint.com/sites/Team" `
    -Auth AppSecret `
    -TenantId "<TENANT_ID>" `
    -ClientId "<CLIENT_ID>" `
    -ClientSecret "<CLIENT_SECRET>" `
    -ServerRelativeUrl "/sites/Team/Shared Documents/Export" `
    -LocalPath "C:\exports"
```

### App-Only Authentication (Certificate)

```powershell
.\workflows\copy-sharepoint-to-local.ps1 `
    -SiteUrl "https://tenant.sharepoint.com/sites/Team" `
    -Auth Certificate `
    -TenantId "<TENANT_ID>" `
    -ClientId "<CLIENT_ID>" `
    -CertificatePath ".\app.pfx" `
    -CertificatePassword "PfxPassword" `
    -LibraryName "Shared Documents" `
    -LocalPath "C:\downloads"
```

## Parameters

### Required

| Parameter | Description |
|-----------|-------------|
| `-SiteUrl` | Full SharePoint site URL (e.g., `https://tenant.sharepoint.com/sites/Team`) |
| `-LocalPath` | Target local or UNC path (e.g., `C:\data` or `\\server\share`) |

### Source Location (Choose One)

| Parameter | Description |
|-----------|-------------|
| `-LibraryName` | Document library name (e.g., "Shared Documents") |
| `-ServerRelativeUrl` | Full server-relative URL (e.g., "/sites/Team/Shared Documents/Reports") |
| `-SourceFolder` | Folder path under library root (e.g., "Reports/2025") - used with `-LibraryName` |

### Optional

| Parameter | Default | Description |
|-----------|---------|-------------|
| `-Recursive` | `$false` | Recurse into subfolders |
| `-Overwrite` | `$false` | Overwrite existing local files |
| `-ModifiedSince` | _(none)_ | Only download files modified on/after this date |
| `-FileExtensions` | `pdf` | File extensions to download (comma-separated) |
| `-MoveToFertig` | `$true` | Move processed SharePoint files to "Fertig" subfolder |
| `-Auth` | `Interactive` | Authentication mode (see below) |

### Authentication Modes

| Mode | Description | Required Parameters |
|------|-------------|---------------------|
| `Interactive` | Browser-based login (default) | None |
| `DeviceLogin` | Device code flow | None |
| `Credentials` | Username/password | `-Credential` (optional, will prompt) |
| `AppSecret` | App-only with client secret | `-TenantId`, `-ClientId`, `-ClientSecret` |
| `Certificate` | App-only with certificate | `-TenantId`, `-ClientId`, `-CertificatePath`, `-CertificatePassword` (optional) |

## Dependencies

### PowerShell Module

```powershell
# Install PnP PowerShell module
Install-Module PnP.PowerShell -Scope CurrentUser

# Verify installation
Get-Module PnP.PowerShell -ListAvailable
```

### Requirements

- **PowerShell 5.1** or higher
- **PnP.PowerShell** module
- **SharePoint Online** access permissions

## Features

### Smart Download

- **Skip unchanged files** - Compares modification dates
- **Resume support** - Only downloads new/modified files
- **Bandwidth efficient** - Avoids re-downloading existing files

### File Organization

- **Automatic archiving** - Moves processed files to "Fertig" folder in SharePoint
- **Folder structure** - Preserves hierarchy with `-Recursive`
- **Selective download** - Filter by file extension

### Authentication Flexibility

- **Interactive** - Best for manual runs
- **App-only** - Best for automation/scheduled tasks
- **Certificate-based** - Most secure for production

## Workflow Steps

1. **Validate Parameters** - Check required parameters and module availability
2. **Connect to SharePoint** - Authenticate using selected method
3. **Resolve Folder Path** - Determine source folder location
4. **Filter Files** - Apply extension and date filters
5. **Download Files** - Copy files to local path
6. **Move to Fertig** - Archive processed files in SharePoint (if enabled)
7. **Recurse Subfolders** - Process child folders (if `-Recursive`)

## Output

### Console Output

```
Source: /sites/Team/Shared Documents/Reports
Target: C:\downloads\reports
Only files modified since: 2025-01-01 00:00:00Z
File extensions: .pdf

Downloading: /sites/Team/Shared Documents/Reports/file1.pdf -> C:\downloads\reports\file1.pdf
Moved to Fertig: /sites/Team/Shared Documents/Reports/file1.pdf -> /sites/Team/Shared Documents/Reports/Fertig/file1.pdf
Skip (up-to-date): /sites/Team/Shared Documents/Reports/file2.pdf

Completed.
```

### File Organization

**Before:**
```
SharePoint: Shared Documents/Reports/
├── file1.pdf
├── file2.pdf
└── file3.pdf

Local: C:\downloads\
(empty)
```

**After:**
```
SharePoint: Shared Documents/Reports/
├── Fertig/
│   ├── file1.pdf
│   ├── file2.pdf
│   └── file3.pdf

Local: C:\downloads\
├── file1.pdf
├── file2.pdf
└── file3.pdf
```

## Examples

### Example 1: Download All PDFs from Library

```powershell
.\workflows\copy-sharepoint-to-local.ps1 `
    -SiteUrl "https://contoso.sharepoint.com/sites/Finance" `
    -LibraryName "Invoices" `
    -LocalPath "\\fileserver\archive\invoices" `
    -Recursive `
    -Overwrite
```

### Example 2: Download Recent Files Only

```powershell
.\workflows\copy-sharepoint-to-local.ps1 `
    -SiteUrl "https://contoso.sharepoint.com/sites/HR" `
    -ServerRelativeUrl "/sites/HR/Documents/Contracts" `
    -LocalPath "C:\contracts" `
    -ModifiedSince "2025-01-01" `
    -MoveToFertig:$false
```

### Example 3: Automated Download with App Secret

```powershell
# For scheduled tasks/automation
.\workflows\copy-sharepoint-to-local.ps1 `
    -SiteUrl "https://contoso.sharepoint.com/sites/Data" `
    -Auth AppSecret `
    -TenantId "12345678-1234-1234-1234-123456789012" `
    -ClientId "87654321-4321-4321-4321-210987654321" `
    -ClientSecret $env:SP_CLIENT_SECRET `
    -LibraryName "Exports" `
    -SourceFolder "Daily" `
    -LocalPath "C:\data\exports" `
    -FileExtensions pdf,xlsx `
    -Recursive
```

### Example 4: Download Without Moving Files

```powershell
# Keep files in original SharePoint location
.\workflows\copy-sharepoint-to-local.ps1 `
    -SiteUrl "https://contoso.sharepoint.com/sites/Team" `
    -LibraryName "Shared Documents" `
    -LocalPath "C:\backup" `
    -MoveToFertig:$false `
    -Recursive
```

## App Registration (For App-Only Auth)

### Azure AD App Setup

1. **Register App** in Azure Portal
   - Navigate to Azure Active Directory → App registrations
   - Click "New registration"
   - Name: "SharePoint File Sync"
   - Supported account types: "Single tenant"

2. **API Permissions**
   - Add permission: SharePoint → Application permissions
   - Required: `Sites.Read.All` or `Sites.ReadWrite.All`
   - Grant admin consent

3. **Client Secret** (for AppSecret auth)
   - Certificates & secrets → New client secret
   - Copy the secret value (only shown once)

4. **Certificate** (for Certificate auth)
   - Certificates & secrets → Upload certificate
   - Or use existing PFX file

### SharePoint Permissions

Grant the app access to the specific site:

```powershell
# Connect as admin
Connect-PnPOnline -Url "https://contoso-admin.sharepoint.com" -Interactive

# Grant app permissions
Grant-PnPAzureADAppSitePermission `
    -AppId "<CLIENT_ID>" `
    -DisplayName "SharePoint File Sync" `
    -Site "https://contoso.sharepoint.com/sites/Team" `
    -Permissions Read
```

## Troubleshooting

### Module Not Found

```powershell
# Install PnP PowerShell
Install-Module PnP.PowerShell -Scope CurrentUser -Force

# If using PowerShell 7+
Install-Module PnP.PowerShell -Scope CurrentUser -AllowPrerelease
```

### Authentication Fails

- **Interactive**: Ensure pop-ups are not blocked
- **AppSecret**: Verify TenantId, ClientId, and ClientSecret are correct
- **Certificate**: Check certificate path and password

### Files Not Downloading

- Check SharePoint permissions (Read access required)
- Verify folder path is correct
- Check file extension filter
- Review modification date filter

### "Fertig" Folder Creation Fails

- Requires Write permissions on SharePoint
- Disable with `-MoveToFertig:$false` if read-only access

## Integration with PDF Workflows

Typical pipeline for processing SharePoint PDFs:

```powershell
# Step 1: Download from SharePoint
.\workflows\copy-sharepoint-to-local.ps1 `
    -SiteUrl "https://tenant.sharepoint.com/sites/Team" `
    -LibraryName "Documents" `
    -LocalPath ".\01_input" `
    -FileExtensions pdf

# Step 2: Process PDFs (Windows PowerShell → Python)
python workflows\iban_extraction.py `
    --input-dir .\01_input `
    --output-dir .\02_processed `
    --error-dir .\98_error `
    --archive-dir .\99_archived `
    --log-file .\logs\iban.log
```

## Scheduled Task Setup

Create a Windows scheduled task for automated downloads:

```powershell
# Create scheduled task
$action = New-ScheduledTaskAction `
    -Execute "PowerShell.exe" `
    -Argument "-File C:\scripts\workflows\copy-sharepoint-to-local.ps1 -SiteUrl 'https://...' -LibraryName 'Documents' -LocalPath 'C:\downloads' -Auth AppSecret -TenantId '...' -ClientId '...' -ClientSecret '...'"

$trigger = New-ScheduledTaskTrigger -Daily -At 2AM

Register-ScheduledTask `
    -TaskName "SharePoint PDF Download" `
    -Action $action `
    -Trigger $trigger `
    -User "SYSTEM"
```

## Security Best Practices

1. **Use App-Only Auth** for automation (more secure than credentials)
2. **Certificate Auth** preferred over client secrets
3. **Store secrets securely** - Use Azure Key Vault or Windows Credential Manager
4. **Least Privilege** - Grant only required permissions (Read vs ReadWrite)
5. **Audit Logs** - Enable SharePoint audit logging
6. **Rotate Secrets** - Regularly rotate client secrets and certificates

## Related Workflows

- [IBAN Extraction](IBAN_EXTRACTION.md) - Process downloaded PDFs
- [PDF Batch Processing](PDF_BATCH_PROCESSING.md) - Split and clean PDFs
- [PDF Normalization](PDF_NORMALIZATION.md) - Optimize PDFs
