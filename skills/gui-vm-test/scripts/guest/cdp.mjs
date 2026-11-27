// Minimal Chrome DevTools Protocol client for driving an Electron/Chromium
// page under test.  Node 22+ (global WebSocket, fetch).
//
// usage: node cdp.mjs <port> <command> [args...]
//   targets                     list targets
//   eval <js>                   evaluate an expression in the first page, print JSON result
//   ui                          list visible clickable/inputs elements with text/labels
//   text                        print document.body.innerText
//   click <text|regex>          click the visible element whose text/label matches
//   type <text>                 insert text into the focused element
//   key <key>                   press a key (Enter, Escape, Tab, ...)
//   shot <file.png>             screenshot of the page
// Environment: CDP_TARGET=<regex on url/title> selects the target (default: first page).
import { writeFileSync } from "node:fs";

const [port, cmd, ...args] = process.argv.slice(2);
// Hard limit for the whole invocation: a stopped or hung browser process
// accepts the TCP connection but never answers the HTTP or WebSocket
// handshake, which no per-command timeout covers.
setTimeout(() => {
  console.error("cdp: no answer, giving up");
  process.exit(124);
}, Number(process.env.CDP_TIMEOUT ?? 10000) + 5000).unref();
const base = `http://127.0.0.1:${port}`;

async function targets() {
  const r = await fetch(`${base}/json`);
  return r.json();
}

async function connect() {
  const list = await targets();
  const re = process.env.CDP_TARGET ? new RegExp(process.env.CDP_TARGET) : null;
  const t = list.find((x) => x.type === "page" && (!re || re.test(x.url) || re.test(x.title)));
  if (!t) throw new Error("no matching page target");
  const ws = new WebSocket(t.webSocketDebuggerUrl);
  await new Promise((res, rej) => {
    ws.onopen = res;
    ws.onerror = rej;
  });
  let id = 0;
  const pending = new Map();
  ws.onmessage = (ev) => {
    const m = JSON.parse(ev.data);
    if (m.id && pending.has(m.id)) {
      const { res, rej } = pending.get(m.id);
      pending.delete(m.id);
      m.error ? rej(new Error(JSON.stringify(m.error))) : res(m.result);
    }
  };
  // Some commands (a key press that starts a navigation) may never get a
  // reply; give up after CDP_TIMEOUT ms instead of hanging the harness.
  const timeoutMs = Number(process.env.CDP_TIMEOUT ?? 10000);
  const send = (method, params = {}) =>
    new Promise((res, rej) => {
      const i = ++id;
      const timer = setTimeout(() => {
        pending.delete(i);
        rej(new Error(`CDP ${method} timed out after ${timeoutMs} ms`));
      }, timeoutMs);
      pending.set(i, {
        res: (v) => (clearTimeout(timer), res(v)),
        rej: (e) => (clearTimeout(timer), rej(e)),
      });
      ws.send(JSON.stringify({ id: i, method, params }));
    });
  return { send, close: () => ws.close() };
}

async function evaluate(c, expression) {
  const r = await c.send("Runtime.evaluate", {
    expression,
    returnByValue: true,
    awaitPromise: true,
  });
  if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails));
  return r.result.value;
}

const UI_JS = `(() => {
  const vis = (e) => { const r = e.getBoundingClientRect(); const s = getComputedStyle(e);
    return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none'; };
  const out = [];
  for (const e of document.querySelectorAll('button,[role=button],a,input,textarea,select,[role=tab],[role=menuitem],[tabindex]')) {
    if (!vis(e)) continue;
    const r = e.getBoundingClientRect();
    const label = (e.getAttribute('aria-label') || e.innerText || e.value || e.placeholder || e.title || '').trim().replace(/\\s+/g, ' ').slice(0, 80);
    if (!label && e.tagName !== 'INPUT' && e.tagName !== 'TEXTAREA') continue;
    out.push({ tag: e.tagName.toLowerCase(), role: e.getAttribute('role'), label, testid: e.getAttribute('data-testid'),
      x: Math.round(r.x + r.width / 2), y: Math.round(r.y + r.height / 2) });
  }
  return out;
})()`;

async function click(c, pattern) {
  const items = await evaluate(c, UI_JS);
  const re = new RegExp(pattern, "i");
  const hit = items.find((i) => re.test(i.label) || (i.testid && re.test(i.testid)));
  if (!hit) throw new Error(`no visible element matches ${pattern}`);
  for (const type of ["mousePressed", "mouseReleased"]) {
    await c.send("Input.dispatchMouseEvent", { type, x: hit.x, y: hit.y, button: "left", clickCount: 1 });
  }
  return hit;
}

const c = cmd === "targets" ? null : await connect();
try {
  switch (cmd) {
    case "targets":
      console.log(JSON.stringify(await targets(), null, 1));
      break;
    case "eval":
      console.log(JSON.stringify(await evaluate(c, args.join(" ")), null, 1));
      break;
    case "ui":
      for (const i of await evaluate(c, UI_JS)) console.log(JSON.stringify(i));
      break;
    case "text":
      console.log(await evaluate(c, "document.body.innerText"));
      break;
    case "click":
      console.log(JSON.stringify(await click(c, args.join(" "))));
      break;
    case "type":
      await c.send("Input.insertText", { text: args.join(" ") });
      break;
    case "key": {
      const key = args[0];
      for (const type of ["keyDown", "keyUp"]) {
        await c.send("Input.dispatchKeyEvent", { type, key, code: key, windowsVirtualKeyCode: key === "Enter" ? 13 : key === "Escape" ? 27 : key === "Tab" ? 9 : 0 });
      }
      break;
    }
    case "shot": {
      const r = await c.send("Page.captureScreenshot", { format: "png" });
      writeFileSync(args[0], Buffer.from(r.data, "base64"));
      break;
    }
    default:
      console.error("unknown command");
      process.exitCode = 64;
  }
} finally {
  c?.close();
}
