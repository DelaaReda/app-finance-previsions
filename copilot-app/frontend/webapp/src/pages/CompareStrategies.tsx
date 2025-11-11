import { useMemo, useState } from 'react';
import { Card, Button, Grid, Title, Text, Loader, Badge } from '@/ui';
import { AreaChart } from '@tremor/react';
import { ensureArray, nn } from '@/lib/safe';
import { useBacktest } from '@/hooks/useBacktest';
import { useBacktestInsights } from '@/hooks/useBacktestInsights';
import type { BacktestParams } from '@/services/backtests';
import { useAutoPresets } from '@/hooks/useAutoPresets';

type Rule = 'momentum' | 'meanrev' | 'carry';

const DEFAULT_A: BacktestParams = { rule: 'momentum', horizon: '1m', lookback: 180, universe: ['SPY', 'QQQ'] };
const DEFAULT_B: BacktestParams = { rule: 'meanrev', horizon: '1m', lookback: 120, universe: ['AAPL', 'MSFT'] };

export default function CompareStrategiesPage() {
  const [draftA, setDraftA] = useState<BacktestParams>(DEFAULT_A);
  const [draftB, setDraftB] = useState<BacktestParams>(DEFAULT_B);
  const [activeA, setActiveA] = useState<BacktestParams>(DEFAULT_A);
  const [activeB, setActiveB] = useState<BacktestParams>(DEFAULT_B);

  const { data: dataA, isFetching: fA, error: errA, refetch: runA } = useBacktest(activeA, true);
  const { data: dataB, isFetching: fB, error: errB, refetch: runB } = useBacktest(activeB, true);

  const sA = dataA?.summary, sB = dataB?.summary;

  const equityA = useMemo(() => ensureArray(dataA?.equity).map((p) => ({ date: p.t, equity: p.v })), [dataA]);
  const equityB = useMemo(() => ensureArray(dataB?.equity).map((p) => ({ date: p.t, equity: p.v })), [dataB]);

  const { data: insightA, isFetching: thinkA } = useBacktestInsights(sA ? { summary: sA, params: activeA } : null, Boolean(sA));
  const { data: insightB, isFetching: thinkB } = useBacktestInsights(sB ? { summary: sB, params: activeB } : null, Boolean(sB));

  const { data: autoA, refetch: refAutoA } = useAutoPresets({ universe: draftA.universe, target: 'balanced' });
  const { data: autoB, refetch: refAutoB } = useAutoPresets({ universe: draftB.universe, target: 'balanced' });

  function runBoth() {
    setActiveA(draftA);
    setActiveB(draftB);
    setTimeout(() => { runA(); runB(); }, 0);
  }

  return (
    <div data-testid="page-compare" style={{ display: 'grid', gap: 16 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Title order={2}>⚖️ Comparateur de stratégies</Title>
        <div style={{ display: 'flex', gap: 8 }}>
          <Button variant="default" onClick={runBoth} data-testid="btn-run-both" disabled={fA || fB}>
            Lancer les deux
          </Button>
        </div>
      </div>

      <Grid>
        <Card withBorder data-testid="strategy-A">
          <Title order={4}>Stratégie A — Paramètres</Title>
          <ParamsEditor value={draftA} onChange={setDraftA} />
          <div style={{ display: 'flex', gap: 8, marginTop: 8, flexWrap: 'wrap' }}>
            <Button size="xs" variant="light" onClick={() => refAutoA()}>Générer presets A</Button>
            {ensureArray(autoA).map((p) => (
              <Button key={p.label} size="xs" onClick={() => setDraftA(p)}>{p.label}</Button>
            ))}
          </div>
        </Card>

        <Card withBorder data-testid="strategy-B">
          <Title order={4}>Stratégie B — Paramètres</Title>
          <ParamsEditor value={draftB} onChange={setDraftB} />
          <div style={{ display: 'flex', gap: 8, marginTop: 8, flexWrap: 'wrap' }}>
            <Button size="xs" variant="light" onClick={() => refAutoB()}>Générer presets B</Button>
            {ensureArray(autoB).map((p) => (
              <Button key={p.label} size="xs" onClick={() => setDraftB(p)}>{p.label}</Button>
            ))}
          </div>
        </Card>

        <Card withBorder>
          <Title order={4}>Équité — A</Title>
          {fA ? <Loader /> : equityA.length === 0 ? <Text c="dimmed">Aucune donnée</Text> : (
            <AreaChart className="h-64" data={equityA} index="date" categories={['equity']} yAxisWidth={56} />
          )}
          {errA && <Text c="red">{String(errA)}</Text>}
        </Card>

        <Card withBorder>
          <Title order={4}>Équité — B</Title>
          {fB ? <Loader /> : equityB.length === 0 ? <Text c="dimmed">Aucune donnée</Text> : (
            <AreaChart className="h-64" data={equityB} index="date" categories={['equity']} yAxisWidth={56} />
          )}
          {errB && <Text c="red">{String(errB)}</Text>}
        </Card>

        <StatsCard title="Statistiques — A" summary={sA} />
        <StatsCard title="Statistiques — B" summary={sB} />

        <Card withBorder>
          <Title order={4}>Interprétation (Copilot) — A</Title>
          {thinkA ? <Loader /> : (
            <pre style={preStyle} data-testid="insight-A">{insightA?.text || '—'}</pre>
          )}
          <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
            <Button size="xs" variant="light" onClick={() => navigator.clipboard?.writeText(insightA?.text ?? '')}>Copier</Button>
          </div>
        </Card>

        <Card withBorder>
          <Title order={4}>Interprétation (Copilot) — B</Title>
          {thinkB ? <Loader /> : (
            <pre style={preStyle} data-testid="insight-B">{insightB?.text || '—'}</pre>
          )}
          <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
            <Button size="xs" variant="light" onClick={() => navigator.clipboard?.writeText(insightB?.text ?? '')}>Copier</Button>
          </div>
        </Card>
      </Grid>
    </div>
  );
}

function ParamsEditor({ value, onChange }: { value: BacktestParams; onChange: (v: BacktestParams) => void }) {
  function parseCSV(s: string) {
    return s.split(',').map((x) => x.trim().toUpperCase()).filter(Boolean);
  }
  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: 12, marginTop: 8 }}>
      <div>
        <label style={lbl}>Règle</label>
        <select
          value={value.rule}
          onChange={(e) => onChange({ ...value, rule: e.target.value as Rule })}
          style={inp}
          data-testid="sel-rule"
        >
          <option value="momentum">momentum</option>
          <option value="meanrev">meanrev</option>
          <option value="carry">carry</option>
        </select>
      </div>
      <div>
        <label style={lbl}>Horizon</label>
        <select
          value={value.horizon}
          onChange={(e) => onChange({ ...value, horizon: e.target.value as BacktestParams['horizon'] })}
          style={inp}
          data-testid="sel-horizon"
        >
          <option value="1m">1 mois</option>
          <option value="3m">3 mois</option>
          <option value="6m">6 mois</option>
        </select>
      </div>
      <div>
        <label style={lbl}>Lookback (jours)</label>
        <input
          type="number"
          value={value.lookback}
          min={30}
          max={2000}
          onChange={(e) => onChange({ ...value, lookback: Math.max(30, Math.min(2000, Number(e.target.value))) })}
          style={inp}
          data-testid="inp-lookback"
        />
      </div>
      <div>
        <label style={lbl}>Univers (CSV)</label>
        <input
          type="text"
          value={value.universe.join(',')}
          onChange={(e) => onChange({ ...value, universe: parseCSV(e.target.value) })}
          placeholder="SPY,QQQ,AAPL"
          style={inp}
          data-testid="inp-universe"
        />
      </div>
    </div>
  );
}

