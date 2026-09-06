# Windows standalone port plan

## Scope

This branch is a direct Windows port of Guitarix, not a clean-room
approximation. The first target is a standalone Windows build that preserves the
upstream JACK/LV2 architecture as far as possible.

## Upstream provenance

- Upstream repository: https://github.com/brummer10/guitarix
- Upstream commit: `34ba3c6a5b43cac9c7db5c8e7433dbe0dedc1dbc`
- Upstream license: GPL-3.0-or-later for the combined project, per
  `trunk/COPYING`
- Files inspected for this phase:
  - `README.md`
  - `trunk/COPYING`
  - `trunk/README.mswin`
  - `trunk/wscript`
  - `trunk/src/gx_head/wscript`
  - `trunk/src/gx_head/engine/ladspaback.cpp`
  - `trunk/src/gx_head/engine/jsonrpc.cpp`
  - `trunk/src/gx_head/gui/machine.cpp`
  - `trunk/src/gx_head/gui/gx_child_process.cpp`
  - `trunk/waftools/lv2.py`
- Reuse mode: fork / direct-port

## Current result

The real upstream Guitarix standalone application now builds on Windows through
MSYS2 MinGW64 with JACK and LV2 enabled.

Validated locally:

1. `./waf configure` completes for the standalone and LV2 targets.
2. `./waf build -j 4` completes.
3. `./waf install --destdir=/d/tmp/codex/guitarwin-lv2-stage` completes.
4. `build/src/gx_head/guitarix.exe --help` prints the expected CLI options.
5. `build/src/gx_head/guitarix.exe --version` reports Guitarix 0.47.0.
6. `lv2ls` discovers 72 Guitarix plugin URIs from the staged install LV2 root.
7. The installed `guitarix.exe -N --log-terminal` stays alive against
   `jackd -d dummy -r 48000 -p 1024` and logs the JACK sample rate/buffer size.
8. A staged executable launched from
   `D:/tmp/codex/guitarwin-portable-stage/msys64/tmp/bin/guitarix.exe` finds its
   resources beside that executable instead of requiring the compiled
   `C:/msys64/tmp` prefix.

Runtime validation with a real Windows audio interface and guitar input is still
pending.

Latest moved-checkout verification, run 2026-09-06 from `D:\code\Guitarwin`,
used `D:\tmp\codex\guitarwin-build-20260906` as the staged prefix and
`D:\tmp\codex\guitarwin-bundle-lv2-20260906` as the full bundle. It confirmed
`./waf build -j 4`, `./waf install`, 72 `lv2ls` Guitarix entries from the staged
LV2 root, static bundle verification, 72 `lv2ls` entries from the packaged
bundle `lib/lv2`, and no-GUI JACK/Guitarix smoke with `GuitarixAlive: True` and
`JackInitLogged: True`.

## Build environment

This branch currently assumes MSYS2 is installed at `C:\msys64` and builds from
an MSYS2 MinGW64 shell or equivalent environment:

```sh
export PATH=/mingw64/bin:/usr/bin:$PATH
cd /d/code/Guitarwin/trunk
```

Useful Windows PowerShell setup for smoke-testing the built executable:

```powershell
$env:HOME='D:\code\Guitarwin\.msys-home'
$env:PATH='D:\code\Guitarwin\trunk\build\libgxw\gxw;' +
          'D:\code\Guitarwin\trunk\build\libgxwmm\gxwmm;' +
          'C:\msys64\mingw64\bin;C:\msys64\usr\bin;' + $env:PATH
.\trunk\build\src\gx_head\guitarix.exe --help
```

## Configure command

The current passing standalone configuration is:

```sh
export INTLTOOL=/usr/bin/intltool-merge
./waf configure -j 4 \
    --check-cxx-compiler=g++ \
    --no-faust \
    --includeresampler \
    --includeconvolver \
    --no-avahi \
    --no-bluez \
    --no-nsm \
    --no-desktop-update \
    --no-lrdf
```

Then build with:

```sh
./waf build -j 4
```

`--static-lib` is intentionally not used for this first milestone. The existing
Windows static-link path is still useful for plugin packaging, but it caused the
standalone build to over-constrain GTK/Cairo/libsndfile linking. The port now
keeps those static flags behind the existing `--static-lib` option.

