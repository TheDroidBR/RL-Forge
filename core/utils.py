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
        except Exception:
            pass
            
    # Fallback to executable directory if APPDATA is not available
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent

def is_game_running() -> bool:
    """Check if RocketLeague.exe is running via tasklist."""
    import subprocess
    try:
        # Otimizar para ocultar a janela cmd ao chamar subprocess
        extra_kwargs = {}
        if os.name == 'nt':
            extra_kwargs['creationflags'] = 0x08000000
        # Use tasklist to check for the process name
        output = subprocess.check_output('tasklist /FI "IMAGENAME eq RocketLeague.exe" /NH', 
                                         shell=True, stderr=subprocess.STDOUT, **extra_kwargs).decode('latin-1')
        return "RocketLeague.exe" in output
    except Exception:
        return False

