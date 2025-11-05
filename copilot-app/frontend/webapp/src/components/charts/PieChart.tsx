import React from 'react';
import { PieChart as MuiPieChart, PiePlot, ChartsTooltip, ChartsLegend, ResponsiveChartContainer, PieValueType } from '@mui/x-charts';
import { Paper, Typography, Box, CircularProgress, Alert } from '@mui/material';
import { ErrorOutline as ErrorIcon } from '@mui/icons-material';

interface PieChartProps {
  title?: string;
  data: PieValueType[];
  loading?: boolean;
  error?: string;
  height?: number;
  width?: number;
  innerRadius?: number;
  outerRadius?: number;
}

const PieChart: React.FC<PieChartProps> = ({ 
  title, 
  data, 
  loading = false, 
  error, 
  height = 400,
  width,
  innerRadius = 30,
  outerRadius = 100
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
        series={[
          {
            type: 'pie',
            data,
            innerRadius: `${innerRadius}%`,
            outerRadius: `${outerRadius}%`,
            paddingAngle: 5,
            cornerRadius: 5,
            startAngle: 0,
            endAngle: 360,
          },
        ]}
        height={height}
        width={width}
      >
        <PiePlot />
        <ChartsTooltip />
        <ChartsLegend />
      </ResponsiveChartContainer>
    </Paper>
  );
};

export default PieChart;