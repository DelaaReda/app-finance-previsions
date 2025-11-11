/**
 * Robustness Score Card Component
 * Displays the robustness score along with detailed metrics
 */

import React from 'react';
import { Ring } from '@/ui/Ring';
import { Card } from '@/components/common/Card';

interface RobustnessScoreCardProps {
  score: number;
  grade: string;
  metrics: {
    cagr?: number;
    maxDrawdown?: number;
    winRate?: number;
    totalTrades?: number;
    sharpeRatio?: number;
    hitRate?: number;
  };
  title?: string;
  showDetails?: boolean;
}

export const RobustnessScoreCard: React.FC<RobustnessScoreCardProps> = ({ 
  score, 
  grade, 
  metrics, 
  title = 'Robustness Score', 
  showDetails = true 
}) => {
  // Determine card color scheme based on score
  const getGradeColor = (grade: string) => {
    switch(grade) {
      case 'S': return { bg: '#DCFCE7', border: '#16A34A', text: '#15803D' }; // Green
      case 'A': return { bg: '#DCFCE7', border: '#16A34A', text: '#15803D' }; // Green
      case 'B': return { bg: '#D1FAE5', border: '#059669', text: '#047857' }; // Green-Teal
      case 'C': return { bg: '#FEF3C7', border: '#D97706', text: '#D97706' }; // Amber
      case 'D': return { bg: '#FEE2E2', border: '#DC2626', text: '#DC2626' }; // Red
      case 'E': return { bg: '#F3F4F6', border: '#6B7280', text: '#6B7280' }; // Gray
      default: return { bg: '#F3F4F6', border: '#6B7280', text: '#6B7280' };
    }
  };

  const colorScheme = getGradeColor(grade);

  return (
    <Card 
      style={{
        border: `1px solid ${colorScheme.border}`,
        backgroundColor: colorScheme.bg
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '1rem' }}>
        <Ring 
          value={score} 
          label="" 
          size={80}
        />
        <div>
          <h3 style={{ 
            margin: 0, 
            fontSize: '1.2rem', 
            color: colorScheme.text,
            fontWeight: 'bold'
          }}>
            {title}
          </h3>
          <div style={{ 
            fontSize: '1.5rem', 
            fontWeight: 'bold', 
            color: colorScheme.text,
            marginTop: '0.25rem'
          }}>
            Grade: <span style={{ fontSize: '2rem' }}>{grade}</span>
          </div>
        </div>
      </div>
      
      {showDetails && (
        <div style={{ 
          display: 'grid', 
          gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', 
          gap: '0.75rem',
          marginTop: '1rem'
        }}>
          <div style={{ padding: '0.5rem', textAlign: 'center' }}>
            <div style={{ fontSize: '0.8rem', color: '#6B7280' }}>CAGR</div>
            <div style={{ fontWeight: 'bold' }}>
              {metrics.cagr !== undefined ? `${(metrics.cagr * 100).toFixed(1)}%` : 'N/A'}
            </div>
          </div>
          
          <div style={{ padding: '0.5rem', textAlign: 'center' }}>
            <div style={{ fontSize: '0.8rem', color: '#6B7280' }}>Max DD</div>
            <div style={{ fontWeight: 'bold', color: '#DC2626' }}>
              {metrics.maxDrawdown !== undefined ? `-${(metrics.maxDrawdown * 100).toFixed(1)}%` : 'N/A'}
            </div>
          </div>
          
          <div style={{ padding: '0.5rem', textAlign: 'center' }}>
            <div style={{ fontSize: '0.8rem', color: '#6B7280' }}>Win Rate</div>
            <div style={{ fontWeight: 'bold' }}>
              {metrics.winRate !== undefined ? `${(metrics.winRate * 100).toFixed(1)}%` : 'N/A'}
            </div>
          </div>
          
          <div style={{ padding: '0.5rem', textAlign: 'center' }}>
            <div style={{ fontSize: '0.8rem', color: '#6B7280' }}>Trades</div>
            <div style={{ fontWeight: 'bold' }}>
              {metrics.totalTrades !== undefined ? metrics.totalTrades : 'N/A'}
            </div>
          </div>
          
          <div style={{ padding: '0.5rem', textAlign: 'center' }}>
            <div style={{ fontSize: '0.8rem', color: '#6B7280' }}>Sharpe</div>
            <div style={{ fontWeight: 'bold' }}>
              {metrics.sharpeRatio !== undefined ? metrics.sharpeRatio.toFixed(2) : 'N/A'}
            </div>
          </div>
          
          <div style={{ padding: '0.5rem', textAlign: 'center' }}>
            <div style={{ fontSize: '0.8rem', color: '#6B7280' }}>Hit Rate</div>
            <div style={{ fontWeight: 'bold' }}>
              {metrics.hitRate !== undefined ? `${(metrics.hitRate * 100).toFixed(1)}%` : 'N/A'}
            </div>
          </div>
        </div>
      )}
    </Card>
  );
};

export default RobustnessScoreCard;