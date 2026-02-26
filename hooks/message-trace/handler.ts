import fs from "node:fs/promises";
import path from "node:path";

const OWNER_NUMBER = "+14389799898";
const MAX_ITEMS = 5;
const MAX_MESSAGE_CHARS = 500;

function normalizeText(input: unknown): string {
  if (typeof input !== "string") return "";
  return input.replace(/\s+/g, " ").trim();
}

function truncate(text: string, max: number): string {
  if (text.length <= max) return text;
  return text.slice(0, max - 3) + "...";
}

function contentText(message: any): string {
  const blocks = Array.isArray(message?.content) ? message.content : [];
  const parts: string[] = [];
  for (const b of blocks) {
    if (b?.type === "text" && typeof b?.text === "string") parts.push(b.text);
  }
  return normalizeText(parts.join("\n"));
}

function addSet(set: Set<string>, value: unknown) {
  const v = normalizeText(value);
  if (v) set.add(v);
}

function joinList(values: Set<string>, maxItems = MAX_ITEMS): string {
  const arr = Array.from(values);
  if (!arr.length) return "none";
  const cut = arr.slice(0, maxItems);
  let out = cut.join(", ");
  if (arr.length > maxItems) out += ", +" + String(arr.length - maxItems);
  return out;
}

function summarizeExec(command: string): string {
  const cmd = normalizeText(command);
  if (!cmd) return "exec";
  const parts = cmd.split(/[;\n]+/).map((p) => p.trim()).filter(Boolean);
  const tokens: string[] = [];
  for (const p of parts) {
    const first = p.split(/\s+/)[0] || "";
    if (!first) continue;
    if (["set", "export", "cd", "echo"].includes(first)) continue;
    if (!tokens.includes(first)) tokens.push(first);
    if (tokens.length >= 3) break;
  }
  if (!tokens.length) return "exec";
  return "exec:" + tokens.join("+");
}

function findAssistantIndex(records: any[], outboundText: string): number {
  const target = normalizeText(outboundText);
  if (!target) return -1;

  for (let i = records.length - 1; i >= 0; i--) {
    const rec = records[i];
    if (rec?.type !== "message") continue;
    const msg = rec?.message;
    if (msg?.role !== "assistant") continue;

    const text = contentText(msg);
    if (!text) continue;
    if (text === target) return i;
    if (text.includes(target) || target.includes(text)) return i;
  }
  return -1;
}

function findTurnStart(records: any[], endIdx: number): number {
  for (let i = endIdx - 1; i >= 0; i--) {
    const rec = records[i];
    if (rec?.type !== "message") continue;
    const role = rec?.message?.role;
    if (role === "user") return i + 1;
  }
  return 0;
}

function hostFromUrl(urlRaw: string): string {
  try {
    const u = new URL(urlRaw);
    return u.host + u.pathname;
  } catch {
    return truncate(urlRaw, 80);
  }
}

function collectTrace(records: any[], startIdx: number, endIdx: number) {
  const actions = new Set<string>();
  const filesChanged = new Set<string>();
  const filesRead = new Set<string>();
  const networkCalls = new Set<string>();

  for (let i = startIdx; i < endIdx; i++) {
    const rec = records[i];
    if (rec?.type !== "message") continue;
    const msg = rec?.message;
    if (msg?.role !== "assistant") continue;

    const blocks = Array.isArray(msg?.content) ? msg.content : [];
    for (const b of blocks) {
      if (b?.type !== "toolCall") continue;
      const name = normalizeText(b?.name);
      const args = b?.arguments || {};

      if (name === "exec") {
        actions.add(summarizeExec(String(args?.command || "")));
        continue;
      }

      if (name === "process") {
        const action = normalizeText(args?.action) || "process";
        actions.add("process:" + action);
        continue;
      }

      if (name === "read") {
        actions.add("read");
        addSet(filesRead, args?.path);
        continue;
      }

      if (name === "write" || name === "edit" || name === "apply_patch") {
        actions.add(name);
        addSet(filesChanged, args?.path);
        continue;
      }

      if (name === "web_fetch") {
        actions.add("web_fetch");
        const method = normalizeText(args?.method) || "GET";
        const url = normalizeText(args?.url);
        if (url) networkCalls.add(method + " " + hostFromUrl(url));
        continue;
      }

      if (name === "web_search") {
        actions.add("web_search");
        const q = normalizeText(args?.q || args?.query);
        if (q) networkCalls.add("SEARCH " + truncate(q, 60));
        continue;
      }

      if (name) actions.add(name);
    }
  }

  return { actions, filesChanged, filesRead, networkCalls };
}

async function resolveSessionFile(event: any): Promise<string | null> {
  const ctx = event?.context || {};
  const direct = normalizeText(ctx?.sessionFile);
  if (direct) return direct;

  const sessionKey = normalizeText(event?.sessionKey);
  if (!sessionKey) return null;

  const home = process.env.HOME || "/home/venom";
  const base = path.join(home, ".openclaw", "agents", "main", "sessions");
  const store = path.join(base, "sessions.json");

  try {
    const raw = await fs.readFile(store, "utf8");
    const map = JSON.parse(raw);
    const entry = map?.[sessionKey];
    const fromEntry = normalizeText(entry?.sessionFile);
    if (fromEntry) return fromEntry;

    const sessionId = normalizeText(entry?.sessionId);
    if (sessionId) return path.join(base, sessionId + ".jsonl");
  } catch {
    return null;
  }
  return null;
}

async function loadJsonl(filePath: string): Promise<any[]> {
  const raw = await fs.readFile(filePath, "utf8");
  return raw.split("\n").filter(Boolean).map((line) => {
    try { return JSON.parse(line); } catch { return null; }
  }).filter(Boolean) as any[];
}

const handler = async (event: any) => {
  if (event?.type !== "message" || event?.action !== "sent") return;

  const ctx = event?.context || {};
  if (normalizeText(ctx?.channelId) !== "whatsapp") return;
  if (!ctx?.success) return;
  if (normalizeText(ctx?.to) !== OWNER_NUMBER) return;

  const outbound = normalizeText(ctx?.content);
  if (!outbound) return;
  if (outbound.includes("Execution Trace")) return;

  const sessionFile = await resolveSessionFile(event);
  if (!sessionFile) return;

  const records = await loadJsonl(sessionFile);
  if (!records.length) return;

  const endIdx = findAssistantIndex(records, outbound);
  if (endIdx < 0) return;

  const startIdx = findTurnStart(records, endIdx);
  const trace = collectTrace(records, startIdx, endIdx);

  const hasTools =
    trace.actions.size > 0 ||
    trace.filesChanged.size > 0 ||
    trace.filesRead.size > 0 ||
    trace.networkCalls.size > 0;

  if (!hasTools) return;

  const lines = [
    "Execution Trace",
    "- Actions: " + joinList(trace.actions),
    "- Files changed: " + joinList(trace.filesChanged),
    "- Files read: " + joinList(trace.filesRead),
    "- Network/API calls: " + joinList(trace.networkCalls),
  ];

  event.messages.push(truncate(lines.join("\n"), MAX_MESSAGE_CHARS));
};

export default handler;
