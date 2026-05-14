import sys
import os
from pathlib import Path

def get_base_dir() -> Path:
    """Return absolute path to the app bundle (assets). In --onefile, this is a TEMP folder."""
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent

def get_data_dir() -> Path:
    """Return absolute path to persistent user data in %AppData%/RLForge."""
    appdata = os.environ.get("APPDATA")
    if appdata:
        path = Path(appdata) / "RLForge"
        # We don't necessarily need to create it here, but it's safe
        try:
            path.mkdir(parents=True, exist_ok=True)
            return path
        except:
            pass
            
    # Fallback to executable directory if APPDATA is not available
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent
