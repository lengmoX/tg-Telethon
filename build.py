"""
Build script for TGF CLI executable

Usage:
    python build.py          # Build for current platform
    python build.py --onefile # Single executable (slower startup)
"""

import subprocess
import sys
import shutil
from pathlib import Path

# Project info
APP_NAME = "tgf"
ENTRY_POINT = "tgf/cli/main.py"

# PyInstaller options
COMMON_OPTIONS = [
    f"--name={APP_NAME}",
    "--console",  # CLI app
    "--clean",    # Clean cache
    "--noconfirm",
    
    # Use custom hooks
    "--additional-hooks-dir=hooks",
    
    # Hidden imports (Telethon and dependencies)
    "--hidden-import=telethon",
    "--hidden-import=telethon.tl.alltlobjects",
    "--hidden-import=aiosqlite",
    "--hidden-import=click",
    "--hidden-import=rich",
    "--hidden-import=rich.markup",
    "--hidden-import=rich.emoji",
    "--hidden-import=qrcode",
    "--hidden-import=dotenv",
    "--hidden-import=python-dotenv",
    
    # Collect all data files from rich (for unicode tables)
    "--collect-all=rich",
    
    # Exclude unnecessary modules to reduce size
    "--exclude-module=tkinter",
    "--exclude-module=matplotlib",
    "--exclude-module=numpy",
    "--exclude-module=pandas",
    "--exclude-module=scipy",
    "--exclude-module=PIL",
]


def build(onefile: bool = False):
    """Build executable with PyInstaller"""
    
    # Check if PyInstaller is installed
    try:
        import PyInstaller
    except ImportError:
        print("Installing PyInstaller...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)
    
    # Build command
    cmd = [sys.executable, "-m", "PyInstaller"]
    cmd.extend(COMMON_OPTIONS)
    
    if onefile:
        cmd.append("--onefile")
        print("Building single file executable (this may take longer)...")
    else:
        cmd.append("--onedir")
        print("Building directory-based executable...")
    
    cmd.append(ENTRY_POINT)
    
    print(f"Running: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)
    
    # Output location
    if onefile:
        if sys.platform == "win32":
            exe_path = Path("dist") / f"{APP_NAME}.exe"
        else:
            exe_path = Path("dist") / APP_NAME
    else:
        exe_path = Path("dist") / APP_NAME
    
    print(f"\n[OK] Build complete!")
    print(f"  Output: {exe_path.absolute()}")
    
    if not onefile:
        if sys.platform == "win32":
            print(f"\n  To run: .\\dist\\{APP_NAME}\\{APP_NAME}.exe")
        else:
            print(f"\n  To run: ./dist/{APP_NAME}/{APP_NAME}")


def clean():
    """Clean build artifacts"""
    for path in ["build", "dist", f"{APP_NAME}.spec"]:
        p = Path(path)
        if p.exists():
            if p.is_dir():
                shutil.rmtree(p)
            else:
                p.unlink()
            print(f"Removed: {path}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Build TGF executable")
    parser.add_argument("--onefile", action="store_true", help="Create single executable")
    parser.add_argument("--clean", action="store_true", help="Clean build artifacts")
    
    args = parser.parse_args()
    
    if args.clean:
        clean()
    else:
        build(onefile=args.onefile)
