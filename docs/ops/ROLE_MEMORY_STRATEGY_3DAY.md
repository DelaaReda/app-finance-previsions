```markdown
# Role Memory Strategy – 3-Day Architecture Continuity

**Objectif:** Agents chargent historique 3 jours pour comprendre décisions architecturales récentes sans régresser vers ancienne structure.

**Policy:** SESSION_INITIALIZATION pour roles (codex cron runner).

---

## Context Loading Hierarchy (Optimisé)

### Phase 1: Session Start (First Codex Response)

Load UNIQUEMENT:
1. **Core identity** (read-only):
   - `SOUL.md` (assistant identity + rules)
   - `USER.md` (owner profile)

2. **Architecture decisions** (last 3 days):
   - `memory/YYYY-MM-DD.md` (today)
   - `memory/YYYY-MM-DD.md` (yesterday)
   - `memory/YYYY-MM-DD.md` (2 days ago)
   - *Assembled in `$ROLE_MEMORY_CONTEXT` var before Codex prompt*

3. **Role-specific memory** (last 3 days):
   - `memory/agents/${ROLE}.md` (latest @ lines 1-50, recent decisions)
   - *Pre-loaded in prompt context*

### Phase 2: During Session (Agent Reasoning)

On-demand context:
- Use `memory_search(pattern)` to find specific decisions
- Pull with `memory_get(date, pattern)` to extract snippet
- **DON'T** load full `MEMORY.md` (curated long-term, triggers regression)

### Phase 3: Session End (Append to Daily Log)

Update:
- `memory/YYYY-MM-DD.md` with session delta (5-10 lines max)
- `memory/agents/${ROLE}.md` with role-specific decisions (3-5 lines max)

---

## Token Footprint (Daily Load)

| Context | Lines | Tokens | Frequency |
|---------|-------|--------|-----------|
| SOUL.md | 40 | 80 | Once/session |
| USER.md | 30 | 60 | Once/session |
| `2026-02-28.md` (today) | 50 | 150 | Once/session |
| `2026-02-27.md` (yesterday) | 80 | 180 | Once/session |
| `2026-02-26.md` (2d ago) | 100 | 200 | Once/session |
| `memory/agents/${ROLE}.md` (first 50 lines) | 50 | 100 | Once/session |
| **Total context overhead** | **350** | **770** | **Per role session** |

**Comparison:**
- ❌ Old (full MEMORY.md + session history): 3,000+ tokens × $0.003/1K = $0.01/session
- ✅ New (3-day window): 770 tokens × $0.003/1K = $0.002/session + clarity
- ✅ **Gain:** 70% context reduction + architectural continuity

---

## Implementation in Role Runner

Location: `scripts/cron_tmux_role_runner.sh`

**Before Codex prompt, inject:**

```bash
# Assemble 3-day memory context (last 3 daily files)
ROLE_MEMORY_CONTEXT=""
for days_ago in 0 1 2; do
  DATE=$(date -v-${days_ago}d +%Y-%m-%d 2>/dev/null || date -d "$days_ago days ago" +%Y-%m-%d 2>/dev/null)
  MEMORY_FILE="${ROLE_MEMORY_DIR}/${DATE}.md"
  if [[ -f "$MEMORY_FILE" ]]; then
    ROLE_MEMORY_CONTEXT+="
## Memory: ${DATE}
$(head -100 "$MEMORY_FILE")
---
"
  fi
done

# Role-specific decisions (last 50 lines of role memory)
if [[ -f "${ROLE_MEMORY_DIR}/${ROLE}.md" ]]; then
  ROLE_SPECIFIC=$(tail -50 "${ROLE_MEMORY_DIR}/${ROLE}.md")
  ROLE_MEMORY_CONTEXT+="
## Role History: ${ROLE}
${ROLE_SPECIFIC}
"
fi

export ROLE_MEMORY_CONTEXT
```

**Inject into Codex system prompt:**

```
[... existing system prompt ...]

## CONTEXT: Architecture & Role Memory (Last 3 Days)

${ROLE_MEMORY_CONTEXT}

