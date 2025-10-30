/**
 * Page Copilot - Pilier 4
 * LLM Q&A + RAG avec ≥5 ans de contexte
 */

import { useState } from 'react'
import { useCopilotQuery, useRAGContext } from '@/hooks/useCopilot'
import Card from '@/components/common/Card'
import LoadingSpinner from '@/components/common/LoadingSpinner'
import type { CopilotMessage } from '@/types'

export default function Copilot() {
  const [messages, setMessages] = useState<CopilotMessage[]>([])
  const [input, setInput] = useState('')
  
  const queryMutation = useCopilotQuery()
  const { data: ragContext } = useRAGContext()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim()) return

    const userMessage: CopilotMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
      timestamp: new Date().toISOString(),
    }

    setMessages(prev => [...prev, userMessage])
    setInput('')

    try {
      const response = await queryMutation.mutateAsync({
        query: input,
        include_context: true,
      })

      const assistantMessage: CopilotMessage = {
        id: response.query_id,
        role: 'assistant',
        content: response.answer,
        timestamp: response.timestamp,
        sources: response.sources,
        context_used: response.context_used,
      }

      setMessages(prev => [...prev, assistantMessage])
    } catch (error) {
      console.error('Copilot error:', error)
    }
  }

  return (
    <div>
      <h1 style={{ marginBottom: '2rem' }}>🤖 Copilot Financier</h1>
      
      {/* RAG Context Info */}
      {ragContext && (
        <Card style={{ marginBottom: '2rem' }}>
          <div style={{ fontSize: '0.9rem', color: '#888' }}>
            <strong>Contexte disponible:</strong> {ragContext.total_documents.toLocaleString()} documents
            • {ragContext.news_items} news
            • {ragContext.price_series} séries prix
            • {ragContext.macro_series} séries macro
            <div style={{ marginTop: '0.5rem' }}>
              Période: {new Date(ragContext.date_range.start).toLocaleDateString()} - {new Date(ragContext.date_range.end).toLocaleDateString()}
            </div>
          </div>
        </Card>
      )}
      {/* Messages */}
      <div style={{
        backgroundColor: '#1a1a1a',
        border: '1px solid #333',
        borderRadius: '8px',
        padding: '1.5rem',
        minHeight: '400px',
        maxHeight: '600px',
        overflowY: 'auto',
        marginBottom: '1.5rem',
      }}>
        {messages.length === 0 ? (
          <div style={{ color: '#666', textAlign: 'center', padding: '2rem' }}>
            Posez une question au copilote financier...
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {messages.map((msg) => (
              <MessageBubble key={msg.id} message={msg} />
            ))}
          </div>
        )}
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} style={{ display: 'flex', gap: '1rem' }}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ex: Quelle est la tendance de l'inflation? Analyse AAPL..."
          disabled={queryMutation.isPending}
          style={{
            flex: 1,
            padding: '1rem',
            backgroundColor: '#1a1a1a',
            border: '1px solid #333',
            borderRadius: '8px',
            color: '#fff',
            fontSize: '1rem',
          }}
        />
        <button
          type="submit"
          disabled={queryMutation.isPending || !input.trim()}
          style={{
            padding: '1rem 2rem',
            backgroundColor: queryMutation.isPending ? '#333' : '#4a9eff',
            border: 'none',
            borderRadius: '8px',
            color: '#fff',
            fontWeight: 600,
            cursor: queryMutation.isPending ? 'not-allowed' : 'pointer',
          }}
        >
          {queryMutation.isPending ? 'Réflexion...' : 'Envoyer'}
        </button>
      </form>
    </div>
  )
}
function MessageBubble({ message }: { message: CopilotMessage }) {
  const isUser = message.role === 'user'
  
  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: isUser ? 'flex-end' : 'flex-start',
      gap: '0.5rem',
    }}>
      <div style={{
        maxWidth: '80%',
        padding: '1rem',
        backgroundColor: isUser ? '#1a2a3a' : '#2a1a2a',
        border: `1px solid ${isUser ? '#4a9eff' : '#666'}`,
        borderRadius: '12px',
      }}>
        <div style={{ whiteSpace: 'pre-wrap', lineHeight: 1.6 }}>
          {message.content}
        </div>

        {message.sources && message.sources.length > 0 && (
          <div style={{
            marginTop: '0.75rem',
            paddingTop: '0.75rem',
            borderTop: '1px solid #333',
            fontSize: '0.85rem',
            color: '#888',
          }}>
            <strong>Sources:</strong>
            <ul style={{ margin: '0.5rem 0 0 0', paddingLeft: '1.5rem' }}>
              {message.sources.map((source, idx) => (
                <li key={idx}>
                  {source.url ? (
                    <a href={source.url} target="_blank" rel="noopener noreferrer" style={{ color: '#4a9eff' }}>
                      {source.name}
                    </a>
                  ) : (
                    source.name
                  )}
                  {' '}({new Date(source.timestamp).toLocaleDateString()})
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      <div style={{ fontSize: '0.75rem', color: '#666' }}>
        {new Date(message.timestamp).toLocaleTimeString()}
      </div>
    </div>
  )
}
