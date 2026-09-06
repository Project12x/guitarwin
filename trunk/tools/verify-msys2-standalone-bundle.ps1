param(
    [Parameter(Mandatory = $true)]
    [string] $BundleDir
)

$ErrorActionPreference = 'Stop'

$bundle = Resolve-Path -LiteralPath $BundleDir
if (-not (Get-Item -LiteralPath $bundle.Path).PSIsContainer) {
    throw "BundleDir must be a directory: $($bundle.Path)"
}

$requiredFiles = @(
    'bin/guitarix.exe',
    'bin/jackd.exe',
    'COPYING',
    'THIRD_PARTY_LICENSES.md',
    'SOURCE.md',
    'BUNDLE_MANIFEST.json',
    'share/gx_head/skins/gx_head_Guitarix.css',
    'share/gx_head/builder/mainpanel.glade',
    'share/gx_head/factorysettings/dirlist.js',
    'share/gx_head/sounds/greathall.wav',
    'share/pixmaps/gx_head.png',
    'share/glib-2.0/schemas',
    'share/icons/Adwaita',
    'share/licenses',
    'lib/gdk-pixbuf-2.0',
    'lib/gtk-3.0',
    'lib/jack/jack_dummy.dll'
)

$missing = foreach ($relative in $requiredFiles) {
    $path = Join-Path $bundle.Path $relative
    if (-not (Test-Path -LiteralPath $path)) {
        $relative
    }
}

$manifestPath = Join-Path $bundle.Path 'BUNDLE_MANIFEST.json'
$manifest = $null
$manifestErrors = @()
if (Test-Path -LiteralPath $manifestPath) {
    try {
        $manifest = Get-Content -Raw -LiteralPath $manifestPath | ConvertFrom-Json
    }
    catch {
        $manifestErrors += "BUNDLE_MANIFEST.json is not valid JSON: $($_.Exception.Message)"
    }
}

if ($manifest) {
    if ($manifest.missing_dependencies.Count -gt 0) {
        $manifestErrors += "manifest records missing dependencies: $($manifest.missing_dependencies -join ', ')"
    }
    if (-not $manifest.options.include_jack_tools) {
        $manifestErrors += 'manifest says JACK tools were not included'
    }
    if (-not $manifest.options.include_gtk_runtime_data) {
        $manifestErrors += 'manifest says GTK runtime data was not included'
    }
    if (-not $manifest.options.include_runtime_licenses) {
        $manifestErrors += 'manifest says runtime licenses were not included'
    }
    if ($manifest.counts.gtk_runtime_data_files -le 0) {
        $manifestErrors += 'manifest GTK runtime data count is zero'
    }
    if ($manifest.counts.runtime_license_files -le 0) {
        $manifestErrors += 'manifest runtime license count is zero'
    }
    if ($manifest.counts.runtime_dependencies_copied -le 0) {
        $manifestErrors += 'manifest runtime dependency copy count is zero'
    }
}

$ok = (-not $missing) -and (-not $manifestErrors)

[PSCustomObject]@{
    Bundle = $bundle.Path
    RequiredFilesOk = -not $missing
    MissingRequiredFiles = @($missing)
    ManifestOk = -not $manifestErrors
    ManifestErrors = @($manifestErrors)
    SourceCommit = if ($manifest) { $manifest.source.commit } else { $null }
}

if (-not $ok) {
    exit 1
}
