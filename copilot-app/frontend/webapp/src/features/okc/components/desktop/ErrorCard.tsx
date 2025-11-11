import { IconAlertCircle } from '@tabler/icons-react';
import { cn } from '@/features/okc/utils';

interface ErrorCardProps {
  title?: string;
  message?: string;
  onRetry?: () => void;
  className?: string;
}

export function ErrorCard({ title = 'Aucune donnée disponible', message = 'Les données seront chargées lors de la prochaine mise à jour.', onRetry, className }: ErrorCardProps) {
  return (
    <div className={cn('text-center p-8 border border-border rounded-xl bg-surface transition-colors', className)}>
      <div className="inline-flex items-center justify-center w-10 h-10 rounded-full bg-surface-elevated border border-border mb-3">
        <IconAlertCircle size={18} className="text-muted" />
      </div>
      <p className="mb-1 font-semibold text-text">{title}</p>
      <p className="text-sm text-muted">{message}</p>
      {onRetry && (
        <button onClick={onRetry} className="mt-3 inline-flex items-center gap-2 px-3 py-1.5 rounded-md text-sm bg-primary text-white hover:opacity-95 transition-opacity">
          Réessayer
        </button>
      )}
    </div>
  );
}

