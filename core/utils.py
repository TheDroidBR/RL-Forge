import sys
import os
from pathlib import Path

def get_base_dir() -> Path:
    """Return absolute path to the app bundle (assets). In --onefile, this is a TEMP folder."""
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent

def get_data_dir() -> Path:
    """Return absolute path to persistent user data. In --onefile, this is next to the .exe."""
    if getattr(sys, 'frozen', False):
        # Path to the directory containing the .exe
        return Path(sys.executable).parent
    # Path to the project root when running from source
    return Path(__file__).resolve().parent.parent
