import { IconExternalLink } from '@tabler/icons-react';
import { cn } from '@/features/okc/utils';

interface NewsCardProps {
  title: string;
  source?: string;
  time?: string; // already formatted string preferred
  url?: string;
  logoUrl?: string;
  className?: string;
}

export function NewsCard({ title, source, time, url, logoUrl, className }: NewsCardProps) {
  return (
    <a
      href={url ?? '#'}
      target="_blank"
      rel="noreferrer"
      className={cn('flex items-start gap-3 rounded-md p-2 hover:bg-surface-elevated/40 border border-transparent hover:border-border transition-all group', className)}
      title={title}
    >
      {logoUrl ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={logoUrl} alt={source ?? 'source'} className="w-5 h-5 mt-0.5 rounded object-cover" loading="lazy" />
      ) : (
        <div className="w-5 h-5 mt-0.5 rounded bg-surface-elevated border border-border" />
      )}
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-text line-clamp-2 group-hover:text-primary transition-colors break-words">
          {title}
        </p>
        <p className="text-xs text-muted mt-0.5">
          {source?.toUpperCase()}
          {source && time ? ' • ' : ''}
          {time}
        </p>
      </div>
      <IconExternalLink size={14} className="opacity-50 group-hover:opacity-100 transition-opacity flex-shrink-0 mt-0.5" />
    </a>
  );
}

