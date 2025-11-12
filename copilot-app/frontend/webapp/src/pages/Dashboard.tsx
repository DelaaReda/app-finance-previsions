import { useMemo, useState } from 'react';
import {
  IconRefresh,
  IconArrowRight,
  IconSparkles,
  IconGauge,
  IconAlertCircle,
  IconDownload,
} from '@tabler/icons-react';
import { useDashboardKPIs } from '@/hooks/useDashboardKPIs';
import { useForecasts } from '@/hooks/useForecasts';
import { useApi } from '@/hooks/useApi';
import { ensureArray } from '@/lib/safe';
import { FinancialChart, ChartDataPoint } from '@/features/okc/components/FinancialChart';
import { Sparkline } from '@/features/okc/components/Sparkline';
import { RadialMetric } from '@/features/okc/components/RadialMetric';
// Components
import { Card, CardHeader, CardTitle, CardContent } from '@/features/okc/components/Card';
import { ForecastCard, ForecastInsight } from '@/features/okc/components/ForecastCard';
import { MetricStrip, type StripMetric } from '@/features/okc/components/desktop/MetricStrip';
import { NewsCard } from '@/features/okc/components/desktop/NewsCard';
import { ErrorCard } from '@/features/okc/components/desktop/ErrorCard';
import { DynamicWidgetGrid } from '@/components/adaptive/DynamicWidgetGrid';
import { DashboardGrid } from '@/features/okc/components/desktop/DashboardGrid';
import { AdaptiveLayoutProvider } from '@/contexts/AdaptiveLayoutContext';
import { EmptyState } from '@/components/ui/EmptyState';
import { Button } from '@/features/okc/components/Button';
import { KPIBar } from '@/components/dashboard/KPIBar';

const PERIODS = ['24h', '7d', '30d', '90d'] as const;
type Period = typeof PERIODS[number];

type MacroSeriesPoint = {
  id?: string;
  series_id?: string;
  name?: string;
  points?: { date?: string; value?: number }[];
  data?: { date?: string; value?: number }[];
};

function normalizeDirection(direction?: string): 'up' | 'down' | 'neutral' {
  if (!direction) return 'neutral';
  const normalized = direction.toLowerCase();
  if (['up', 'bullish', 'haussier'].includes(normalized)) return 'up';
  if (['down', 'bearish', 'baissier'].includes(normalized)) return 'down';
  return 'neutral';
}

function extractMacroSeries(raw: any): Record<string, number> {
  if (!raw) return {};
  const payload: MacroSeriesPoint[] = Array.isArray(raw?.series)
    ? raw.series
    : Array.isArray(raw?.data)
    ? raw.data
    : Array.isArray(raw)
    ? raw
    : [];

  const values: Record<string, number> = {};
  payload.forEach((series) => {
    const points = Array.isArray(series.points) ? series.points : Array.isArray(series.data) ? series.data : [];
    if (points.length === 0) return;
    const lastPoint = points[points.length - 1];
    const value = lastPoint?.value ?? (Array.isArray(lastPoint) ? lastPoint[1] : undefined);
    const key = series.id ?? series.series_id ?? series.name;
    if (key && typeof value === 'number') {
      values[key] = value;
    }
  });
  return values;
}

