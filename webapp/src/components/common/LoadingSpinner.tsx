/**
 * Composant LoadingSpinner
 */

export default function LoadingSpinner({ message = 'Chargement...' }: { message?: string }) {
  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '2rem',
      gap: '1rem',
    }}>
      <div style={{
        border: '3px solid #333',
        borderTop: '3px solid #4a9eff',
        borderRadius: '50%',
        width: '40px',
        height: '40px',
        animation: 'spin 1s linear infinite',
      }} />
      <style>
        {`
          @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
          }
        `}
      </style>
      <small style={{ color: '#888' }}>{message}</small>
    </div>
  )
}
