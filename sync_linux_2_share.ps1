param(
  [string]$LinuxHost = "your.linux.host",
  [int]$Port = 22,
  [string]$LinuxUser = "youruser",

  # Use either SSH key OR password (prefer key)
  [string]$SshKeyPath = "C:\Keys\id_ed25519.ppk",    # or OpenSSH key path
  [string]$Password = "",                             # leave empty if using key

  # Get this once and paste it here (ed25519 recommended)
  [string]$SshHostKeyFingerprint = "ssh-ed25519 256 xx:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx",

  # Remote source and archive
  [string]$RemoteFolder = "/data/outgoing",
  [string]$RemoteArchiveFolder = "/data/outgoing/archived",

  # Destination Windows fileshare (UNC or local path)
  [string]$WindowsShare = "\\WIN-FILESRV01\drop\incoming",

  # Optional: only pick files older than N seconds (0 = off)
  [int]$MinAgeSeconds = 0,

  # Optional log
  [string]$LogPath = "C:\Scripts\logs\Sync-LinuxToShare.log"
)

$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Path (Split-Path $LogPath) -Force | Out-Null
Start-Transcript -Path $LogPath -Append

try {
  $winscpDll = "C:\Program Files (x86)\WinSCP\WinSCPnet.dll"
  if (-not (Test-Path $winscpDll)) { throw "WinSCP .NET assembly not found at $winscpDll" }
  Add-Type -Path $winscpDll

  if (-not (Test-Path $WindowsShare)) {
    New-Item -ItemType Directory -Path $WindowsShare -Force | Out-Null
  }

  $sessionOptions = New-Object WinSCP.SessionOptions -Property @{
    Protocol = [WinSCP.Protocol]::Sftp
    HostName = $LinuxHost
    PortNumber = $Port
    UserName = $LinuxUser
    SshHostKeyFingerprint = $SshHostKeyFingerprint
  }

  if ([string]::IsNullOrWhiteSpace($Password)) {
    $sessionOptions.SshPrivateKeyPath = $SshKeyPath
  } else {
    $sessionOptions.Password = $Password
  }

  $transferOptions = New-Object WinSCP.TransferOptions
  $transferOptions.TransferMode = [WinSCP.TransferMode]::Binary
  $transferOptions.OverwriteMode = [WinSCP.OverwriteMode]::Overwrite
  $transferOptions.ResumeSupport.State = $true
  $transferOptions.PreserveTimestamp = $true

  $session = New-Object WinSCP.Session
  try {
    $session.Open($sessionOptions)

    # Ensure archive folder exists
    if (-not $session.FileExists($RemoteArchiveFolder)) {
      $session.CreateDirectory($RemoteArchiveFolder) | Out-Null
    }

    # Build the remote mask (optionally enforce min age)
    $mask = "*"
    if ($MinAgeSeconds -gt 0) {
      # WinSCP file mask time constraint: >=Ns / Nm / Nh / Nd
      $mask = "*>={0}s" -f $MinAgeSeconds
    }
    $remoteMask = [WinSCP.RemotePath]::Combine($RemoteFolder, $mask)

    # Download but DO NOT delete; we’ll move to archive only after success
    $result = $session.GetFiles($remoteMask, (Join-Path $WindowsShare "*"), $false, $transferOptions)

    $hadFailures = $false

    foreach ($t in $result.Transfers) {
      if ($null -eq $t.Error) {
        $fileNameOnly = Split-Path -Path $t.FileName -Leaf
        $destBase = [System.IO.Path]::GetFileNameWithoutExtension($fileNameOnly)
        $destExt  = [System.IO.Path]::GetExtension($fileNameOnly)

        $archiveTarget = [WinSCP.RemotePath]::Combine(
          $RemoteArchiveFolder,
          [WinSCP.RemotePath]::EscapeFileMask($fileNameOnly)
        )

        # If a same-named file already exists in archive, add a timestamp
        if ($session.FileExists($archiveTarget)) {
          $ts = (Get-Date).ToString("yyyyMMdd-HHmmss")
          $newName = "{0}.{1}{2}" -f $destBase, $ts, $destExt
          $archiveTarget = [WinSCP.RemotePath]::Combine(
            $RemoteArchiveFolder,
            [WinSCP.RemotePath]::EscapeFileMask($newName)
          )
        }

        $session.MoveFile($t.FileName, $archiveTarget) | Out-Null
        Write-Host "Transferred and archived: $fileNameOnly"
      } else {
        Write-Error "FAILED to transfer: $($t.FileName) — $($t.Error.Message)"
        $hadFailures = $true
      }
    }

    if ($result.Failures.Count -gt 0 -or $hadFailures) {
      throw "One or more files failed to transfer."
    }
  }
  finally {
    $session.Dispose()
  }
}
catch {
  Write-Error $_
  Stop-Transcript | Out-Null
  exit 1
}

Stop-Transcript | Out-Null
exit 0