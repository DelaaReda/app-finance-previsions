# UI Styling Guide

## Glass Widget Pattern

Use `src/shared/styles/widgets/glassWidget.module.css` for shared classes:

| Class | Purpose |
| --- | --- |
| `glassCard` | Translucent card background (apply to root `Card`). |
| `sparkIcon` | Gradient icon badge. |
| `actionIcon` | Frosted icon button background. |
| `contextPill` | Rounded pill for metadata. |
| `skeletonCard` | Uniform skeleton placeholder card. |
| `flatCard` | Inner cards (news entries, recommendation rows, etc.). |

### Usage
```tsx
import shared from '@/shared/styles/widgets/glassWidget.module.css';
import styles from './NewsWidget.module.css';

<Card className={`${shared.glassCard} ${styles.widgetCard}`}>...
```

Keep widget-specific layout rules in their own module (`SmartRecommendationsWidget.module.css`, etc.) so they can extend the shared look without duplicating colors/shadows.

### Navigation Icons
`AppShell.module.css` styles sidebar links with glass backgrounds and gradients. Each entry in `navItems` provides a `gradient` so icons stay on-brand per route.
