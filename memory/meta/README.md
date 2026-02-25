# Cognitive-light memory

This folder adds lightweight signal tracking without replacing your existing memory system.

## Tags to use in daily notes

- `[decision]` stable choices and trade-offs
- `[todo]` actionable next steps
- `[risk]` blockers, vulnerabilities, regressions
- `[note]` useful context worth keeping

## Weekly consolidation

Run:

```bash
python3 scripts/memory_cognitive_light.py --from-days 7
```

Optional append to `MEMORY.md`:

```bash
python3 scripts/memory_cognitive_light.py --from-days 7 --apply
```

This keeps your current memory architecture and only adds prioritization helpers.
