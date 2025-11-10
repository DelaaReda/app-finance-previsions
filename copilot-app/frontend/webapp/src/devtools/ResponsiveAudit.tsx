import { useEffect, useMemo, useState } from 'react';

type Issue = {
  type: 'overflow-x' | 'fixed-width' | 'large-min-width' | 'text-overflow';
  tag: string;
  className: string;
  width: number;
  scrollWidth: number;
  computedWidth: string;
  minWidth: string;
  selector: string;
};

function toSelector(el: Element): string {
  if (!(el as HTMLElement).parentElement) return el.tagName.toLowerCase();
  const id = (el as HTMLElement).id ? `#${(el as HTMLElement).id}` : '';
  const cls = (el as HTMLElement).className
    ? `.${String((el as HTMLElement).className).trim().split(/\s+/).slice(0, 3).join('.')}`
    : '';
  const tag = el.tagName.toLowerCase();
  return `${tag}${id || cls}`;
}

function collectIssues(): Issue[] {
  const issues: Issue[] = [];
  const nodes = Array.from(document.querySelectorAll('*')).slice(0, 5000);
  const vw = Math.max(document.documentElement.clientWidth || 0, window.innerWidth || 0);

  for (const el of nodes) {
    const rect = (el as HTMLElement).getBoundingClientRect();
    const style = window.getComputedStyle(el as HTMLElement);
    const width = rect.width;
    const scrollWidth = (el as HTMLElement).scrollWidth;
    const computedWidth = style.width || '';
    const minWidth = style.minWidth || '';
    const className = (el as HTMLElement).className ? String((el as HTMLElement).className) : '';

    // 1) Horizontal overflow
    if (scrollWidth - 2 > (el as HTMLElement).clientWidth) {
      issues.push({
        type: 'overflow-x',
        tag: el.tagName.toLowerCase(),
        className,
        width,
        scrollWidth,
        computedWidth,
        minWidth,
        selector: toSelector(el),
      });
      continue;
    }

    // 2) Fixed large width on small screens
    if (vw <= 640 && computedWidth.endsWith('px')) {
      const px = parseFloat(computedWidth);
      if (px > vw) {
        issues.push({
          type: 'fixed-width',
          tag: el.tagName.toLowerCase(),
          className,
          width,
          scrollWidth,
          computedWidth,
          minWidth,
          selector: toSelector(el),
        });
        continue;
      }
    }

    // 3) Large min-width can break layouts
    if (vw <= 640 && minWidth.endsWith('px')) {
      const px = parseFloat(minWidth);
      if (px > vw) {
        issues.push({
          type: 'large-min-width',
          tag: el.tagName.toLowerCase(),
          className,
          width,
          scrollWidth,
          computedWidth,
          minWidth,
          selector: toSelector(el),
        });
        continue;
      }
    }

    // 4) Text overflow detection (very basic)
    if ((el as HTMLElement).childNodes.length === 1 && (el as HTMLElement).scrollWidth > (el as HTMLElement).clientWidth + 16) {
      issues.push({
        type: 'text-overflow',
        tag: el.tagName.toLowerCase(),
        className,
        width,
        scrollWidth,
        computedWidth,
        minWidth,
        selector: toSelector(el),
      });
    }
  }

  return issues;
}

export default function ResponsiveAudit() {
  const [issues, setIssues] = useState<Issue[]>([]);
  const [ts, setTs] = useState<number>(Date.now());

  useEffect(() => {
    const run = () => setIssues(collectIssues());
    run();
    const ro = new ResizeObserver(() => run());
    ro.observe(document.documentElement);
    return () => ro.disconnect();
  }, [ts]);

  const grouped = useMemo(() => {
    const map = new Map<Issue['type'], Issue[]>();
    for (const i of issues) {
      const arr = map.get(i.type) ?? [];
      arr.push(i);
      map.set(i.type, arr);
    }
    return Array.from(map.entries());
  }, [issues]);

  return (
    <div className="p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Responsive Audit</h1>
        <button className="btn" onClick={() => setTs(Date.now())}>Re-scan</button>
      </div>
      <p className="text-sm text-muted">Viewport: {Math.round(window.innerWidth)}×{Math.round(window.innerHeight)} — Issues: {issues.length}</p>

      {grouped.map(([type, list]) => (
        <div key={type} className="card">
          <h2 className="text-lg font-semibold mb-2">{type} ({list.length})</h2>
          <div className="overflow-auto">
            <table className="w-full text-sm">
              <thead className="text-left">
                <tr>
                  <th className="py-1 pr-2">Selector</th>
                  <th className="py-1 pr-2">width</th>
                  <th className="py-1 pr-2">scrollWidth</th>
                  <th className="py-1 pr-2">computedWidth</th>
                  <th className="py-1 pr-2">minWidth</th>
                  <th className="py-1 pr-2">className</th>
                </tr>
              </thead>
              <tbody>
                {list.slice(0, 50).map((i, idx) => (
                  <tr key={idx} className="border-t border-border">
                    <td className="py-1 pr-2 whitespace-nowrap">{i.selector}</td>
                    <td className="py-1 pr-2">{Math.round(i.width)}</td>
                    <td className="py-1 pr-2">{i.scrollWidth}</td>
                    <td className="py-1 pr-2">{i.computedWidth}</td>
                    <td className="py-1 pr-2">{i.minWidth}</td>
                    <td className="py-1 pr-2 truncate max-w-[420px]" title={i.className}>{i.className}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ))}

      {issues.length === 0 && (
        <div className="card">
          <p className="text-sm text-muted">No responsive issues detected on this viewport.</p>
        </div>
      )}
    </div>
  );
}

/* Usage:
 * Temporarily render <ResponsiveAudit /> inside a page to scan current DOM.
 * Example: add a dev-only route or drop it at the end of Dashboard to audit that view.
 */

