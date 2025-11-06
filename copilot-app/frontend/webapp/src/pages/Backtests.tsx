import { useMemo, useState } from 'react';
import { Card, Button, Grid, Title, Text, Loader, Badge } from '@/ui';
import { useAutoPresets } from '@/hooks/useAutoPresets';
import { AreaChart } from '@tremor/react';
import type { BacktestParams } from '@/services/backtests';
import { useBacktest } from '@/hooks/useBacktest';
import { ensureArray, nn } from '@/lib/safe';
import { useBacktestInsights } from '@/hooks/useBacktestInsights';

type Rule = 'momentum' | 'meanrev' | 'carry';

const DEFAULT_PARAMS: BacktestParams = {
  rule: 'momentum',
  horizon: '1m',
  lookback: 180,
  universe: ['SPY', 'QQQ'],
};

function parseCSV(input: string): string[] {
  return input
    .split(',')
    .map((s) => s.trim().toUpperCase())
    .filter(Boolean);
}

function pct(v: number, digits = 1) {
  if (Number.isFinite(v)) return `${(v * 100).toFixed(digits)}%`;
  return '—';
}

const PRESETS: Array<{ label: string; params: BacktestParams }> = [
  { label: 'Momentum Top-2 (SPY,QQQ)', params: { rule: 'momentum', horizon: '1m', lookback: 180, universe: ['SPY', 'QQQ'] } },
  { label: 'MeanRev Tech (AAPL,MSFT)', params: { rule: 'meanrev', horizon: '1m', lookback: 120, universe: ['AAPL', 'MSFT'] } },
  { label: 'Carry LargeCap (SPY,DIA)', params: { rule: 'carry', horizon: '3m', lookback: 360, universe: ['SPY', 'DIA'] } },
  { label: 'Momentum Growth (QQQ,NVDA)', params: { rule: 'momentum', horizon: '3m', lookback: 240, universe: ['QQQ', 'NVDA'] } },
];

