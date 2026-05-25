import os
import subprocess
import shutil
import sys
from pathlib import Path

def clean():
    for d in ["build", "dist"]:
        if os.path.exists(d):
            shutil.rmtree(d)

def build():
    clean()
    
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--windowed", # no console
        "--onefile",  # single executable
        "--name", "rl_forge_api",
        "--icon", "data/icon.ico",
        
        # Add our app data (config, csv, images)
        "--add-data=data;data/",
        
        # Add the Tool binary
        "--add-binary=RLUPKTool.exe;.",
        
        "main.py"
    ]
    
    print("Running PyInstaller to build Flask API...")
    subprocess.run(cmd, check=True)
    
    # Copy compiled backend to electron/python/ for Electron integration
    exe_src = Path("dist") / "rl_forge_api.exe"
    electron_py_dir = Path("electron") / "python"
    electron_py_dir.mkdir(parents=True, exist_ok=True)
    exe_dest = electron_py_dir / "rl_forge_api.exe"
    
    if exe_src.exists():
        print(f"Copying {exe_src.name} to {exe_dest}...")
        shutil.copy2(exe_src, exe_dest)
        print("Backend integrated successfully!")
    else:
        print(f"Error: {exe_src} was not generated.")
        sys.exit(1)
    
    print("\n[OK] Build Concluido!")
    print(f"O backend compilado está em: {exe_dest}")
    print("Agora você pode rodar 'npm run build' na pasta 'electron' para gerar o pacote final do instalador!")

if __name__ == "__main__":
    build()
