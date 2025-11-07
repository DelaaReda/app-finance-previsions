// Composant Card réutilisable

import { PropsWithChildren, CSSProperties } from 'react'

type CardProps = PropsWithChildren<{
  title?: string
  subtitle?: string
  className?: string
  style?: CSSProperties
}>

function Card({ title, subtitle, children, style }: CardProps) {
  return (
    <div style={{ ...styles.card, ...style }}>
      {(title || subtitle) && (
        <div style={styles.header}>
          {title && <h3 style={styles.title}>{title}</h3>}
          {subtitle && <p style={styles.subtitle}>{subtitle}</p>}
        </div>
      )}
      <div style={styles.content}>
        {children}
      </div>
    </div>
  )
}

// Named and default export for compatibility
export { Card };
export default Card;

const styles = {
  card: {
    backgroundColor: '#1a1a1a',
    border: '1px solid #2a2a2a',
    borderRadius: 8,
    overflow: 'hidden',
  } as CSSProperties,
  header: {
    padding: '16px 20px',
    borderBottom: '1px solid #2a2a2a',
  } as CSSProperties,
  title: {
    margin: 0,
    fontSize: 16,
    fontWeight: 600,
    color: '#fff',
  } as CSSProperties,
  subtitle: {
    margin: '4px 0 0',
    fontSize: 13,
    color: '#999',
  } as CSSProperties,
  content: {
    padding: 20,
  } as CSSProperties,
}
