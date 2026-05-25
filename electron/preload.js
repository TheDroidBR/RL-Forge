/**
 * Preload — exposes safe Electron APIs to renderer via contextBridge.
 */

const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("electronAPI", {
  openFolderDialog: () => ipcRenderer.invoke("dialog:openFolder"),
  minimize:         () => ipcRenderer.invoke("window:minimize"),
  maximize:         () => ipcRenderer.invoke("window:maximize"),
  close:            () => ipcRenderer.invoke("window:close"),
  isMaximized:      () => ipcRenderer.invoke("window:isMaximized"),
  openExternal:     (url) => ipcRenderer.invoke("shell:openExternal", url),
});
