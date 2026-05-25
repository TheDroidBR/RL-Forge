/**
 * RL Forge — Electron Main Process
 * Spawns Python Flask backend, reads the port, opens BrowserWindow.
 */

const { app, BrowserWindow, ipcMain, dialog, shell } = require("electron");
const { spawn } = require("child_process");
const path = require("path");
const fs   = require("fs");

let mainWindow = null;
let pyProcess  = null;
let apiPort    = null;

// ── Find Python executable ────────────────────────────────────────────────────
function findPython() {
  // In packaged app, look for bundled executable
  const candidates = [
    path.join(process.resourcesPath, "python", "rl_forge_api.exe"),
    path.join(process.resourcesPath, "python", "rl_forge_api"),
  ];
  for (const c of candidates) {
    if (fs.existsSync(c)) return { exe: c, args: [] };
  }
  // Development: run api/server.py directly
  const serverScript = path.join(__dirname, "..", "api", "server.py");

  // 1. Try local workspace virtual environment (.venv)
  const venvPython = path.join(__dirname, "..", "..", ".venv", "Scripts", "python.exe");
  const venvCfg = path.join(__dirname, "..", "..", ".venv", "pyvenv.cfg");
  let venvOk = false;
  if (fs.existsSync(venvPython) && fs.existsSync(venvCfg)) {
    try {
      const cfgContent = fs.readFileSync(venvCfg, "utf8");
      // Check home directory
      const homeMatch = cfgContent.match(/home\s*=\s*(.*)/);
      if (homeMatch) {
        const homePath = homeMatch[1].trim();
        if (fs.existsSync(homePath)) {
          venvOk = true;
        }
      }
      // If home check failed or not found, check executable if present
      const exeMatch = cfgContent.match(/executable\s*=\s*(.*)/);
      if (exeMatch) {
        const baseExe = exeMatch[1].trim();
        if (fs.existsSync(baseExe)) {
          venvOk = true;
        } else {
          venvOk = false; // base exe is explicitly defined but missing
        }
      }
    } catch (e) {
      // ignore, fall back to safe check
      venvOk = fs.existsSync(venvPython);
    }
  }
  if (venvOk) {
    return { exe: venvPython, args: [serverScript] };
  }

  // 2. Try common specific Windows installations
  const localAppData = process.env.LOCALAPPDATA || path.join(process.env.USERPROFILE, "AppData", "Local");
  const commonPaths = [
    path.join(localAppData, "Programs", "Python", "Python314", "python.exe"),
    path.join(localAppData, "Programs", "Python", "Python312", "python.exe"),
  ];
  for (const p of commonPaths) {
    if (fs.existsSync(p)) return { exe: p, args: [serverScript] };
  }

  // 3. Fallback to py Windows launcher
  return { exe: "py", args: [serverScript] };
}

// ── Spawn Python backend ──────────────────────────────────────────────────────
function startPython() {
  return new Promise((resolve, reject) => {
    const { exe, args } = findPython();
    const cwd = path.join(__dirname, "..");

    pyProcess = spawn(exe, args, {
      cwd,
      stdio: ["ignore", "pipe", "pipe"],
      windowsHide: true,
    });

    let buffer = "";

    pyProcess.stdout.on("data", (data) => {
      buffer += data.toString();
      const match = buffer.match(/PORT:(\d+)/);
      if (match) {
        apiPort = parseInt(match[1], 10);
        console.log(`[Electron] Python API on port ${apiPort}`);
        resolve(apiPort);
      }
    });

    pyProcess.stderr.on("data", (d) => {
      // Only log real errors, not Flask startup messages
      const msg = d.toString();
      if (!msg.includes("WARNING") && !msg.includes("Development Server")) {
        console.error("[Python]", msg.trim());
      }
    });

    pyProcess.on("error", (err) => {
      console.error("[Python spawn error]", err);
      reject(err);
    });

    pyProcess.on("exit", (code) => {
      console.log(`[Python] exited with code ${code}`);
    });

    // Timeout safety
    setTimeout(() => reject(new Error("Python startup timeout")), 15000);
  });
}

// ── Create Window ─────────────────────────────────────────────────────────────
function createWindow(port) {
  mainWindow = new BrowserWindow({
    width:  1280,
    height: 780,
    minWidth:  960,
    minHeight: 620,
    frame: false,
    titleBarStyle: "hidden",
    backgroundColor: "#0f1117",
    icon: path.join(__dirname, "..", "assets", "icon.ico"),
    show: false,   // show only after ready-to-show to avoid white flash
    webPreferences: {
      preload:          path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration:  false,
    },
  });

  // Wait a moment for Flask to be fully ready
  const tryLoad = (attempt = 0) => {
    mainWindow.loadURL(`http://127.0.0.1:${port}`).catch((err) => {
      if (attempt < 10) {
        setTimeout(() => tryLoad(attempt + 1), 400);
      } else {
        console.error("Failed to load app:", err);
      }
    });
  };
  tryLoad();

  mainWindow.once("ready-to-show", () => mainWindow.show());
  mainWindow.on("closed", () => { mainWindow = null; });
}

// ── IPC Handlers ─────────────────────────────────────────────────────────────
ipcMain.handle("dialog:openFolder", async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ["openDirectory"],
    title: "Selecione a pasta CookedPCConsole do Rocket League",
  });
  return result.canceled ? null : result.filePaths[0];
});

ipcMain.handle("window:minimize",  () => mainWindow?.minimize());
ipcMain.handle("window:maximize",  () => {
  if (mainWindow?.isMaximized()) mainWindow.unmaximize();
  else mainWindow?.maximize();
});
ipcMain.handle("window:close",     () => mainWindow?.close());
ipcMain.handle("window:isMaximized", () => mainWindow?.isMaximized() ?? false);

ipcMain.handle("shell:openExternal", (_e, url) => shell.openExternal(url));

// ── App Lifecycle ─────────────────────────────────────────────────────────────
app.whenReady().then(async () => {
  // Set Application User Model ID for Windows taskbar icon linking
  if (process.platform === "win32") {
    app.setAppUserModelId("com.thedroid.rlforge");
  }
  try {
    const port = await startPython();
    createWindow(port);
  } catch (err) {
    console.error("Failed to start Python backend:", err);
    // Still try to open window — show error page
    createWindow(3000);
  }
});

app.on("window-all-closed", () => {
  if (pyProcess) pyProcess.kill();
  if (process.platform !== "darwin") app.quit();
});

app.on("before-quit", () => {
  if (pyProcess) pyProcess.kill();
});
