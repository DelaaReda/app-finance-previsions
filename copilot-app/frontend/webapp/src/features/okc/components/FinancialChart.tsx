import {
  LineChart,
  Line,
  AreaChart,
  Area,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { Card } from '@/features/okc/components/Card';

export interface ChartDataPoint {
  name: string;
  [key: string]: number | string;
}

interface FinancialChartProps {
  data: ChartDataPoint[];
  type: 'line' | 'area' | 'bar' | 'pie';
  height?: number;
  title?: string;
  colors?: string[];
}

const defaultColors = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4'];

export function FinancialChart({ data, type, height = 280, title, colors = defaultColors }: FinancialChartProps) {
  if (!data || data.length === 0) {
    return (
      <Card>
        <p className="text-sm text-muted">Aucune donnée disponible</p>
      </Card>
    );
  }

  const keys = Object.keys(data[0]).filter((key) => key !== 'name');

  const tooltipStyles = {
    contentStyle: {
      backgroundColor: 'rgba(26, 31, 46, 0.9)',
      border: '1px solid rgba(255, 255, 255, 0.1)',
      borderRadius: '8px',
      backdropFilter: 'blur(10px)',
    },
    labelStyle: { color: '#f8fafc' },
    itemStyle: { color: '#f8fafc' },
  } as const;

  const renderChart = () => {
    switch (type) {
      case 'line':
        return (
          <ResponsiveContainer width="100%" height={height}>
            <LineChart data={data} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
              <XAxis dataKey="name" stroke="#8892a0" tickLine={false} fontSize={12} />
              <YAxis stroke="#8892a0" tickLine={false} fontSize={12} />
              <Tooltip {...tooltipStyles} />
              <Legend />
              {keys.map((key, index) => (
                <Line
                  key={key}
                  type="monotone"
                  dataKey={key}
                  stroke={colors[index % colors.length]}
                  strokeWidth={2}
                  dot={{ r: 4 }}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        );
      case 'area':
        return (
          <ResponsiveContainer width="100%" height={height}>
            <AreaChart data={data} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
              <defs>
                {colors.map((color, index) => (
                  <linearGradient key={color} id={`okcColor${index}`} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={color} stopOpacity={0.8} />
                    <stop offset="95%" stopColor={color} stopOpacity={0.1} />
                  </linearGradient>
                ))}
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
              <XAxis dataKey="name" stroke="#8892a0" tickLine={false} fontSize={12} />
              <YAxis stroke="#8892a0" tickLine={false} fontSize={12} />
              <Tooltip {...tooltipStyles} />
              <Legend />
              {keys.map((key, index) => (
                <Area key={key} type="monotone" dataKey={key} stroke={colors[index % colors.length]} fill={`url(#okcColor${index})`} strokeWidth={2} />
              ))}
            </AreaChart>
          </ResponsiveContainer>
        );
      case 'bar':
        return (
          <ResponsiveContainer width="100%" height={height}>
            <BarChart data={data} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
              <XAxis dataKey="name" stroke="#8892a0" tickLine={false} fontSize={12} />
              <YAxis stroke="#8892a0" tickLine={false} fontSize={12} />
              <Tooltip {...tooltipStyles} />
              <Legend />
              {keys.map((key, index) => (
                <Bar key={key} dataKey={key} fill={colors[index % colors.length]} radius={[4, 4, 0, 0]} />
              ))}
            </BarChart>
          </ResponsiveContainer>
        );
      case 'pie':
        return (
          <ResponsiveContainer width="100%" height={height}>
            <PieChart>
              <Pie data={data} dataKey="value" outerRadius={80} labelLine={false} label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}>
                {data.map((entry, index) => (
                  <Cell key={entry.name} fill={colors[index % colors.length]} />
                ))}
              </Pie>
              <Tooltip {...tooltipStyles} />
            </PieChart>
          </ResponsiveContainer>
        );
      default:
        return null;
    }
  };

  return (
    <Card>
      {title && <h3 className="text-lg font-semibold text-text mb-4">{title}</h3>}
      {renderChart()}
    </Card>
  );
}
