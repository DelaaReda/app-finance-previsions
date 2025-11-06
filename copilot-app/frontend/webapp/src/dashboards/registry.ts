import type { DashboardTemplate } from './types';

const registry = new Map<string, DashboardTemplate>();

export function registerTemplate(template: DashboardTemplate) {
  registry.set(template.slug, template);
}

export function getTemplate(slug?: string): DashboardTemplate | undefined {
  if (!slug) return undefined;
  return registry.get(slug);
}

export function listTemplates(): DashboardTemplate[] {
  return Array.from(registry.values());
}
