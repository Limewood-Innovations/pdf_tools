# copy-sharepoint-to-local.ps1 Documentation

## Overview

`copy-sharepoint-to-local.ps1` is a PowerShell script that downloads files from SharePoint Online document libraries to a local or network folder. It supports multiple authentication methods, selective file filtering, and automatic organization of processed files.

## Features

- **Multiple authentication modes**: Interactive, DeviceLogin, Credentials, AppSecret, Certificate.
- **Selective download**: Filter by file extensions, modification date, and folder hierarchy.
- **Automatic archiving**: Moves processed SharePoint files to a `Fertig` (finished) sub‑folder.
- **Recursive processing**: Optionally traverse sub‑folders.
- **Overwrite control**: Choose whether to replace existing local files.

## Parameters

| Parameter | Required? | Default | Description |
|-----------|-----------|---------|-------------|
| `-SiteUrl` | Yes | – | Full SharePoint site URL (e.g., `https://tenant.sharepoint.com/sites/Team`). |
| `-LocalPath` | Yes | – | Destination local or UNC path (e.g., `C:\data` or `\\server\share`). |
| `-LibraryName` | No | – | Name of the document library (e.g., `Shared Documents`). |
| `-ServerRelativeUrl` | No | – | Full server‑relative URL (e.g., `/sites/Team/Shared Documents/Reports`). |
| `-SourceFolder` | No | – | Folder under the library root (used with `-LibraryName`). |
| `-Recursive` | No | `$false` | Recurse into sub‑folders. |
| `-Overwrite` | No | `$false` | Overwrite existing local files. |
| `-ModifiedSince` | No | – | Only download files modified on/after this date (ISO format). |
| `-FileExtensions` | No | `pdf` | Comma‑separated list of extensions to download. |
| `-MoveToFertig` | No | `$true` | Move processed SharePoint files to a `Fertig` sub‑folder. |
| `-Auth` | No | `Interactive` | Authentication mode (`Interactive`, `DeviceLogin`, `Credentials`, `AppSecret`, `Certificate`). |
| `-TenantId` | Conditional | – | Azure AD tenant ID (required for `AppSecret`/`Certificate`). |
| `-ClientId` | Conditional | – | Azure AD app client ID (required for `AppSecret`/`Certificate`). |
| `-ClientSecret` | Conditional | – | Client secret (required for `AppSecret`). |
| `-CertificatePath` | Conditional | – | Path to PFX certificate (required for `Certificate`). |
| `-CertificatePassword` | Optional | – | Password for the PFX certificate (if encrypted). |
| `-Credential` | Optional | – | PSCredential object for `Credentials` auth. |

## Usage Examples

### Basic Interactive Login
```powershell
.\workflows\copy-sharepoint-to-local.ps1 `
    -SiteUrl "https://tenant.sharepoint.com/sites/Team" `
    -LibraryName "Shared Documents" `
    -LocalPath "C:\downloads"
```

### Download Only PDFs from a Specific Folder (Recursive)
```powershell
.\workflows\copy-sharepoint-to-local.ps1 `
    -SiteUrl "https://tenant.sharepoint.com/sites/Team" `
    -LibraryName "Shared Documents" `
    -SourceFolder "Reports/2025" `
    -LocalPath "C:\downloads\reports" `
    -Recursive `
    -FileExtensions pdf
```

### App‑Only Authentication (Client Secret)
```powershell
.\workflows\copy-sharepoint-to-local.ps1 `
    -SiteUrl "https://tenant.sharepoint.com/sites/Team" `
    -Auth AppSecret `
    -TenantId "<TENANT_ID>" `
    -ClientId "<CLIENT_ID>" `
    -ClientSecret "<CLIENT_SECRET>" `
    -LibraryName "Documents" `
    -LocalPath "C:\downloads"
```

### App‑Only Authentication (Certificate)
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

### Download Files Modified Since a Date
```powershell
.\workflows\copy-sharepoint-to-local.ps1 `
    -SiteUrl "https://tenant.sharepoint.com/sites/Team" `
    -LibraryName "Shared Documents" `
    -LocalPath "C:\downloads" `
    -ModifiedSince "2025-01-01"
```

## Integration with PDF Workflows

Typical pipeline for processing SharePoint PDFs:
```powershell
# Step 0: Download PDFs from SharePoint
.\workflows\copy-sharepoint-to-local.ps1 `
    -SiteUrl "https://tenant.sharepoint.com/sites/Team" `
    -LibraryName "Documents" `
    -LocalPath ".\01_input" `
    -FileExtensions pdf

# Step 1: Split & clean PDFs (Python)
python workflows/pdf_batch_tools_new.py --in-dir .\01_input --out-dir .\02_processed

# Step 2: Normalize PDFs (Python)
python workflows/pdf_normalizer_new.py .\02_processed .\03_normalized

# Step 3: Extract IBANs (Python)
python workflows/iban_extraction.py --input-dir .\03_normalized --log-file ./logs/iban.log
```

## Dependencies

- **PowerShell 5.1+**
- **PnP.PowerShell** module:
  ```powershell
  Install-Module PnP.PowerShell -Scope CurrentUser
  ```
- Appropriate SharePoint permissions (Read for download, Write for archiving).

## Security Best Practices

1. Prefer **App‑Only** authentication for scheduled runs.
2. Use **certificate‑based** auth over client secrets when possible.
3. Store secrets securely (Azure Key Vault, Windows Credential Manager).
4. Grant the least privilege required (`Sites.Read.All` vs `Sites.ReadWrite.All`).
5. Rotate secrets/certificates regularly.

## Troubleshooting

- **Module not found**: Re‑install PnP.PowerShell with `-Force`.
- **Authentication failures**: Verify tenant/app IDs, secret, or certificate path.
- **No files downloaded**: Check folder path, file extension filter, and modification date.
- **"Fertig" folder creation fails**: Ensure the account has write permissions; disable with `-MoveToFertig:$false`.

---

*For more detailed information, see the full documentation file `SHAREPOINT_COPY.md` in the same directory.*
