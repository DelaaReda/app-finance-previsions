type DumpNode = {
  name: string
  key: string | null
  props: any
  state: any
  children: DumpNode[]
}

function safeClone<T>(value: T, depth = 0): any {
  if (depth > 3) return '[DepthLimit]'
  if (value === null || typeof value !== 'object') {
    if (typeof value === 'function') return '[Function]'
    if (typeof value === 'symbol') return '[Symbol]'
    return value
  }
  if (Array.isArray(value)) return value.slice(0, 20).map(v => safeClone(v, depth + 1))
  const out: Record<string, any> = {}
  let count = 0
  for (const k in value as any) {
    if (count++ > 50) { out['[Truncated]'] = true; break }
    try {
      const v = (value as any)[k]
      out[k] = typeof v === 'function' ? '[Function]' : safeClone(v, depth + 1)
    } catch {
      out[k] = '[Unserializable]'
    }
  }
  return out
}

// appelé dans le navigateur
export function dumpReactTree(): { ok: true; trees: DumpNode[] } | { ok: false; error: string } {
  const hook = (window as any).__REACT_DEVTOOLS_GLOBAL_HOOK__
  if (!hook || !hook.renderers || hook.renderers.size === 0) {
    return { ok: false, error: 'DevTools hook not available' }
  }
  const [rendererId] = Array.from(hook.renderers.keys())
  const roots = hook.getFiberRoots(rendererId)
  const trees: DumpNode[] = []

  function ser(fiber: any): DumpNode {
    const name =
      fiber.elementType?.displayName ||
      fiber.elementType?.name ||
      fiber.type?.displayName ||
      fiber.type?.name ||
      `tag:${fiber.tag}`

    const node: DumpNode = {
      name,
      key: fiber.key ?? null,
      props: safeClone(fiber.memoizedProps),
      state: safeClone(fiber.memoizedState),
      children: []
    }

    let child = fiber.child
    while (child) {
      node.children.push(ser(child))
      child = child.sibling
    }
    return node
  }

  for (const root of Array.from(roots)) {
    trees.push(ser((root as any).current || root))
  }
  return { ok: true, trees }
}

// expose en dev si besoin (facilite l'appel depuis Playwright)
if (process.env.NODE_ENV === 'development') {
  ;(window as any).__DUMP_REACT_TREE__ = dumpReactTree
}