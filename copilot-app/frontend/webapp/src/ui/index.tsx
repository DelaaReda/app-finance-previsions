import { forwardRef } from 'react';
import type { ComponentPropsWithoutRef } from 'react';
import {
  ActionIcon as MantineActionIcon,
  ActionIconProps,
  Anchor as MantineAnchor,
  Avatar as MantineAvatar,
  Badge as MantineBadge,
  BadgeProps,
  Box as MantineBox,
  Button as MantineButton,
  ButtonProps,
  Card as MantineCard,
  CardProps,
  Chip as MantineChip,
  Container as MantineContainer,
  Grid as MantineGrid,
  Divider as MantineDivider,
  Flex as MantineFlex,
  Group as MantineGroup,
  Loader as MantineLoader,
  LoaderProps,
  Modal as MantineModal,
  ModalProps,
  Paper as MantinePaper,
  Progress as MantineProgress,
  ScrollArea as MantineScrollArea,
  Select as MantineSelect,
  SimpleGrid as MantineSimpleGrid,
  Skeleton as MantineSkeleton,
  Slider as MantineSlider,
  Stack as MantineStack,
  Tabs as MantineTabs,
  TabsProps,
  Table as MantineTable,
  TableProps,
  NumberInput as MantineNumberInput,
  NumberInputProps,
  Text as MantineText,
  TextInput as MantineTextInput,
  TextProps,
  ThemeIcon as MantineThemeIcon,
  Title as MantineTitle,
  TitleProps,
  Tooltip as MantineTooltip,
  TooltipProps,
  Transition as MantineTransition,
} from '@mantine/core';
import { AreaChart, BarList, DonutChart, LineChart } from '@tremor/react';
import type { RingProps } from './Ring';
import { RingProgress as RingComponent } from './Ring';

type ButtonComponentProps = ButtonProps & ComponentPropsWithoutRef<'button'>;
type ActionIconComponentProps = ActionIconProps & ComponentPropsWithoutRef<'button'>;
type ModalComponentProps = ModalProps & ComponentPropsWithoutRef<'div'>;

export const Button = forwardRef<HTMLButtonElement, ButtonComponentProps>((props, ref) => (
  <MantineButton ref={ref} radius="md" size={props.size ?? 'md'} {...props} />
));
Button.displayName = 'Button';

export const Card = (props: CardProps) => (
  <MantineCard radius="lg" shadow={props.shadow ?? 'md'} withBorder padding="lg" {...props} />
);

export const Badge = (props: BadgeProps) => (
  <MantineBadge radius="sm" variant={props.variant ?? 'light'} {...props} />
);

export const Tabs = (props: TabsProps) => (
  <MantineTabs radius="md" variant={props.variant ?? 'pills'} {...props} />
);

export const Modal = (props: ModalComponentProps) => (
  <MantineModal radius="lg" overlayProps={{ opacity: 0.35, blur: 4 }} {...props} />
);

export const ActionIcon = forwardRef<HTMLButtonElement, ActionIconComponentProps>((props, ref) => (
  <MantineActionIcon ref={ref} radius="lg" variant={props.variant ?? 'light'} {...props} />
));
ActionIcon.displayName = 'ActionIcon';

export const Tooltip = (props: TooltipProps) => (
  <MantineTooltip radius="md" withArrow {...props} />
);

export const Typo = (props: TextProps) => <Text fw={props.fw ?? 500} {...props} />;

export const Heading = (props: TitleProps) => (
  <Title order={props.order ?? 3} fw={props.fw ?? 700} {...props} />
);

export const LoadingSpinner = (props: LoaderProps) => (
  <Loader size={props.size ?? 'md'} color={props.color ?? 'indigo'} variant={props.variant ?? 'bars'} {...props} />
);

export const RingProgress = (props: RingProps) => <RingComponent {...props} />;

export {
  AreaChart,
  BarList,
  DonutChart,
  LineChart,
  Anchor,
  Avatar,
  Box,
  Chip,
  Container,
  Grid,
  Divider,
  Flex,
  Group,
  Loader,
  Paper,
  Progress,
  ScrollArea,
  Select,
  SimpleGrid,
  Skeleton,
  Slider,
  Stack,
  Table,
  Text,
  TextInput,
  ThemeIcon,
  Title,
  Transition,
  NumberInput,
};

// Safe access helpers - ensure never-empty patterns
// Import from ../lib/safe and re-export for convenience
import {
  ensureArray,
  nn,
  hasItems,
  safeLength,
  safeMap,
  safeGet,
  safeBool,
  safeString,
  safeNumber,
} from '../lib/safe';

export type {
  ButtonProps,
  CardProps,
  BadgeProps,
  ActionIconProps,
  ModalProps,
  TabsProps,
  TableProps,
  NumberInputProps,
};

// Export safe access helpers
export {
  ensureArray,
  nn,
  hasItems,
  safeLength,
  safeMap,
  safeGet,
  safeBool,
  safeString,
  safeNumber
};
