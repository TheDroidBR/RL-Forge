import os
import sys
import tempfile
import urllib.request
import threading

def apply_update(exe_path: str, progress_cb, on_complete_cb, on_error_cb):
    """Launches the self-updating batch script to replace the executable."""
    try:
        temp_dir = tempfile.gettempdir()
        
        progress_cb(50, "Preparando instalação...")
        
        # Get current installation directory
        current_exe = sys.executable
        if not getattr(sys, 'frozen', False):
            # Running from source, testing mode
            current_exe = os.path.abspath(__file__)
            
        bat_path = os.path.join(temp_dir, "rl_forge_updater.bat")
        vbs_path = os.path.join(temp_dir, "rl_forge_updater.vbs")
        
        # Create BAT file that waits, copies the exe, restarts, and cleans up
        bat_content = f"""@echo off
timeout /t 2 /nobreak > NUL
copy /y "{exe_path}" "{current_exe}"
start "" "{current_exe}"
del "{exe_path}"
del "{vbs_path}"
del "%~f0"
"""
        with open(bat_path, "w", encoding="utf-8") as f:
            f.write(bat_content)
            
        # Create VBS file to run the BAT hidden
        vbs_content = f"""Set WshShell = CreateObject("WScript.Shell")
WshShell.Run chr(34) & "{bat_path}" & chr(34), 0, False
"""
        with open(vbs_path, "w", encoding="utf-8") as f:
            f.write(vbs_content)
            
        progress_cb(100, "Reiniciando aplicativo...")
        
        # Run VBS and exit
        os.startfile(vbs_path)
        on_complete_cb()
        
    except Exception as e:
        on_error_cb(str(e))

def download_and_update(url: str, progress_cb, on_complete_cb, on_error_cb):
    """Downloads the EXE from URL and applies the update."""
    try:
        temp_dir = tempfile.gettempdir()
        exe_path = os.path.join(temp_dir, "RL_Forge_Update.exe")
        
        def report(blocknum, blocksize, totalsize):
            if totalsize > 0:
                percent = blocknum * blocksize / totalsize
                # Cap at 95% because extraction is the rest
                p = min(95, int(percent * 95))
                progress_cb(p, f"Baixando... {p}%")

        urllib.request.urlretrieve(url, exe_path, reporthook=report)
        apply_update(exe_path, progress_cb, on_complete_cb, on_error_cb)
        
    except Exception as e:
        on_error_cb(str(e))

def start_update_thread(url: str, progress_cb, on_complete_cb, on_error_cb):
    threading.Thread(
        target=download_and_update,
        args=(url, progress_cb, on_complete_cb, on_error_cb),
        daemon=True
    ).start()
