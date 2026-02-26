import fs from "node:fs/promises";
import path from "node:path";

const DEFAULT_MAX_CHARS = 8000;

function coerceText(value: unknown): string {
  if (typeof value !== "string") return "";
  return value.replace(/\r\n/g, "\n").trim();
}

function clampText(text: string, maxChars: number): string {
  if (text.length <= maxChars) return text;
  return `${text.slice(0, maxChars)}\n\n[truncated ${text.length - maxChars} chars]`;
}

function toDate(ts: unknown): Date {
  if (ts instanceof Date && !Number.isNaN(ts.getTime())) return ts;
  if (typeof ts === "number") {
    const d = new Date(ts);
    if (!Number.isNaN(d.getTime())) return d;
  }
  return new Date();
}

const handler = async (event: any) => {
  if (event?.type !== "message") return;

  const action = event?.action;
  if (action !== "received" && action !== "sent") return;

  const ctx = event?.context ?? {};
  const raw = coerceText(ctx.content);
  if (!raw) return;

  const maxChars = Number(process.env.MEMORY_JOURNAL_MAX_CHARS || DEFAULT_MAX_CHARS);
  const safeMaxChars = Number.isFinite(maxChars) && maxChars > 0 ? Math.floor(maxChars) : DEFAULT_MAX_CHARS;
  const content = clampText(raw, safeMaxChars);

  const ts = toDate(event?.timestamp);
  const iso = ts.toISOString();
  const day = iso.slice(0, 10);

  const workspaceDir =
    (typeof ctx.workspaceDir === "string" && ctx.workspaceDir.trim()) ||
    process.env.OPENCLAW_WORKSPACE ||
    process.cwd();

  const journalDir = path.join(workspaceDir, "memory", "chat-journal");
  const journalFile = path.join(journalDir, `${day}.md`);

  const direction = action === "received" ? "IN" : "OUT";
  const peer = action === "received" ? (ctx.from || "unknown") : (ctx.to || "unknown");
  const channel = ctx.channelId || "unknown";
  const account = ctx.accountId ? ` account=${ctx.accountId}` : "";

  const block = [
    `## ${iso} ${direction} channel=${channel}${account} peer=${peer}`,
    "",
    content,
    "",
  ].join("\n");

  await fs.mkdir(journalDir, { recursive: true });
  await fs.appendFile(journalFile, block, "utf8");
};

export default handler;
