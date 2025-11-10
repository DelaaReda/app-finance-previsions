import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { 
  TrendingUp, 
  TrendingDown, 
  DollarSign, 
  Users, 
  ShoppingCart, 
  Activity,
  PieChart,
  BarChart3,
  LineChart,
  Calendar,
  Filter,
  Download,
  RefreshCw
} from 'lucide-react';
import { MetricCard, MetricGrid } from '@/components/metrics/MetricCard';
import FinancialChart from '@/components/charts/FinancialChart';
import { Button } from '@/components/ui/Button';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { formatCurrency, formatPercentage, formatNumber } from '@/lib/utils';

const Dashboard: React.FC = () => {
  const [selectedPeriod, setSelectedPeriod] = useState('7d');
  const [isLoading, setIsLoading] = useState(false);
  const [revenueData, setRevenueData] = useState<any[]>([]);
  const [portfolioData, setPortfolioData] = useState<any[]>([]);
  const [marketData, setMarketData] = useState<any[]>([]);

  // Mock data generation
  useEffect(() => {
    generateMockData();
  }, [selectedPeriod]);

  const generateMockData = () => {
    // Revenue trend data
    const revenue = Array.from({ length: 30 }, (_, i) => ({
      name: `Day ${i + 1}`,
      revenue: Math.floor(Math.random() * 50000) + 100000,
      profit: Math.floor(Math.random() * 20000) + 30000,
      expenses: Math.floor(Math.random() * 30000) + 50000,
    }));
    setRevenueData(revenue);

    // Portfolio allocation data
    const portfolio = [
      { name: 'Stocks', value: 45 },
      { name: 'Bonds', value: 25 },
      { name: 'Real Estate', value: 15 },
      { name: 'Commodities', value: 10 },
      { name: 'Cash', value: 5 },
    ];
    setPortfolioData(portfolio);

    // Market performance data
    const market = Array.from({ length: 12 }, (_, i) => ({
      name: `Month ${i + 1}`,
      sp500: Math.floor(Math.random() * 500) + 4000,
      nasdaq: Math.floor(Math.random() * 1000) + 12000,
      dow: Math.floor(Math.random() * 2000) + 33000,
    }));
    setMarketData(market);
  };

  const handleRefresh = () => {
    setIsLoading(true);
    setTimeout(() => {
      generateMockData();
      setIsLoading(false);
    }, 1000);
  };

  const metrics = [
    {
      title: 'Total Revenue',
      value: 2456789,
      change: 12.5,
      currency: true,
      icon: <DollarSign className="w-5 h-5 text-primary" />,
      trend: 'up' as const,
    },
    {
      title: 'Portfolio Value',
      value: 1567890,
      change: 8.3,
      currency: true,
      icon: <TrendingUp className="w-5 h-5 text-success" />,
      trend: 'up' as const,
    },
    {
      title: 'Active Users',
      value: 45678,
      change: -2.1,
      icon: <Users className="w-5 h-5 text-warning" />,
      trend: 'down' as const,
    },
    {
      title: 'Conversion Rate',
      value: 3.45,
      change: 0.8,
      percentage: true,
      icon: <Activity className="w-5 h-5 text-accent" />,
      trend: 'up' as const,
    },
  ];

  return (
    <div className="min-h-screen bg-bg p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <motion.div 
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="mb-8"
        >
          <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
            <div>
              <h1 className="text-3xl font-bold gradient-text mb-2">Financial Dashboard</h1>
              <p className="text-muted">Monitor your financial performance and market trends</p>
            </div>
            
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2 bg-surface rounded-lg p-1 border border-border">
                {['24h', '7d', '30d', '90d'].map((period) => (
                  <button
                    key={period}
                    onClick={() => setSelectedPeriod(period)}
                    className={`px-3 py-1 rounded-md text-sm font-medium transition-colors ${
                      selectedPeriod === period
                        ? 'bg-primary text-white'
                        : 'text-muted hover:text-text'
                    }`}
                  >
                    {period}
                  </button>
                ))}
              </div>
              
              <Button
                onClick={handleRefresh}
                loading={isLoading}
                leftIcon={<RefreshCw className="w-4 h-4" />}
              >
                Refresh
              </Button>
              
              <Button
                variant="secondary"
                leftIcon={<Download className="w-4 h-4" />}
              >
                Export
              </Button>
            </div>
          </div>
        </motion.div>

        {/* Metrics Grid */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1 }}
          className="mb-8"
        >
          <MetricGrid>
            {metrics.map((metric, index) => (
              <motion.div
                key={metric.title}
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.3, delay: index * 0.1 }}
              >
                <MetricCard {...metric} />
              </motion.div>
            ))}
          </MetricGrid>
        </motion.div>

        {/* Charts Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          {/* Revenue Trend */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.5, delay: 0.2 }}
          >
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <LineChart className="w-5 h-5 text-primary" />
                  Revenue Trend
                </CardTitle>
              </CardHeader>
              <CardContent>
                <FinancialChart
                  data={revenueData.slice(-14)}
                  type="area"
                  height={300}
                  colors={['#3b82f6', '#10b981', '#ef4444']}
                />
              </CardContent>
            </Card>
          </motion.div>

          {/* Portfolio Allocation */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.5, delay: 0.3 }}
          >
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <PieChart className="w-5 h-5 text-primary" />
                  Portfolio Allocation
                </CardTitle>
              </CardHeader>
              <CardContent>
                <FinancialChart
                  data={portfolioData}
                  type="pie"
                  height={300}
                  colors={['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6']}
                />
              </CardContent>
            </Card>
          </motion.div>
        </div>

        {/* Market Performance */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.4 }}
          className="mb-8"
        >
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <BarChart3 className="w-5 h-5 text-primary" />
                Market Performance
              </CardTitle>
            </CardHeader>
            <CardContent>
              <FinancialChart
                data={marketData}
                type="line"
                height={400}
                colors={['#3b82f6', '#10b981', '#f59e0b']}
              />
            </CardContent>
          </Card>
        </motion.div>

        {/* Recent Activity */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.5 }}
        >
          <Card>
            <CardHeader>
              <CardTitle>Recent Activity</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {[
                  { action: 'Portfolio rebalanced', time: '2 hours ago', type: 'success' },
                  { action: 'Market alert triggered', time: '4 hours ago', type: 'warning' },
                  { action: 'New investment made', time: '6 hours ago', type: 'info' },
                  { action: 'Risk assessment updated', time: '8 hours ago', type: 'success' },
                ].map((activity, index) => (
                  <div key={index} className="flex items-center justify-between py-3 border-b border-border last:border-0">
                    <div className="flex items-center gap-3">
                      <div className={`w-2 h-2 rounded-full ${
                        activity.type === 'success' ? 'bg-success' :
                        activity.type === 'warning' ? 'bg-warning' :
                        activity.type === 'error' ? 'bg-danger' : 'bg-primary'
                      }`} />
                      <span className="text-text">{activity.action}</span>
                    </div>
                    <span className="text-sm text-muted">{activity.time}</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </div>
    </div>
  );
};

export default Dashboard;