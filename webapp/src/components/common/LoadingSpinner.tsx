// Composant LoadingSpinner

export default function LoadingSpinner({ size = 40 }: { size?: number }) {
  return (
    <div style={styles.container}>
      <div style={{ ...styles.spinner, width: size, height: size }} />
    </div>
  )
}

const styles = {
  container: {
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 40,
  } as React.CSSProperties,
  spinner: {
    border: '3px solid #333',
    borderTop: '3px solid #fff',
    borderRadius: '50%',
    animation: 'spin 1s linear infinite',
  } as React.CSSProperties,
}
