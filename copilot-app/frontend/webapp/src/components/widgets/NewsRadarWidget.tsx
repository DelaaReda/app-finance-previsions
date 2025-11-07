import { useMemo, useState } from 'react';
import { BarChart, BarList, AreaChart } from '@tremor/react';
import {
  Alert,
  Badge,
  Group,
  MultiSelect,
  ScrollArea,
  SegmentedControl,
  Stack,
  TextInput,
} from '@mantine/core';
import { IconDownload } from '@tabler/icons-react';
import { Card, Title, Button, Text } from '@/ui';
import FreshnessBadge from '@/components/ui/FreshnessBadge';
import { ensureArray } from '@/lib/safe';
import { useNewsRadar, type NewsRadarArticle } from '@/hooks/useNewsRadar';

type WindowKey = '24h' | '7d' | '30d';

function windowToRange(win: WindowKey): { from: string; to: string } {
  const end = new Date();
  const start = new Date(end);
  if (win === '24h') start.setDate(end.getDate() - 1);
  if (win === '7d') start.setDate(end.getDate() - 7);
  if (win === '30d') start.setDate(end.getDate() - 30);
  return { from: start.toISOString(), to: end.toISOString() };
}

function classifySentiment(value?: number | null) {
  if (typeof value !== 'number') return 'Neutral' as const;
  if (value > 0.1) return 'Positive' as const;
  if (value < -0.1) return 'Negative' as const;
  return 'Neutral' as const;
}

function timelineKey(date: Date, win: WindowKey) {
  if (win === '24h') return date.toISOString().slice(0, 13) + ':00';
  return date.toISOString().slice(0, 10);
}

