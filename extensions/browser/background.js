'use strict';
const api = globalThis.browser || chrome;
let nativePort, active, idleTimer;
const queue = [];
function disconnect(error) {
  clearTimeout(idleTimer);
  const port = nativePort; nativePort = undefined;
  const waiting = active ? [active, ...queue] : [...queue]; active = undefined; queue.length = 0;
  if (port) port.disconnect();
  for (const item of waiting) { clearTimeout(item.timer); item.respond({error}); }
}
function pump() {
  if (active || !queue.length) return;
  clearTimeout(idleTimer);
  if (!nativePort) {
    try {
      const port = api.runtime.connectNative('dev.parzr.engine'); nativePort = port;
      port.onMessage.addListener(result => {
        if (port !== nativePort || !active) return;
        const item = active; active = undefined; clearTimeout(item.timer); item.respond(result);
        pump();
        if (!active && !queue.length) idleTimer = setTimeout(() => { if (port === nativePort) disconnect('The local connection closed. Try again.'); }, 35000);
      });
      port.onDisconnect.addListener(() => {
        void api.runtime.lastError;
        if (port === nativePort) disconnect('Connect the Parzr native host first. See Integrations in the Parzr app.');
      });
    } catch { disconnect('The local engine could not start.'); return; }
  }
  active = queue.shift();
  active.timer = setTimeout(() => disconnect('The local model timed out. Try a shorter selection.'), 25000);
  try { nativePort.postMessage(active.request); } catch { disconnect('The local engine disconnected. Try again.'); }
}
async function open(tab) {
  if (!tab?.id || !/^https?:|^file:/.test(tab.url || '')) return;
  try { await api.scripting.executeScript({ target: { tabId: tab.id, allFrames: true }, files: ['editor.js', 'content.js'] }); }
  catch { api.action.setBadgeText({ tabId: tab.id, text: '!' }); api.action.setTitle({ tabId: tab.id, title: 'Parzr cannot access this page. Use the macOS shortcut or playground.' }); }
}
api.action.onClicked.addListener(open);
api.commands.onCommand.addListener(async command => { if (command === 'rewrite') { const [tab] = await api.tabs.query({ active: true, currentWindow: true }); await open(tab); } });
api.runtime.onMessage.addListener((message, sender, respond) => {
  if (message?.type !== 'parzr-rewrite' || !sender.tab || sender.id !== api.runtime.id || !/^https?:\/\/|^file:\/\//.test(sender.url || '')) return;
  const incoming = message.request;
  const request = incoming && { text: incoming.text, mode: incoming.mode, deep: incoming.deep !== false, dictionary: ['Parzr'], protected_ranges: incoming.protected_ranges || [], sentence_start: incoming.sentence_start !== false, sentence_end: incoming.sentence_end !== false };
  if (!Array.isArray(request?.protected_ranges) || request.protected_ranges.length > 4096) { respond({error: 'Invalid editor metadata.'}); return; }
  if (!request || typeof request.text !== 'string' || new TextEncoder().encode(request.text).length > 65536 || !['fix','professional','friendly','concise','direct'].includes(request.mode)) { respond({ error: 'Invalid writing request.' }); return; }
  // Keep one warm process for all tabs and retain only the latest queued request per tab.
  for (let i = queue.length - 1; i >= 0; --i) if (queue[i].tab === sender.tab.id && queue[i].frame === sender.frameId) { queue[i].respond({error:'A newer request replaced this check.'}); queue.splice(i,1); }
  if (queue.length >= 8) { respond({error:'Parzr is checking other writing. Try again shortly.'}); return; }
  queue.push({request, respond, tab:sender.tab.id, frame:sender.frameId}); pump();
  return true;
});
