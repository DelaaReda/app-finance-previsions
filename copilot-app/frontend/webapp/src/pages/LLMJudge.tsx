import { useEffect, useState } from 'react'
import { apiGet, apiPost } from '../api/client'
import {
  Accordion,
  Alert,
  Badge,
  Button,
  Card,
  Divider,
  Group,
  Progress,
  Select,
  Stack,
  Text,
  Textarea,
  Title,
} from '@mantine/core'

type JudgeModelRun = {
  model?: string | null
  provider?: string | null
  ok?: boolean
  latency_ms?: number | null
  attempt?: number | null
  answer?: string | null
  parsed?: unknown
  error?: string | null
}

type JudgeDebug = {
  models?: JudgeModelRun[]
  adjudication?: { decision?: string; judge_model?: string } | null
  avg_agreement?: number | null
  pairwise_agreement?: Array<{ model_i?: string; model_j?: string; agreement?: number }>
  context?: {
    tickers?: string[]
    stats?: { total?: number; high_conf_count?: number }
    deterministic_summary?: string
    attachments_preview?: Array<{ ticker?: string; date?: string; text?: string }>
    features?: Record<string, unknown>
    forecast_preview?: any[]
  }
}

type JudgeResponse = {
  stdout?: { context?: string; forecast?: string }
  rows?: any[]
  model_used?: string
  derived?: { stats?: { total?: number; high_conf_count?: number } }
  parameters?: { max_er?: number; min_conf?: number; tickers?: string[] }
  debug?: JudgeDebug
}

