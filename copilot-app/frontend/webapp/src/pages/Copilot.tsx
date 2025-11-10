// Page Copilot - Pilier 4: LLM Q&A + RAG (≥5 ans contexte)
// Interface de conversation avec le LLM pour questions financières

import { useState, useEffect, useRef } from 'react';
import { Container, Stack, Card, Text, Textarea, Button, Group, Paper, Loader, Alert, Badge, ScrollArea, ActionIcon, Tooltip } from '@mantine/core';
import { IconRobot, IconSend, IconInfoCircle, IconCheck, IconX, IconTrash, IconExternalLink } from '@tabler/icons-react';
import PageHeader from '@/components/layout/PageHeader';
import { useCopilotQuery } from '@/hooks/useCopilot';
import EmptyState from '@/components/ui/EmptyState';

export default function Copilot() {
  const [question, setQuestion] = useState('');
  const [conversation, setConversation] = useState<Array<{ role: 'user' | 'assistant'; content: string; sources?: any[]; timestamp?: Date }>>([]);
  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  
  const copilotMutation = useCopilotQuery();

  // Auto-scroll vers le bas quand de nouveaux messages arrivent
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth', block: 'end' });
    }
  }, [conversation]);

  // Charger la conversation depuis localStorage au montage
  useEffect(() => {
    const saved = localStorage.getItem('copilot_conversation');
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        setConversation(parsed.map((msg: any) => ({
          ...msg,
          timestamp: msg.timestamp ? new Date(msg.timestamp) : new Date(),
        })));
      } catch (e) {
        console.warn('Failed to load conversation from localStorage', e);
      }
    }
  }, []);

  // Sauvegarder la conversation dans localStorage
  useEffect(() => {
    if (conversation.length > 0) {
      localStorage.setItem('copilot_conversation', JSON.stringify(conversation));
    }
  }, [conversation]);

  const clearConversation = () => {
    setConversation([]);
    localStorage.removeItem('copilot_conversation');
  };

  const handleSubmit = async () => {
    if (!question.trim() || copilotMutation.isPending) return;

    const userMessage = question.trim();
    setQuestion('');
    
    // Ajouter le message utilisateur à la conversation
    const userMsg = { role: 'user' as const, content: userMessage, timestamp: new Date() };
    setConversation(prev => [...prev, userMsg]);

    try {
      const response = await copilotMutation.mutateAsync({
        question: userMessage,
        max_sources: 5,
        context_years: 5,
      });

      if (response.ok && response.data) {
        setConversation(prev => [...prev, {
          role: 'assistant',
          content: response.data.answer || 'Aucune réponse générée',
          sources: response.data.sources || [],
          timestamp: new Date(),
        }]);
      } else {
        setConversation(prev => [...prev, {
          role: 'assistant',
          content: `Erreur: ${response.error || 'Impossible de générer une réponse'}`,
          timestamp: new Date(),
        }]);
      }
    } catch (error: any) {
      setConversation(prev => [...prev, {
        role: 'assistant',
        content: `Erreur: ${error?.message || 'Une erreur est survenue. Veuillez réessayer.'}`,
        timestamp: new Date(),
      }]);
    }
  };

  return (
    <Container size="xl" py="xl">
      <PageHeader
        title="Copilot LLM"
        icon={<IconRobot size={28} />}
        description="Q&A avec contexte historique (RAG ≥5 ans)"
        badge={{ label: 'Beta', color: 'blue' }}
        infoTooltip="Interface de conversation avec le LLM pour questions financières avec contexte historique"
      />
      
      <Stack gap="lg" mt="xl">
        {/* Zone de conversation */}
        <Card padding="lg" radius="md" withBorder style={{ minHeight: 500, maxHeight: 600, display: 'flex', flexDirection: 'column' }}>
          <Group justify="space-between" mb="md">
            <Text size="sm" fw={600}>Conversation</Text>
            {conversation.length > 0 && (
              <Tooltip label="Effacer la conversation">
                <ActionIcon
                  variant="light"
                  color="red"
                  size="sm"
                  onClick={clearConversation}
                >
                  <IconTrash size={16} />
                </ActionIcon>
              </Tooltip>
            )}
          </Group>
          <ScrollArea 
            style={{ flex: 1, minHeight: 0 }}
            viewportRef={scrollAreaRef}
            type="auto"
          >
            {conversation.length === 0 ? (
              <EmptyState
                icon={<IconRobot size={48} />}
                title="Démarrer une conversation"
                description="Posez une question sur le marché financier. Le Copilot utilise un contexte historique de 5+ ans pour répondre."
              />
            ) : (
              <Stack gap="md" pb="md">
                {conversation.map((msg, idx) => (
                  <Paper
                    key={idx}
                    p="md"
                    radius="md"
                    withBorder
                    style={{
                      backgroundColor: msg.role === 'user' 
                        ? 'var(--mantine-color-blue-0)' 
                        : 'var(--mantine-color-gray-0)',
                      marginLeft: msg.role === 'user' ? 'auto' : 0,
                      marginRight: msg.role === 'user' ? 0 : 'auto',
                      maxWidth: '85%',
                      alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
                    }}
                  >
                    <Group gap="xs" mb="xs" justify="space-between">
                      <Group gap="xs">
                        <Badge size="sm" color={msg.role === 'user' ? 'blue' : 'gray'}>
                          {msg.role === 'user' ? 'Vous' : 'Copilot'}
                        </Badge>
                        {msg.sources && msg.sources.length > 0 && (
                          <Badge size="sm" color="green" variant="light">
                            {msg.sources.length} source{msg.sources.length > 1 ? 's' : ''}
                          </Badge>
                        )}
                      </Group>
                      {msg.timestamp && (
                        <Text size="xs" c="dimmed">
                          {msg.timestamp.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })}
                        </Text>
                      )}
                    </Group>
                    <Text size="sm" style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                      {msg.content}
                    </Text>
                    {msg.sources && msg.sources.length > 0 && (
                      <Stack gap="xs" mt="md" p="xs" style={{ backgroundColor: 'var(--mantine-color-gray-1)', borderRadius: 4 }}>
                        <Text size="xs" fw={600} c="dimmed">Sources:</Text>
                        {msg.sources.slice(0, 5).map((source, sIdx) => (
                          <Group key={sIdx} gap="xs" align="flex-start">
                            <Text size="xs" c="dimmed" style={{ flex: 1 }}>
                              • {source.ticker || source.type || 'Source'}
                              {source.excerpt && ` - ${source.excerpt.substring(0, 80)}${source.excerpt.length > 80 ? '...' : ''}`}
                            </Text>
                            {source.url && (
                              <ActionIcon
                                component="a"
                                href={source.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                size="xs"
                                variant="light"
                                color="blue"
                              >
                                <IconExternalLink size={12} />
                              </ActionIcon>
                            )}
                          </Group>
                        ))}
                      </Stack>
                    )}
                  </Paper>
                ))}
                {copilotMutation.isPending && (
                  <Paper p="md" radius="md" withBorder style={{ alignSelf: 'flex-start', maxWidth: '85%' }}>
                    <Group gap="xs">
                      <Loader size="sm" />
                      <Text size="sm" c="dimmed">Copilot réfléchit...</Text>
                    </Group>
                  </Paper>
                )}
                <div ref={messagesEndRef} />
              </Stack>
            )}
          </ScrollArea>
        </Card>

        {/* Zone de saisie */}
        <Card padding="lg" radius="md" withBorder>
          <Stack gap="md">
            <Textarea
              placeholder="Posez votre question sur le marché financier... (ex: Quelle est la tendance actuelle du S&P 500 ?)"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey && !e.ctrlKey && !e.metaKey) {
                  e.preventDefault();
                  handleSubmit();
                }
              }}
              minRows={2}
              maxRows={6}
              disabled={copilotMutation.isPending}
              autosize
            />
            <Group justify="space-between" align="center">
              <Text size="xs" c="dimmed">
                Appuyez sur <kbd style={{ padding: '2px 6px', backgroundColor: 'var(--mantine-color-gray-2)', borderRadius: 3, fontSize: '0.75rem' }}>Entrée</kbd> pour envoyer, <kbd style={{ padding: '2px 6px', backgroundColor: 'var(--mantine-color-gray-2)', borderRadius: 3, fontSize: '0.75rem' }}>Shift+Entrée</kbd> pour une nouvelle ligne
              </Text>
              <Button
                onClick={handleSubmit}
                disabled={!question.trim() || copilotMutation.isPending}
                leftSection={copilotMutation.isPending ? <Loader size={16} /> : <IconSend size={16} />}
                loading={copilotMutation.isPending}
              >
                {copilotMutation.isPending ? 'Envoi...' : 'Envoyer'}
              </Button>
            </Group>
          </Stack>
        </Card>

        {/* Info sur le Copilot */}
        <Alert icon={<IconInfoCircle size={20} />} title="À propos du Copilot" color="blue" variant="light">
          <Text size="sm">
            Le Copilot utilise un système RAG (Retrieval-Augmented Generation) avec un contexte historique de 5+ ans.
            Il peut répondre à des questions sur les marchés financiers, les tendances, les événements passés, etc.
          </Text>
        </Alert>
      </Stack>
    </Container>
  );
}
