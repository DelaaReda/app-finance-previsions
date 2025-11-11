import { ReactNode } from 'react';
import { IconInbox, IconRefresh } from '@tabler/icons-react';
import { Button } from '@/features/okc/components/Button';
import { cn } from '@/features/okc/utils';

interface EmptyStateProps {
  title?: string;
  description?: string;
  icon?: ReactNode;
  action?: {
    label: string;
    onClick: () => void;
  };
  className?: string;
}

export function EmptyState({
  title = 'Aucune donnée disponible',
  description = 'Les données seront disponibles une fois chargées.',
  icon,
  action,
  className,
}: EmptyStateProps) {
  return (
    <div className={cn('flex flex-col items-center justify-center py-12 px-4 text-center', className)}>
      <div className="w-16 h-16 rounded-full bg-surface-elevated border border-border flex items-center justify-center mb-4">
        {icon || <IconInbox size={32} className="text-muted" />}
      </div>
      <h3 className="text-lg font-semibold text-text mb-2">{title}</h3>
      <p className="text-sm text-muted max-w-md mb-6">{description}</p>
      {action && (
        <Button variant="secondary" size="sm" onClick={action.onClick} leftIcon={<IconRefresh size={16} />}>
          {action.label}
        </Button>
      )}
    </div>
  );
}

// Backwards compatibility: allow both default and named imports
export default EmptyState;
