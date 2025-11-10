import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { 
  Filter, 
  Search, 
  Calendar, 
  TrendingUp, 
  Target,
  Activity,
  BarChart3,
  RefreshCw,
  Download,
  Plus
} from 'lucide-react';
import { Forecast, ForecastGrid } from '@/components/forecasts/ForecastCard';
import { Button } from '@/components/ui/Button';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import FinancialChart from '@/components/charts/FinancialChart';
import { formatCurrency, formatPercentage } from '@/lib/utils';

const Forecasts: React.FC = () => {
  const [selectedPeriod, setSelectedPeriod] = useState('30d');
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [expandedForecastId, setExpandedForecastId] = useState<string | undefined>();
  const [isLoading, setIsLoading] = useState(false);

  // Mock forecast data
  const mockForecasts: Forecast[] = [
    {
      id: '1',
      title: 'S&P 500 Index',
      currentValue: 4567.89,
      predictedValue: 4789.45,
      confidence: 85,
      timeframe: 'Next 30 days',
      trend: 'bullish',
      type: 'price',
      rationale: 'Strong economic indicators and positive earnings reports suggest continued market growth. Technical analysis supports upward momentum.',
      factors: [
        'Positive GDP growth projections',
        'Strong corporate earnings',
        'Low unemployment rates',
        'Federal Reserve policy stability'
      ],
      lastUpdated: new Date('2024-01-15'),
    },
    {
      id: '2',
      title: 'Bitcoin Price',
      currentValue: 43250,
      predictedValue: 38900,
      confidence: 72,
      timeframe: 'Next 14 days',
      trend: 'bearish',
      type: 'price',
      rationale: 'Regulatory concerns and market volatility suggest potential downward pressure. Institutional adoption remains cautious.',
      factors: [
        'Regulatory uncertainty',
        'Market volatility increase',
        'Profit-taking behavior',
        'Technical resistance levels'
      ],
      lastUpdated: new Date('2024-01-14'),
    },
    {
      id: '3',
      title: 'EUR/USD Exchange Rate',
      currentValue: 1.0890,
      predictedValue: 1.0920,
      confidence: 78,
      timeframe: 'Next 7 days',
      trend: 'neutral',
      type: 'price',
      rationale: 'Central bank policies and economic data suggest stable trading range with slight upward bias.',
      factors: [
        'ECB policy decisions',
        'US inflation data',
        'Trade balance figures',
        'Political stability indicators'
      ],
      lastUpdated: new Date('2024-01-13'),
    },
    {
      id: '4',
      title: 'Gold Futures',
      currentValue: 2034.50,
      predictedValue: 2089.75,
      confidence: 82,
      timeframe: 'Next 21 days',
      trend: 'bullish',
      type: 'price',
      rationale: 'Inflation hedging demand and geopolitical tensions support precious metals. Dollar weakness expected.',
      factors: [
        'Inflation expectations rising',
        'Geopolitical tensions',
        'Dollar index decline',
        'Central bank gold purchases'
      ],
      lastUpdated: new Date('2024-01-12'),
    },
    {
      id: '5',
      title: 'Tesla Stock (TSLA)',
      currentValue: 218.45,
      predictedValue: 245.80,
      confidence: 76,
      timeframe: 'Next 45 days',
      trend: 'bullish',
      type: 'price',
      rationale: 'Strong delivery numbers and expansion plans support positive outlook. EV market growth continues.',
      factors: [
        'Q4 delivery beat expectations',
        'New factory announcements',
        'EV market growth',
        'Technology advancement'
      ],
      lastUpdated: new Date('2024-01-11'),
    },
    {
      id: '6',
      title: 'Oil Prices (WTI)',
      currentValue: 74.20,
      predictedValue: 69.80,
      confidence: 69,
      timeframe: 'Next 30 days',
      trend: 'bearish',
      type: 'price',
      rationale: 'Increased supply and reduced demand expectations weigh on oil prices. Global economic slowdown concerns.',
      factors: [
        'OPEC+ production increases',
        'Global demand concerns',
        'Strategic reserve releases',
        'Alternative energy adoption'
      ],
      lastUpdated: new Date('2024-01-10'),
    },
  ];

  const [forecasts, setForecasts] = useState<Forecast[]>(mockForecasts);

  const filteredForecasts = forecasts.filter(forecast => {
    const matchesSearch = forecast.title.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesCategory = selectedCategory === 'all' || forecast.trend === selectedCategory;
    return matchesSearch && matchesCategory;
  });

  const handleRefresh = () => {
    setIsLoading(true);
    setTimeout(() => {
      // Simulate data refresh
      setForecasts(prev => prev.map(forecast => ({
        ...forecast,
        lastUpdated: new Date(),
        confidence: Math.max(60, Math.min(95, forecast.confidence + (Math.random() - 0.5) * 10)),
      })));
      setIsLoading(false);
    }, 1500);
  };

  const handleToggleForecast = (id: string) => {
    setExpandedForecastId(prev => prev === id ? undefined : id);
  };

  // Chart data for forecast accuracy
  const accuracyData = [
    { name: 'Week 1', accuracy: 92 },
    { name: 'Week 2', accuracy: 88 },
    { name: 'Week 3', accuracy: 85 },
    { name: 'Week 4', accuracy: 82 },
    { name: 'Week 5', accuracy: 79 },
    { name: 'Week 6', accuracy: 76 },
  ];

  // Forecast distribution data
  const distributionData = [
    { name: 'Bullish', value: 45 },
    { name: 'Bearish', value: 30 },
    { name: 'Neutral', value: 25 },
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
              <h1 className="text-3xl font-bold gradient-text mb-2">Financial Forecasts</h1>
              <p className="text-muted">AI-powered predictions and market analysis</p>
            </div>
            
            <div className="flex items-center gap-4">
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
              <Button
                leftIcon={<Plus className="w-4 h-4" />}
              >
                New Forecast
              </Button>
            </div>
          </div>
        </motion.div>

        {/* Filters */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1 }}
          className="mb-8"
        >
          <Card>
            <CardContent className="p-6">
              <div className="flex flex-col lg:flex-row lg:items-center gap-4">
                <div className="flex-1">
                  <div className="relative">
                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-muted" />
                    <input
                      type="text"
                      placeholder="Search forecasts..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      className="w-full pl-10 pr-4 py-2 bg-surface border border-border rounded-lg text-text placeholder-muted focus:outline-none focus:ring-2 focus:ring-primary"
                    />
                  </div>
                </div>
                
                <div className="flex items-center gap-4">
                  <div className="flex items-center gap-2">
                    <Filter className="w-5 h-5 text-muted" />
                    <select
                      value={selectedCategory}
                      onChange={(e) => setSelectedCategory(e.target.value)}
                      className="bg-surface border border-border rounded-lg px-3 py-2 text-text focus:outline-none focus:ring-2 focus:ring-primary"
                    >
                      <option value="all">All Trends</option>
                      <option value="bullish">Bullish</option>
                      <option value="bearish">Bearish</option>
                      <option value="neutral">Neutral</option>
                    </select>
                  </div>
                  
                  <div className="flex items-center gap-2">
                    <Calendar className="w-5 h-5 text-muted" />
                    <select
                      value={selectedPeriod}
                      onChange={(e) => setSelectedPeriod(e.target.value)}
                      className="bg-surface border border-border rounded-lg px-3 py-2 text-text focus:outline-none focus:ring-2 focus:ring-primary"
                    >
                      <option value="7d">Next 7 days</option>
                      <option value="14d">Next 14 days</option>
                      <option value="30d">Next 30 days</option>
                      <option value="90d">Next 90 days</option>
                    </select>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* Analytics Overview */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
          {/* Forecast Accuracy */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.5, delay: 0.2 }}
          >
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Activity className="w-5 h-5 text-primary" />
                  Forecast Accuracy
                </CardTitle>
              </CardHeader>
              <CardContent>
                <FinancialChart
                  data={accuracyData}
                  type="line"
                  height={200}
                  colors={['#10b981']}
                />
                <div className="mt-4 text-center">
                  <p className="text-2xl font-bold text-success">84.2%</p>
                  <p className="text-sm text-muted">Average accuracy</p>
                </div>
              </CardContent>
            </Card>
          </motion.div>

          {/* Trend Distribution */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.3 }}
          >
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <BarChart3 className="w-5 h-5 text-primary" />
                  Trend Distribution
                </CardTitle>
              </CardHeader>
              <CardContent>
                <FinancialChart
                  data={distributionData}
                  type="pie"
                  height={200}
                  colors={['#10b981', '#ef4444', '#f59e0b']}
                />
              </CardContent>
            </Card>
          </motion.div>

          {/* Performance Metrics */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.5, delay: 0.4 }}
          >
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Target className="w-5 h-5 text-primary" />
                  Performance
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-muted">Total Forecasts</span>
                  <span className="text-2xl font-bold text-text">{forecasts.length}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-muted">High Confidence</span>
                  <span className="text-2xl font-bold text-success">
                    {forecasts.filter(f => f.confidence >= 80).length}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-muted">Success Rate</span>
                  <span className="text-2xl font-bold text-primary">92.4%</span>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        </div>

        {/* Forecasts Grid */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.5 }}
        >
          <div className="mb-6">
            <h2 className="text-2xl font-bold text-text mb-2">
              Active Forecasts ({filteredForecasts.length})
            </h2>
            <p className="text-muted">Real-time predictions based on market analysis</p>
          </div>
          
          <ForecastGrid
            forecasts={filteredForecasts}
            expandedId={expandedForecastId}
            onToggle={handleToggleForecast}
          />
        </motion.div>

        {/* Empty State */}
        {filteredForecasts.length === 0 && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="text-center py-12"
          >
            <div className="w-16 h-16 bg-muted/20 rounded-full flex items-center justify-center mx-auto mb-4">
              <TrendingUp className="w-8 h-8 text-muted" />
            </div>
            <h3 className="text-lg font-semibold text-text mb-2">No forecasts found</h3>
            <p className="text-muted">Try adjusting your search criteria or filters</p>
          </motion.div>
        )}
      </div>
    </div>
  );
};

export default Forecasts;