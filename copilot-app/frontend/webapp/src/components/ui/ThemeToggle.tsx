import { IconMoonStars, IconSun } from '@tabler/icons-react';
import { ActionIcon, Tooltip } from '@/ui';
import { useThemeMode } from '@/context/ThemeContext';

export default function ThemeToggle() {
  const { mode, toggleMode } = useThemeMode();
  const isDark = mode === 'dark';
  return (
    <Tooltip label={`Passer en mode ${isDark ? 'clair' : 'sombre'}`}>
      <ActionIcon
        onClick={toggleMode}
        size="lg"
        variant="light"
        color={isDark ? 'yellow' : 'indigo'}
        aria-label={`Basculer en mode ${isDark ? 'clair' : 'sombre'}`}
      >
        {isDark ? <IconSun size={18} /> : <IconMoonStars size={18} />}
      </ActionIcon>
    </Tooltip>
  );
}