## SESSION INITIALIZATION RULE:

1. You have loaded 3 days of architecture decisions above.
2. DO NOT reference or assume:
   - Full MEMORY.md (not loaded; use memory_search if needed)
   - Pre-migration structure (copilot-app/*) - it's archived in archive/
   - Old paths (backend/src/backend/src/) - structure is flattened to apps/api/src/
3. When referencing prior decisions:
   - Check the 3-day memory context above
   - If older than 3 days: use memory_search() then memory_get()
4. At session end:
   - Append 3-5 lines decision delta to memory/YYYY-MM-DD.md
   - Append role-specific notes to memory/agents/${ROLE}.md
```

---

## Anti-Regression Guards

Insert after context, before task:

```markdown
## ARCHITECTURE ANCHORS (Non-negotiable)

Do NOT regress to:
- ❌ `copilot-app/` paths (archived in archive/structure-migrations/)
- ❌ `backend/src/backend/src/` nesting (flattened to apps/api/src/)
- ❌ Legacy `src.* imports` (deprecated; use absolute from apps/api/src/)
- ❌ Full MEMORY.md auto-load (use memory_search + memory_get on demand)

Do reference instead:
- ✅ `apps/api/src/domains/` for backend code
- ✅ `apps/web/src/` for frontend
- ✅ `apps/api/runtime/` for data + cache
- ✅ `memory/YYYY-MM-DD.md` for recent decisions
- ✅ `docs/ops/AGENTS_READY.md` for current state validation
```

---

## Role Memory File Maintenance

Keep `memory/agents/${ROLE}.md` lean:

```markdown
# Agent Memory: ${ROLE}

## Recent Decisions (Append at end, keep last 50 lines)

- [ISO timestamp] decision=<brief> blocker=<none|blocker_id> status=<done|pending>
  - context: <one-liner>
  - impact: <one-liner>
```

**Example:**
```markdown
# Agent Memory: backend_engineer

- [2026-02-28T13:00Z] decision=use_uvicorn_reload_for_dev blocker=NONE status=done
  - context: dev cycle time was 45s per change
  - impact: reduced to 8s; improves iteration velocity

- [2026-02-27T19:30Z] decision=migrate_to_domains_structure blocker=NONE status=done
  - context: consolidate copilot-app/* into apps/api/src/domains/*
  - impact: fewer import errors, clearer ownership per domain
```

---

## Rotation & Archive

When daily files get old (> 7 days):

```bash
# Manual cleanup (quarterly)
cd /Users/venom/Documents/analyse-financiere
mkdir -p memory/archive
mv memory/2026-02-1*.md memory/archive/  # Old entries
```

*System handles this automatically in stale-sweep jobs.*

---

## Verification Checklist

- [ ] `$ROLE_MEMORY_CONTEXT` assembled before Codex exec
- [ ] SESSION_INITIALIZATION_RULE injected in system prompt
- [ ] ARCHITECTURE ANCHORS guard is present
- [ ] Role cron executes with memory context (trace logs show "3-day loaded")
- [ ] New sessions don't regress to old paths
- [ ] daily notes + role notes append at session end

---

## Test Command

```bash
# Simulate 3-day context load for role
ROLE=backend_engineer \
ROLE_MEMORY_DIR=$ROOT/memory/agents \
bash -c '
  for days_ago in 0 1 2; do
    DATE=$(date -v-${days_ago}d +%Y-%m-%d)
    FILE="memory/${DATE}.md"
    echo "=== ${DATE} (exists: $([ -f "$FILE" ] && echo yes || echo no)) ==="
    [ -f "$FILE" ] && wc -l "$FILE"
  done
  echo ""
  echo "=== Role memory: ${ROLE} ==="
  [ -f "memory/agents/${ROLE}.md" ] && tail -20 "memory/agents/${ROLE}.md"
'
```

---

## References

- **AGENTS.md** – Memory policy
- **AGENTS_READY.md** – Current state validation
- **memory/YYYY-MM-DD.md** – Daily logs (format example in last 50 lines)
```
