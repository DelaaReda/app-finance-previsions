import React from 'react';
import { ErrorBoundary as ReactErrorBoundary, FallbackProps } from 'react-error-boundary';
import { Button, Card, Group, Stack, Text, Title } from '@/ui';
import { IconAlertCircle, IconRefresh } from '@tabler/icons-react';

function FallbackComponent({ error, resetErrorBoundary }: FallbackProps) {
  return (
    <Card padding="xl" radius="lg" shadow="lg">
      <Stack gap="md" align="center">
        <IconAlertCircle size={40} color="#fa5252" />
        <Title order={3}>Quelque chose s’est mal passé</Title>
        <Text ta="center" c="dimmed">
          {error?.message ?? 'Une erreur inconnue est survenue. Merci de réessayer.'}
        </Text>
        <Group>
          <Button leftSection={<IconRefresh size={16} />} variant="light" onClick={resetErrorBoundary}>
            Recharger la vue
          </Button>
        </Group>
      </Stack>
    </Card>
  );
}

export class ErrorBoundary extends React.Component<React.PropsWithChildren> {
  render() {
    return (
      <ReactErrorBoundary FallbackComponent={FallbackComponent}>
        {this.props.children}
      </ReactErrorBoundary>
    );
  }
}
