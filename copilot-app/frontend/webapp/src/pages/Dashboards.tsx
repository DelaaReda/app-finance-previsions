import { useMemo, useState } from 'react';
import { Container, Group, Select, Stack, Title } from '@mantine/core';
import { useNavigate, useParams } from 'react-router-dom';
import { listTemplates, getTemplate } from '@/dashboards/registry';
import '@/dashboards';
import type { DashboardContext, DashboardTemplate } from '@/dashboards/types';
import { DashboardRenderer } from '@/components/dashboard/DashboardRenderer';
import { DashboardControls } from '@/components/dashboard/DashboardControls';

export default function DashboardsPage() {
  const { slug } = useParams();
  const navigate = useNavigate();
  const templates = useMemo(() => listTemplates(), []);
  const initialTemplate = (slug && getTemplate(slug)) || templates[0];

  const [currentTemplate, setCurrentTemplate] = useState<DashboardTemplate | undefined>(initialTemplate);
  const [context, setContext] = useState<DashboardContext>(initialTemplate?.defaultContext ?? {
    horizon: 'short',
    universe: ['SPY', 'QQQ'],
    themes: [],
    macroIds: ['CPIAUCSL', 'VIXCLS'],
  });

  const templateOptions = templates.map((template) => ({ value: template.slug, label: template.title }));

  return (
    <Container size="xl" data-testid="page-dashboards">
      <Stack gap="lg">
        <Group justify="space-between" align="center">
          <Title order={2}>Dashboards</Title>
          <Select
            label="Template"
            data={templateOptions}
            value={currentTemplate?.slug}
            onChange={(nextSlug) => {
              const nextTemplate = getTemplate(nextSlug ?? undefined);
              if (nextTemplate) {
                setCurrentTemplate(nextTemplate);
                setContext(nextTemplate.defaultContext);
                navigate(`/dashboards/${nextTemplate.slug}`);
              }
            }}
            w={260}
          />
        </Group>

        <DashboardControls value={context} onChange={setContext} onRefresh={() => { /* query hooks refetch via state change */ }} />

        {currentTemplate && <DashboardRenderer template={currentTemplate} context={context} />}
      </Stack>
    </Container>
  );
}