function StatsCard({ title, summary }: { title: string; summary: any }) {
  function pct(v: number, d = 1) { return Number.isFinite(v) ? `${(v * 100).toFixed(d)}%` : '—'; }
  return (
    <Card withBorder>
      <Title order={4}>{title}</Title>
      {!summary ? (
        <Text c="dimmed" style={{ marginTop: 8 }}>Aucune statistique</Text>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, minmax(0,1fr))', gap: 12, marginTop: 12 }}>
          <Stat label="CAGR" value={pct(nn(summary?.cagr, 0))} color="teal" />
          <Stat label="MaxDD" value={pct(nn(summary?.maxDD, 0))} color="red" />
          <Stat label="WinRate" value={pct(nn(summary?.winRate, 0))} color="indigo" />
          <Stat label="Trades" value={String(nn(summary?.trades, 0))} color="gray" />
        </div>
      )}
    </Card>
  );
}

function Stat({ label, value, color }: { label: string; value: string; color: 'teal' | 'red' | 'indigo' | 'gray' }) {
  return (
    <div style={{ display: 'grid', gap: 6 }}>
      <Text size="sm" c="dimmed">{label}</Text>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <Title order={3}>{value}</Title>
        <Badge color={color} variant="light">{label}</Badge>
      </div>
    </div>
  );
}

const lbl: React.CSSProperties = { display: 'block', fontSize: 12, opacity: 0.7, marginBottom: 6 };
const inp: React.CSSProperties = { width: '100%', padding: 8, borderRadius: 8, background: '#1f2937', border: '1px solid #374151', color: 'white' };
const preStyle: React.CSSProperties = { margin: 0, whiteSpace: 'pre-wrap', background: '#0b1220', padding: 12, borderRadius: 8, border: '1px solid #1f2937', fontSize: 14, lineHeight: 1.5 };
