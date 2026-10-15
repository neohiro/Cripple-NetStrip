#!/usr/bin/env python3
"""
Release automation script for Cripple-NetStrip.
Handles version bumping, changelog generation, and release preparation.
"""
import sys
import re
import subprocess
import argparse
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple

ROOT = Path(__file__).parent.parent
VERSION_FILE = ROOT / "netstrip" / "__init__.py"
CHANGELOG_FILE = ROOT / "changelog.md"
REQUIREMENTS_FILE = ROOT / "requirements.txt"
BUILDOZER_FILE = ROOT / "buildozer.spec"


def get_current_version() -> str:
    """Get current version from __init__.py"""
    content = VERSION_FILE.read_text()
    match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', content)
    if not match:
        raise ValueError("Could not find version in __init__.py")
    return match.group(1)


def parse_version(version: str) -> Tuple[int, int, int]:
    """Parse version string into (major, minor, patch)"""
    match = re.match(r'v?(\d+)\.(\d+)\.(\d+)', version)
    if not match:
        raise ValueError(f"Invalid version format: {version}")
    return tuple(map(int, match.groups()))


def format_version(major: int, minor: int, patch: int, prefix: bool = True) -> str:
    """Format version tuple into string"""
    v = f"{major}.{minor}.{patch}"
    return f"v{v}" if prefix else v


def bump_version(version: str, part: str) -> str:
    """Bump version by part (major, minor, patch)"""
    major, minor, patch = parse_version(version)
    
    if part == "major":
        major += 1
        minor = 0
        patch = 0
    elif part == "minor":
        minor += 1
        patch = 0
    elif part == "patch":
        patch += 1
    else:
        raise ValueError(f"Invalid part: {part}")
    
    return format_version(major, minor, patch, prefix=False)


def update_version_file(new_version: str):
    """Update __version__ in __init__.py"""
    content = VERSION_FILE.read_text()
    new_content = re.sub(
        r'__version__\s*=\s*["\'][^"\']+["\']',
        f'__version__ = "{new_version}"',
        content
    )
    VERSION_FILE.write_text(new_content)
    print(f"Updated {VERSION_FILE} to {new_version}")


def update_buildozer_version(new_version: str):
    """Update version in buildozer.spec"""
    if not BUILDOZER_FILE.exists():
        return
    
    content = BUILDOZER_FILE.read_text()
    # Update version line
    new_content = re.sub(
        r'^version\s*=\s*.+$',
        f'version = {new_version}',
        content,
        flags=re.MULTILINE
    )
    BUILDOZER_FILE.write_text(new_content)
    print(f"Updated {BUILDOZER_FILE} to {new_version}")


def generate_changelog_entry(version: str, changes: list) -> str:
    """Generate changelog entry for new version"""
    date = datetime.now().strftime("%Y-%m-%d")
    lines = [f"## [{version}] - {date}", ""]
    
    categories = {
        "Added": [],
        "Changed": [],
        "Fixed": [],
        "Removed": [],
        "Security": [],
    }
    
    for change in changes:
        # Simple categorization based on prefix
        lower = change.lower()
        if lower.startswith(("add", "new", "implement", "support")):
            categories["Added"].append(change)
        elif lower.startswith(("fix", "resolve", "correct", "patch")):
            categories["Fixed"].append(change)
        elif lower.startswith(("change", "update", "modify", "improve", "refactor")):
            categories["Changed"].append(change)
        elif lower.startswith(("remove", "delete", "drop")):
            categories["Removed"].append(change)
        elif lower.startswith(("security", "vuln", "cve")):
            categories["Security"].append(change)
        else:
            categories["Changed"].append(change)
    
    for cat, items in categories.items():
        if items:
            lines.append(f"### {cat}")
            for item in items:
                lines.append(f"- {item}")
            lines.append("")
    
    return "\n".join(lines)


def prepend_changelog(entry: str):
    """Prepend entry to changelog.md"""
    if CHANGELOG_FILE.exists():
        existing = CHANGELOG_FILE.read_text()
    else:
        existing = "# Changelog\n\nAll notable changes to this project will be documented in this file.\n\n"
    
    new_content = entry + "\n" + existing
    CHANGELOG_FILE.write_text(new_content)
    print(f"Updated {CHANGELOG_FILE}")


