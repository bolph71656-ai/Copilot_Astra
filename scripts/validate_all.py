#!/usr/bin/env python3
"""Run the complete Copilot Astra validation suite locally.

This repository intentionally does not use GitHub Actions. This script is the
single supported validation entry point and also guards against hosted workflow
files being reintroduced accidentally.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"


def ensure_no_github_actions() -> int:
    files = []
    if WORKFLOWS.exists():
        files = sorted(path for path in WORKFLOWS.rglob("*") if path.is_file())
    if files:
        print("Validation failed: GitHub Actions workflows are intentionally disabled.")
        for path in files:
            print(f"- {path.relative_to(ROOT)}")
        return 1
    print("[ok] no GitHub Actions workflows")
    return 0


def run(label: str, args: list[str]) -> int:
    print(f"\n== {label} ==")
    completed = subprocess.run([sys.executable, *args], cwd=ROOT, check=False)
    if completed.returncode:
        print(f"[fail] {label}: exit {completed.returncode}")
        return completed.returncode
    print(f"[ok] {label}")
    return 0


def main() -> int:
    if ensure_no_github_actions():
        return 1
    steps = [
        ("agent and policy configuration", ["scripts/validate_config.py"]),
        ("routing and calibration tests", ["-m", "unittest", "discover", "-s", "tests", "-v"]),
        ("offline policy regression", ["scripts/policy_search.py"]),
    ]
    for label, args in steps:
        code = run(label, args)
        if code:
            return code
    print("\nAll local validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