## Dependency baseline

Installed MSYS2 packages for this phase include:

```sh
pacman -S \
    git base-devel \
    mingw-w64-x86_64-gcc \
    mingw-w64-x86_64-pkg-config \
    mingw-w64-x86_64-jack2 \
    mingw-w64-x86_64-lv2 \
    mingw-w64-x86_64-lilv \
    mingw-w64-x86_64-gtk3 \
    mingw-w64-x86_64-gtkmm3 \
    mingw-w64-x86_64-glibmm \
    mingw-w64-x86_64-libsigc++ \
    mingw-w64-x86_64-eigen3 \
    mingw-w64-x86_64-fftw \
    mingw-w64-x86_64-libsndfile \
    mingw-w64-x86_64-cairo \
    mingw-w64-x86_64-curl \
    mingw-w64-x86_64-boost \
    mingw-w64-x86_64-gperf \
    mingw-w64-x86_64-sassc \
    mingw-w64-x86_64-ladspa-sdk \
    intltool
```

MSYS2 installs `intltool-merge` as an extensionless script. Set `INTLTOOL`
explicitly during configure so Waf's MinGW Python process does not miss it
during Windows program lookup.

## Portability changes made

- Added `--no-lrdf` so the standalone app can build without the LADSPA RDF
  metadata library.
- Added a small `gx_dlcompat.h` shim that maps the limited `dlopen`/`dlsym`
  usage to GLib `GModule` on Windows.
- Added WinSock handling for JSON-RPC and GUI socket code.
- Guarded POSIX-only signal, `mkdir`, `sync`, memory-locking, and child-process
  code paths.
- Made Boost iostreams detection accept MSYS2's `boost_iostreams-mt` package
  name.
- Made the Waf JSON-RPC generator invoke the extensionless Python helper through
  the active Python executable.
- Skipped `gxw_demo.exe` on Windows; it is not part of the standalone milestone.
- Added a fallback copy path when Waf's Sass/icon helper cannot create symlinks
  on Windows.
- Made install skip the Linux-only `ldconfig` uid check on Windows.
- Replaced config-file temp promotion with a Windows-aware helper so saving over
  existing config files works.
- Switched first-run config directory creation to GLib's recursive directory
  creation and initialized `banklist.js` as a valid empty JSON array.
- Added Windows executable-relative resource discovery for the standalone app.
  When launched from an installed tree, default skin, builder, factory preset,
  pixmap, and system IR paths are resolved from the executable's sibling
  `share` tree.
- Added `trunk/tools/package-msys2-standalone.py` to collect a lean Windows
  standalone bundle from a staged MSYS2 install.

The current Windows child-process implementation is deliberately minimal:
external helper launch/monitoring is disabled for the first milestone. That
keeps the main standalone app buildable while avoiding a half-ported POSIX
`fork`/`waitpid` abstraction.

## LRDF status

MSYS2 does not provide a current MinGW64 LRDF package in this environment. The
upstream LRDF candidate inspected was:

- Repository: https://github.com/swh/LRDF
- Commit: `0094d2ad6efca382004f12c38195fcb788377023`
- Observed license: GPL-2.0-only style text in the source distribution

Because this branch targets a GPLv3 Guitarix port, vendoring or directly linking
that LRDF source is not appropriate without a clearer license path. The current
choice is to keep LADSPA plugin loading and skip LRDF metadata support with
`--no-lrdf`.

## LV2 status

LV2 support through `lilv-0` now configures, builds, and stage-installs on this
host. The earlier xputty resource-object failure was not a source blocker after
the Windows symlink fallback was in place and the full LV2 compile was allowed
to finish.

The staged install root used for discovery was:

```sh
./waf install --destdir=/d/tmp/codex/guitarwin-lv2-stage
export LV2_PATH=/d/tmp/codex/guitarwin-lv2-stage/msys64/tmp/lib/lv2
lv2ls | grep -c guitarix
```

That reported 72 Guitarix LV2 plugin URIs.

