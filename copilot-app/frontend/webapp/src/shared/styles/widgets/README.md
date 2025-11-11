# Widget Glass Styles

- `glassWidget.module.css` contains reusable classes for glass card visuals (`glassCard`, `sparkIcon`, `actionIcon`, etc.).
- Each widget should import this file and combine it with its own module for layout-specific rules.
- Example:
  ```ts
  import shared from '@/shared/styles/widgets/glassWidget.module.css';
  import styles from './SomeWidget.module.css';
  <Card className={`${shared.glassCard} ${styles.widgetCard}`}>...
  ```
