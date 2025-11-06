import { Button } from '@/ui';
import { useState } from 'react';
import { exportSectionsToPdf } from '@/utils/exportPdf';

export default function FullReportButton({
  sectionIds,
  filename,
}: {
  sectionIds: string[];
  filename?: string;
}) {
  const [busy, setBusy] = useState(false);

  return (
    <Button
      size="xs"
      variant="default"
      disabled={busy}
      data-testid="btn-export-full-report"
      onClick={async () => {
        setBusy(true);
        try {
          await exportSectionsToPdf(sectionIds, filename ?? 'report.pdf');
        } finally {
          setBusy(false);
        }
      }}
    >
      {busy ? 'Export…' : 'Exporter le rapport (PDF)'}
    </Button>
  );
}
