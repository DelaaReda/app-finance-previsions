import type { RingProgressProps } from '@mantine/core';
import { RingProgress as MantineRingProgress } from '@mantine/core';

export type RingProps = RingProgressProps;

export function RingProgress(props: RingProps) {
  return (
    <MantineRingProgress
      thickness={props.thickness ?? 12}
      roundCaps
      size={props.size ?? 144}
      {...props}
    />
  );
}
