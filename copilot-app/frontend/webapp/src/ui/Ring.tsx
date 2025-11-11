import type { RingProgressProps } from '@mantine/core';
import { RingProgress as MantineRingProgress } from '@mantine/core';

export type RingProps = RingProgressProps & {
  value?: number;
};

export function RingProgress(props: RingProps) {
  const { value, sections, ...rest } = props;

  // If value is provided instead of sections, convert it to sections format
  const computedSections = sections ?? (value !== undefined ? [
    { value, color: 'teal' },
    { value: 100 - value, color: 'gray.1' }
  ] : []);

  return (
    <MantineRingProgress
      thickness={rest.thickness ?? 12}
      roundCaps
      size={rest.size ?? 144}
      sections={computedSections}
      {...rest}
    />
  );
}

// Export alias for compatibility
export { RingProgress as Ring };
