/**
 * Universal Search API Routes - FC-API-035
 * Author: ALEX-API-ARCHITECT-SUPERMAN-7
 * Task: FC-API-035 - Endpoint /api/search/universal pour recherche globale (stocks, news, briefs, prévisions)
 */
import React from 'react';
import { Tooltip } from '@mui/material';
import { InfoOutlined } from '@mui/icons-material';

interface SourceTooltipProps {
  source: string;        // Name of the data source (e.g., 'FRED', 'yfinance', 'RSS')
  lastUpdate?: string;   // Timestamp of the last update
  metadata?: Record<string, unknown>; // Additional metadata about the source
  children?: React.ReactNode; // Optional custom content instead of default info
}

export default function SourceTooltip({ 
  source, 
  lastUpdate, 
  metadata,
  children
}: SourceTooltipProps) {
  const formatDate = (dateString?: string) => {
    if (!dateString) return 'Inconnu';
    try {
      return new Date(dateString).toLocaleString('fr-FR', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch (e) {
      return dateString;
    }
  };

  // Create tooltip content
  const tooltipContent = children || (
    <div style={{ padding: '12px', maxWidth: '300px' }}>
      <div style={{ fontWeight: 'bold', marginBottom: '8px', fontSize: '14px' }}>
        📊 Source: {source}
      </div>
      {lastUpdate && (
        <div style={{ fontSize: '12px', marginBottom: '4px' }}>
          <span style={{ color: '#aaa' }}>Mis à jour:</span> {formatDate(lastUpdate)}
        </div>
      )}
      {metadata && Object.keys(metadata).length > 0 && (
        <div style={{ fontSize: '12px', marginTop: '8px', borderTop: '1px solid #444', paddingTop: '8px' }}>
          <div style={{ fontWeight: 'bold', marginBottom: '4px' }}>Métadonnées:</div>
          {Object.entries(metadata).map(([key, value]) => (
            <div key={key} style={{ marginBottom: '2px' }}>
              <span style={{ color: '#aaa' }}>{key}:</span> {String(value)}
            </div>
          ))}
        </div>
      )}
      <div style={{ fontSize: '11px', color: '#999', marginTop: '8px' }}>
        Données provenant de {source} • {lastUpdate ? 'Actualisé' : 'Dernière extraction inconnue'}
      </div>
    </div>
  );

  return (
    <Tooltip title={tooltipContent} placement="top" arrow>
      <span style={{ cursor: 'help', verticalAlign: 'middle' }}>
        <InfoOutlined style={{ fontSize: '14px', color: '#999' }} />
      </span>
    </Tooltip>
  );
}