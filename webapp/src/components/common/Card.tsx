/**
 * Composant Card réutilisable
 * Basé sur la VISION: affichage uniforme des données
 */

import { CSSProperties, ReactNode } from 'react'

type CardProps = {
  title?: string
  children: ReactNode
  style?: CSSProperties
  footer?: ReactNode
}

export default function Card({ title, children, style, footer }: CardProps) {
  return (
    <div style={{
      backgroundColor: '#1e1e1e',
      border: '1px solid #333',
      borderRadius: '8px',
      overflow: 'hidden',
      ...style,
    }}>
      {title && (
        <div style={{
          padding: '1rem',
          borderBottom: '1px solid #333',
          fontWeight: 600,
          fontSize: '1rem',
        }}>
          {title}
        </div>
      )}
      
      <div style={{ padding: '1rem' }}>
        {children}
      </div>

      {footer && (
        <div style={{
          padding: '0.75rem 1rem',
          borderTop: '1px solid #333',
          fontSize: '0.85rem',
          color: '#888',
        }}>
          {footer}
        </div>
      )}
    </div>
  )
}
