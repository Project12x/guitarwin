param(
    [string] $RepoDir,

    [string] $OutputDir,

    [string] $Name,

    [switch] $AllowDirty,

    [switch] $Force
)

$ErrorActionPreference = 'Stop'

if (-not $RepoDir) {
    $RepoDir = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
}
$repo = Resolve-Path -LiteralPath $RepoDir
if (-not (Test-Path -LiteralPath (Join-Path $repo.Path '.git'))) {
    throw "RepoDir is not a Git checkout: $($repo.Path)"
}

function Invoke-RepoGit {
    param(
        [Parameter(Mandatory = $true)]
        [string[]] $GitArgs
    )

    $safeDirectory = $repo.Path.Replace('\', '/')
    $previousErrorActionPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        $output = & git `
            -c "safe.directory=$safeDirectory" `
            -c 'core.excludesfile=' `
            -C $repo.Path `
            @GitArgs 2>&1
        $exitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }
    if ($exitCode -ne 0) {
        throw "git $($GitArgs -join ' ') failed: $($output -join "`n")"
    }
    return $output
}

$commit = ((Invoke-RepoGit @('rev-parse', '--verify', 'HEAD')) -join "`n").Trim()
$branch = ((Invoke-RepoGit @('rev-parse', '--abbrev-ref', 'HEAD')) -join "`n").Trim()
$dirty = Invoke-RepoGit @('status', '--porcelain')
if ($dirty -and -not $AllowDirty) {
    throw "Working tree has uncommitted changes; commit them or pass -AllowDirty to archive HEAD anyway."
}

if (-not $OutputDir) {
    $OutputDir = Join-Path $repo.Path 'dist'
}
if (-not $Name) {
    $short = $commit.Substring(0, 12)
    $Name = "guitarwin-source-$short"
}
if ($Name.IndexOfAny([System.IO.Path]::GetInvalidFileNameChars()) -ge 0 -or $Name -match '[\\/]') {
    throw "Name must be a plain file name stem, not a path: $Name"
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

Invoke-RepoGit @(
    'archive',
    '--format=zip',
    "--output=$zipPath",
    "--prefix=$Name/",
    'HEAD'
)

$hash = Get-FileHash -LiteralPath $zipPath -Algorithm SHA256
"$($hash.Hash.ToLowerInvariant())  $(Split-Path -Leaf $zipPath)" |
    Set-Content -LiteralPath $hashPath -Encoding ascii

[PSCustomObject]@{
    Repository = $repo.Path
    Branch = $branch
    Commit = $commit
    Dirty = [bool] $dirty
    Zip = $zipPath
    Sha256 = $hash.Hash.ToLowerInvariant()
    Sha256File = $hashPath
    SizeBytes = (Get-Item -LiteralPath $zipPath).Length
}
