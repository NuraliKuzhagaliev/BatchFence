const { contextBridge, ipcRenderer } = require("electron");
contextBridge.exposeInMainWorld(
  "batchfence",
  Object.freeze({
    request: (method, route, body) =>
      ipcRenderer.invoke("bf:request", method, route, body),
    chooseFiles: () => ipcRenderer.invoke("bf:chooseFiles"),
    savePacket: (packet) => ipcRenderer.invoke("bf:savePacket", packet),
    openPacket: () => ipcRenderer.invoke("bf:openPacket"),
    copyDraft: (draft) => ipcRenderer.invoke("bf:copyDraft", draft),
    platform: "Windows desktop",
  }),
);
