// Composant ErrorMessage

export default function ErrorMessage({ message }: { message: string }) {
  return (
    <div style={styles.container}>
      <div style={styles.icon}>⚠️</div>
      <div style={styles.message}>{message}</div>
    </div>
  )
}

const styles = {
  container: {
    backgroundColor: '#2a1515',
    border: '1px solid #4a2020',
    borderRadius: 8,
    padding: 16,
    display: 'flex',
    alignItems: 'center',
    gap: 12,
  } as React.CSSProperties,
  icon: {
    fontSize: 24,
  } as React.CSSProperties,
  message: {
    color: '#ff6b6b',
    fontSize: 14,
  } as React.CSSProperties,
}
