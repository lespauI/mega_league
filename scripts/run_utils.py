#!/usr/bin/env python3
import sys
import subprocess
import os


def run_script(script_name, description, optional=False, extra_args=None):
    """Run a Python script and print its status"""
    print("\n" + "="*80)
    print(f"Running: {description}")
    if optional:
        print("(Optional)")
    print("="*80)

    try:
        cmd = [sys.executable, script_name]
        if extra_args:
            cmd.extend(extra_args)
        result = subprocess.run(
            cmd,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            capture_output=False,
            text=True
        )

        if result.returncode == 0:
            print(f"✓ {description} completed successfully")
            return True
        else:
            if optional:
                print(f"⚠ {description} skipped (missing dependencies)")
                return True
            else:
                print(f"✗ {description} failed with exit code {result.returncode}")
                return False

    except Exception as e:
        if optional:
            print(f"⚠ {description} skipped: {str(e)}")
            return True
        else:
            print(f"✗ Error running {description}: {str(e)}")
            return False
