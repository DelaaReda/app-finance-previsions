import { useEffect, useState } from 'react';
import { Badge, Box, Button, Group, ScrollArea, Text } from '@mantine/core';

const DEBUG_FLAG = ((import.meta.env.VITE_APP_DEBUG ?? '0')).toString() !== '0';
const DEBUG_EVENT = 'finance-debug:event';
type DebugEventDetail = {
  type: 'http';
  url: string;
  method: string;
  message: string;
  status?: number;
};

type DebugEntry = {
  id: number;
  timestamp: string;
  summary: string;
  detail?: string;
};

const formatter = new Intl.DateTimeFormat(undefined, {
  hour: '2-digit',
  minute: '2-digit',
  second: '2-digit',
});

let entryId = 0;

export default function DevDebugPanel() {
  const [entries, setEntries] = useState<DebugEntry[]>([]);
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    if (!DEBUG_FLAG) return;

    const addEntry = (summary: string, detail?: string) => {
      const ts = formatter.format(new Date());
      setEntries((prev) => {
        const next = [{ id: ++entryId, timestamp: ts, summary, detail }, ...prev];
        return next.slice(0, 8);
      });
    };

    const handleHttpEvent = (event: Event) => {
      const detail = (event as CustomEvent<DebugEventDetail>).detail;
      if (!detail) return;
      addEntry(
        `[HTTP ${detail.status ?? 'ERR'}] ${detail.method} ${detail.url}`,
        detail.message,
      );
    };

    const handleError = (event: ErrorEvent) => {
      addEntry(`Runtime error: ${event.message}`, event.filename);
    };

    const handleRejection = (event: PromiseRejectionEvent) => {
      addEntry('Unhandled rejection', String(event.reason));
    };

    window.addEventListener(DEBUG_EVENT, handleHttpEvent as EventListener);
    window.addEventListener('error', handleError);
    window.addEventListener('unhandledrejection', handleRejection);

    return () => {
      window.removeEventListener(DEBUG_EVENT, handleHttpEvent as EventListener);
      window.removeEventListener('error', handleError);
      window.removeEventListener('unhandledrejection', handleRejection);
    };
  }, []);

  const latestSummary = entries[0]?.summary ?? 'No errors captured yet';

  if (!DEBUG_FLAG) {
    return null;
  }

  return (
    <Box
      style={{
        position: 'fixed',
        bottom: 24,
        right: 24,
        zIndex: 4000,
        width: expanded ? 420 : 280,
        background: 'rgba(15, 23, 42, 0.9)',
        border: '1px solid rgba(255,255,255,0.2)',
        borderRadius: 12,
        padding: 16,
        boxShadow: '0 12px 38px rgba(0,0,0,0.35)',
        color: '#fff',
        backdropFilter: 'blur(12px)',
      }}
    >
      <Group justify="space-between" align="flex-start">
        <div>
          <Group gap="xs">
            <Badge color="yellow" variant="light">DEV DEBUG</Badge>
            <Badge color={entries.length ? 'red' : 'gray'} variant="dot">
              {entries.length ? `${entries.length} issue${entries.length > 1 ? 's' : ''}` : 'idle'}
            </Badge>
          </Group>
          <Text mt={6} fz="sm" fw={500}>
            {latestSummary}
          </Text>
        </div>
        <Group gap="xs">
          <Button
            size="xs"
            variant="light"
            color="gray"
            onClick={() => setEntries([])}
          >
            Clear
          </Button>
          <Button
            size="xs"
            variant="filled"
            color="yellow"
            onClick={() => setExpanded((prev) => !prev)}
          >
            {expanded ? 'Hide' : 'Details'}
          </Button>
        </Group>
      </Group>

      {expanded && (
        <ScrollArea mt="md" mah={200}>
          {entries.length === 0 && (
            <Text fz="sm" c="dimmed">
              Waiting for network or runtime errors…
            </Text>
          )}
          {entries.map((entry) => (
            <Box key={entry.id} mb="sm">
              <Text fz="xs" c="dimmed">{entry.timestamp}</Text>
              <Text fz="sm" fw={500}>{entry.summary}</Text>
              {entry.detail && (
                <Text fz="xs" c="gray.4" style={{ whiteSpace: 'pre-wrap' }}>
                  {entry.detail}
                </Text>
              )}
            </Box>
          ))}
        </ScrollArea>
      )}
    </Box>
  );
}
