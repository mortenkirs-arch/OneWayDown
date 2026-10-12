"""Build a standalone release of One Way Down for itch.io: one folder holding the game (Python, pygame and the
assets all inside - nothing to install), zipped up ready to push with butler.

Run (from the project folder, on the platform you're building for):
    uv run --with pyinstaller --with pillow tools/build_release.py

Out:
    dist/OneWayDown/                          the game: run OneWayDown.exe (or OneWayDown on Mac/Linux)
    dist/OneWayDown-<version>-<platform>.zip  that folder, zipped: upload this (or push the folder with butler)

Saves and settings in a packaged build live in the player's own folder (%APPDATA%/OneWayDown on Windows), never next
to the game: see dig/config.py.
"""
import os
import shutil
import subprocess
import sys
import tomllib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NAME = "OneWayDown"
BUILD, DIST = os.path.join(ROOT, "build"), os.path.join(ROOT, "dist")
PLATFORM = {"win32": "windows", "darwin": "mac"}.get(sys.platform, "linux")


def version():
    with open(os.path.join(ROOT, "pyproject.toml"), "rb") as f:
        return tomllib.load(f)["project"]["version"]


def make_icon(path):
    """The game's window icon (dig/appicon.py), saved as a PNG for the executable (PyInstaller turns it into an .ico)."""
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    sys.path.insert(0, ROOT)
    import pygame
    pygame.init()
    pygame.display.set_mode((1, 1))
    from dig.appicon import make_icon as draw
    pygame.image.save(pygame.transform.smoothscale(draw(), (256, 256)), path)


def source_note(folder):
    """The GPL asks that players can get the source: say where it is."""
    try:
        url = subprocess.run(["git", "remote", "get-url", "origin"], cwd=ROOT, capture_output=True, text=True,
                             check=True).stdout.strip().removesuffix(".git")
    except (OSError, subprocess.CalledProcessError):
        url = "(see the game's itch.io page)"
    with open(os.path.join(folder, "SOURCE.txt"), "w", encoding="utf-8") as f:
        f.write(f"One Way Down {version()} is free software, under the GNU General Public License (see COPYING).\n"
                f"Its source code: {url}\n")


def main():
    os.makedirs(BUILD, exist_ok=True)
    icon = os.path.join(BUILD, "icon.png")
    make_icon(icon)
    sep = ";" if sys.platform == "win32" else ":"
    import PyInstaller.__main__
    PyInstaller.__main__.run([
        os.path.join(ROOT, "main.py"),
        "--name", NAME,
        "--onedir",          # one folder, not one self-unpacking file: starts faster, fewer antivirus false alarms
        "--windowed",        # no console window
        "--icon", icon,
        "--add-data", f"{os.path.join(ROOT, 'assets')}{sep}assets",
        "--distpath", DIST,
        "--workpath", os.path.join(BUILD, "pyinstaller"),
        "--specpath", BUILD,
        "--noconfirm", "--clean",
    ])
    folder = os.path.join(DIST, NAME)
    for doc in ("COPYING", "README.md"):
        shutil.copy(os.path.join(ROOT, doc), folder)
    source_note(folder)
    zip_base = os.path.join(DIST, f"{NAME}-{version()}-{PLATFORM}")
    shutil.make_archive(zip_base, "zip", DIST, NAME)
    print(f"\nBuilt {folder}\nZipped {zip_base}.zip")


if __name__ == "__main__":
    main()
