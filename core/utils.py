import sys
import os
from pathlib import Path

def get_base_dir() -> Path:
    """Return absolute path to the app root, compatible with PyInstaller."""
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent
