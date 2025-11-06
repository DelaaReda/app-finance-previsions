import { useState } from 'react';
import { Button } from '@/ui';
import { exportContainerToPdf } from '@/utils/exportPdf';

export default function ExportReportButton({
  targetId,
  filename,
}: {
  targetId: string;
  filename?: string;
}) {
  const [busy, setBusy] = useState(false);

  return (
    <Button
      size="xs"
      variant="default"
      disabled={busy}
      data-testid="btn-export-pdf"
      onClick={async () => {
        setBusy(true);
        try {
          await exportContainerToPdf(targetId, filename ?? 'report.pdf');
        } finally {
          setBusy(false);
        }
      }}
    >
      {busy ? 'Export…' : 'Exporter en PDF'}
    </Button>
  );
}
