// Page Copilot - Pilier 4: LLM Q&A + RAG (≥5 ans contexte)

import MainLayout from '@/components/layout/MainLayout'
import Card from '@/components/common/Card'

export default function Copilot() {
  return (
    <MainLayout>
      <div className="space-y-6">
        <Card>
          <h1 className="text-2xl font-bold">Copilot LLM</h1>
          <p>Q&A avec contexte historique (RAG ≥5 ans)</p>
        </Card>
      </div>
    </MainLayout>
  )
}
