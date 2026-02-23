#!/usr/bin/env node

import {
  query,
  isSDKAssistantMessage,
  isSDKResultMessage,
  isSDKPartialAssistantMessage,
  isAbortError,
} from "@qwen-code/sdk";

function parseArgs(argv) {
  const out = {};
  for (let i = 2; i < argv.length; i += 1) {
    const token = argv[i];
    if (!token.startsWith("--")) {
      continue;
    }
    const key = token.slice(2);
    const next = argv[i + 1];
    if (!next || next.startsWith("--")) {
      out[key] = true;
      continue;
    }
    out[key] = next;
    i += 1;
  }
  return out;
}

function toText(value) {
  if (value == null) {
    return "";
  }
  if (typeof value === "string") {
    return value;
  }
  if (Array.isArray(value)) {
    return value
      .map((item) => toText(item))
      .filter(Boolean)
      .join("\n")
      .trim();
  }
  if (typeof value === "object") {
    if (typeof value.text === "string") {
      return value.text;
    }
    if (value.content !== undefined) {
      return toText(value.content);
    }
    if (value.message !== undefined) {
      return toText(value.message);
    }
  }
  return "";
}

function compactParts(parts) {
  const cleaned = [];
  for (const part of parts) {
    const txt = String(part || "").trim();
    if (!txt) {
      continue;
    }
    if (cleaned.length > 0 && cleaned[cleaned.length - 1] === txt) {
      continue;
    }
    cleaned.push(txt);
  }
  return cleaned;
}

async function main() {
  const args = parseArgs(process.argv);
  const prompt = String(args.prompt || "").trim();
  if (!prompt) {
    throw new Error("--prompt est obligatoire");
  }

  const cwd = String(args.cwd || process.cwd());
  const permissionMode = String(args["permission-mode"] || "default");
  const model = String(args.model || "").trim();
  const debug = Boolean(args.debug);
  const pathToQwenExecutable = String(args["path-to-qwen-executable"] || "").trim();
  const timeoutSec = Math.max(0, Number(args["timeout-sec"] || "0"));
  const resume = String(args.resume || "").trim();
  const sessionIdArg = String(args["session-id"] || "").trim();
  const maxSessionTurns = Number(args["max-session-turns"] || "-1");

  const abortController = new AbortController();
  let timer = null;
  if (timeoutSec > 0) {
    timer = setTimeout(() => abortController.abort(), timeoutSec * 1000);
  }

  const options = {
    cwd,
    permissionMode,
    abortController,
    includePartialMessages: false,
  };

  if (model) {
    options.model = model;
  }
  if (debug) {
    options.debug = true;
  }
  if (pathToQwenExecutable) {
    options.pathToQwenExecutable = pathToQwenExecutable;
  }
  if (resume) {
    options.resume = resume;
  }
  if (sessionIdArg) {
    options.sessionId = sessionIdArg;
  }
  if (Number.isFinite(maxSessionTurns) && maxSessionTurns > 0) {
    options.maxSessionTurns = Math.floor(maxSessionTurns);
  }

  const q = query({ prompt, options });
  const assistantParts = [];
  let result = null;
  let messages = 0;

  try {
    for await (const message of q) {
      messages += 1;
      if (isSDKAssistantMessage(message) || isSDKPartialAssistantMessage(message)) {
        const txt = toText(message?.message?.content);
        if (txt) {
          assistantParts.push(txt);
        }
      } else if (isSDKResultMessage(message)) {
        result = message.result ?? null;
      }
    }
  } finally {
    if (timer) {
      clearTimeout(timer);
    }
    if (typeof q.close === "function") {
      await q.close().catch(() => {});
    }
  }

  const sessionId = typeof q.getSessionId === "function" ? q.getSessionId() : null;
  const assistant = compactParts(assistantParts).join("\n").trim();

  process.stdout.write(
    `${JSON.stringify({
      ok: true,
      assistant,
      result,
      sessionId,
      messages,
    })}\n`,
  );
}

main().catch((error) => {
  const isAbort = isAbortError(error);
  const payload = {
    ok: false,
    error: isAbort ? "abort" : String(error?.message || error),
    detail: String(error?.stack || ""),
  };
  process.stdout.write(`${JSON.stringify(payload)}\n`);
  process.exit(1);
});