function DashboardContent() {
  const [selectedPeriod, setSelectedPeriod] = useState<Period>('7d');
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [newsExpanded, setNewsExpanded] = useState(false);

  const { data: kpis, isLoading: kpiLoading } = useDashboardKPIs();
  const forecastsQuery = useForecasts({ limit: 24, horizon: selectedPeriod === '24h' ? 'short' : undefined });
  const macroQuery = useApi<any>('/api/macro/series');
  const newsQuery = useApi<any>('/api/news/feed?limit=4');

  const forecastRows = ensureArray(forecastsQuery.data?.rows);
  const macroValues = useMemo(() => extractMacroSeries(macroQuery.data), [macroQuery.data]);
  const newsItems = useMemo(() => {
    const raw = newsQuery.data as any;
    if (!raw) return [] as Array<{ id: string; title: string; source?: string; url?: string; date?: string }>;
    // useApi now returns the inner payload from backend; handle normalized shapes
    const articles = Array.isArray(raw?.items)
      ? raw.items
      : Array.isArray(raw?.articles)
      ? raw.articles
      : Array.isArray(raw?.rows)
      ? raw.rows
      : Array.isArray(raw?.data?.articles)
      ? raw.data.articles
      : Array.isArray(raw)
      ? raw
      : [];
    return articles.map((article: any, index: number) => ({
      id: article.id ?? `${article.ticker ?? 'article'}-${index}`,
      title: article.title ?? article.headline ?? 'Sans titre',
      source: article.source ?? article.publisher ?? article.sourceDomain,
      url: article.url ?? article.link ?? article.href,
      date: article.pubDate ?? article.published_at ?? article.date,
    }));
  }, [newsQuery.data]);

  // Removed legacy KPI strip (metrics) to avoid duplication with adaptive widgets

  const performanceChartData: ChartDataPoint[] = useMemo(() => {
    return forecastRows.slice(0, 12).map((row) => ({
      name: row.ticker ?? row.symbol ?? '—',
      expected: Number((((row.expected_return ?? 0) * 100) || row.expected_return_pct || 0).toFixed(2)),
      confidence: Math.round((row.confidence ?? 0) * 100),
    }));
  }, [forecastRows]);

  const confidenceDistribution: ChartDataPoint[] = useMemo(() => {
    const buckets = [
      { label: '0–20%', from: 0, to: 20, count: 0 },
      { label: '20–40%', from: 20, to: 40, count: 0 },
      { label: '40–60%', from: 40, to: 60, count: 0 },
      { label: '60–80%', from: 60, to: 80, count: 0 },
      { label: '80–100%', from: 80, to: 100, count: 0 },
    ];
    forecastRows.forEach((row) => {
      const pct = Math.round((row.confidence ?? 0) * 100);
      for (const b of buckets) {
        if (pct >= b.from && pct < (b.to === 100 ? 101 : b.to)) {
          b.count += 1;
          break;
        }
      }
    });
    return buckets.map((b) => ({ name: b.label, count: b.count }));
  }, [forecastRows]);

  const directionDistribution = useMemo(() => {
    const counts = { Haussier: 0, Baissier: 0, Neutre: 0 };
    forecastRows.forEach((row) => {
      const dir = normalizeDirection(row.direction);
      if (dir === 'up') counts.Haussier += 1;
      else if (dir === 'down') counts.Baissier += 1;
      else counts.Neutre += 1;
    });
    return Object.entries(counts)
      .filter(([, value]) => value > 0)
      .map(([name, value]) => ({ name, value }));
  }, [forecastRows]);

  const forecastInsights: ForecastInsight[] = useMemo(() => {
    return forecastRows.slice(0, 6).map((row, index) => ({
      id: `${row.ticker ?? 'forecast'}-${index}`,
      ticker: row.ticker ?? row.symbol ?? 'N/A',
      horizon: row.horizon ?? 'Horizon mixte',
      direction: normalizeDirection(row.direction),
      confidence: row.confidence,
      expectedReturn:
        typeof row.expected_return === 'number'
          ? row.expected_return
          : typeof row.expected_return_pct === 'number'
          ? row.expected_return_pct / 100
          : undefined,
      reason: row.explanation ?? row.reason,
      riskFactors: row.risk_factors ?? row.factors ?? [],
      lastUpdated: row.timestamp ?? row.forecasted_at ?? row.updatedAt,
    }));
  }, [forecastRows]);

  const macroSummary = useMemo(() => {
    const map = {
      CPIAUCSL: { label: 'CPI' },
      UNRATE: { label: 'Chômage' },
      DGS10: { label: 'T-Bond 10Y' },
      DGS2: { label: 'T-Bond 2Y' },
      VIXCLS: { label: 'Indice VIX' },
    } as Record<string, { label: string }>;
    return Object.entries(macroValues)
      .filter(([key]) => key in map)
      .map(([key, value]) => ({ id: key, label: map[key].label, value }));
  }, [macroValues]);

  const macroSeriesMap = useMemo(() => {
    const raw = macroQuery.data as any;
    const arr: any[] = Array.isArray(raw?.series)
      ? raw.series
      : Array.isArray(raw?.data)
      ? raw.data
      : Array.isArray(raw)
      ? raw
      : [];
    const byId: Record<string, number[]> = {};
    arr.forEach((s) => {
      const id = s.id ?? s.series_id ?? s.name;
      const pts = (Array.isArray(s.points) ? s.points : Array.isArray(s.data) ? s.data : []).map((p: any) =>
        typeof p?.value === 'number' ? p.value : Array.isArray(p) ? p[1] : undefined
      );
      if (id && pts.length > 0) byId[id] = pts.slice(-20).filter((v: any) => typeof v === 'number');
    });
    return byId;
  }, [macroQuery.data]);

  const handleRefresh = async () => {
    setIsRefreshing(true);
    await Promise.allSettled([
      forecastsQuery.refetch(),
      macroQuery.refetch(),
      newsQuery.refetch(),
    ]);
    setIsRefreshing(false);
  };

  // Compact KPI values for quick glance bar
  const kpiTotalForecasts = kpis?.forecasts?.total ?? kpis?.total_forecasts ?? 0;
  const kpiAvgConfidencePct = Math.round(((kpis?.forecasts?.avg_confidence ?? 0) * 100));
  const kpiHitRatePct = (() => {
    const hr = kpis?.backtests?.hit_rate ?? 0;
    return Math.round((hr > 1 ? hr : hr * 100));
  })();
  const kpiLastUpdate = kpis?.system?.last_forecast_update
    ? new Date(kpis.system.last_forecast_update).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })
    : undefined;
  const macroLast = (macroQuery.data as any)?.data?.last_updated || (macroQuery.data as any)?.last_updated;
  const newsLast = (() => {
    const raw = newsQuery.data as any;
    const arr = Array.isArray(raw?.items) ? raw.items : Array.isArray(raw?.articles) ? raw.articles : Array.isArray(raw?.rows) ? raw.rows : Array.isArray(raw?.data) ? raw.data : [];
    if (arr.length === 0) return undefined;
    const d = arr[0].pubDate || arr[0].published_at || arr[0].date;
    return d ? new Date(d).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' }) : undefined;
  })();

  return (
    <div className="min-h-screen bg-bg text-text">
      <div className="max-w-7xl mx-auto px-4 md:px-6 py-4 space-y-4">
        
        {/* KPI Bar compacte */}
        <KPIBar onRefresh={handleRefresh} />
        
        <div className="space-y-4 sm:space-y-6 lg:space-y-8">
        {/* Header first, then adaptive widgets */}
        {
        <div className="bg-glass border border-glass-border rounded-xl sm:rounded-2xl p-4 sm:p-5 shadow-lg backdrop-blur-xl">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div className="space-y-3">
              <div className="inline-flex items-center gap-2 text-sm text-primary uppercase tracking-[0.3em]">
                <IconSparkles size={16} />
                Finance Copilot
              </div>
              <h1 className="text-3xl sm:text-4xl lg:text-5xl font-semibold gradient-text">Command center temps réel</h1>
              <p className="text-muted text-sm sm:text-base">
                Synthèse intelligente des prévisions hybrides, signaux de risques et régimes macro.
              </p>
              {kpis?.system?.last_forecast_update && (
                <p className="text-xs text-muted">
                  Dernière mise à jour forecasts : {new Date(kpis.system.last_forecast_update).toLocaleString('fr-FR')}
                </p>
              )}
            </div>

            <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2 sm:gap-3">
              <div className="buttons-group bg-surface rounded-xl border border-border p-1">
                {PERIODS.map((period) => (
                  <button
                    key={period}
                    onClick={() => setSelectedPeriod(period)}
                    className={`px-2 sm:px-3 py-1 text-xs sm:text-sm rounded-full transition-all ${
                      selectedPeriod === period
                        ? 'bg-primary text-white shadow-lg shadow-primary/25'
                        : 'text-muted hover:text-text hover:bg-surface-elevated'
                    }`}
                  >
                    {period}
                  </button>
                ))}
              </div>
              <div className="flex items-center gap-2 sm:gap-3 w-full sm:w-auto">
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={handleRefresh}
                  loading={isRefreshing || forecastsQuery.isFetching}
                  leftIcon={<IconRefresh size={16} />}
                  className="flex-1 sm:flex-none"
                >
                  Rafraîchir
                </Button>
                <Button variant="ghost" size="sm" leftIcon={<IconDownload size={16} />} className="flex-1 sm:flex-none">
                  <span className="hidden sm:inline">Exporter</span>
                  <span className="sm:hidden">Exp.</span>
                </Button>
              </div>
            </div>
          </div>
          {/* News ticker: shows recent headlines inline, horizontally scrollable on small screens */}
          {newsItems.length > 0 && (
            <div className="mt-3 -mb-2 overflow-x-auto">
              <div className="flex items-center gap-4 py-1 text-xs sm:text-sm min-w-full">
                <span className="uppercase tracking-[0.3em] text-primary flex-shrink-0">Now</span>
                {newsItems.slice(0, 8).map((article) => (
                  <a
                    key={article.id}
                    href={article.url ?? '#'}
                    target="_blank"
                    rel="noreferrer"
                    className="text-muted hover:text-text transition-colors whitespace-nowrap"
                    title={article.title}
                  >
                    {article.title}
                  </a>
                ))}
              </div>
            </div>
          )}
        </div>
        }

        {/* KPI compact bar (executive snapshot) */}
        <div className="bg-surface rounded-lg border border-border px-3 py-2 flex flex-wrap gap-3 items-center text-xs text-muted">
          <span className="text-text font-medium">Prévisions actives:</span>
          <span className="text-text">{kpiTotalForecasts}</span>
          <span className="opacity-30">•</span>
          <span className="text-text font-medium">Confiance moyenne:</span>
          <span className="text-emerald-400 font-semibold">{kpiAvgConfidencePct}%</span>
          <span className="opacity-30">•</span>
          <span className="text-text font-medium">Taux de réussite:</span>
          <span className="text-emerald-400 font-semibold">{kpiHitRatePct}%</span>
          {kpiLastUpdate && (
            <>
              <span className="opacity-30">•</span>
              <span className="text-text font-medium">MAJ:</span>
              <span className="text-text">{kpiLastUpdate}</span>
            </>
          )}
          {macroLast && (
            <>
              <span className="opacity-30">•</span>
              <span className="text-text font-medium">Macro:</span>
              <span className="text-text">{new Date(macroLast).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })}</span>
            </>
          )}
          {newsLast && (
            <>
              <span className="opacity-30">•</span>
              <span className="text-text font-medium">News:</span>
              <span className="text-text">{newsLast}</span>
            </>
          )}
        </div>

        {/* Adaptive widgets directly under the header */}
        <Card variant="glass" hoverable={false}>
          <CardContent className="p-3 sm:p-4">
            <DynamicWidgetGrid />
          </CardContent>
        </Card>

        {/* KPI metric grid removed */}

        {false && (
        <DashboardGrid
          left={
            <>
              {performanceChartData.length > 0 ? (
                <FinancialChart
                  data={performanceChartData}
                  type="bar"
                  title="Score de confiance vs rendement attendu"
                  colors={['#3b82f6', '#10b981']}
                />
              ) : (
                <Card>
                  <EmptyState
                    title="Aucun graphique disponible"
                    description="Les données de performance seront affichées une fois les prévisions chargées."
                    action={{ label: 'Rafraîchir', onClick: handleRefresh }}
                  />
                </Card>
              )}
              {directionDistribution.length > 0 ? (
                <Card className="hidden sm:block">
                  <CardHeader className="sticky top-0 z-10 bg-bg/80 backdrop-blur supports-[backdrop-filter]:bg-bg/60 border-b border-border">
                    <CardTitle>Distribution des directions</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <FinancialChart data={directionDistribution} type="pie" colors={['#10b981', '#ef4444', '#6366f1']} height={260} />
                  </CardContent>
                </Card>
              ) : (
                <Card className="hidden sm:block">
                  <CardHeader className="sticky top-0 z-10 bg-bg/80 backdrop-blur supports-[backdrop-filter]:bg-bg/60 border-b border-border">
                    <CardTitle>Distribution des directions</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <EmptyState title="Aucune distribution disponible" description="La distribution des directions sera affichée une fois les prévisions chargées." />
                  </CardContent>
                </Card>
              )}

              {/* Confidence distribution (desktop-focused) */}
              {confidenceDistribution.some((d) => (d as any).count > 0) && (
                <Card className="hidden sm:block">
                  <CardHeader className="sticky top-0 z-10 bg-bg/80 backdrop-blur supports-[backdrop-filter]:bg-bg/60 border-b border-border">
                    <CardTitle>Distribution de la confiance</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <FinancialChart data={confidenceDistribution} type="bar" colors={["#6366f1"]} />
                  </CardContent>
                </Card>
              )}
            </>
          }
          right={
            <>
              <Card>
                <CardHeader className="sticky top-0 z-10 bg-bg/80 backdrop-blur supports-[backdrop-filter]:bg-bg/60 border-b border-border">
                  <CardTitle>Indicateurs Macro</CardTitle>
                </CardHeader>
                <CardContent>
                  {macroQuery.isLoading && (
                    <div className="py-8">
                      <p className="text-sm text-muted text-center">Chargement des séries…</p>
                    </div>
                  )}
                  {macroQuery.error && (
                    <EmptyState
                      title="Erreur de chargement"
                      description={macroQuery.error}
                      icon={<IconAlertCircle size={32} className="text-danger" />}
                      action={{ label: 'Réessayer', onClick: () => macroQuery.refetch() }}
                    />
                  )}
                  {!macroQuery.isLoading && !macroQuery.error && (
                    <>
                      {macroSummary.length > 0 ? (
                        <>
                          <div className="hidden xl:block">
                            {(() => {
                              const items: StripMetric[] = macroSummary.map((indicator) => {
                                const val = Number(indicator.value || 0);
                                let tone: 'low' | 'moderate' | 'high' | 'neutral' = 'neutral';
                                if (indicator.id === 'VIXCLS') tone = val < 15 ? 'low' : val < 25 ? 'moderate' : 'high';
                                else if (indicator.id === 'UNRATE') tone = val < 4 ? 'low' : val < 6 ? 'moderate' : 'high';
                                else if (indicator.id === 'DGS10' || indicator.id === 'DGS2') tone = val < 3 ? 'low' : val < 5 ? 'moderate' : 'high';
                                return { label: indicator.label, value: val, tone };
                              });
                              return <MetricStrip items={items} />;
                            })()}
                          </div>
                          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 xl:hidden">
                            {macroSummary.map((indicator) => {
                              const val = Number(indicator.value || 0);
                              const spark = macroSeriesMap[indicator.id] ?? [];
                              let percent: number | undefined = undefined;
                              let badge: { label: string; color?: string } | undefined;
                              if (indicator.id === 'VIXCLS') {
                                percent = Math.max(0, Math.min(100, ((val - 10) / 30) * 100));
                                badge = { label: val < 15 ? 'low' : val < 25 ? 'moderate' : 'high', color: val < 15 ? 'teal' : val < 25 ? 'yellow' : undefined };
                                if (val >= 25) badge.color = 'red';
                              } else if (indicator.id === 'UNRATE') {
                                percent = Math.max(0, Math.min(100, ((val - 3) / 5) * 100));
                                badge = { label: val < 4 ? 'low' : val < 6 ? 'moderate' : 'high', color: val < 4 ? 'teal' : val < 6 ? 'yellow' : undefined };
                                if (val >= 6) badge.color = 'red';
                              } else if (indicator.id === 'DGS10' || indicator.id === 'DGS2') {
                                percent = Math.max(0, Math.min(100, ((val - 1) / 5) * 100));
                                badge = { label: val < 3 ? 'low' : val < 5 ? 'moderate' : 'high', color: val < 3 ? 'teal' : val < 5 ? 'yellow' : undefined };
                                if (val >= 5) badge.color = 'red';
                              }
                              return (
                                <div key={indicator.id} className="flex items-center justify-between gap-3">
                                  <div className="flex-1 min-w-0">
                                    <RadialMetric
                                      label={indicator.label}
                                      value={val}
                                      percent={percent}
                                      badge={badge}
                                      color={badge?.color === 'red' ? 'red' : badge?.color === 'yellow' ? 'yellow' : 'teal'}
                                    />
                                  </div>
                                  {spark.length > 0 && <Sparkline data={spark} className="w-24 hidden sm:block" />}
                                </div>
                              );
                            })}
                          </div>
                        </>
                      ) : (
                        <EmptyState
                          title="Aucune donnée macro"
                          description="Les indicateurs macroéconomiques seront disponibles une fois chargés."
                          action={{ label: 'Rafraîchir', onClick: () => macroQuery.refetch() }}
                        />
                      )}
                    </>
                  )}
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="sticky top-0 z-10 bg-bg/80 backdrop-blur supports-[backdrop-filter]:bg-bg/60 border-b border-border">
                  <CardTitle>Focus news</CardTitle>
                </CardHeader>
                <CardContent className="xl:max-h-[520px] xl:overflow-auto">
                  {newsQuery.isLoading && (
                    <div className="py-8">
                      <p className="text-sm text-muted text-center">Chargement des actualités…</p>
                    </div>
                  )}
                  {newsQuery.error && (
                    <EmptyState
                      title="Erreur de chargement"
                      description={newsQuery.error}
                      icon={<IconAlertCircle size={32} className="text-danger" />}
                      action={{ label: 'Réessayer', onClick: () => newsQuery.refetch() }}
                    />
                  )}
                  {!newsQuery.isLoading && !newsQuery.error && (
                    <>
                      {newsItems.length > 0 ? (
                        <div className="space-y-2">
                          {(newsExpanded ? newsItems : newsItems.slice(0, 5)).map((article) => (
                            <NewsCard
                              key={article.id}
                              title={article.title}
                              source={article.source}
                              url={article.url}
                              time={article.date ? new Date(article.date).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' }) : undefined}
                            />
                          ))}
                          {newsItems.length > 5 && (
                            <div className="pt-1">
                              <Button variant="ghost" size="sm" onClick={() => setNewsExpanded((v) => !v)}>
                                {newsExpanded ? 'Afficher moins' : 'Afficher plus'}
                              </Button>
                            </div>
                          )}
                        </div>
                      ) : (
                        <EmptyState
                          title="Pas d'actualité récente"
                          description="Les actualités financières seront affichées une fois chargées."
                          action={{ label: 'Rafraîchir', onClick: () => newsQuery.refetch() }}
                        />
                      )}
                    </>
                  )}
                </CardContent>
              </Card>
            </>
          }
        />
        )}

        {false && (
        <div className="space-y-3 sm:space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 sm:gap-4">
            <div>
              <p className="text-xs sm:text-sm uppercase tracking-[0.3em] text-muted">Prévisions hybrides</p>
              <h2 className="text-xl sm:text-2xl font-semibold text-text">Top signaux surveillés</h2>
            </div>
            <span className="text-xs sm:text-sm text-muted flex items-center gap-2">
              <IconGauge size={16} /> {forecastRows.length} prévisions chargées
            </span>
          </div>
          {forecastsQuery.isLoading && (
            <div className="py-6">
              <p className="text-sm text-muted text-center">Chargement des prévisions…</p>
            </div>
          )}
          {forecastsQuery.error instanceof Error && (
            <Card>
              <ErrorCard title="Erreur de chargement" message={forecastsQuery.error.message} onRetry={() => forecastsQuery.refetch()} />
            </Card>
          )}
          {!forecastsQuery.isLoading && !forecastsQuery.error && (
            <>
              {forecastInsights.length > 0 ? (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 sm:gap-6">
                  {forecastInsights.map((forecast) => (
                    <ForecastCard key={forecast.id} forecast={forecast} />
                  ))}
                </div>
              ) : (
                <Card>
                  <EmptyState
                    title="Aucune prévision disponible"
                    description="Les prévisions seront affichées une fois générées."
                    action={{
                      label: 'Rafraîchir',
                      onClick: handleRefresh,
                    }}
                  />
                </Card>
              )}
            </>
          )}
          </div>
        )}

        {/* All core tiles (Forecasts, Stocks, Performance, News, Macro) now live in DynamicWidgetGrid above */}
        </div>
      </div>
    </div>
  );
}

export default function Dashboard() {
  return (
    <AdaptiveLayoutProvider>
      <DashboardContent />
    </AdaptiveLayoutProvider>
  );
}
