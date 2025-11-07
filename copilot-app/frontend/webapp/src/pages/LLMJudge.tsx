import { useEffect, useState } from 'react'
import { apiGet, apiPost } from '../api/client'
import { Alert, Badge, Button, Group, Select, Stack, Text, Textarea, Title } from '@mantine/core'

export default function LLMJudge() {
  const [model, setModel] = useState('deepseek-ai/DeepSeek-V3-0324-Turbo')
  const [tickers, setTickers] = useState('AAPL,MSFT,NGD.TO')
  const [busy, setBusy] = useState(false)
  const [out, setOut] = useState('')
  const [rowsCount, setRowsCount] = useState<number | null>(null)
  const [err, setErr] = useState<string | null>(null)

  // Working models for quick selection (top3 + ranked)
  const [models, setModels] = useState<string[]>([])
  const [top3, setTop3] = useState<string[]>([])

  const loadWorking = async () => {
    try {
      const res = await apiGet<any>('/api/llm/providers/working?limit=20')
      if (res.ok && res.data) {
        const t3: string[] = Array.isArray(res.data.top3) ? res.data.top3.filter(Boolean) : []
        const ranked: string[] = Array.isArray(res.data.ranked) ? res.data.ranked.map((r: any) => r?.model).filter(Boolean) : []
        const seen = new Set<string>()
        const combined = [...t3, ...ranked].filter((m) => (m && !seen.has(m) ? (seen.add(m), true) : false))
        setTop3(t3)
        setModels(combined)
        // If current model not in list, keep it but append
        if (!combined.includes(model)) setModels([model, ...combined])
      }
    } catch (e) {
      // ignore fetch errors
    }
  }

  useEffect(() => {
    loadWorking()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const [refreshBusy, setRefreshBusy] = useState(false)
  const refreshProviders = async () => {
    setRefreshBusy(true)
    setErr(null)
    try {
      await apiPost('/api/llm/providers/refresh', {
        limit: 20,
        refresh_verified: false,
        merge_remote: true,
      })
      await loadWorking()
    } catch (e: any) {
      setErr(e?.message ?? String(e))
    }
    setRefreshBusy(false)
  }

  const run = async () => {
    setBusy(true)
    setOut('(running…)')
    setErr(null)
    try {
      const res = await apiPost<{ stdout?: { context?: string; forecast?: string }; rows?: any[] }>(
        '/api/llm/judge/run',
        { model, max_er: 0.08, min_conf: 0.6, tickers }
      )
      if (res.ok && res.data) {
        const ctx = res.data.stdout?.context ?? '—'
        const fc = res.data.stdout?.forecast ?? '—'
        const rows = Array.isArray(res.data.rows) ? res.data.rows : []
        setRowsCount(rows.length)
        setOut([ctx, '----', fc].join('\n'))
      } else {
        setRowsCount(null)
        const msg = res.error ?? 'Réponse invalide'
        setErr(msg)
        setOut('Erreur: ' + msg)
      }
    } catch (e: any) {
      setRowsCount(null)
      const msg = e?.message ?? String(e)
      setErr(msg)
      setOut('Erreur: ' + msg)
    }
    setBusy(false)
  }

  return (
    <Stack gap="md" data-testid="judge-root">
      <Title order={2}>LLM Judge</Title>
      {err && (
        <Alert color="red" title="Erreur" variant="light">{err}</Alert>
      )}
      <Group align="end" gap="md" wrap="wrap">
        <div style={{ minWidth: 360 }}>
          <Text size="sm" c="dimmed">Modèle</Text>
          <Select
            data={models.length ? models : [model]}
            value={model}
            searchable
            placeholder="Sélectionner un modèle G4F"
            onChange={(v) => setModel(v || model)}
            nothingFoundMessage={models.length ? 'Aucun' : 'Pas de modèles — rafraîchir les providers'}
          />
        </div>
        <div style={{ minWidth: 260 }}>
          <Text size="sm" c="dimmed">Tickers</Text>
          <Textarea autosize minRows={1} maxRows={3} value={tickers} onChange={(e) => setTickers(e.currentTarget.value)} />
        </div>
        <Group>
          <Button loading={busy} onClick={run}>Run</Button>
          <Button variant="light" loading={refreshBusy} onClick={refreshProviders}>Refresh providers</Button>
        </Group>
      </Group>
      {top3.length > 0 && (
        <Group gap="xs">
          <Text size="sm" c="dimmed">Top 3 (working):</Text>
          {top3.map((m) => (
            <Badge key={m} variant={m === model ? 'filled' : 'light'} onClick={() => setModel(m)} style={{ cursor: 'pointer' }}>{m}</Badge>
          ))}
        </Group>
      )}
      <Group gap="sm" align="center" c="dimmed">
        <Text size="sm">Rows:</Text>
        <Text size="sm" fw={700}>{rowsCount ?? '—'}</Text>
      </Group>
      <Textarea
        readOnly
        autosize
        minRows={8}
        maxRows={20}
        value={out || 'Cliquez sur Run pour exécuter le juge LLM.'}
      />
    </Stack>
  )
}