function exportCsv(articles: NewsRadarArticle[]) {
  if (!articles.length) return;
  const cols = ['published_at', 'source', 'title', 'url', 'tickers', 'themes', 'sentiment'];
  const lines = [cols.join(',')];
  for (const article of articles) {
    lines.push([
      article.published_at,
      article.source ?? '',
      `"${article.title.replace(/"/g, '""')}"`,
      article.url,
      ensureArray(article.tickers).join('|'),
      ensureArray(article.themes).join('|'),
      typeof article.sentiment === 'number' ? article.sentiment.toFixed(3) : '',
    ].join(','));
  }
  const blob = new Blob([lines.join('\n')], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = 'news_radar.csv';
  anchor.click();
  URL.revokeObjectURL(url);
}

export function NewsRadarWidget({
  title = '🛰️ News Radar',
  initialUniverse = ['SPY', 'QQQ'],
  initialThemes = [] as string[],
  initialWindow = '7d' as WindowKey,
  initialLimit = 400,
}: {
  title?: string;
  initialUniverse?: string[];
  initialThemes?: string[];
  initialWindow?: WindowKey;
  initialLimit?: number;
}) {
  const [universe, setUniverse] = useState<string[]>(initialUniverse);
  const [themes, setThemes] = useState<string[]>(initialThemes);
  const [query, setQuery] = useState('');
  const [window, setWindow] = useState<WindowKey>(initialWindow);

  const { from, to } = useMemo(() => windowToRange(window), [window]);

  const { data, isLoading, error, isFetching, refetch } = useNewsRadar({
    universe,
    themes,
    q: query || undefined,
    from,
    to,
    limit: initialLimit,
    sort: 'recent',
  });

  const articles = ensureArray(data?.articles);

  const aggregations = useMemo(() => {
    const themeCounts = new Map<string, number>();
    const tickerCounts = new Map<string, number>();
    const sentimentByTheme = new Map<string, { Positive: number; Neutral: number; Negative: number }>();
    const timelineCounts = new Map<string, number>();

    for (const article of articles) {
      const themeList = ensureArray(article.themes);
      const tickerList = ensureArray(article.tickers);
      const sentiment = classifySentiment(article.sentiment);
      const bucketKey = timelineKey(new Date(article.published_at), window);

      timelineCounts.set(bucketKey, (timelineCounts.get(bucketKey) ?? 0) + 1);

      for (const theme of themeList) {
        themeCounts.set(theme, (themeCounts.get(theme) ?? 0) + 1);
        const bucket = sentimentByTheme.get(theme) ?? { Positive: 0, Neutral: 0, Negative: 0 };
        bucket[sentiment] += 1;
        sentimentByTheme.set(theme, bucket);
      }

      for (const ticker of tickerList) {
        tickerCounts.set(ticker, (tickerCounts.get(ticker) ?? 0) + 1);
      }
    }

    const toBarList = (map: Map<string, number>) =>
      Array.from(map.entries())
        .map(([name, value]) => ({ name, value }))
        .sort((a, b) => b.value - a.value)
        .slice(0, 12);

    const sentimentGrouped = Array.from(sentimentByTheme.entries())
      .map(([theme, counts]) => ({ theme, ...counts }))
      .sort((a, b) => (b.Positive + b.Neutral + b.Negative) - (a.Positive + a.Neutral + a.Negative))
      .slice(0, 10);

    const timeline = Array.from(timelineCounts.entries())
      .map(([time, value]) => ({ time, Articles: value }))
      .sort((a, b) => a.time.localeCompare(b.time));

    return {
      topThemes: toBarList(themeCounts),
      topTickers: toBarList(tickerCounts),
      sentimentGrouped,
      timeline,
    };
  }, [articles, window]);

  return (
    <Card data-testid="news-radar">
      <Group justify="space-between" align="center" wrap="wrap">
        <div>
          <Title order={4}>{title}</Title>
          <Text c="dimmed" mt={4}>
            Explorer l’actualité: thèmes, tickers, sentiment, time-line, export CSV.
          </Text>
        </div>
        <Group gap="xs" wrap="nowrap">
          <MultiSelect
            aria-label="Univers"
            data={[...new Set([...universe, ...initialUniverse])].map((value) => ({ value, label: value }))}
            value={universe}
            onChange={setUniverse}
            searchable
            placeholder="Tickers (SPY, QQQ, NVDA...)"
            style={{ minWidth: 260 }}
          />
          <MultiSelect
            aria-label="Thèmes"
            data={[...new Set([...themes, ...initialThemes])].map((value) => ({ value, label: value }))}
            value={themes}
            onChange={setThemes}
            searchable
            placeholder="Thèmes (AI, chips, macro...)"
            style={{ minWidth: 220 }}
          />
          <SegmentedControl
            aria-label="Fenêtre temporelle"
            value={window}
            onChange={(value) => setWindow(value as WindowKey)}
            data={[
              { label: '24h', value: '24h' },
              { label: '7j', value: '7d' },
              { label: '30j', value: '30d' },
            ]}
          />
          <TextInput
            aria-label="Recherche"
            placeholder="Recherche plein texte"
            value={query}
            onChange={(event) => setQuery(event.currentTarget.value)}
            style={{ width: 220 }}
          />
          <Button onClick={() => refetch()} loading={isFetching}>
            Rafraîchir
          </Button>
          <Button variant="light" leftSection={<IconDownload size={16} />} onClick={() => exportCsv(articles)}>
            Export CSV
          </Button>
          <FreshnessBadge freshness={data?.updated_at ?? undefined} />
        </Group>
      </Group>

      {isLoading && (
        <Alert mt="md" color="blue" title="Chargement">
          Récupération des articles…
        </Alert>
      )}

      {error && (
        <Alert mt="md" color="red" title="Erreur">
          Impossible de charger les articles ({String(error)})
        </Alert>
      )}

      {!isLoading && !error && (
        articles.length === 0 ? (
          <Alert mt="md" color="gray" title="Aucun article">
            Aucun résultat pour ces filtres.
          </Alert>
        ) : (
          <Stack mt="md" gap="lg">
            <Group grow align="start">
              <Card>
                <Title order={6}>Top thèmes</Title>
                <BarList data={aggregations.topThemes} className="mt-2" />
              </Card>
              <Card>
                <Title order={6}>Top tickers</Title>
                <BarList data={aggregations.topTickers} className="mt-2" />
              </Card>
            </Group>

            <Card>
              <Title order={6}>Sentiment par thème</Title>
              <BarChart
                className="mt-3 h-72"
                index="theme"
                data={aggregations.sentimentGrouped}
                categories={['Positive', 'Neutral', 'Negative']}
                stack
                yAxisWidth={48}
              />
            </Card>

            <Card>
              <Title order={6}>Flux temporel</Title>
              <AreaChart
                className="mt-3 h-72"
                data={aggregations.timeline}
                index="time"
                categories={['Articles']}
                showLegend={false}
                yAxisWidth={48}
              />
            </Card>

            <Card>
              <Title order={6}>Articles</Title>
              <ScrollArea h={420} type="hover">
                <div style={{ display: 'grid', gap: 12, paddingRight: 8 }}>
                  {articles.slice(0, 120).map((article) => {
                    const sentiment = classifySentiment(article.sentiment);
                    return (
                      <div key={article.id} style={{ display: 'grid', gridTemplateColumns: '1fr auto', gap: 8 }}>
                        <div>
                          <a href={article.url} target="_blank" rel="noreferrer" style={{ fontWeight: 600 }}>
                            {article.title}
                          </a>
                          <div style={{ fontSize: 12, opacity: 0.7, marginTop: 4 }}>
                            {new Date(article.published_at).toLocaleString()} • {article.source ?? '—'}
                          </div>
                          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 6 }}>
                            {ensureArray(article.tickers).map((ticker) => (
                              <Badge key={`${article.id}-ticker-${ticker}`} variant="light">
                                {ticker}
                              </Badge>
                            ))}
                            {ensureArray(article.themes).map((theme) => (
                              <Badge key={`${article.id}-theme-${theme}`} color="grape" variant="light">
                                {theme}
                              </Badge>
                            ))}
                          </div>
                        </div>
                        <div>
                          <Badge color={sentiment === 'Positive' ? 'green' : sentiment === 'Negative' ? 'red' : 'gray'}>
                            {sentiment}
                          </Badge>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </ScrollArea>
            </Card>
          </Stack>
        )
      )}
    </Card>
  );
}
