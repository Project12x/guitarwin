# Changelog

All notable changes to this project are documented in this file.

This project follows the Keep a Changelog format.

## [Unreleased]

### Added

- Restored the Windows standalone port work from Codex session history after the
  local repository was deleted.
- Added MSYS2/MinGW64 standalone build documentation, packaging helpers, bundle
  verification, source archive generation, and Windows runtime provenance
  manifest support.

### Changed

- Re-verified the moved `D:\code\Guitarwin` checkout with LV2 enabled: build,
  staged install, packaged `--include-lv2` bundle discovery, static bundle
  verification, and no-GUI plus bounded GUI JACK/Guitarix smoke all pass from
  D: scratch paths.
- Documented `D:\tmp\codex` scratch paths and the explicit MSYS2 `INTLTOOL`
  configure override validated after moving the checkout to `D:\code`.
- Updated Windows standalone setup notes for the moved `D:\code\Guitarwin`
  checkout path.
- Ported the standalone Guitarix build path toward Windows by adding guarded
  JACK/LADSPA/LV2 build options, Windows-compatible dynamic loading, socket,
  filesystem, signal, and child-process handling.
- Kept the first Windows standalone milestone focused on JACK and the existing
  upstream architecture while documenting LRDF and LV2 follow-up blockers.
