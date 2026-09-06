#!/usr/bin/env python3
#
# Collect a relocatable Windows standalone tree from an MSYS2/MinGW install
# prefix. Run this from an MSYS2 MinGW shell after `./waf install --destdir=...`.

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


BINARY_SUFFIXES = (".exe", ".dll", ".so")
SOURCE_REPOSITORY = "https://github.com/Project12x/guitarwin"
UPSTREAM_REPOSITORY = "https://github.com/brummer10/guitarix"
LDD_ARROW_RE = re.compile(r"^\s*(?P<name>\S+)\s+=>\s+(?P<path>\S.*?)\s+\(0x[0-9a-fA-F]+\)")
LDD_DIRECT_RE = re.compile(r"^\s*(?P<path>/\S+\.(?:dll|exe|so))\s+\(0x[0-9a-fA-F]+\)")
WINDOWS_SYSTEM_PREFIXES = ("/c/windows/",)
DEFAULT_JACK_TOOLS = ("jackd.exe",)
GTK_RUNTIME_DATA_DIRS = (
    "etc/fonts",
    "etc/gtk-3.0",
    "share/fontconfig",
    "share/glib-2.0",
    "share/gtk-3.0",
    "share/icons",
    "share/mime",
    "share/themes",
    "lib/gdk-pixbuf-2.0",
    "lib/gio",
    "lib/gtk-3.0",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a Windows Guitarix standalone bundle from an MSYS2 staged prefix."
    )
    parser.add_argument(
        "--staged-prefix",
        required=True,
        help="Installed prefix to copy, for example /c/tmp/guitarwin-portable-stage/msys64/tmp",
    )
    parser.add_argument(
        "--bundle-dir",
        required=True,
        help="Output bundle directory. It must not already exist unless --force is set.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Remove an existing bundle directory before writing it.",
    )
    parser.add_argument(
        "--no-jack-tools",
        action="store_true",
        help="Do not copy jackd.exe into the bundle.",
    )
    parser.add_argument(
        "--include-lv2",
        action="store_true",
        help="Include installed LV2 bundles. Omitted by default for the lean standalone bundle.",
    )
    parser.add_argument(
        "--include-ir-library",
        action="store_true",
        help="Include the large bundled amp/band IR libraries. The default keeps greathall.wav only.",
    )
    parser.add_argument(
        "--no-gtk-runtime-data",
        action="store_true",
        help="Do not copy GTK/GLib/GIO runtime data from the MSYS2 MinGW prefix.",
    )
    parser.add_argument(
        "--no-runtime-licenses",
        action="store_true",
        help="Do not copy MSYS2 MinGW runtime dependency license files.",
    )
    return parser.parse_args()


def reject_unsafe_remove(path: Path) -> None:
    resolved = path.resolve()
    if resolved.anchor == str(resolved):
        raise SystemExit(f"Refusing to remove filesystem root: {resolved}")
    if len(resolved.parts) < 3:
        raise SystemExit(f"Refusing to remove suspiciously broad path: {resolved}")


def make_ignore_filter(include_lv2: bool, include_ir_library: bool):
    def ignore_dev_artifacts(directory: str, names: list[str]) -> set[str]:
        ignored: set[str] = set()
        directory_norm = directory.replace("\\", "/").lower()
        if not include_lv2 and directory_norm.endswith("/lib") and "lv2" in names:
            ignored.add("lv2")
        if not include_ir_library and directory_norm.endswith("/share/gx_head/sounds"):
            ignored.update(name for name in names if name.lower() in {"amps", "bands"})
        for name in names:
            lower = name.lower()
            if lower in {"include", "pkgconfig", "__pycache__"}:
                ignored.add(name)
            elif lower.endswith((".a", ".la", ".pc", ".pdb")):
                ignored.add(name)
        return ignored

    return ignore_dev_artifacts


