/**
 * Composant ErrorMessage
 */

export default function ErrorMessage({ error }: { error: string | Error }) {
  const message = typeof error === 'string' ? error : error.message

  return (
    <div style={{
      backgroundColor: '#2a1a1a',
      border: '1px solid #ff4444',
      borderRadius: '8px',
      padding: '1rem',
      color: '#ff6666',
    }}>
      <div style={{ fontWeight: 600, marginBottom: '0.5rem' }}>
        ⚠️ Erreur
      </div>
      <div style={{ fontSize: '0.9rem' }}>
        {message}
      </div>
    </div>
  )
}
