import type { CSSProperties } from 'react';
import { Stack, Title, Text } from '@mantine/core';
import type { DashboardContext, DashboardTemplate, WidgetBase } from '@/dashboards/types';
import { MetricCard, LineChartWidget, AreaChartWidget, BarListWidget, TableWidget } from './widgets';
import { useForecasts } from '@/hooks/useForecasts';
import { useMacroSeries } from '@/hooks/useMacroSeries';
import { useNews } from '@/hooks/useNews';
import { ensureArray, asNumber, asString } from '@/lib/safe';

function colSpanStyle(colSpan?: number): CSSProperties {
  const span = Math.min(Math.max(colSpan ?? 12, 1), 12);
  return { gridColumn: `span ${span}` };
}

function SectionGrid({ children }: { children: React.ReactNode }) {
  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(12, minmax(0, 1fr))',
        gap: '1rem',
      }}
    >
      {children}
    </div>
  );
}

function MacroWidget({ widget, context }: { widget: WidgetBase; context: DashboardContext }) {
  const ids = context.macroIds && context.macroIds.length ? context.macroIds : ['CPIAUCSL'];
  const { data, isLoading } = useMacroSeries(ids);
  const indexField = widget.data.mapping?.index ?? 'date';
  const merged = (() => {
    const byDate = new Map<string, any>();
    ids.forEach((id) => {
      const points = ensureArray(data?.[id]);
      points.forEach((point) => {
        const idx = asString((point as any)[indexField], '');
        if (!idx) return;
        const row = byDate.get(idx) ?? { [indexField]: idx };
        row[id] = asNumber((point as any).value, 0);
        byDate.set(idx, row);
      });
    });
    return Array.from(byDate.values()).sort((a, b) => asString(a[indexField], '').localeCompare(asString(b[indexField], '')));
  })();

  if (widget.type === 'line') {
    return (
      <div style={colSpanStyle(widget.colSpan)}>
        <LineChartWidget
          title={widget.title}
          data={merged}
          index={indexField}
          categories={ids}
          height={widget.height}
          empty={!merged.length && !isLoading}
          loading={isLoading}
        />
      </div>
    );
  }

  if (widget.type === 'area') {
    return (
      <div style={colSpanStyle(widget.colSpan)}>
        <AreaChartWidget
          title={widget.title}
          data={merged}
          index={indexField}
          categories={ids}
          height={widget.height}
          empty={!merged.length && !isLoading}
          loading={isLoading}
        />
      </div>
    );
  }

  return null;
}

function ForecastWidget({ widget, context }: { widget: WidgetBase; context: DashboardContext }) {
  const { data, isLoading } = useForecasts({ horizon: context.horizon, universe: context.universe, themes: context.themes });
  const items = ensureArray(data);

  if (widget.type === 'metric') {
    const metric = widget.data.params?.metric as string;
    let value: string | number = '—';
    if (metric === 'count') value = items.length;
    if (metric === 'avgScore') {
      value = items.length ? (items.reduce((acc, cur) => acc + asNumber(cur.score), 0) / items.length).toFixed(2) : '0.00';
    }
    if (metric === 'pctUp') {
      const up = items.filter((item) => item.direction === 'up').length;
      value = items.length ? `${Math.round((up * 100) / items.length)}%` : '0%';
    }
    if (metric === 'lastUpdate') {
      const last = items.find((item) => item.updatedAt)?.updatedAt;
      value = last ? new Date(last).toLocaleString('fr-FR') : '—';
    }
    return (
      <div style={colSpanStyle(widget.colSpan)}>
        <MetricCard title={widget.title} value={value} loading={isLoading} />
      </div>
    );
  }

  if (widget.type === 'barlist') {
    const order = widget.data.params?.orderBy as string | undefined;
    const limit = Number(widget.data.params?.limit ?? 10);
    const scored = items
      .map((item) => ({
        name: item.symbol,
        value: order === 'expectedReturn' ? asNumber(item.expectedReturn) : asNumber(item.score),
      }))
      .sort((a, b) => b.value - a.value)
      .slice(0, limit);
    return (
      <div style={colSpanStyle(widget.colSpan)}>
        <BarListWidget title={widget.title} items={scored} height={widget.height} empty={!scored.length && !isLoading} loading={isLoading} />
      </div>
    );
  }

  return null;
}

function NewsWidget({ widget, context }: { widget: WidgetBase; context: DashboardContext }) {
  const limit = Number(widget.data.params?.limit ?? 6);
  const { data, isLoading } = useNews({ universe: context.universe, limit });
  const rows = ensureArray(data).map((article) => ({
    title: asString(article.title),
    source: asString(article.source),
    publishedAt: asString(article.publishedAt),
    url: asString(article.url),
  }));

  return (
    <div style={colSpanStyle(widget.colSpan)}>
      <TableWidget
        title={widget.title}
        rows={rows}
        height={widget.height}
        empty={!rows.length && !isLoading}
        loading={isLoading}
        columns={[
          {
            key: 'title',
            header: 'Titre',
            render: (value, row) => (
              <a href={row.url} target="_blank" rel="noreferrer">
                {value}
              </a>
            ),
          },
          { key: 'source', header: 'Source' },
          { key: 'publishedAt', header: 'Date' },
        ]}
      />
    </div>
  );
}

function WidgetView({ widget, context }: { widget: WidgetBase; context: DashboardContext }) {
  if (widget.data.kind === 'macro') {
    return MacroWidget({ widget, context }) ?? <div style={colSpanStyle(widget.colSpan)} />;
  }
  if (widget.data.kind === 'forecasts') {
    return ForecastWidget({ widget, context }) ?? <div style={colSpanStyle(widget.colSpan)} />;
  }
  if (widget.data.kind === 'news') {
    return NewsWidget({ widget, context });
  }
  return <div style={colSpanStyle(widget.colSpan)} />;
}

export function DashboardRenderer({ template, context }: { template: DashboardTemplate; context: DashboardContext }) {
  return (
    <Stack>
      {template.layout.map((section) => (
        <Stack key={section.id} gap="md">
          {section.title && <Title order={3}>{section.title}</Title>}
          {section.subtitle && <Text c="dimmed">{section.subtitle}</Text>}
          <SectionGrid>
            {section.widgets.map((widget) => (
              <WidgetView key={widget.id} widget={widget} context={context} />
            ))}
          </SectionGrid>
        </Stack>
      ))}
    </Stack>
  );
}