export default function BacktestsPage() {
  const [draft, setDraft] = useState<BacktestParams>(DEFAULT_PARAMS);
  const [active, setActive] = useState<BacktestParams>(DEFAULT_PARAMS);
  const [question, setQuestion] = useState('');

  const { data, isLoading, isFetching, error, refetch } = useBacktest(active, true);
  const [wantAuto, setWantAuto] = useState(false);
  const { data: autoPresets, isFetching: isAutoLoading, refetch: refetchAuto } =
    useAutoPresets({ universe: draft.universe, target: 'balanced' }, wantAuto);

  const equityDataset = useMemo(() => {
    return ensureArray(data?.equity).map((point) => ({
      date: point.t,
      equity: point.v,
    }));
  }, [data]);

  const summary = data?.summary;

  const insightsInput = summary
    ? { summary, params: { ...active }, question: question.trim() || undefined }
    : null;
  const { data: insight, isFetching: isThinking } = useBacktestInsights(insightsInput, Boolean(summary));

  function onRun() {
    setActive(draft);
    setTimeout(() => refetch(), 0);
  }

  function onExportCSV() {
    const rows = [['date', 'equity'], ...ensureArray(data?.equity).map((p) => [p.t, String(p.v)])];
    const csv = rows.map((r) => r.join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    const name = `${active.rule}_${active.horizon}_${active.universe.join('-')}.csv`;
    a.download = `backtest_${name}`;
    a.click();
    URL.revokeObjectURL(url);
  }

  function applyPreset(params: BacktestParams) {
    setDraft(params);
    setActive(params);
    setTimeout(() => refetch(), 0);
  }

  return (
    <div data-testid="page-backtests" style={{ display: 'grid', gap: 16 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Title order={2}>🧪 Backtests</Title>
        <div style={{ display: 'flex', gap: 8 }}>
          <Button variant="default" onClick={onRun} data-testid="btn-run" disabled={isFetching}>
            Lancer le backtest
          </Button>
          <Button
            variant="light"
            onClick={onExportCSV}
            data-testid="btn-export-csv"
            disabled={!data || ensureArray(data?.equity).length === 0}
          >
            Export CSV
          </Button>
        </div>
      </div>

      <Card withBorder>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8 }}>
          <Title order={4} style={{ marginBottom: 8 }}>Presets (1-clic)</Title>
          <div style={{ display: 'flex', gap: 8 }}>
            <Button
              size="xs"
              variant="light"
              data-testid="btn-auto-presets"
              onClick={() => {
                setWantAuto(true);
                refetchAuto();
              }}
              disabled={isAutoLoading}
            >
              {isAutoLoading ? 'Génération…' : 'Générer 5 presets auto'}
            </Button>
          </div>
        </div>

        {/* Auto presets if available */}
        {!!autoPresets?.length && (
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 8 }} data-testid="auto-presets">
            {autoPresets.map((p) => (
              <Button
                key={p.label}
                size="xs"
                variant="default"
                onClick={() => applyPreset(p)}
                data-testid={`auto-preset-${p.label}`}
              >
                {p.label}
              </Button>
            ))}
          </div>
        )}

        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }} data-testid="presets-bar">
          {PRESETS.map((preset) => (
            <Button
              key={preset.label}
              size="xs"
              variant="light"
              onClick={() => applyPreset(preset.params)}
              data-testid={`preset-${preset.label}`}
            >
              {preset.label}
            </Button>
          ))}
        </div>
      </Card>

      <Card withBorder>
        <div style={{ display: 'grid', gap: 12 }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, minmax(0, 1fr))', gap: 12 }}>
            <div>
              <label style={{ display: 'block', fontSize: 12, opacity: 0.7, marginBottom: 6 }}>Règle</label>
              <select
                data-testid="sel-rule"
                value={draft.rule}
                onChange={(e) => setDraft((d) => ({ ...d, rule: e.target.value as Rule }))}
                style={{
                  width: '100%',
                  padding: 8,
                  borderRadius: 8,
                  background: '#1f2937',
                  border: '1px solid #374151',
                  color: 'white',
                }}
              >
                <option value="momentum">momentum</option>
                <option value="meanrev">meanrev</option>
                <option value="carry">carry</option>
              </select>
            </div>

            <div>
              <label style={{ display: 'block', fontSize: 12, opacity: 0.7, marginBottom: 6 }}>Horizon</label>
              <select
                data-testid="sel-horizon"
                value={draft.horizon}
                onChange={(e) => setDraft((d) => ({ ...d, horizon: e.target.value as BacktestParams['horizon'] }))}
                style={{
                  width: '100%',
                  padding: 8,
                  borderRadius: 8,
                  background: '#1f2937',
                  border: '1px solid #374151',
                  color: 'white',
                }}
              >
                <option value="1m">1 mois</option>
                <option value="3m">3 mois</option>
                <option value="6m">6 mois</option>
              </select>
            </div>

            <div>
              <label style={{ display: 'block', fontSize: 12, opacity: 0.7, marginBottom: 6 }}>Lookback (jours)</label>
              <input
                data-testid="inp-lookback"
                type="number"
                value={draft.lookback}
                min={30}
                max={2000}
                onChange={(e) =>
                  setDraft((d) => ({ ...d, lookback: Math.max(30, Math.min(2000, Number(e.target.value))) }))
                }
                style={{
                  width: '100%',
                  padding: 8,
                  borderRadius: 8,
                  background: '#1f2937',
                  border: '1px solid #374151',
                  color: 'white',
                }}
              />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: 12, opacity: 0.7, marginBottom: 6 }}>Univers (CSV)</label>
              <input
                data-testid="inp-universe"
                type="text"
                value={draft.universe.join(',')}
                onChange={(e) => setDraft((d) => ({ ...d, universe: parseCSV(e.target.value) }))}
                placeholder="SPY,QQQ,AAPL"
                style={{
                  width: '100%',
                  padding: 8,
                  borderRadius: 8,
                  background: '#1f2937',
                  border: '1px solid #374151',
                  color: 'white',
                }}
              />
            </div>
          </div>

          <Text size="sm" c="dimmed">
            Astuce : garde l’univers compact (2–20 tickers) pour des itérations rapides.
          </Text>
        </div>
      </Card>

      {(isLoading || isFetching) && <Loader />}

      {error && (
        <Card withBorder>
          <Text c="red">{String(error)}</Text>
        </Card>
      )}

      {summary && (
        <Grid>
          <Card withBorder>
            <Title order={4}>Résumé</Title>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, minmax(0, 1fr))', gap: 12, marginTop: 12 }}>
              <Stat label="CAGR" value={pct(nn(summary.cagr, 0))} color="teal" />
              <Stat label="Max Drawdown" value={pct(nn(summary.maxDD, 0))} color="red" />
              <Stat label="Win Rate" value={pct(nn(summary.winRate, 0))} color="indigo" />
              <Stat label="Trades" value={String(nn(summary.trades, 0))} color="gray" />
            </div>
          </Card>

          <Card withBorder>
            <Title order={4}>Courbe d’équité</Title>
            {equityDataset.length === 0 ? (
              <Text c="dimmed" style={{ marginTop: 8 }}>
                Aucune donnée d’équité retournée.
              </Text>
            ) : (
              <AreaChart
                className="h-80"
                data={equityDataset}
                index="date"
                categories={['equity']}
                valueFormatter={(value) => String(value)}
                yAxisWidth={56}
              />
            )}
          </Card>
        </Grid>
      )}

      {summary && (
        <Card withBorder data-testid="card-insights">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
            <Title order={4}>Interprétation (Copilot)</Title>
            <div style={{ display: 'flex', gap: 8 }}>
              <input
                data-testid="inp-question"
                type="text"
                placeholder="Pose une question (ex: est-ce robuste si j’ajoute AAPL ?)"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                style={{
                  width: 360,
                  padding: 8,
                  borderRadius: 8,
                  background: '#111827',
                  border: '1px solid #374151',
                  color: 'white',
                }}
              />
              <Button
                variant="default"
                onClick={() => setQuestion((q) => q.trim())}
                disabled={isThinking}
                data-testid="btn-ask"
              >
                Demander
              </Button>
            </div>
          </div>

          {isThinking && <Loader />}

          {!isThinking && (
            <pre
              data-testid="txt-insight"
              style={{
                margin: 0,
                whiteSpace: 'pre-wrap',
                background: '#0b1220',
                padding: 12,
                borderRadius: 8,
                border: '1px solid #1f2937',
                fontSize: 14,
                lineHeight: 1.5,
              }}
            >
              {insight?.text || '—'}
            </pre>
          )}

          <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
            <Button
              size="xs"
              variant="light"
              onClick={() => {
                if (insight?.text) {
                  navigator.clipboard?.writeText(insight.text);
                }
              }}
              data-testid="btn-copy-insight"
            >
              Copier
            </Button>
          </div>
        </Card>
      )}

      {!error && !isLoading && !isFetching && !summary && (
        <Card withBorder>
          <Text c="dimmed">Configure tes paramètres ou clique un preset, puis lance un backtest.</Text>
        </Card>
      )}
    </div>
  );
}

function Stat({ label, value, color }: { label: string; value: string; color: 'teal' | 'red' | 'indigo' | 'gray' }) {
  return (
    <div style={{ display: 'grid', gap: 6 }}>
      <Text size="sm" c="dimmed">
        {label}
      </Text>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <Title order={3}>{value}</Title>
        <Badge color={color} variant="light">
          {label}
        </Badge>
      </div>
    </div>
  );
}
