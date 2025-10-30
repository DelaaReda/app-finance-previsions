// Page Copilot - Pilier 4: LLM Q&A + RAG (≥5 ans contexte)

import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { copilotService } from '@/services/copilot.service'
import { CopilotMessage } from '@/types/copilot.types'
import MainLayout from '@/components/layout/MainLayout'
import Card from '@/components/common/Card'
import LoadingSpinner from '@/components/common/LoadingSpinner'
import ErrorMessage from '@/components/common/ErrorMessage'

export default function Copilot() {
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [messages, setMessages] = useState<CopilotMessage[]>([])
  const [question, setQuestion] = useState('')

  // Stats RAG
  const { data: ragStats } = useQuery({
    queryKey: ['rag-stats'],
    queryFn: async () => {
      const result = await copilotService.getRAGStats()
      return result.ok ? result.data : null
    },
  })

  // Créer une session
  const createSession = useMutation({
    mutationFn: async () => {
      const result = await copilotService.createSession()
      if (!result.ok) throw new Error(result.error)
      return result.data
    },
    onSuccess: (session) => {
      setSessionId(session.id)
      setMessages(session.messages)
    },
  })
