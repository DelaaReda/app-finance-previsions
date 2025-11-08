// Page Copilot - Pilier 4: LLM Q&A + RAG (≥5 ans contexte)
// Interface de conversation avec le LLM pour questions financières

import { useState } from 'react';
import { Container, Stack, Card, Text, Textarea, Button, Group, Paper, Loader, Alert, Badge, ScrollArea } from '@mantine/core';
import { IconRobot, IconSend, IconInfoCircle, IconCheck, IconX } from '@tabler/icons-react';
import PageHeader from '@/components/layout/PageHeader';
import { useCopilotQuery } from '@/hooks/useCopilot';
import EmptyState from '@/components/ui/EmptyState';

export default function Copilot() {
  const [question, setQuestion] = useState('');
  const [conversation, setConversation] = useState<Array<{ role: 'user' | 'assistant'; content: string; sources?: any[] }>>([]);
  
  const copilotMutation = useCopilotQuery();

  const handleSubmit = async () => {
    if (!question.trim()) return;

    const userMessage = question.trim();
    setQuestion('');
    
    // Ajouter le message utilisateur à la conversation
    setConversation(prev => [...prev, { role: 'user', content: userMessage }]);

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
        }]);
      } else {
        setConversation(prev => [...prev, {
          role: 'assistant',
          content: `Erreur: ${response.error || 'Impossible de générer une réponse'}`,
        }]);
      }
    } catch (error: any) {
      setConversation(prev => [...prev, {
        role: 'assistant',
        content: `Erreur: ${error?.message || 'Une erreur est survenue'}`,
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
        <Card padding="lg" radius="md" withBorder style={{ minHeight: 400 }}>
          <ScrollArea h={400}>
            {conversation.length === 0 ? (
              <EmptyState
                icon={<IconRobot size={48} />}
                title="Démarrer une conversation"
                description="Posez une question sur le marché financier. Le Copilot utilise un contexte historique de 5+ ans pour répondre."
              />
            ) : (
              <Stack gap="md">
                {conversation.map((msg, idx) => (
                  <Paper
                    key={idx}
                    p="md"
                    radius="md"
                    withBorder
                    style={{
                      backgroundColor: msg.role === 'user' ? 'var(--mantine-color-blue-0)' : 'var(--mantine-color-gray-0)',
                      marginLeft: msg.role === 'user' ? 'auto' : 0,
                      marginRight: msg.role === 'user' ? 0 : 'auto',
                      maxWidth: '80%',
                    }}
                  >
                    <Group gap="xs" mb="xs">
                      <Badge size="sm" color={msg.role === 'user' ? 'blue' : 'gray'}>
                        {msg.role === 'user' ? 'Vous' : 'Copilot'}
                      </Badge>
                      {msg.sources && msg.sources.length > 0 && (
                        <Badge size="sm" color="green" variant="light">
                          {msg.sources.length} source{msg.sources.length > 1 ? 's' : ''}
                        </Badge>
                      )}
                    </Group>
                    <Text size="sm" style={{ whiteSpace: 'pre-wrap' }}>
                      {msg.content}
                    </Text>
                    {msg.sources && msg.sources.length > 0 && (
                      <Stack gap="xs" mt="md">
                        <Text size="xs" fw={600} c="dimmed">Sources:</Text>
                        {msg.sources.slice(0, 3).map((source, sIdx) => (
                          <Text key={sIdx} size="xs" c="dimmed">
                            • {source.ticker || source.type || 'Source'} - {source.excerpt?.substring(0, 100)}...
                          </Text>
                        ))}
                      </Stack>
                    )}
                  </Paper>
                ))}
                {copilotMutation.isPending && (
                  <Group gap="xs">
                    <Loader size="sm" />
                    <Text size="sm" c="dimmed">Copilot réfléchit...</Text>
                  </Group>
                )}
              </Stack>
            )}
          </ScrollArea>
        </Card>

        {/* Zone de saisie */}
        <Card padding="lg" radius="md" withBorder>
          <Stack gap="md">
            <Textarea
              placeholder="Posez votre question sur le marché financier..."
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSubmit();
                }
              }}
              minRows={3}
              disabled={copilotMutation.isPending}
            />
            <Group justify="space-between">
              <Text size="xs" c="dimmed">
                Appuyez sur Entrée pour envoyer, Shift+Entrée pour une nouvelle ligne
              </Text>
              <Button
                onClick={handleSubmit}
                disabled={!question.trim() || copilotMutation.isPending}
                leftSection={copilotMutation.isPending ? <Loader size={16} /> : <IconSend size={16} />}
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
