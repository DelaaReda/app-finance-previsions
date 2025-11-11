// Layout principal avec Header et contenu

import { PropsWithChildren } from 'react'
import Header from './Header'

export default function MainLayout({ children }: PropsWithChildren) {
  return (
    <div className="min-h-screen" style={{ backgroundColor: 'var(--bg)', color: 'var(--text)' }}>
      <Header />
      <main className="py-6 px-6">
        <div className="container mx-auto">
          {children}
        </div>
      </main>
    </div>
  )
}
