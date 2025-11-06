/**
 * GlobalFreshness Component
 * Shows freshness status for key data sources: forecasts, news, brief
 */

import React, { useState, useEffect } from 'react';
import { Tooltip } from '@/ui';
import { apiGet } from '../../api/client';
import type { LegacyHealthData } from '../../hooks/useHealth';

interface FreshnessData {
  forecasts: string | number | null;
  news: string | number | null;
  brief: string | number | null;
  brief_weekly: string | number | null;
  timestamp: string | null;
}

interface FreshnessStatus {
  status: 'fresh' | 'stale' | 'unknown';
  minutes: number | null;
}

const checkFreshness = (timestamp: string | number | null): FreshnessStatus => {
  if (!timestamp) {
    return { status: 'unknown', minutes: null };
  }

  try {
    // Handle both ISO string and Unix timestamp formats
    let updateDate: Date;
    if (typeof timestamp === 'number') {
      // Unix timestamp in seconds or milliseconds (check if it's too large to be seconds)
      updateDate = timestamp > 1e10 ? new Date(timestamp) : new Date(timestamp * 1000);
    } else {
      updateDate = new Date(timestamp);
    }
    
    const now = new Date();
    const diffMinutes = Math.round((now.getTime() - updateDate.getTime()) / (1000 * 60));

    if (diffMinutes < 15) {
      return { status: 'fresh', minutes: diffMinutes };
    } else if (diffMinutes < 60) {
      return { status: 'stale', minutes: diffMinutes };
    } else {
      return { status: 'stale', minutes: diffMinutes };
    }
  } catch (error) {
    return { status: 'unknown', minutes: null };
  }
};

export default function GlobalFreshness() {
  const [freshnessData, setFreshnessData] = useState<FreshnessData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchFreshness = async () => {
      setLoading(true);
      setError(null);

      try {
        const response = await apiGet<LegacyHealthData>('/health');

        if (response.ok && response.data) {
          const healthData = response.data as LegacyHealthData;
          const lastUpdates = healthData.last_updates || {};

          setFreshnessData({
            forecasts: lastUpdates.forecasts || null,
            news: lastUpdates.news || null,
            brief: lastUpdates.brief || null,
            brief_weekly: lastUpdates.brief_weekly || null,
            timestamp: healthData.timestamp || null
          });
        } else {
          setError(response.error || 'Réponse inattendue de l\'API');
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Erreur de chargement des données de fraîcheur');
      } finally {
        setLoading(false);
      }
    };

    // Fetch immediately
    fetchFreshness();

    // Refresh every 5 minutes
    const interval = setInterval(fetchFreshness, 5 * 60 * 1000);

    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div style={styles.container}>
        <span style={{ ...styles.freshnessText, color: '#666' }}>Fraîcheur: Chargement...</span>
      </div>
    );
  }

  if (error || !freshnessData) {
    return (
      <div style={styles.container}>
        <span style={{ ...styles.freshnessText, color: '#f44336' }}>Fraîcheur: Erreur</span>
      </div>
    );
  }

  // Calculate freshness for each data source
  const forecastsStatus = checkFreshness(freshnessData.forecasts);
  const newsStatus = checkFreshness(freshnessData.news);
  const briefStatus = checkFreshness(freshnessData.brief);
  const briefWeeklyStatus = checkFreshness(freshnessData.brief_weekly);

  // Determine overall status (use worst status among all sources)
  const overallStatus = [forecastsStatus, newsStatus, briefStatus, briefWeeklyStatus].some(
    s => s.status === 'stale'
  ) ? 'stale' : 
  [forecastsStatus, newsStatus, briefStatus, briefWeeklyStatus].some(
    s => s.status === 'fresh'
  ) ? 'fresh' : 'unknown';

  // Determine icon and color based on status
  let icon = '⏱️';
  let color = '#666';
  let statusText = 'Inconnu';

  if (overallStatus === 'fresh') {
    icon = '✅';
    color = '#4caf50';
    statusText = 'Fraîche';
  } else if (overallStatus === 'stale') {
    icon = '⏰';
    color = '#ff9800';
    statusText = 'Ancienne';
  }

  // Create detailed tooltip
  const tooltipContent = (
    <div style={{ padding: '8px' }}>
      <div style={{ marginBottom: '4px', fontWeight: 'bold' }}>Status de fraîcheur des données:</div>
      <div>Forecasts: {forecastsStatus.minutes !== null ? `${forecastsStatus.minutes} min` : 'N/A'} {forecastsStatus.status === 'fresh' ? '✅' : '⏰'}</div>
      <div>News: {newsStatus.minutes !== null ? `${newsStatus.minutes} min` : 'N/A'} {newsStatus.status === 'fresh' ? '✅' : '⏰'}</div>
      <div>Brief: {briefStatus.minutes !== null ? `${briefStatus.minutes} min` : 'N/A'} {briefStatus.status === 'fresh' ? '✅' : '⏰'}</div>
      <div>Brief hebdo: {briefWeeklyStatus.minutes !== null ? `${briefWeeklyStatus.minutes} min` : 'N/A'} {briefWeeklyStatus.status === 'fresh' ? '✅' : '⏰'}</div>
    </div>
  );

  return (
    <Tooltip label={tooltipContent} position="bottom">
      <div style={styles.container}>
        <span style={{ ...styles.freshnessText, color }}>
          {icon} {statusText}
        </span>
      </div>
    </Tooltip>
  );
}

const styles = {
  container: {
    display: 'flex',
    alignItems: 'center',
    padding: '4px 8px',
    borderRadius: '4px',
    backgroundColor: '#222',
    cursor: 'help',
  } as React.CSSProperties,
  freshnessText: {
    fontSize: '12px',
    fontWeight: 500,
  } as React.CSSProperties,
};
