param(
    [Parameter(Mandatory = $true)]
    [string] $BundleDir,

    [int] $JackWarmupSeconds = 12,
    [int] $RunSeconds = 20,

    [switch] $Gui,

    [switch] $PreserveHome
)

$ErrorActionPreference = 'Stop'

$bundle = Resolve-Path -LiteralPath $BundleDir
$binDir = Join-Path $bundle 'bin'
$guitarix = Join-Path $binDir 'guitarix.exe'
$jackd = Join-Path $binDir 'jackd.exe'

if (-not (Test-Path -LiteralPath $guitarix)) {
    throw "guitarix.exe not found at $guitarix"
}
if (-not (Test-Path -LiteralPath $jackd)) {
    throw "jackd.exe not found at $jackd"
}

$stamp = [guid]::NewGuid().ToString('N')
$configDir = Join-Path $env:TEMP "guitarwin-smoke-config-$stamp"
$jackOut = Join-Path $env:TEMP "guitarwin-smoke-jack-$stamp.out.log"
$jackErr = Join-Path $env:TEMP "guitarwin-smoke-jack-$stamp.err.log"
$gxOut = Join-Path $env:TEMP "guitarwin-smoke-gx-$stamp.out.log"
$gxErr = Join-Path $env:TEMP "guitarwin-smoke-gx-$stamp.err.log"

New-Item -ItemType Directory -Path $configDir | Out-Null

$oldHome = [Environment]::GetEnvironmentVariable('HOME', 'Process')
$oldXdgConfig = [Environment]::GetEnvironmentVariable('XDG_CONFIG_HOME', 'Process')
[Environment]::SetEnvironmentVariable('XDG_CONFIG_HOME', $configDir, 'Process')
if (-not $PreserveHome) {
    [Environment]::SetEnvironmentVariable('HOME', $null, 'Process')
}

$jack = $null
$gx = $null

try {
    $version = & $guitarix --version
    $jack = Start-Process -FilePath $jackd `
        -ArgumentList @('-d', 'dummy', '-r', '48000', '-p', '1024') `
        -RedirectStandardOutput $jackOut `
        -RedirectStandardError $jackErr `
        -PassThru `
        -WindowStyle Hidden

    Start-Sleep -Seconds $JackWarmupSeconds
    if ($jack.HasExited) {
        throw "jackd exited before Guitarix startup. See $jackOut and $jackErr"
    }

    $gxArgs = @('--log-terminal')
    if (-not $Gui) {
        $gxArgs = @('-N') + $gxArgs
    }

    $gx = Start-Process -FilePath $guitarix `
        -ArgumentList $gxArgs `
        -RedirectStandardOutput $gxOut `
        -RedirectStandardError $gxErr `
        -PassThru `
        -WindowStyle Hidden

    Start-Sleep -Seconds $RunSeconds
    $gxAlive = -not $gx.HasExited
    $gxLog = (Get-Content $gxOut, $gxErr -ErrorAction SilentlyContinue) -join "`n"
    $hasJackInit = $gxLog -match 'Jack init' -and
        $gxLog -match 'The jack sample rate is 48000/sec' -and
        $gxLog -match 'The jack buffer size is 1024/frames'

    [PSCustomObject]@{
        Bundle = $bundle.Path
        Mode = if ($Gui) { 'gui' } else { 'nogui' }
        Version = ($version -join ' ')
        GuitarixAlive = $gxAlive
        JackInitLogged = $hasJackInit
        ConfigDir = $configDir
        GuitarixLog = "$gxOut ; $gxErr"
        JackLog = "$jackOut ; $jackErr"
    }

    if (-not $gxAlive -or -not $hasJackInit) {
        exit 1
    }
}
finally {
    if ($gx -and -not $gx.HasExited) {
        Stop-Process -Id $gx.Id -Force
    }
    if ($jack -and -not $jack.HasExited) {
        Stop-Process -Id $jack.Id -Force
    }
    [Environment]::SetEnvironmentVariable('XDG_CONFIG_HOME', $oldXdgConfig, 'Process')
    [Environment]::SetEnvironmentVariable('HOME', $oldHome, 'Process')
}
