# Safe Access Patterns - Never-Empty Guidelines

## Overview
To prevent UI crashes like `Cannot read properties of undefined (reading 'map')`, always use safe access helpers.

## Available Helper Functions

### `ensureArray(value)`
Converts any value to an array, preventing crashes when using `.map`, `.length`, etc.

```ts
// ❌ Don't do this
const items = data.items.map(item => ...) // Will crash if data.items is undefined

// ✅ Do this instead
import { ensureArray } from '@/ui' // or '@/lib/safe'
const items = ensureArray(data?.items).map(item => ...)
```

### `nn(value, fallback)`
Returns the value if it's not null/undefined, otherwise returns the fallback.

```ts
// ❌ Don't do this
const name = user.name // Will crash if user is undefined

// ✅ Do this instead
import { nn } from '@/ui'
const name = nn(user?.name, 'Anonymous')
```

### `hasItems(value)`
Safely checks if an array has items without crashing.

```ts
// ❌ Don't do this
if (data.items.length > 0) { ... } // Will crash if data.items is undefined

// ✅ Do this instead
import { hasItems } from '@/ui'
if (hasItems(data?.items)) { ... }
```

### `safeLength(value)`
Safely gets the length of an array without crashing.

```ts
import { safeLength } from '@/ui'
const count = safeLength(data?.items) // Returns 0 if data.items is undefined
```

### `safeMap(array, fn)`
Safely maps over an array, with protection against undefined arrays.

```ts
import { safeMap } from '@/ui'
const mapped = safeMap(data?.items, (item) => ({ ... })) // Won't crash if data.items is undefined
```

## Implementation Examples

### Before (crash-prone)
```tsx
function ForecastList({ data }) {
  return (
    <div>
      {data.forecasts.map(f => (
        <ForecastCard key={f.id} forecast={f} />
      ))}
    </div>
  );
}
```

### After (safe)
```tsx
import { ensureArray } from '@/ui'

function ForecastList({ data }) {
  const forecasts = ensureArray(data?.forecasts);
  return (
    <div>
      {forecasts.map(f => (
        <ForecastCard key={f.id} forecast={f} />
      ))}
    </div>
  );
}
```

### Complete Safe Pattern with All States
```tsx
import { ensureArray, safeLength } from '@/ui';

function SafeForecastList({ data, isLoading, error }) {
  if (isLoading) return <Skeleton count={5} />;
  if (error) return <Alert color="red">{error.message}</Alert>;
  
  const forecasts = ensureArray(data?.forecasts);
  const count = safeLength(forecasts);
  
  if (count === 0) {
    return <EmptyState title="No forecasts available" hint="Check back later or adjust filters" />;
  }
  
  return (
    <div data-testid="forecast-list">
      {forecasts.map(f => (
        <ForecastCard key={f.id} forecast={f} />
      ))}
    </div>
  );
}
```

## Required States for All Components
Every component must handle these 4 states:
1. Loading (Skeleton)
2. Empty (EmptyState)
3. Error (Alert)
4. Freshness (Timestamp badge)

## References
- RFC: FC-P0-007 (Error boundaries)
- DoD: All UI components must be crash-proof
- Pattern: Never-empty with fallbacks