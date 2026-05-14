import os
import sys
import tempfile
import urllib.request
import zipfile
import subprocess
import threading
from pathlib import Path

def apply_update(zip_path: str, progress_cb, on_complete_cb, on_error_cb):
    """Extracts the update and launches the self-updating batch script."""
    try:
        temp_dir = tempfile.gettempdir()
        extract_path = os.path.join(temp_dir, "RL_Forge_Update")
        
        progress_cb(10, "Extraindo arquivos...")
        
        if os.path.exists(extract_path):
            import shutil
            shutil.rmtree(extract_path)
            
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_path)
            
        progress_cb(50, "Preparando instalação...")
        
        # The zip from GitHub usually has a root folder inside it (e.g., "RL Forge/").
        # We need to find where the actual RL Forge.exe is inside the extracted dir.
        exe_source_dir = extract_path
        for root, dirs, files in os.walk(extract_path):
            if "RL Forge.exe" in files:
                exe_source_dir = root
                break

        # Get current installation directory
        current_exe = sys.executable
        if not getattr(sys, 'frozen', False):
            # Running from source, testing mode
            current_exe = os.path.abspath(__file__)
            
        install_dir = os.path.dirname(current_exe)
        
        bat_path = os.path.join(temp_dir, "rl_forge_updater.bat")
        vbs_path = os.path.join(temp_dir, "rl_forge_updater.vbs")
        
        # Create BAT file that waits, copies, restarts, and cleans up
        bat_content = f"""@echo off
timeout /t 2 /nobreak > NUL
xcopy /s /e /y /q "{exe_source_dir}\\*" "{install_dir}\\"
start "" "{current_exe}"
del "{zip_path}"
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
    """Downloads the ZIP from URL and applies the update."""
    try:
        temp_dir = tempfile.gettempdir()
        zip_path = os.path.join(temp_dir, "RL_Forge_Update.zip")
        
        def report(blocknum, blocksize, totalsize):
            if totalsize > 0:
                percent = blocknum * blocksize / totalsize
                # Cap at 95% because extraction is the rest
                p = min(95, int(percent * 95))
                progress_cb(p, f"Baixando... {p}%")

        urllib.request.urlretrieve(url, zip_path, reporthook=report)
        apply_update(zip_path, progress_cb, on_complete_cb, on_error_cb)
        
    except Exception as e:
        on_error_cb(str(e))

def start_update_thread(url: str, progress_cb, on_complete_cb, on_error_cb):
    threading.Thread(
        target=download_and_update,
        args=(url, progress_cb, on_complete_cb, on_error_cb),
        daemon=True
    ).start()
