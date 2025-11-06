import { API_BASE } from '@/config/env';

type CopilotChunk = {
  delta?: string;
  done?: boolean;
  error?: string;
};

export async function askCopilotStream(
  body: { prompt: string; context?: any },
  onDelta: (text: string) => void,
  opts?: { signal?: AbortSignal; onDone?: () => void; onError?: (e: any) => void },
) {
  try {
    const res = await fetch(`${API_BASE}/copilot/ask`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      signal: opts?.signal,
    });

    if (!res.ok || !res.body) {
      throw new Error(`Copilot HTTP ${res.status}`);
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      const parts = buffer.split(/\n\n|\r\n\r\n/);
      buffer = parts.pop() || '';

      for (const chunk of parts) {
        const line = chunk.trim().startsWith('data:')
          ? chunk.trim().replace(/^data:\s*/, '')
          : chunk.trim();
        if (!line) continue;
        try {
          const json = JSON.parse(line) as CopilotChunk;
          if (json.delta) onDelta(json.delta);
          if (json.done) { opts?.onDone?.(); return; }
          if (json.error) throw new Error(json.error);
        } catch {
          onDelta(line);
        }
      }
    }

    opts?.onDone?.();
  } catch (error) {
    opts?.onError?.(error);
    throw error;
  }
}

