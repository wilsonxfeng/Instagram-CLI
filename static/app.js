const output = document.getElementById("output");
const promptEl = document.getElementById("prompt");
const form = document.getElementById("command-form");
const input = document.getElementById("command-input");

let inboxCache = [];
let currentThread = null;
let currentUsers = {};
let meId = null;

function printLine(text, kind = "") {
  const line = document.createElement("div");
  line.className = `line ${kind}`.trim();
  line.textContent = text;
  output.appendChild(line);
  output.scrollTop = output.scrollHeight;
}

function setPrompt() {
  if (currentThread) {
    promptEl.textContent = `ig/${currentThread.title}/>`;
  } else {
    promptEl.textContent = "ig/>";
  }
}

async function fetchMe() {
  try {
    const res = await fetch("/api/me");
    if (res.ok) {
      const data = await res.json();
      meId = data.user_id;
    }
  } catch (err) {
    printLine("failed to reach backend", "warn");
  }
}

function indexToThread(index) {
  const idx = Number(index) - 1;
  if (Number.isNaN(idx) || idx < 0 || idx >= inboxCache.length) {
    return null;
  }
  return inboxCache[idx];
}

function formatUserMap(thread) {
  const map = {};
  for (const u of thread.users || []) {
    map[String(u.id)] = u.username;
  }
  return map;
}

async function cmdInbox(amount = 10) {
  printLine("fetching inbox...", "muted");
  const res = await fetch(`/api/inbox?amount=${amount}`);
  if (!res.ok) {
    printLine("failed to fetch inbox", "warn");
    return;
  }
  const data = await res.json();
  inboxCache = data;
  if (data.length === 0) {
    printLine("inbox empty");
    return;
  }
  data.forEach((t, i) => {
    const last = t.last_text ? ` - ${t.last_text}` : "";
    printLine(`[${i + 1}] ${t.title}${last}`);
  });
}

async function cmdOpen(index) {
  const thread = indexToThread(index);
  if (!thread) {
    printLine("invalid index", "warn");
    return;
  }
  currentThread = thread;
  currentUsers = formatUserMap(thread);
  setPrompt();
  printLine(`opened: ${thread.title}`, "muted");
}

async function cmdRead(amount = 20) {
  if (!currentThread) {
    printLine("open a thread first", "warn");
    return;
  }
  const res = await fetch(
    `/api/thread/${currentThread.id}?amount=${amount}`
  );
  if (!res.ok) {
    printLine("failed to fetch thread", "warn");
    return;
  }
  const messages = await res.json();
  for (const m of messages) {
    const sender =
      String(m.user_id) === String(meId)
        ? "me"
        : currentUsers[String(m.user_id)] || m.user_id;
    const text = m.text || "";
    printLine(`${m.timestamp} ${sender}: ${text}`);
  }
}

async function cmdSend(text) {
  if (!currentThread) {
    printLine("open a thread first", "warn");
    return;
  }
  if (!text.trim()) {
    printLine("usage: send <message>", "warn");
    return;
  }
  const res = await fetch("/api/send", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ thread_id: currentThread.id, text }),
  });
  if (!res.ok) {
    printLine("failed to send message", "warn");
    return;
  }
  printLine("sent", "muted");
}

function cmdHelp() {
  printLine("commands:", "muted");
  printLine("help");
  printLine("inbox [n]");
  printLine("open <index>");
  printLine("read [n]");
  printLine("send <message>");
  printLine("back");
  printLine("quit");
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const raw = input.value.trim();
  if (!raw) return;
  printLine(`${promptEl.textContent} ${raw}`, "muted");
  input.value = "";

  const [command, ...args] = raw.split(" ");
  switch (command) {
    case "help":
      cmdHelp();
      break;
    case "inbox": {
      const amount = args[0] ? Number(args[0]) : 10;
      await cmdInbox(Number.isNaN(amount) ? 10 : amount);
      break;
    }
    case "open":
      await cmdOpen(args[0]);
      break;
    case "read": {
      const amount = args[0] ? Number(args[0]) : 20;
      await cmdRead(Number.isNaN(amount) ? 20 : amount);
      break;
    }
    case "send":
      await cmdSend(args.join(" "));
      break;
    case "back":
      currentThread = null;
      currentUsers = {};
      setPrompt();
      printLine("thread cleared", "muted");
      break;
    case "quit":
    case "exit":
      printLine("close this tab to exit.", "muted");
      break;
    default:
      printLine("unknown command. type 'help'", "warn");
  }
});

setPrompt();
fetchMe();
