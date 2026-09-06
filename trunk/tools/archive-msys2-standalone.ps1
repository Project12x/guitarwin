param(
    [Parameter(Mandatory = $true)]
    [string] $BundleDir,

    [string] $OutputDir,

    [string] $Name,

    [switch] $SkipVerify,

    [switch] $Force
)

$ErrorActionPreference = 'Stop'

$bundle = Resolve-Path -LiteralPath $BundleDir
if (-not (Get-Item -LiteralPath $bundle.Path).PSIsContainer) {
    throw "BundleDir must be a directory: $($bundle.Path)"
}
if (-not $OutputDir) {
    $OutputDir = Split-Path -Parent $bundle.Path
}
if (-not $Name) {
    $Name = Split-Path -Leaf $bundle.Path
}
if ($Name.IndexOfAny([System.IO.Path]::GetInvalidFileNameChars()) -ge 0 -or $Name -match '[\\/]') {
    throw "Name must be a plain file name stem, not a path: $Name"
}

if (-not $SkipVerify) {
    $verifier = Join-Path $PSScriptRoot 'verify-msys2-standalone-bundle.ps1'
    if (-not (Test-Path -LiteralPath $verifier)) {
        throw "Bundle verifier not found: $verifier"
    }
    $previousErrorActionPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        $verifyOutput = & powershell `
            -NoProfile `
            -ExecutionPolicy Bypass `
            -File $verifier `
            -BundleDir $bundle.Path 2>&1
        $verifyExitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }
    if ($verifyExitCode -ne 0) {
        throw "Bundle verification failed before archive:`n$($verifyOutput -join "`n")"
    }
}

$output = New-Item -ItemType Directory -Force -Path $OutputDir
$zipPath = Join-Path $output.FullName "$Name.zip"
$hashPath = "$zipPath.sha256"

foreach ($path in @($zipPath, $hashPath)) {
    if ((Test-Path -LiteralPath $path) -and -not $Force) {
        throw "Output already exists: $path"
    }
}

if (Test-Path -LiteralPath $zipPath) {
    Remove-Item -LiteralPath $zipPath -Force
}
if (Test-Path -LiteralPath $hashPath) {
    Remove-Item -LiteralPath $hashPath -Force
}

Compress-Archive -LiteralPath $bundle.Path -DestinationPath $zipPath

$hash = Get-FileHash -LiteralPath $zipPath -Algorithm SHA256
"$($hash.Hash.ToLowerInvariant())  $(Split-Path -Leaf $zipPath)" |
    Set-Content -LiteralPath $hashPath -Encoding ascii

[PSCustomObject]@{
    Bundle = $bundle.Path
    Verified = -not $SkipVerify
    Zip = $zipPath
    Sha256 = $hash.Hash.ToLowerInvariant()
    Sha256File = $hashPath
    SizeBytes = (Get-Item -LiteralPath $zipPath).Length
}