export default function LLMJudge() {
  const [model, setModel] = useState('deepseek-ai/DeepSeek-V3-0324-Turbo')
  const [tickers, setTickers] = useState('AAPL,MSFT,NGD.TO')
  const [busy, setBusy] = useState(false)
  const [out, setOut] = useState('')
  const [rowsCount, setRowsCount] = useState<number | null>(null)
  const [modelUsed, setModelUsed] = useState<string | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [debugInfo, setDebugInfo] = useState<JudgeDebug | null>(null)
  const [stats, setStats] = useState<{ total?: number; high_conf_count?: number } | null>(null)
  const [parameters, setParameters] = useState<{ max_er?: number; min_conf?: number; tickers?: string[] } | null>(null)
  const coveragePct =
    stats && typeof stats.total === 'number' && stats.total > 0
      ? Math.round(((stats.high_conf_count ?? 0) / stats.total) * 100)
      : null
  const modelRuns = debugInfo?.models ?? []
  const attachmentsPreview = debugInfo?.context?.attachments_preview ?? []
  const featuresEntries = debugInfo?.context?.features
    ? Object.entries(debugInfo.context.features).slice(0, 8)
    : []
  const forecastPreview = debugInfo?.context?.forecast_preview ?? []
  const deterministicSummary = debugInfo?.context?.deterministic_summary ?? ''
  const tickersList = parameters?.tickers ?? debugInfo?.context?.tickers ?? []
  const adjudication = debugInfo?.adjudication

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
      const res = await apiPost<JudgeResponse>(
        '/api/llm/judge/run',
        { model, max_er: 0.08, min_conf: 0.6, tickers },
        { timeoutMs: 60000 }
      )
      if (res.ok && res.data) {
        const ctx = res.data.stdout?.context ?? '—'
        const fc = res.data.stdout?.forecast ?? '—'
        const rows = Array.isArray(res.data.rows) ? res.data.rows : []
        setRowsCount(rows.length)
        setModelUsed(res.data.model_used ?? null)
        setDebugInfo(res.data.debug ?? null)
        setStats(res.data.derived?.stats ?? null)
        setParameters(res.data.parameters ?? null)
        setOut([ctx, '----', fc].join('\n'))
      } else {
        setRowsCount(null)
        setModelUsed(null)
        setDebugInfo(null)
        setStats(null)
        setParameters(null)
        const msg = res.error ?? 'Réponse invalide'
        setErr(msg)
        setOut('Erreur: ' + msg)
      }
    } catch (e: any) {
      setRowsCount(null)
      setDebugInfo(null)
      setStats(null)
      setParameters(null)
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
        <Text size="sm">•</Text>
        <Text size="sm">Model utilisé:</Text>
        <Badge variant="light" color="blue">{modelUsed ?? '—'}</Badge>
      </Group>
      <Textarea
        readOnly
        autosize
        minRows={8}
        maxRows={20}
        value={out || 'Cliquez sur Run pour exécuter le juge LLM.'}
      />
      {(coveragePct !== null || parameters) && (
        <Card shadow="sm" padding="md" withBorder>
          <Group justify="space-between" align="flex-start">
            <div>
              <Text size="sm" c="dimmed">Paramètres</Text>
              <Group gap="xs" mt={4}>
                <Badge color="blue" variant="light">max_er: {parameters?.max_er ?? '0.08'}</Badge>
                <Badge color="blue" variant="light">min_conf: {parameters?.min_conf ?? '0.6'}</Badge>
                <Badge color="blue" variant="light">{tickersList.length} tickers</Badge>
              </Group>
            </div>
            {coveragePct !== null && (
              <div style={{ minWidth: 200 }}>
                <Text size="sm" fw={600}>High confidence coverage</Text>
                <Progress mt={6} value={coveragePct} label={`${coveragePct}%`} />
              </div>
            )}
          </Group>
        </Card>
      )}

      {modelRuns.length > 0 && (
        <Card shadow="sm" padding="md" withBorder>
          <Group justify="space-between">
            <Title order={4}>Ensemble des modèles</Title>
            {typeof debugInfo?.avg_agreement === 'number' && (
              <Badge color="indigo" variant="light">Avg agreement {Math.round(debugInfo.avg_agreement * 100)}%</Badge>
            )}
          </Group>
          <Accordion variant="contained" mt="md">
            {modelRuns.map((run, idx) => (
              <Accordion.Item key={`run-${idx}`} value={`run-${idx}`}>
                <Accordion.Control>
                  <Group justify="space-between">
                    <div>
                      <Text fw={600}>{run.model ?? 'modèle inconnu'}</Text>
                      <Text size="xs" c="dimmed">{run.provider ?? 'EconomicAnalyst'}</Text>
                    </div>
                    <Group gap="xs">
                      {typeof run.latency_ms === 'number' && (
                        <Badge color="gray" variant="light">{run.latency_ms} ms</Badge>
                      )}
                      <Badge color={run.ok ? 'green' : 'red'} variant="filled">
                        {run.ok ? 'Succès' : 'Erreur'}
                      </Badge>
                    </Group>
                  </Group>
                </Accordion.Control>
                <Accordion.Panel>
                  <Text size="sm" fw={500}>Réponse</Text>
                  <Textarea readOnly value={run.answer || '(vide)'} autosize minRows={4} maxRows={12} mt="xs" />
                  {run.parsed && (
                    <>
                      <Divider my="sm" />
                      <Text size="sm" fw={500}>JSON parsé</Text>
                      <Textarea
                        readOnly
                        value={JSON.stringify(run.parsed, null, 2)}
                        autosize
                        minRows={4}
                        maxRows={12}
                        mt="xs"
                      />
                    </>
                  )}
                  {run.error && (
                    <Alert color="red" variant="light" mt="sm">
                      {run.error}
                    </Alert>
                  )}
                </Accordion.Panel>
              </Accordion.Item>
            ))}
          </Accordion>
        </Card>
      )}

      {adjudication && (
        <Card shadow="sm" padding="md" withBorder>
          <Title order={4}>Adjudication</Title>
          <Text size="sm" mt="xs">Judge model: <Badge>{adjudication.judge_model ?? 'n/a'}</Badge></Text>
          <Textarea readOnly value={adjudication.decision ?? '(aucune décision)'} autosize minRows={3} maxRows={10} mt="sm" />
        </Card>
      )}

      {(deterministicSummary || attachmentsPreview.length || featuresEntries.length) && (
        <Card shadow="sm" padding="md" withBorder>
          <Title order={4}>Context snapshot</Title>
          {deterministicSummary && (
            <>
              <Text size="sm" fw={600} mt="sm">Résumé déterministe</Text>
              <Textarea readOnly value={deterministicSummary} autosize minRows={3} maxRows={10} mt="xs" />
            </>
          )}
          {featuresEntries.length > 0 && (
            <>
              <Divider my="sm" />
              <Text size="sm" fw={600}>Features clés</Text>
              <Stack gap={4} mt="xs">
                {featuresEntries.map(([key, value]) => (
                  <Group key={key} justify="space-between">
                    <Text size="sm" c="dimmed">{key}</Text>
                    <Text size="sm" fw={600}>{String(value)}</Text>
                  </Group>
                ))}
              </Stack>
            </>
          )}
          {attachmentsPreview.length > 0 && (
            <>
              <Divider my="sm" />
              <Text size="sm" fw={600}>Attachments (preview)</Text>
              <Stack gap="sm" mt="xs">
                {attachmentsPreview.map((att, idx) => (
                  <Card key={`att-${idx}`} padding="sm" radius="md" withBorder>
                    <Group justify="space-between">
                      <Badge variant="light">{att.ticker ?? '—'}</Badge>
                      <Text size="xs" c="dimmed">{att.date ?? ''}</Text>
                    </Group>
                    <Text size="sm" mt="xs" c="dimmed" style={{ whiteSpace: 'pre-wrap' }}>{att.text ?? ''}</Text>
                  </Card>
                ))}
              </Stack>
            </>
          )}
          {forecastPreview.length > 0 && (
            <>
              <Divider my="sm" />
              <Text size="sm" fw={600}>Forecast preview</Text>
              <Textarea
                readOnly
                value={JSON.stringify(forecastPreview, null, 2)}
                autosize
                minRows={4}
                maxRows={12}
                mt="xs"
              />
            </>
          )}
        </Card>
      )}
    </Stack>
  )
}
