// Layout principal avec Header et contenu

import { PropsWithChildren } from 'react'
import Header from './Header'

export default function MainLayout({ children }: PropsWithChildren) {
  return (
    <div style={styles.container}>
      <Header />
      <main style={styles.main}>
        <div style={styles.content}>
          {children}
        </div>
      </main>
    </div>
  )
}

const styles = {
  container: {
    minHeight: '100vh',
    backgroundColor: '#0a0a0a',
    color: '#e0e0e0',
  } as React.CSSProperties,
  main: {
    padding: '24px',
  } as React.CSSProperties,
  content: {
    maxWidth: 1400,
    margin: '0 auto',
  } as React.CSSProperties,
}
