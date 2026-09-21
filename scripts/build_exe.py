"""
Build script to package Clembot into a standalone Windows executable (Clembot.exe)
using PyInstaller.
"""

import os
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent


def build():
    print("=" * 60)
    print("  Building Clembot.exe using PyInstaller...")
    print("=" * 60)

    # Check pyinstaller
    try:
        import PyInstaller
    except ImportError:
        print("[!] PyInstaller is not installed in the current environment.")
        print("    Run: pip install pyinstaller")
        return 1

    entry_point = ROOT_DIR / "app" / "main.py"
    dist_dir = ROOT_DIR / "dist"
    build_dir = ROOT_DIR / "build"

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--name=Clembot",
        "--noconsole",
        "--onefile",
        f"--paths={ROOT_DIR}",
        "--hidden-import=comtypes",
        "--hidden-import=pypiwin32",
        "--hidden-import=win32gui",
        "--hidden-import=win32con",
        "--hidden-import=win32api",
        "--hidden-import=win32process",
        "--hidden-import=pyttsx3.drivers.sapi5",
        "--hidden-import=customtkinter",
        "--hidden-import=pystray",
        "--hidden-import=send2trash",
        "--hidden-import=pyautogui",
        f"--distpath={dist_dir}",
        f"--workpath={build_dir}",
        str(entry_point)
    ]

    print("Running command:")
    print(" ".join(cmd))
    res = subprocess.run(cmd, cwd=str(ROOT_DIR))
    if res.returncode == 0:
        print("\n[SUCCESS] Clembot.exe built successfully in:", dist_dir / "Clembot.exe")
    else:
        print(f"\n[FAILURE] PyInstaller exited with code {res.returncode}")
    return res.returncode


if __name__ == "__main__":
    sys.exit(build())
