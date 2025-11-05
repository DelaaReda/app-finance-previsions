import { useEffect, useState, useMemo } from 'react';
import type { GridValueFormatterParams, GridColDef } from '@mui/x-data-grid';
import Container from '@mui/material/Container';
import Typography from '@mui/material/Typography';
import Skeleton from '@mui/material/Skeleton';
import Alert from '@mui/material/Alert';
import Button from '@mui/material/Button';
import Box from '@mui/material/Box';
import { apiGet } from '../api/client';
import FreshnessBadge from '../components/ui/FreshnessBadge';
import EmptyState from '../components/ui/EmptyState';
import { safeArray } from '../utils/safeAccess';
import DataTable from '../components/DataTable';

type Row = {
  id?: string;
  asset_type?: string;
  ticker?: string;
  commodity_name?: string;
  category?: string;
  horizon?: string;
  final_score?: number;
  direction?: string;
  confidence?: number;
  expected_return?: number;
}

type ApiForecastsPayload = {
  rows: Row[];
  count?: number;
  asset_type?: string;
  freshness?: string;
  last_update?: string;
}

async function fetchForecastsFromApi(): Promise<ApiForecastsPayload> {
  const res = await apiGet<ApiForecastsPayload>(`/forecasts`, { asset_type: 'all', horizon: 'all', sort_by: 'score' });
  const data = (res as any).data as ApiForecastsPayload | undefined;
  if (res.ok && data) {
    const safeRows = Array.isArray(data.rows) ? data.rows : [];
    return { ...data, rows: safeRows };
  }
  return { rows: [] } as ApiForecastsPayload;
}

export default function Forecasts() {
  const [rawData, setRawData] = useState<ApiForecastsPayload | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setErr(null);
    try {
      const payload = await fetchForecastsFromApi();
      setRawData(payload);
    } catch (e: any) {
      setErr(e?.message || 'Erreur de chargement');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const freshness = rawData?.freshness ?? rawData?.last_update ?? null;

  const rows = useMemo(() => {
    const arr = safeArray(rawData?.rows ?? []);
    return arr.map((r, i) => ({ id: r.id ?? `${r.ticker ?? r.commodity_name ?? 'r'}-${r.horizon ?? 'h'}-${i}`, ...r }));
  }, [rawData]);

  const columns: GridColDef[] = useMemo(() => ([
    { field: 'asset_type', headerName: 'Type', width: 120 },
    { field: 'ticker', headerName: 'Symbole', width: 140 },
    { field: 'commodity_name', headerName: 'Nom', width: 180 },
    { field: 'horizon', headerName: 'Horizon', width: 110 },
  { field: 'final_score', headerName: 'Score', width: 100, type: 'number', valueFormatter: (params: GridValueFormatterParams) => params.value != null ? (params.value as number).toFixed(2) : '-' },
    { field: 'direction', headerName: 'Dir', width: 90 },
  { field: 'confidence', headerName: 'Conf', width: 100, type: 'number', valueFormatter: (p: GridValueFormatterParams) => p.value != null ? `${(p.value as number * 100).toFixed(0)}%` : '-' },
  { field: 'expected_return', headerName: 'ER', width: 120, type: 'number', valueFormatter: (p: GridValueFormatterParams) => p.value != null ? `${(p.value as number * 100).toFixed(2)}%` : '-' },
  ]), []);

  return (
    <Container maxWidth="lg" sx={{ py: 2 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
        <Typography variant="h5">Prévisions</Typography>
        <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
          <FreshnessBadge freshness={freshness ?? undefined} stale={freshness ? (Date.now() - new Date(freshness).getTime() > 3600000) : false} />
          <Button variant="outlined" onClick={load} disabled={loading}>Rafraîchir</Button>
        </Box>
      </Box>

      {loading && <Skeleton variant="rectangular" height={320} />}
      {err && <Alert severity="error">{err}</Alert>}

      {!loading && !err && rows.length === 0 && (
        <EmptyState title="Aucune prévision disponible" hint={freshness ? `Dernière mise à jour: ${new Date(freshness).toLocaleString()}` : 'Le modèle calcule en arrière-plan…'} />
      )}

      {!loading && !err && rows.length > 0 && (
        <DataTable 
          title="Tableau des Prévisions" 
          columns={columns} 
          rows={rows} 
          loading={loading} 
          error={null} 
          toolbar={true} 
          defaultPageSize={25} 
          pageSizeOptions={[10, 25, 50, 100]}
          height={520}
        />
      )}
    </Container>
  );
}
