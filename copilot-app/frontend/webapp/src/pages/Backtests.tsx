import { useMemo, useState } from 'react';
import {
  AreaChart,
  Badge,
  Button,
  Card,
  Grid,
  Loader,
  Text,
  Title,
} from '@/ui';
import { ensureArray, nn } from '@/lib/safe';
import type { BacktestParams } from '@/services/backtests';
import { useBacktest } from '@/hooks/useBacktest';
import { useBacktestInsights } from '@/hooks/useBacktestInsights';
import { useBacktestHistory } from '@/hooks/useBacktestHistory';
import type { BacktestSummary as ScoreSummary } from '@/lib/robustScore';
import RobustnessScoreCard from '@/components/metrics/RobustnessScoreCard';
import RobustnessHistoryCard from '@/components/metrics/RobustnessHistoryCard';
import PresetTunerPanel from '@/components/tuner/PresetTunerPanel';
import FullReportButton from '@/components/report/FullReportButton';
import ExportReportButton from '@/components/report/ExportReportButton';
import { useAutoPresets } from '@/hooks/useAutoPresets';

type Rule = 'momentum' | 'meanrev' | 'carry';

const DEFAULT_PARAMS: BacktestParams = {
  rule: 'momentum',
  horizon: '1m',
  lookback: 180,
  universe: ['SPY', 'QQQ'],
};

const PRESETS: Array<{ label: string; params: BacktestParams }> = [
  { label: 'Momentum Top-2 (SPY,QQQ)', params: { rule: 'momentum', horizon: '1m', lookback: 180, universe: ['SPY', 'QQQ'] } },
  { label: 'MeanRev Tech (AAPL,MSFT)', params: { rule: 'meanrev', horizon: '1m', lookback: 120, universe: ['AAPL', 'MSFT'] } },
  { label: 'Carry LargeCap (SPY,DIA)', params: { rule: 'carry', horizon: '3m', lookback: 360, universe: ['SPY', 'DIA'] } },
  { label: 'Momentum Growth (QQQ,NVDA)', params: { rule: 'momentum', horizon: '3m', lookback: 240, universe: ['QQQ', 'NVDA'] } },
];

const REPORT_SECTION_IDS = [
  'backtests-section-intro',
  'backtests-section-kpis',
  'backtests-section-history',
  'backtests-section-insights',
];

function parseCSV(input: string): string[] {
  return input
    .split(',')
    .map((token) => token.trim().toUpperCase())
    .filter(Boolean);
}

function pct(value: number, digits = 1) {
  if (Number.isFinite(value)) return `${(value * 100).toFixed(digits)}%`;
  return '—';
}

