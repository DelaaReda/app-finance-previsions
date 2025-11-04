import React from 'react';

interface EmptyStateProps {
  title: string;
  hint?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({ title, hint }) => {
  return (
    <div className="empty-state" style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '40px 20px',
      textAlign: 'center',
      border: '1px dashed #ddd',
      borderRadius: '8px',
      backgroundColor: '#fafafa',
      minHeight: '200px',
      marginTop: '20px'
    }}>
      <h3 style={{ margin: '0 0 10px 0', color: '#666' }}>{title}</h3>
      {hint && <p style={{ margin: '5px 0 0 0', color: '#888' }}>{hint}</p>}
    </div>
  );
};