`lv2_validate` can read representative manifests, but it reports existing
metadata errors about missing `doap:name` plain-literal values. That appears to
be an upstream LV2 metadata quality issue rather than a Windows build failure.

## JACK runtime status

JACK2 1.9.22 from MSYS2 starts with the dummy backend:

```sh
jackd -d dummy -r 48000 -p 1024
```

After installing to the configured prefix (`C:/msys64/tmp`), the standalone
executable starts in no-GUI mode against that server:

```sh
export XDG_CONFIG_HOME=/d/tmp/codex/guitarwin-smoke-config-banklist
export PATH=/c/msys64/tmp/lib:/mingw64/bin:/usr/bin:$PATH
/c/msys64/tmp/bin/guitarix.exe -N --log-terminal
```

The smoke log reports:

```text
Jack init  ***  The jack sample rate is 48000/sec
Jack init  ***  The jack buffer size is 1024/frames ...
Press Ctrl-C to quit
```

The dummy backend still reports xruns during the smoke. That is useful evidence
that the JACK clients are running, but it is not a substitute for testing with a
real Windows JACK backend and physical audio hardware.

## Portable staged runtime status

The standalone now has a Windows-only fallback that derives the install prefix
from the running executable. For the current Waf install layout:

```text
<prefix>/bin/guitarix.exe
<prefix>/share/gx_head/skins/gx_head_Guitarix.css
<prefix>/share/gx_head/builder/mainpanel.glade
<prefix>/share/gx_head/factorysettings/dirlist.js
<prefix>/share/gx_head/sounds/greathall.wav
<prefix>/share/pixmaps/gx_head.png
```

the default resource directories are relocated to `<prefix>` at startup.
Explicit `--style-dir` and `--builder-dir` values are still honored.

The latest staged smoke used:

```sh
./waf install --destdir=/d/tmp/codex/guitarwin-portable-stage
export PATH=/d/tmp/codex/guitarwin-portable-stage/msys64/tmp/lib:/mingw64/bin:/usr/bin:$PATH
export LV2_PATH=/d/tmp/codex/guitarwin-portable-stage/msys64/tmp/lib/lv2
/d/tmp/codex/guitarwin-portable-stage/msys64/tmp/bin/guitarix.exe --version
lv2ls | grep -c guitarix
jackd -d dummy -r 48000 -p 1024
/d/tmp/codex/guitarwin-portable-stage/msys64/tmp/bin/guitarix.exe -N --log-terminal
```

Results:

- `guitarix.exe --version` reports Guitarix 0.47.0.
- `lv2ls | grep -c guitarix` reports 72.
- The no-GUI executable stays alive against JACK dummy and logs the 48000 Hz
  sample rate and 1024-frame buffer size.

## Lean standalone bundle status

The current helper creates a direct-launchable Windows tree from a staged Waf
install:

```sh
python tools/package-msys2-standalone.py \
    --staged-prefix /d/tmp/codex/guitarwin-portable-stage/msys64/tmp \
    --bundle-dir /d/tmp/codex/guitarwin-bundle-lean
```

By default this is a lean standalone bundle:

- Copies the staged `bin`, `lib`, and `share` runtime tree.
- Drops import/static development artifacts such as `.dll.a` and `.a` files.
- Copies required MinGW/JACK/GTK runtime DLLs into `bin` using recursive `ldd`
  discovery.
- Copies GTK/GLib/GIO runtime data from the active MSYS2 MinGW prefix, including
  schemas, icon themes, MIME data, GTK settings, GDK pixbuf loaders, GIO
  modules, and GTK modules.
- Copies `jackd.exe` and JACK backend modules under `lib/jack`.
- Keeps only the required `greathall.wav` system IR by default.
- Omits installed LV2 bundles by default to keep the first standalone bundle
  small. Use `--include-lv2` for the fuller payload.
- Omits the large bundled amp/band IR libraries by default. Use
  `--include-ir-library` to include them.
- Copies MSYS2 MinGW per-package license files to `share/licenses` by default
  and writes a root `THIRD_PARTY_LICENSES.md` pointer file. Use
  `--no-runtime-licenses` only for local package debugging.