def run_git_commands(version: str, message: str = None):
    """Run git commands for release"""
    if message is None:
        message = f"Release {version}"
    
    cmds = [
        ["git", "add", "-A"],
        ["git", "commit", "-m", message],
        ["git", "tag", "-a", f"v{version}", "-m", f"Release {version}"],
    ]
    
    for cmd in cmds:
        result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Command failed: {' '.join(cmd)}")
            print(result.stderr)
            return False
        print(result.stdout.strip() or "OK")
    return True


def push_release(version: str):
    """Push release to remote"""
    cmds = [
        ["git", "push", "origin", "main"],
        ["git", "push", "origin", f"v{version}"],
    ]
    
    for cmd in cmds:
        result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Push failed: {' '.join(cmd)}")
            print(result.stderr)
            return False
        print(result.stdout.strip() or "Pushed")
    return True


def main():
    parser = argparse.ArgumentParser(description="Cripple-NetStrip release automation")
    parser.add_argument(
        "action", 
        choices=["bump", "release", "changelog", "version"],
        help="Action to perform"
    )
    parser.add_argument(
        "--part", 
        choices=["major", "minor", "patch"], 
        default="patch",
        help="Version part to bump"
    )
    parser.add_argument(
        "--version", 
        help="Explicit version to set (e.g., 4.0.0)"
    )
    parser.add_argument(
        "--message", 
        help="Commit message for release"
    )
    parser.add_argument(
        "--dry-run", 
        action="store_true",
        help="Show what would be done without making changes"
    )
    parser.add_argument(
        "--push", 
        action="store_true",
        help="Push to remote after release"
    )
    
    args = parser.parse_args()
    
    current = get_current_version()
    print(f"Current version: {current}")
    
    if args.action == "version":
        print(f"Version: {current}")
        return 0
    
    if args.action == "bump":
        if args.version:
            new_version = args.version.lstrip('v')
        else:
            new_version = bump_version(current, args.part)
        
        print(f"New version: {new_version}")
        
        if args.dry_run:
            print("DRY RUN - no changes made")
            return 0
        
        update_version_file(new_version)
        update_buildozer_version(new_version)
        
        if args.message:
            msg = args.message
        else:
            msg = f"Bump version to {new_version}"
        
        if run_git_commands(new_version, msg):
            print(f"Successfully bumped to {new_version}")
            if args.push:
                push_release(new_version)
        return 0
    
    if args.action == "release":
        if not args.version:
            new_version = bump_version(current, args.part)
        else:
            new_version = args.version.lstrip('v')
        
        print(f"Preparing release {new_version}")
        
        # Generate changelog from git log
        result = subprocess.run(
            ["git", "log", "--oneline", "--no-merges", f"v{current}..HEAD"],
            cwd=ROOT, capture_output=True, text=True
        )
        changes = [line for line in result.stdout.strip().split('\n') if line]
        
        if args.dry_run:
            print("DRY RUN - would release:", new_version)
            print("Changes:", changes)
            return 0
        
        update_version_file(new_version)
        update_buildozer_version(new_version)
        
        # Generate and prepend changelog
        entry = generate_changelog_entry(new_version, changes)
        prepend_changelog(entry)
        
        msg = args.message or f"Release {new_version}"
        if run_git_commands(new_version, msg):
            print(f"Successfully released {new_version}")
            if args.push:
                push_release(new_version)
        return 0
    
    if args.action == "changelog":
        if not args.version:
            new_version = bump_version(current, args.part)
        else:
            new_version = args.version.lstrip('v')
        
        result = subprocess.run(
            ["git", "log", "--oneline", "--no-merges", f"v{current}..HEAD"],
            cwd=ROOT, capture_output=True, text=True
        )
        changes = [line for line in result.stdout.strip().split('\n') if line]
        
        entry = generate_changelog_entry(new_version, changes)
        print(entry)
        
        if not args.dry_run:
            prepend_changelog(entry)
        return 0
    
    return 1


if __name__ == "__main__":
    sys.exit(main())