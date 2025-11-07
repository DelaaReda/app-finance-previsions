// Page Copilot - Pilier 4: LLM Q&A + RAG (≥5 ans contexte)
// Refactorisé avec Mantine pour un look professionnel

import { Container, Stack, Card, Text, Alert } from '@mantine/core';
import { IconRobot, IconInfoCircle } from '@tabler/icons-react';
import PageHeader from '@/components/layout/PageHeader';

export default function Copilot() {
  return (
    <Container size="xl" py="xl">
      <PageHeader
        title="Copilot LLM"
        icon={<IconRobot size={28} />}
        description="Q&A avec contexte historique (RAG ≥5 ans)"
        badge={{ label: 'Beta', color: 'blue' }}
        infoTooltip="Interface de conversation avec le LLM pour questions financières avec contexte historique"
      />
      
      <Stack gap="lg">
        <Alert
          icon={<IconInfoCircle size={20} />}
          title="Fonctionnalité en développement"
          color="blue"
          variant="light"
        >
          <Text size="sm">
            Le module Copilot LLM est en cours de développement. 
            L'interface de conversation avec contexte RAG sera disponible prochainement.
          </Text>
        </Alert>
        
        <Card padding="lg" radius="md" withBorder>
          <Stack gap="md">
            <Text fw={600} size="lg">À venir</Text>
            <Text c="dimmed" size="sm">
              Interface de conversation intelligente pour poser des questions sur le marché financier
              avec accès à un contexte historique de 5+ ans.
            </Text>
          </Stack>
        </Card>
      </Stack>
    </Container>
  )
}