export default function BacktestsPage() {
  const [draft, setDraft] = useState<BacktestParams>(DEFAULT_PARAMS);
  const [active, setActive] = useState<BacktestParams>(DEFAULT_PARAMS);
  const [question, setQuestion] = useState('');
  const [autoRequested, setAutoRequested] = useState(false);

  const { data, isLoading, isFetching, error, refetch } = useBacktest(active, true);
  const autoPresetQuery = useAutoPresets({ universe: draft.universe, target: 'balanced' }, autoRequested);

  const summary = data?.summary;
  const summaryForScore: ScoreSummary | undefined = summary
    ? {
        cagr: summary.cagr ?? 0,
        maxDD: Math.abs(summary.maxDD ?? 0),
        winRate: summary.winRate ?? 0,
        trades: summary.trades ?? 0,
      }
    : undefined;

  const historyQuery = useBacktestHistory(
    {
      rule: active.rule,
      horizon: active.horizon,
      lookback: active.lookback,
      universe: active.universe,
    },
    Boolean(summary),
  );

  const equityDataset = useMemo(
    () =>
      ensureArray(data?.equity).map((point) => ({
        date: point.t,
        equity: point.v,
      })),
    [data],
  );

  const insightsInput = summary
    ? { summary, params: { ...active }, question: question.trim() || undefined }
    : null;
  const { data: insight, isFetching: isThinking } = useBacktestInsights(insightsInput, Boolean(summary));

  function onRun() {
    setActive(draft);
    setTimeout(() => refetch(), 0);
  }

  function onExportCSV() {
    const rows = [['date', 'equity'], ...ensureArray(data?.equity).map((point) => [point.t, String(point.v)])];
    const csv = rows.map((row) => row.join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    const name = `${active.rule}_${active.horizon}_${active.universe.join('-')}.csv`;
    anchor.download = `backtest_${name}`;
    anchor.click();
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
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', justifyContent: 'flex-end' }}>
          {summary && (
            <>
              <FullReportButton sectionIds={REPORT_SECTION_IDS} filename="backtests-report.pdf" />
              <ExportReportButton targetId="backtests-section-kpis" filename="backtests-kpis.pdf" />
            </>
          )}
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
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}>
          <Title order={4}>Presets (1-clic)</Title>
          <Button
            size="xs"
            variant="light"
            data-testid="btn-auto-presets"
            disabled={autoPresetQuery.isFetching}
            onClick={() => {
              setAutoRequested(true);
              autoPresetQuery.refetch();
            }}
          >
            {autoPresetQuery.isFetching ? 'Génération…' : 'Générer 5 presets auto'}
          </Button>
        </div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 12 }} data-testid="presets-bar">
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
          {ensureArray(autoPresetQuery.data).map((preset) => (
            <Button
              key={preset.label}
              size="xs"
              variant="default"
              onClick={() =>
                applyPreset({
                  rule: preset.rule,
                  horizon: preset.horizon,
                  lookback: preset.lookback,
                  universe: preset.universe,
                })
              }
              data-testid={`preset-auto-${preset.label}`}
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
                onChange={(event) =>
                  setDraft((draftParams) => ({ ...draftParams, rule: event.target.value as Rule }))
                }
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
                onChange={(event) =>
                  setDraft((draftParams) => ({
                    ...draftParams,
                    horizon: event.target.value as BacktestParams['horizon'],
                  }))
                }
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
                max={4000}
                onChange={(event) =>
                  setDraft((draftParams) => ({
                    ...draftParams,
                    lookback: Math.max(30, Math.min(4000, Number(event.target.value))),
                  }))
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
                onChange={(event) =>
                  setDraft((draftParams) => ({
                    ...draftParams,
                    universe: parseCSV(event.target.value),
                  }))
                }
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
            Astuce&nbsp;: garde l’univers compact (2–20 tickers) pour des itérations rapides.
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
        <>
          <div id="backtests-section-intro" style={{ display: 'grid', gap: 12 }}>
            <Card withBorder>
              <Title order={4}>Configuration active</Title>
              <Text c="dimmed" size="sm" mt={6}>
                Règle&nbsp;
                <Badge color="indigo" variant="light">
                  {active.rule}
                </Badge>{' '}
                • Horizon&nbsp;
                <Badge color="teal" variant="light">
                  {active.horizon}
                </Badge>{' '}
                • Lookback&nbsp;
                <Badge color="grape" variant="light">
                  {active.lookback}j
                </Badge>{' '}
                • Univers&nbsp;
                <Badge variant="outline">{active.universe.join(', ')}</Badge>
              </Text>
            </Card>
          </div>

          <div id="backtests-section-kpis" style={{ display: 'grid', gap: 16 }}>
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

            <RobustnessScoreCard summary={summaryForScore} />
          </div>

          <div id="backtests-section-history">
            {historyQuery.isLoading ? (
              <Card withBorder>
                <Loader size="sm" />
                <Text c="dimmed" size="sm" mt={8}>
                  Chargement de l’historique de robustesse…
                </Text>
              </Card>
            ) : (
              <RobustnessHistoryCard snapshots={historyQuery.data} />
            )}
          </div>

          <div id="backtests-section-insights" style={{ display: 'grid', gap: 16 }}>
            <Card withBorder data-testid="card-insights">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                <Title order={4}>Interprétation (Copilot)</Title>
                <div style={{ display: 'flex', gap: 8 }}>
                  <input
                    data-testid="inp-question"
                    type="text"
                    placeholder="Pose une question (ex: est-ce robuste si j’ajoute AAPL ?)"
                    value={question}
                    onChange={(event) => setQuestion(event.target.value)}
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
                    onClick={() => setQuestion((value) => value.trim())}
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
                  onClick={() => insight?.text && navigator.clipboard?.writeText(insight.text)}
                  data-testid="btn-copy-insight"
                >
                  Copier
                </Button>
              </div>
            </Card>

            <PresetTunerPanel
              initialStrategy={active.rule}
              initialLookback={active.lookback}
              initialUniverse={active.universe.join(',')}
            />
          </div>
        </>
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