def copy_install_tree(
    staged_prefix: Path,
    bundle_dir: Path,
    force: bool,
    include_lv2: bool,
    include_ir_library: bool,
) -> None:
    if not staged_prefix.exists():
        raise SystemExit(f"Staged prefix does not exist: {staged_prefix}")
    if bundle_dir.exists():
        if not force:
            raise SystemExit(f"Bundle directory already exists: {bundle_dir}")
        reject_unsafe_remove(bundle_dir)
        shutil.rmtree(bundle_dir)
    shutil.copytree(
        staged_prefix,
        bundle_dir,
        ignore=make_ignore_filter(include_lv2, include_ir_library),
    )


def is_binary(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in BINARY_SUFFIXES


def iter_binaries(root: Path):
    for path in root.rglob("*"):
        if is_binary(path):
            yield path


def is_windows_system_path(path_text: str) -> bool:
    normalized = path_text.replace("\\", "/").lower()
    if normalized.startswith(WINDOWS_SYSTEM_PREFIXES):
        return True
    return bool(re.match(r"^[a-z]:/windows/", normalized))


def to_native_path(path_text: str) -> Path:
    if os.name == "nt" and path_text.startswith("/"):
        proc = subprocess.run(
            ["cygpath", "-w", path_text],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return Path(proc.stdout.strip())
    return Path(path_text)


def find_mingw_prefix() -> Path | None:
    env_prefix = os.environ.get("MINGW_PREFIX")
    if env_prefix:
        prefix = to_native_path(env_prefix)
        if prefix.exists():
            return prefix

    for tool_name in (
        "gtk-query-immodules-3.0.exe",
        "gdk-pixbuf-query-loaders.exe",
        "jackd.exe",
    ):
        tool = shutil.which(tool_name)
        if tool:
            prefix = Path(tool).parent.parent
            if prefix.exists():
                return prefix
    return None


def copy_runtime_data_tree(source: Path, target: Path) -> int:
    if not source.exists():
        return 0
    before = (
        {path.relative_to(target) for path in target.rglob("*") if path.is_file()}
        if target.exists()
        else set()
    )
    shutil.copytree(
        source,
        target,
        dirs_exist_ok=True,
        ignore=make_ignore_filter(True, True),
    )
    after = {path.relative_to(target) for path in target.rglob("*") if path.is_file()}
    return len(after - before)


def copy_gtk_runtime_data(bundle_dir: Path) -> int:
    mingw_prefix = find_mingw_prefix()
    if mingw_prefix is None:
        print(
            "warning: MSYS2 MinGW prefix was not found; GTK runtime data was not copied",
            file=sys.stderr,
        )
        return 0

    copied_count = 0
    for relative_dir in GTK_RUNTIME_DATA_DIRS:
        source = mingw_prefix / relative_dir
        target = bundle_dir / relative_dir
        copied_count += copy_runtime_data_tree(source, target)
    return copied_count


def write_third_party_license_notice(bundle_dir: Path) -> None:
    notice = """# Third-party runtime licenses

This Windows bundle includes dynamically linked runtime libraries, loadable
modules, and runtime data copied from the active MSYS2 MinGW prefix used during
packaging.

Per-package license texts from that prefix are preserved under
`share/licenses/`. Guitarix's own license is copied to `COPYING`.
"""
    (bundle_dir / "THIRD_PARTY_LICENSES.md").write_text(notice, encoding="utf-8")


def copy_runtime_licenses(bundle_dir: Path) -> int:
    mingw_prefix = find_mingw_prefix()
    if mingw_prefix is None:
        print(
            "warning: MSYS2 MinGW prefix was not found; runtime licenses were not copied",
            file=sys.stderr,
        )
        return 0

    copied_count = copy_runtime_data_tree(
        mingw_prefix / "share" / "licenses",
        bundle_dir / "share" / "licenses",
    )
    write_third_party_license_notice(bundle_dir)
    return copied_count


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def git_output(repo: Path, *args: str) -> str | None:
    try:
        proc = subprocess.run(
            ["git", "-c", f"safe.directory={repo}", "-C", str(repo), *args],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    except FileNotFoundError:
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.strip()


def collect_source_info() -> dict[str, object]:
    repo = repo_root()
    commit = git_output(repo, "rev-parse", "--verify", "HEAD")
    branch = git_output(repo, "rev-parse", "--abbrev-ref", "HEAD")
    status = git_output(repo, "status", "--porcelain")
    return {
        "repository": SOURCE_REPOSITORY,
        "upstream_repository": UPSTREAM_REPOSITORY,
        "commit": commit,
        "branch": branch,
        "dirty": None if status is None else bool(status),
    }


def write_source_notice(bundle_dir: Path, source_info: dict[str, object]) -> None:
    commit = source_info.get("commit") or "unknown"
    branch = source_info.get("branch") or "unknown"
    dirty = source_info.get("dirty")
    dirty_text = "unknown" if dirty is None else ("yes" if dirty else "no")
    notice = f"""# Source availability

This Windows bundle was generated from the Guitarix Windows port source tree.

- Port repository: {SOURCE_REPOSITORY}
- Upstream Guitarix repository: {UPSTREAM_REPOSITORY}
- Source branch: {branch}
- Source commit: {commit}
- Working tree had uncommitted changes when packaged: {dirty_text}

Guitarix is distributed under the GPL. When redistributing this binary bundle,
provide the complete corresponding source tree for the exact build, or provide a
valid written offer to provide that source.
"""
    (bundle_dir / "SOURCE.md").write_text(notice, encoding="utf-8")


def write_bundle_manifest(
    bundle_dir: Path,
    staged_prefix: Path,
    args: argparse.Namespace,
    runtime_data_count: int,
    runtime_license_count: int,
    copied_count: int,
    missing: list[str],
) -> None:
    source_info = collect_source_info()
    write_source_notice(bundle_dir, source_info)
    manifest = {
        "format": 1,
        "project": "Guitarix Windows standalone",
        "source": source_info,
        "staged_prefix": str(staged_prefix),
        "options": {
            "include_lv2": bool(args.include_lv2),
            "include_ir_library": bool(args.include_ir_library),
            "include_jack_tools": not bool(args.no_jack_tools),
            "include_gtk_runtime_data": not bool(args.no_gtk_runtime_data),
            "include_runtime_licenses": not bool(args.no_runtime_licenses),
        },
        "counts": {
            "gtk_runtime_data_files": runtime_data_count,
            "runtime_license_files": runtime_license_count,
            "runtime_dependencies_copied": copied_count,
        },
        "missing_dependencies": sorted(set(missing)),
    }
    (bundle_dir / "BUNDLE_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def parse_ldd_paths(output: str) -> tuple[list[Path], list[str]]:
    paths: list[Path] = []
    missing: list[str] = []
    for line in output.splitlines():
        if "not found" in line:
            missing.append(line.strip())
            continue
        match = LDD_ARROW_RE.match(line) or LDD_DIRECT_RE.match(line)
        if not match:
            continue
        path_text = match.group("path").strip()
        if is_windows_system_path(path_text):
            continue
        path = to_native_path(path_text)
        if path.is_absolute() and path.exists():
            paths.append(path)
    return paths, missing


def ldd(binary: Path, env: dict[str, str]) -> tuple[list[Path], list[str]]:
    proc = subprocess.run(
        ["ldd", str(binary)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=env,
        check=False,
    )
    if proc.returncode != 0:
        return [], [f"ldd failed for {binary}: {proc.stdout.strip()}"]
    return parse_ldd_paths(proc.stdout)


def copy_runtime_dep(dep: Path, bin_dir: Path) -> tuple[Path, bool]:
    target = bin_dir / dep.name
    if target.exists():
        return target, False
    shutil.copy2(dep, target)
    return target, True


def copy_jack_drivers(jackd_path: Path, bundle_dir: Path) -> list[Path]:
    mingw_root = jackd_path.parent.parent
    source_dir = mingw_root / "lib" / "jack"
    if not source_dir.exists():
        print(f"warning: JACK driver directory was not found: {source_dir}", file=sys.stderr)
        return []
    target_dir = bundle_dir / "lib" / "jack"
    if target_dir.exists():
        shutil.rmtree(target_dir)
    shutil.copytree(source_dir, target_dir, ignore=make_ignore_filter(True, True))
    return list(iter_binaries(target_dir))


def add_jack_tools(bundle_dir: Path) -> list[Path]:
    bin_dir = bundle_dir / "bin"
    copied: list[Path] = []
    for tool_name in DEFAULT_JACK_TOOLS:
        source = shutil.which(tool_name)
        if not source:
            print(f"warning: {tool_name} was not found on PATH", file=sys.stderr)
            continue
        source_path = Path(source)
        target, _copied = copy_runtime_dep(source_path, bin_dir)
        copied.append(target)
        copied.extend(copy_jack_drivers(source_path, bundle_dir))
    return copied


def collect_runtime_dlls(bundle_dir: Path, include_jack_tools: bool) -> tuple[int, list[str]]:
    bin_dir = bundle_dir / "bin"
    lib_dir = bundle_dir / "lib"
    bin_dir.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["PATH"] = os.pathsep.join(
        str(path) for path in (bin_dir, lib_dir) if path.exists()
    ) + os.pathsep + env.get("PATH", "")

    queue = list(iter_binaries(bundle_dir))
    if include_jack_tools:
        queue.extend(add_jack_tools(bundle_dir))

    seen: set[Path] = set()
    copied_count = 0
    missing: list[str] = []

    while queue:
        binary = queue.pop(0)
        resolved = binary.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)

        deps, dep_missing = ldd(binary, env)
        missing.extend(dep_missing)
        for dep in deps:
            target, copied = copy_runtime_dep(dep, bin_dir)
            if target.resolve() not in seen:
                queue.append(target)
            if copied:
                copied_count += 1

    return copied_count, missing


def copy_license(staged_prefix: Path, bundle_dir: Path) -> None:
    candidates = [
        staged_prefix / "share" / "doc" / "guitarix" / "COPYING",
        Path(__file__).resolve().parents[1] / "COPYING",
    ]
    for candidate in candidates:
        if candidate.exists():
            shutil.copy2(candidate, bundle_dir / "COPYING")
            return


def main() -> int:
    args = parse_args()
    staged_prefix = Path(args.staged_prefix)
    bundle_dir = Path(args.bundle_dir)

    copy_install_tree(
        staged_prefix,
        bundle_dir,
        args.force,
        args.include_lv2,
        args.include_ir_library,
    )
    copy_license(staged_prefix, bundle_dir)
    runtime_data_count = 0
    if not args.no_gtk_runtime_data:
        runtime_data_count = copy_gtk_runtime_data(bundle_dir)
    runtime_license_count = 0
    if not args.no_runtime_licenses:
        runtime_license_count = copy_runtime_licenses(bundle_dir)
    copied_count, missing = collect_runtime_dlls(bundle_dir, not args.no_jack_tools)
    write_bundle_manifest(
        bundle_dir,
        staged_prefix,
        args,
        runtime_data_count,
        runtime_license_count,
        copied_count,
        missing,
    )

    print(f"bundle: {bundle_dir}")
    print(f"GTK runtime data files copied: {runtime_data_count}")
    print(f"runtime license files copied: {runtime_license_count}")
    print(f"runtime dependencies copied: {copied_count}")
    if missing:
        print("missing dependencies:", file=sys.stderr)
        for item in sorted(set(missing)):
            print(f"  {item}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
