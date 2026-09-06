# KentScript v3.1.0 Installer for Windows
# Supports Windows 7, 8, 8.1, 10, 11
# Compatible with PowerShell 2.0+ (Windows 7 default)
# Run as Administrator: right-click -> Run with PowerShell

$Version = "3.1.0"
$InstallDir = "$env:LOCALAPPDATA\KentScript"
$CacheDir = "$env:LOCALAPPDATA\KentScript\cache"
$BinaryUrl = "https://github.com/musikaalvin/kentscript/raw/main/kentscript-windows.exe"

Write-Host ""
Write-Host "============================================="
Write-Host "  KentScript v$Version Installer (Windows)"
Write-Host "============================================="
Write-Host ""

# Clean old cache versions
if (Test-Path $CacheDir) {
    Get-ChildItem $CacheDir -Directory -Filter "v*" | Where-Object { $_.Name -ne "v$Version" } | ForEach-Object {
        Write-Host "  Removing old cache: $($_.Name)"
        Remove-Item $_.FullName -Recurse -Force
    }
}

# Create install directory
Write-Host "[1/3] Creating install directory..."
if (!(Test-Path $InstallDir)) {
    New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
}
Write-Host "  OK: $InstallDir"

# Download binary
Write-Host "[2/3] Downloading KentScript..."
$ExePath = Join-Path $InstallDir "kentscript.exe"
try {
    # Enable TLS 1.2 for GitHub (may fail on very old .NET, that's OK)
    try { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12 } catch {}

    $WebClient = New-Object System.Net.WebClient
    $WebClient.DownloadFile($BinaryUrl, $ExePath)
    $Size = (Get-Item $ExePath).Length
    Write-Host "  OK: Downloaded ($Size bytes)"
} catch {
    Write-Host "  FAILED: Download failed"
    Write-Host ""
    Write-Host "  Build from source instead:"
    Write-Host "    git clone --branch source https://github.com/musikaalvin/kentscript.git"
    Write-Host "    cd kentscript"
    Write-Host "    pip install pyinstaller"
    Write-Host "    python build_binary.py --platform windows"
    exit 1
}

# Add to PATH
Write-Host "[3/3] Adding to PATH..."
$CurrentPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($CurrentPath -notlike "*$InstallDir*") {
    [Environment]::SetEnvironmentVariable("Path", "$CurrentPath;$InstallDir", "User")
    Write-Host "  OK: Added to user PATH"
} else {
    Write-Host "  OK: Already in PATH"
}

Write-Host ""
Write-Host "============================================="
Write-Host "  KentScript v$Version installed!"
Write-Host "============================================="
Write-Host ""
Write-Host "  Restart your terminal, then:"
Write-Host "    kentscript run file.ks"
Write-Host "    kentscript build file.ks -O3"
Write-Host "    kentscript"
Write-Host ""
Write-Host "  Docs: https://github.com/musikaalvin/kentscript"
Write-Host ""
