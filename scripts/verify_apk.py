"""
Structural verification gate for the buildozer-produced APK.

Fails CI when the build output is missing, truncated, or lacks the pieces a
bootable NetStrip APK must contain. Optionally prints badging via aapt if the
Android SDK happens to be on PATH.

Usage:  python scripts/verify_apk.py <dist-dir>
"""

import os
import sys
import zipfile
from pathlib import Path

MIN_APK_BYTES = 5 * 1024 * 1024          # python3+kivy debug builds are ~15-25 MB
REQUIRED_ENTRIES = (
    "AndroidManifest.xml",
    "classes.dex",
)
REQUIRED_ENTRY_PREFIXES = (
    "res/",                               # compiled resources
)


def fail(msg: str) -> None:
    print(f"[APK GATE] FAIL: {msg}")
    sys.exit(1)


def main() -> int:
    dist_dir = Path(sys.argv[1] if len(sys.argv) > 1 else "dist")
    apks = sorted(dist_dir.glob("*.apk"))

    if not apks:
        fail(f"no .apk found in {dist_dir} — buildozer gate produced nothing")

    apk = apks[0]
    size = apk.stat().st_size
    print(f"[APK GATE] found {apk.name} ({size / 1_048_576:.1f} MB)")

    if len(apks) > 1:
        print(f"[APK GATE] note: {len(apks)} apks present, verifying first")

    if size < MIN_APK_BYTES:
        fail(f"apk suspiciously small ({size:,} bytes < {MIN_APK_BYTES:,}) — likely truncated cross-compile")

    try:
        zf = zipfile.ZipFile(apk)
    except zipfile.BadZipFile as e:
        fail(f"not a valid zip/apk: {e}")

    names = set(zf.namelist())

    missing = [e for e in REQUIRED_ENTRIES if not any(n == e or n.startswith(e + "/") for n in names)]
    if missing:
        fail(f"missing required entries: {missing}")

    missing_res = [p for p in REQUIRED_ENTRY_PREFIXES if not any(n.startswith(p) for n in names)]
    if missing_res:
        fail(f"missing resource tree: {missing_res}")

    has_native = any(n.startswith("lib/") and n.endswith(".so") for n in names)
    if not has_native:
        fail("no native libraries under lib/ — python runtime not packaged")

    dex_count = sum(1 for n in names if n == "classes.dex" or (n.startswith("classes") and n.endswith(".dex")))
    print(f"[APK GATE] entries={len(names):,} dex={dex_count} native_libs={'yes' if has_native else 'no'}")

    # Optional human-readable badging when aapt is available
    aapt = os.environ.get("AAPT")
    if aapt and os.path.exists(aapt):
        import subprocess
        out = subprocess.run([aapt, "dump", "badging", str(apk)], capture_output=True, text=True)
        for line in out.stdout.splitlines():
            if line.startswith(("package:", "sdkVersion:", "targetSdkVersion:", "application-label:")):
                print("   ", line[:120])

    print("[APK GATE] PASS — APK is structurally complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