- Writes `SOURCE.md` and `BUNDLE_MANIFEST.json` with source repository/commit
  metadata, selected packaging options, copy counts, and missing dependency
  diagnostics.
- `trunk/tools/verify-msys2-standalone-bundle.ps1` checks required executables,
  resources, GTK/JACK runtime data, license/source files, and manifest health
  without launching Guitarix.
- `trunk/tools/archive-msys2-standalone.ps1` can turn a verified bundle into a
  ZIP plus `.sha256` checksum sidecar. It runs the static bundle verifier first
  unless `-SkipVerify` is passed.
- `trunk/tools/archive-guitarwin-source.ps1` can turn a clean Git `HEAD` into a
  matching source ZIP plus `.sha256` checksum sidecar for GPL redistribution.

The latest lean-bundle smoke used
`D:/tmp/codex/guitarwin-bundle-lean-1783121694` and ran from PowerShell without adding
MSYS2 to `PATH` and without setting `HOME`:

```powershell
.\bin\guitarix.exe --version
.\bin\jackd.exe -d dummy -r 48000 -p 1024
.\bin\guitarix.exe -N --log-terminal
```

Results:

- `guitarix.exe --version` reports Guitarix 0.47.0.
- Bundled `jackd.exe` finds the bundled `lib/jack` backend directory and starts
  the dummy server.
- Bundled `guitarix.exe -N --log-terminal` stays alive and logs JACK 48000 Hz /
  1024-frame initialization.
- The reusable smoke command is:

  ```powershell
  powershell -ExecutionPolicy Bypass -File .\tools\smoke-msys2-standalone.ps1 -BundleDir D:\tmp\codex\guitarwin-bundle-lean-1783121694
  ```

The fuller LV2 bundle mode has also been smoke-tested:

```sh
python tools/package-msys2-standalone.py \
    --staged-prefix /d/tmp/codex/guitarwin-portable-stage/msys64/tmp \
    --bundle-dir /d/tmp/codex/guitarwin-bundle-full \
    --include-lv2
```

The latest full-bundle smoke used `D:/tmp/codex/guitarwin-bundle-full-1783281219`.
Direct `guitarix.exe --version` reports Guitarix 0.47.0,
`LV2_PATH=<bundle>/lib/lv2 lv2ls | grep -c guitarix` reports 72, and bundled
`jackd.exe` plus bundled `guitarix.exe -N --log-terminal` logs JACK 48000 Hz /
1024-frame initialization after allowing JACK a longer startup window. The
PowerShell smoke helper passed against this full bundle.

The GTK-runtime-data packaging path was smoke-tested with
`D:/tmp/codex/guitarwin-bundle-manifest-final`. The helper copied 3,742 GTK runtime data
files, 138 runtime license files, and 90 runtime dependencies. Representative
data roots such as `share/glib-2.0/schemas`, `share/icons/Adwaita`,
`lib/gdk-pixbuf-2.0`, and `lib/gtk-3.0` are present, `share/licenses` and
`THIRD_PARTY_LICENSES.md` are present, `SOURCE.md` and `BUNDLE_MANIFEST.json`
are present, and the PowerShell JACK smoke helper passed in both default no-GUI
mode and `-Gui` mode. The static bundle verifier also passed against this
bundle.

The latest archive smoke used:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\archive-msys2-standalone.ps1 -BundleDir D:\tmp\codex\guitarwin-bundle-manifest-final -OutputDir D:\tmp\codex\guitarwin-archives-verify-default
```

That produced a 74,764,670-byte ZIP plus `.sha256` sidecar. The sidecar hash
matched `Get-FileHash`, the archive helper reported `Verified : True`, and the
ZIP contains `BUNDLE_MANIFEST.json`, `SOURCE.md`, and
`THIRD_PARTY_LICENSES.md`.

The source archive helper can be run after the release commit is clean:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\archive-guitarwin-source.ps1 -OutputDir D:\tmp\codex\guitarwin-archives-source
```

It refuses dirty working trees by default. Use `-AllowDirty` only when
intentionally archiving the current `HEAD` while local edits are present.

The bundle helper is still a development tool, not a final installer. GTK
interactive GUI validation, desktop integration, signing, and real Windows audio
hardware validation remain open.
