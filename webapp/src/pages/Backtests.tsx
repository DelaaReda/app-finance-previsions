import { useQuery } from '@tanstack/react-query'
import { apiGet } from '@/api/client'

// Since the backtests endpoint doesn't exist in the API yet, we'll show a placeholder
export default function Backtests() {
  // Since backtests endpoint doesn't exist yet, return placeholder content
  return (
    <div>
      <h2>Backtests</h2>
      <div style={{ padding: '20px', backgroundColor: '#f5f5f5', borderRadius: '8px', margin: '16px 0' }}>
        <p><strong>Fonctionnalité en développement</strong></p>
        <p>Le module de backtesting est en cours de développement.</p>
        <p>Il permettra d'analyser les performances historiques des stratégies de trading.</p>
      </div>
    </div>
  )
}