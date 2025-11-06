import { useMemo } from 'react';
import { useNews } from './useNews';
import type { NewsArticle } from '@/types/news';

/**
 * News Signal Data for visualization
 */
export interface NewsSignalData {
  ticker: string;
  count: number; // Number of articles (size in treemap)
  avgSentiment: number; // Average sentiment (0=negative, 0.5=neutral, 1=positive)
  sentiment: 'positive' | 'neutral' | 'negative'; // Categorical sentiment
  recentNews: NewsArticle[]; // Latest articles for this ticker
  freshness: number; // Minutes since last article
  sector?: string; // Optional sector classification
}

/**
 * Filters for news signals
 */
export interface NewsSignalsFilters {
  sector?: string;
  timeframe?: '24h' | '7d' | '30d';
  minArticles?: number;
}

/**
 * Get minutes elapsed since timestamp
 */
function getMinutesSince(timestamp?: string): number {
  if (!timestamp) return Infinity;
  try {
    const date = new Date(timestamp);
    const now = new Date();
    return Math.floor((now.getTime() - date.getTime()) / (1000 * 60));
  } catch {
    return Infinity;
  }
}

/**
 * Convert sentiment string to numeric score
 */
function sentimentToScore(sentiment?: 'pos' | 'neg' | 'neu'): number {
  if (!sentiment) return 0.5; // Neutral default
  switch (sentiment) {
    case 'pos':
      return 1.0;
    case 'neg':
      return 0.0;
    case 'neu':
      return 0.5;
    default:
      return 0.5;
  }
}

/**
 * Convert numeric sentiment score to category
 */
function scoreToCategorical(score: number): 'positive' | 'neutral' | 'negative' {
  if (score > 0.6) return 'positive';
  if (score < 0.4) return 'negative';
  return 'neutral';
}

/**
 * Get sector for ticker (simple heuristic, can be expanded)
 */
function getSector(ticker: string): string {
  // Tech
  if (['AAPL', 'MSFT', 'GOOGL', 'GOOG', 'META', 'NVDA', 'AMD', 'INTC', 'TSLA'].includes(ticker)) {
    return 'Technology';
  }
  // Finance
  if (['JPM', 'BAC', 'GS', 'MS', 'C', 'WFC'].includes(ticker)) {
    return 'Finance';
  }
  // Healthcare
  if (['JNJ', 'PFE', 'UNH', 'ABBV', 'TMO', 'MRK'].includes(ticker)) {
    return 'Healthcare';
  }
  // Energy
  if (['XOM', 'CVX', 'COP', 'SLB', 'EOG'].includes(ticker)) {
    return 'Energy';
  }
  // Consumer
  if (['AMZN', 'WMT', 'HD', 'MCD', 'NKE', 'SBUX', 'PG', 'KO'].includes(ticker)) {
    return 'Consumer';
  }
  // ETFs / Indices
  if (['SPY', 'QQQ', 'IWM', 'DIA', 'TLT', 'GLD', 'VIX'].includes(ticker)) {
    return 'ETF/Index';
  }
  return 'Other';
}

/**
 * Hook to process news data into signals for visualization
 */
export function useNewsSignals(
  tickers: string[],
  filters?: NewsSignalsFilters
): {
  data: NewsSignalData[];
  isLoading: boolean;
  isError: boolean;
  totalArticles: number;
  sentimentDistribution: { positive: number; neutral: number; negative: number };
} {
  // Fetch news with extended limit to get more data
  const { data: news, isLoading, isError } = useNews(tickers, undefined);

  const processedData = useMemo(() => {
    if (!news || news.length === 0) {
      return {
        data: [],
        totalArticles: 0,
        sentimentDistribution: { positive: 0, neutral: 0, negative: 0 },
      };
    }

    // Group articles by ticker
    const byTicker: Record<string, NewsArticle[]> = {};
    
    news.forEach((article) => {
      // An article can be associated with multiple tickers
      const articleTickers = article.tickers || [];
      
      // If no tickers specified, try to extract from title or use 'GENERAL'
      if (articleTickers.length === 0) {
        // Try to find ticker mentions in title
        const foundTickers = tickers.filter(t => 
          article.title.toUpperCase().includes(t.toUpperCase())
        );
        
        if (foundTickers.length > 0) {
          foundTickers.forEach(ticker => {
            if (!byTicker[ticker]) byTicker[ticker] = [];
            byTicker[ticker].push(article);
          });
        } else {
          // General news not specific to a ticker
          if (!byTicker['GENERAL']) byTicker['GENERAL'] = [];
          byTicker['GENERAL'].push(article);
        }
      } else {
        articleTickers.forEach((ticker) => {
          if (!byTicker[ticker]) byTicker[ticker] = [];
          byTicker[ticker].push(article);
        });
      }
    });

    // Calculate stats per ticker
    const signals: NewsSignalData[] = Object.entries(byTicker)
      .map(([ticker, articles]) => {
        // Sort by date (most recent first)
        const sortedArticles = [...articles].sort((a, b) => {
          const dateA = a.publishedAt ? new Date(a.publishedAt).getTime() : 0;
          const dateB = b.publishedAt ? new Date(b.publishedAt).getTime() : 0;
          return dateB - dateA;
        });

        // Calculate average sentiment
        const sentimentScores = articles
          .filter(a => a.sentiment)
          .map(a => sentimentToScore(a.sentiment));
        
        const avgSentiment = sentimentScores.length > 0
          ? sentimentScores.reduce((sum, score) => sum + score, 0) / sentimentScores.length
          : 0.5;

        // Get freshness (minutes since most recent article)
        const freshness = sortedArticles.length > 0
          ? getMinutesSince(sortedArticles[0].publishedAt)
          : Infinity;

        return {
          ticker,
          count: articles.length,
          avgSentiment,
          sentiment: scoreToCategorical(avgSentiment),
          recentNews: sortedArticles.slice(0, 3), // Top 3 most recent
          freshness,
          sector: getSector(ticker),
        };
      })
      .filter(signal => {
        // Apply filters
        if (filters?.sector && signal.sector !== filters.sector) {
          return false;
        }
        if (filters?.minArticles && signal.count < filters.minArticles) {
          return false;
        }
        // Timeframe filter (freshness)
        if (filters?.timeframe) {
          const maxMinutes = {
            '24h': 24 * 60,
            '7d': 7 * 24 * 60,
            '30d': 30 * 24 * 60,
          }[filters.timeframe];
          
          if (signal.freshness > maxMinutes) {
            return false;
          }
        }
        return true;
      })
      .sort((a, b) => b.count - a.count); // Sort by count (most articles first)

    // Calculate sentiment distribution
    const sentimentDist = signals.reduce(
      (acc, signal) => {
        acc[signal.sentiment] += signal.count;
        return acc;
      },
      { positive: 0, neutral: 0, negative: 0 }
    );

    const totalArticles = signals.reduce((sum, s) => sum + s.count, 0);

    return {
      data: signals,
      totalArticles,
      sentimentDistribution: sentimentDist,
    };
  }, [news, filters]);

  return {
    data: processedData.data,
    isLoading,
    isError,
    totalArticles: processedData.totalArticles,
    sentimentDistribution: processedData.sentimentDistribution,
  };
}
