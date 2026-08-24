#!/usr/bin/env python3
"""Single-source version bump for NetStrip.

Usage:
    python scripts/bump_version.py 3.9.0     # propagate a new version everywhere
    python scripts/bump_version.py --check   # CI: verify every copy matches

Files kept in sync:
    netstrip/__init__.py   __version__ = "X.Y.Z"
    setup.py               version='X.Y.Z',
    buildozer.spec         version = X.Y.Z
    version_info.txt       PyInstaller Windows metadata (tuples + strings)
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# rel, pattern(version capture group named V), replacement template
TARGETS = [
    ("netstrip/__init__.py",
     r'^(__version__\s*=\s*["\'])(?P<V>\d+\.\d+\.\d+)(["\'])',
     r"\g<1>{v}\g<3>"),
    ("setup.py",
     r"^([ \t]*version\s*=\s*)(['\"])(?P<V>\d+\.\d+\.\d+)(\2)",
     r"\g<1>\g<2>{v}\g<4>"),
    ("buildozer.spec",
     r"^(version\s*=\s*)(?P<V>\d+(?:\.\d+)*)[ \t]*$",
     r"\g<1>{v}"),
]

SEMVER = re.compile(r"^\d+\.\d+\.\d+$")


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8-sig")


def write(rel, text):
    (ROOT / rel).write_text(text, encoding="utf-8", newline="\n")


def source_version():
    m = re.search(TARGETS[0][1], read(TARGETS[0][0]), re.M)
    if not m:
        sys.exit("ERROR: cannot find __version__ in netstrip/__init__.py")
    return m.group("V")


def patch_version_info(text, ver):
    quad = f"{ver}.0"
    tuple_ver = "(" + ver.replace(".", ", ") + ", 0)"
    text = re.sub(r"(filevers=)\(\d+, \d+, \d+, \d+\)",
                  rf"\g<1>{tuple_ver}", text, count=1)
    text = re.sub(r"(prodvers=)\(\d+, \d+, \d+, \d+\)",
                  rf"\g<1>{tuple_ver}", text, count=1)
    text = re.sub(r"(StringStruct\('FileVersion',\s*')\d+\.\d+\.\d+\.\d+(')",
                  rf"\g<1>{quad}\g<2>", text, count=1)
    text = re.sub(r"(StringStruct\('ProductVersion',\s*')\d+\.\d+\.\d+\.\d+(')",
                  rf"\g<1>{quad}\g<2>", text, count=1)
    return text


def bump(new_ver):
    for rel, pattern, template in TARGETS:
        rx = re.compile(pattern, re.M)
        text = read(rel)
        patched, n = rx.subn(template.format(v=new_ver), text)
        if n != 1:
            sys.exit(f"ERROR: expected exactly one version line in {rel}, found {n}")
        write(rel, patched)
        print(f"  updated {rel}")

    rel = "version_info.txt"
    original = read(rel)
    patched = patch_version_info(original, new_ver)
    tuple_ver = "(" + new_ver.replace(".", ", ") + ", 0)"
    if f"'{new_ver}.0'" not in patched or f"filevers={tuple_ver}" not in patched:
        sys.exit(f"ERROR: substitutions failed for {rel}")
    write(rel, patched)
    print(f"  updated {rel}")
    print(f"Version bumped to {new_ver} in 4 files.")


def check(expected):
    ok = True
    for rel, pattern, _ in TARGETS:
        m = re.search(pattern, read(rel), re.M)
        got = m.group("V") if m else None
        status = "OK" if got == expected else "MISMATCH"
        if got != expected:
            ok = False
        print(f"  {status:<9} {rel:<22} found={got!r} expected={expected!r}")

    vi = read("version_info.txt")
    quads_ok = (f"'{expected}.0'" in vi
                and f"filevers=({expected.replace('.', ', ')}, 0)" in vi)
    status = "OK" if quads_ok else "MISMATCH"
    if not quads_ok:
        ok = False
    detail = f"{expected}.0 metadata present" if quads_ok else "inconsistent metadata"
    print(f"  {status:<9} {'version_info.txt':<22} found={detail!r}")

    if not ok:
        sys.exit(1)
    print(f"All version references consistent at {expected}.")


def main():
    argv = sys.argv[1:]
    if argv in (["--check"], []):
        check(source_version())
        return
    new_ver = argv[0]
    if not SEMVER.match(new_ver):
        sys.exit(f"ERROR: '{new_ver}' is not X.Y.Z semantic version")
    bump(new_ver)


if __name__ == "__main__":
    main()
