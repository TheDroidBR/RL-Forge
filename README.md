<h1 align="center">
  <img src="assets/logo.png" alt="RL Forge Logo" width="128"><br>
  🚀 RL Forge
</h1>

<p align="center">
  <strong>A modern, fast, and secure local cosmetic swapper for Rocket League.</strong>
</p>

<p align="center">
  <img alt="GitHub release (latest by date)" src="https://img.shields.io/github/v/release/TheDroidBR/RL-Forge">
  <img alt="License" src="https://img.shields.io/badge/License-GPL_v3-blue.svg">
</p>

## 📖 About

**Developed by [TheDroid](https://github.com/TheDroidBR)**, RL Forge is a native Windows desktop application built to simplify local cosmetic modding in Rocket League. It replaces local item models with the ones you want without the need for complex command-line tools. 

RL Forge v2.0.0 utilizes an ultra-premium, high-performance hybrid architecture:
- **Frontend:** A modern, high-performance native desktop shell built with **Electron** (HTML5, CSS3, Vanilla ES6 Javascript) utilizing curated, gorgeous HSL color palettes and smooth animations.
- **Backend:** A lightweight, headless local REST API server powered by **Python Flask**, running in asynchronous fallback mode.
- **Unreal UPK Engine:** A secure integration with the community-trusted `RLUPKTool` engine for safe UPK decryption, name table matching, and color patching.

### ✨ Features
- **Ultra-Modern Hybrid UI:** Exquisite glassmorphism-based UI, built on Electron and Vanilla CSS, running at a fluid 60+ FPS.
- **Dynamic Paint Selector (RGB):** A custom paint matrix allowing you to apply any custom color and neon glow intensity (emissiveness slider) to any local car or accessory in the game.
- **Smart Search:** Fast client-side fuzzy-filtering with item shorthands (e.g. `tw` for Titanium White) and beautiful thumbnails.
- **Favorites & Combos:** Flag favorite accessories and compile full multi-item swaps (presets) that can be applied with a single click.
- **Preset Share (Base64 URL-Safe):** Export and import preset combos easily using compressed, short Base64 codes.
- **Real-Time Active Backups:** Check individual backup integrity in real-time, displaying readable, prettified local names (e.g., "Carro: Fennec" instead of `body_grain`), and dynamically disabling the "Restore" action if files are altered.
- **Auto-Detect Installation:** Dynamic path auto-detection by reading Windows Registry and Epic Games local manifests.

## 📥 Installation & Usage

1. Go to the **[Releases](https://github.com/TheDroidBR/RL-Forge/releases/latest)** tab.
2. Download the latest `RLForge.exe`.
3. Put the `.exe` anywhere on your computer (like your Desktop) and run it.
4. Point the app to your Rocket League `CookedPCConsole` folder (the app usually auto-detects it).
5. Select the item you have, the item you want, and click **⚡ SWAP**.

## 🛠️ Development & Building from Source

### Prerequisites
- **Python 3.10+** (with virtual environment recommended)
- **Node.js 18+ & npm** (for the Electron frontend shell)

### Setup & Run
1. Install Python backend dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Install Electron dependencies in the `electron` directory:
   ```bash
   cd electron
   npm install
   ```
3. Run the application in development mode:
   - Double-click `Abrir RL Swapper.bat` or `Abrir RL Forge.vbs` in the root folder, OR
   - Run the Electron shell directly from the `electron` directory:
     ```bash
     cd electron
     npm start
     ```

### Compilation & Distribution
To package the app into a standalone Windows installer or executable:
```bash
cd electron
npm run build
```
The packed installer and unpackaged files will be generated under the `electron/dist/` directory.

*Note: Make sure `RLUPKTool.exe` is present in the root directory before running or compiling.*

## 🙏 Credits & Acknowledgments

This project is made possible thanks to the open-source modding community:
* **[ShinyEmii (Toga)](https://github.com/ShinyEmii/Toga-Files):** Providing the incredibly maintained database of item IDs, packages, and AES keys.
* **[AltimorTASDK](https://github.com/AltimorTASDK/RLUPKTool):** For creating the `RLUPKTool` engine that powers the safe UPK decryption/encryption.

## 🔒 Privacy & Metrics

To help improve the software and track adoption, RL Forge collects anonymous usage metrics:
- **Unique Users:** An anonymous hash based on your machine ID to count total installations.
- **Active Users:** A periodic heartbeat while the app is open to track concurrent users.
- **No Personal Data:** We do not collect names, emails, IPs (beyond standard web request logs), or any game-sensitive data.

## ⚖️ Disclaimer & License

*RL Forge is an open-source project distributed under the **GNU GPL v3.0 License**.*
*This tool is **NOT** affiliated with, endorsed, or sponsored by Psyonix, Epic Games, or any of their partners. Local cosmetic modding is done at your own risk.*
