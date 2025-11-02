type Node = { name: string; props: any; state: any; children: Node[] }

export function findPropBloat(n: Node, out: string[] = [], path: string[] = []): string[] {
  const size = Buffer.byteLength(JSON.stringify(n.props ?? {}))
  if (size > 100_000) out.push([...path, n.name].join(' > '))
  n.children.forEach((c, i) => findPropBloat(c, out, [...path, `${n.name}[${i}]`]))
  return out
}

export function findAnonymous(n: Node, out: string[] = [], path: string[] = []): string[] {
  if (!n.name || n.name.startsWith('tag:')) out.push([...path, n.name].join(' > '))
  n.children.forEach((c, i) => findAnonymous(c, out, [...path, `${n.name}[${i}]`]))
  return out
}