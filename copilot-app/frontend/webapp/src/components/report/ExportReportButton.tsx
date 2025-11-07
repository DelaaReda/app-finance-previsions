/**
 * Export Report Button Component
 * Creates a button to export any section to PDF
 */

import React, { useState } from 'react';
import { Button } from '@mantine/core';
import { IconDownload, IconFileDownload } from '@tabler/icons-react';
import * as exportPdfUtils from '../../utils/exportPdf';

interface ExportReportButtonProps {
  elementId: string;
  fileName?: string;
  title?: string;
  label?: string;
  variant?: 'outline' | 'filled' | 'light' | 'subtle' | 'transparent';
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl';
}

export const ExportReportButton: React.FC<ExportReportButtonProps> = ({ 
  elementId, 
  fileName = 'report.pdf', 
  title = 'Finance Report',
  label = 'Export PDF',
  variant = 'outline',
  size = 'md'
}) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleExport = async () => {
    setLoading(true);
    setError(null);
    
    try {
      if (title) {
        await exportPdfUtils.exportReportToPdf(elementId, title, fileName);
      } else {
        await exportPdfUtils.exportElementToPdf(elementId, fileName);
      }
    } catch (err) {
      console.error('PDF export failed:', err);
      setError(err instanceof Error ? err.message : 'Export failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ position: 'relative' }}>
      <Button
        leftSection={loading ? undefined : <IconFileDownload size={16} />}
        variant={variant}
        size={size}
        onClick={handleExport}
        loading={loading}
        style={{ minWidth: '120px' }}
      >
        {label}
      </Button>
      
      {error && (
        <div style={{
          position: 'absolute',
          top: '100%',
          left: 0,
          backgroundColor: '#fee2e2',
          color: '#dc2626',
          padding: '0.5rem',
          borderRadius: '4px',
          zIndex: 100,
          fontSize: '0.8rem',
          whiteSpace: 'nowrap'
        }}>
          {error}
        </div>
      )}
    </div>
  );
};

export default ExportReportButton;