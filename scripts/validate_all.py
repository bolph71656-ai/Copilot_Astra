#!/usr/bin/env python3
"""Run the complete Copilot Astra validation suite locally."""
from __future__ import annotations
import subprocess, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
WORKFLOWS=ROOT/".github"/"workflows"

def ensure_no_github_actions():
    files=sorted(p for p in WORKFLOWS.rglob("*") if p.is_file()) if WORKFLOWS.exists() else []
    if files:
        print("Validation failed: GitHub Actions workflows are intentionally disabled.")
        for p in files: print(f"- {p.relative_to(ROOT)}")
        return 1
    print("[ok] no GitHub Actions workflows");return 0

def run(label,args):
    print(f"\n== {label} ==")
    done=subprocess.run([sys.executable,*args],cwd=ROOT,check=False)
    if done.returncode:
        print(f"[fail] {label}: exit {done.returncode}");return done.returncode
    print(f"[ok] {label}");return 0

def main():
    if ensure_no_github_actions():return 1
    for label,args in [
        ("generated model configuration",["scripts/sync_model_config.py"]),
        ("agent and policy configuration",["scripts/validate_config.py"]),
        ("gateway policy and economics",["scripts/validate_gateway_policy.py"]),
        ("routing/calibration tests",["-m","unittest","discover","-s","tests","-v"]),
        ("offline policy regression",["scripts/policy_search.py"]),
    ]:
        code=run(label,args)
        if code:return code
    print("\nAll local validation passed.");return 0

if __name__=="__main__":raise SystemExit(main())
