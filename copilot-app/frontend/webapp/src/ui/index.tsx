import { forwardRef } from 'react';
import type { ComponentPropsWithoutRef } from 'react';
import {
  ActionIcon as MantineActionIcon,
  ActionIconProps,
  Anchor,
  Avatar,
  Badge as MantineBadge,
  BadgeProps,
  Box,
  Button as MantineButton,
  ButtonProps,
  Card as MantineCard,
  CardProps,
  Chip,
  Container,
  Grid,
  Divider,
  Flex,
  Group,
  Loader,
  LoaderProps,
  Modal as MantineModal,
  ModalProps,
  Paper,
  Progress,
  ScrollArea,
  Select,
  SimpleGrid,
  Skeleton,
  Slider,
  Stack,
  Tabs as MantineTabs,
  TabsProps,
  Table,
  TableProps,
  NumberInput,
  NumberInputProps,
  Text,
  TextInput,
  TextProps,
  ThemeIcon,
  Title,
  TitleProps,
  Tooltip as MantineTooltip,
  TooltipProps,
  Transition,
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

export const ActionIcon = (props: ActionIconComponentProps) => (
  <MantineActionIcon radius="lg" variant={props.variant ?? 'light'} {...props} />
);

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
