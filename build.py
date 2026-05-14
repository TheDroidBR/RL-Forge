import os
import subprocess
import shutil

def clean():
    for d in ["build", "dist"]:
        if os.path.exists(d):
            shutil.rmtree(d)

def build():
    clean()
    
    # CustomTkinter needs its assets bundled. PyInstaller sometimes misses them.
    # It's usually inside site-packages/customtkinter
    import customtkinter
    ctk_path = os.path.dirname(customtkinter.__file__)
    
    cmd = [
        "pyinstaller",
        "--noconfirm",
        "--windowed", # no console
        "--name", "RL Forge",
        
        # Add CustomTkinter library files
        f"--add-data={ctk_path};customtkinter/",
        
        # Add our app data (config, csv, images)
        "--add-data=data;data/",
        
        # Add the Tool binary
        "--add-binary=RLUPKTool.exe;.",
        
        "main.py"
    ]
    
    print("Running PyInstaller...")
    subprocess.run(cmd, check=True)
    
    print("\nBuild Concluido!")
    print("O executável está na pasta: dist/RL Forge")

if __name__ == "__main__":
    build()
