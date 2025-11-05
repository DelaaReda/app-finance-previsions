import React from 'react';
import { LineChart as MuiLineChart, LinePlot, ChartsGrid, ChartsXAxis, ChartsYAxis, ChartsTooltip, ChartsLegend, ResponsiveChartContainer, LineSeriesType } from '@mui/x-charts';
import { Paper, Typography, Box, CircularProgress, Alert } from '@mui/material';
import { ErrorOutline as ErrorIcon } from '@mui/icons-material';

interface LineChartProps {
  title?: string;
  data: LineSeriesType[];
  xAxisLabel?: string;
  yAxisLabel?: string;
  loading?: boolean;
  error?: string;
  height?: number;
  width?: number;
}

const LineChart: React.FC<LineChartProps> = ({ 
  title, 
  data, 
  xAxisLabel, 
  yAxisLabel, 
  loading = false, 
  error, 
  height = 400,
  width 
}) => {
  if (loading) {
    return (
      <Paper sx={{ p: 2, height: height, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <CircularProgress />
      </Paper>
    );
  }

  if (error) {
    return (
      <Paper sx={{ p: 2 }}>
        <Alert severity="error" icon={<ErrorIcon />}>
          <Typography variant="subtitle1">Erreur de chargement du graphique</Typography>
          <Typography variant="body2">{error}</Typography>
        </Alert>
      </Paper>
    );
  }

  if (!data || data.length === 0) {
    return (
      <Paper sx={{ p: 2 }}>
        <Typography variant="body1" align="center" color="text.secondary">
          Aucune donnée disponible
        </Typography>
      </Paper>
    );
  }

  return (
    <Paper sx={{ p: 2, height: height }}>
      {title && (
        <Typography variant="h6" component="h3" gutterBottom>
          {title}
        </Typography>
      )}
      <ResponsiveChartContainer
        series={data}
        xAxis={[
          {
            data: data[0]?.data?.map((_: any, i: number) => i) || [],
            scaleType: 'band',
            label: xAxisLabel,
          },
        ]}
        height={height}
        width={width}
      >
        <LinePlot />
        <ChartsGrid vertical={false} horizontal={true} />
        <ChartsXAxis label={xAxisLabel} />
        <ChartsYAxis label={yAxisLabel} />
        <ChartsTooltip />
        <ChartsLegend />
      </ResponsiveChartContainer>
    </Paper>
  );
};

export default LineChart;