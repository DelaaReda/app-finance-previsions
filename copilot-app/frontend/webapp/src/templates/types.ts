import type { ReactNode } from 'react';

export type TemplateRenderCtx = {
  horizon?: any;
  universe?: string[];
  themes?: string[];
  [key: string]: any;
};

export type DashboardTemplate = {
  slug: string;
  label: string;
  description?: string;
  render: (ctx: TemplateRenderCtx) => ReactNode;
};
