# Audit: Architecture Cleanup Recommendations

**Date:** 2026-02-28  
**Scope:** Codebase structure, documentation, symlinks, storage  
**Focus:** Pre-agent reactivation cleanup

---

## Summary

Comprehensive audit identified **4 categories of technical debt** that could impact agent execution and onboarding clarity. All issues are **low-impact for runtime** but **high-impact for maintainability**.

---

## 1. ✅ RESOLVED: Obsolete Paths in Planning Docs

### Issue
- **docs/product/planning/epics.md** – 7+ references to `copilot-app/backend/src/` (pre-migration path)
- **docs/product/planning/mvp-plan.md** – Active commands referencing `copilot-app/backend/`
- **docs/product/planning/stories.md** – Multiple obsolete path references

### Solution Applied
✅ **All 3 files updated** to current structure:
- `copilot-app/backend/` → `apps/api/src/domains/judge/`
- `copilot-app/frontend/` → `apps/web/src/domains/home/pages/`
- `cd copilot-app/backend && pytest` → `cd apps/api && pytest`

**Impact:** Prevents new agents from following outdated paths → reduces regression risk

---

## 2. ✅ RESOLVED: Broken Symlinks in docs/memory-hub

### Issue
- `docs/memory-hub/imported-from-openclaw-workspace` → points to non-existent directory

### Solution Applied
✅ **Broken symlink removed**

### Valid Symlinks (status: OK)
- `docs/memory-hub/memory` → `../memory` ✓
- `docs/memory-hub/agents` → `../memory/agents` ✓
- `docs/memory-hub/archive` → `../archive` ✓
- `docs/memory-hub/chat-journal` → `../memory/chat-journal` ✓

---

## 3. ⚠️ EXPECTED: Broken Symlinks in scripts/ (60+)

### Issue
- **60+ broken symlinks in `scripts/` directory**
- All point to `/home/venom/shared/analyse-financiere/platform/` (VM shared path)

### Analysis
**This is BY DESIGN**, not a bug:
- Local Mac workspace intentionally doesn't have VM-shared scripts
- VM-only automation/admin scripts (tmux crons, orchestration, Qwen tools)
- These work correctly **on the VM** where shared path exists
- Not needed on Mac development machine

### Recommendation
**No immediate action required.** Document as expected behavior:
- Add comment to `scripts/.gitignore` or readme
- These scripts auto-work when git-mounted on VM
- Developers unfamiliar with architecture won't be confused

---

## 4. 🔴 RECOMMEND: Consolidated docs/ops vs docs/operations

### Issue

**Duplicate documentation directories:**
- `docs/operations/` – 16 root files (legacy structure)
- `docs/ops/` – 23 root files (post-migration structure with new files)

**Subdirectories identical:**
- `docs/ops/ops/` = `docs/operations/ops/` (both 40 files, diff shows identical content)
- `docs/ops/orchestrator/` = `docs/operations/orchestrator/` (same structure)
- `docs/ops/safety/` = `docs/operations/safety/` (same structure)

**References scattered:**
- `docs/WORKSPACE_MAP.md` links to `docs/operations/`
- Some docs reference `docs/ops/`
- Agents reading nav might pick either location

### Recommendation

**Phase 1 (Immediate):**
1. Establish `docs/ops/` as canonical location (already updated with new strategy docs)
2. Update `docs/WORKSPACE_MAP.md` to reference `docs/ops/*` instead of `docs/operations/*`
3. Add navigation header to `docs/operations/README.md` redirecting to `docs/ops/`

**Phase 2 (Future):**
- Archive or remove `docs/operations/` once all references updated
- Maintain dual structure for 1 sprint if needed, but clearly mark obsolescence

**Impact of NOT fixing:**
- New agents might reference outdated docs (confusion)
- Duplicate maintenance (changes needed in 2 places)
- Unclear which is canonical location

---

## 5. 📦 Storage Audit

### Issue
- `archive/` directory = **276 MB** of post-migration debris
  - `cleanup_lt100_20260228T005817Z/` – incomplete migration state
  - `legacy/` – pre-2.0 code
  - `obsolete-locks/` – stale lock files
  - `runtime-legacy-20260227T225812Z/` – old backend runtime
  - `structure-migrations/` – migration temp files

### Recommendation

**Assessment:**
- Low priority for runtime (agents never touch archive/)
- Useful for historical reference during transition
- Slows git clone by ~276 MB

**Options:**
1. **Keep:** Retain for post-migration reference (minimal impact if unused)
2. **Archive to external:** Store archive/ tarball on external disk, remove from git
3. **Selective cleanup:** Remove only `cleanup_*` and `runtime-legacy-*` (~150 MB gain)

**Recommended:** Option 1 (keep for now, revisit in 2 weeks when migration fully stabilized)

---

## 6. Configuration Files Audit

### Status: ✅ ALL HEALTHY
- `docs/orchestrator-ops/priority-queue.json` – Valid JSON ✓
- `platform/config/llm-models.json` – Valid JSON ✓
- `scripts/cron_tmux_role_runner.sh` – Syntax valid ✓

---

## 7. Memory Structure Verification

### Status: ✅ COMPLETE
- **Daily memory files:** 4 (Feb 25-28) ✓
- **Role memory files:** 17 agents ✓
- **3-day strategy deployed:** Function in cron_tmux_role_runner.sh ✓
- **VM sync status:** Git mount working, scripts synchronized ✓

---

## Summary Table

| Issue | Category | Severity | Status | Action | Owner |
|-------|----------|----------|--------|--------|-------|
| Obsolete paths in epics/mvp/stories | Architecture | 🔴 HIGH | ✅ Fixed | None | - |
| Broken symlink docs/memory-hub | Integrity | 🟡 MEDIUM | ✅ Fixed | None | - |
| Broken scripts/ symlinks | Expected | 🟢 LOW | N/A | Document | Ops docs |
| docs/ops vs docs/operations | Navigation | 🟡 MEDIUM | ⚠️ Pending | Consolidate references | Next sprint |
| archive/ bloat | Storage | 🟢 LOW | N/A | Monitor | Next review |
| configs/JSON | Quality | 🟢 LOW | ✅ Verified | None | - |
| Memory structure | Continuity | 🟢 LOW | ✅ Verified | None | - |

---

## Next Steps (Priority Order)

### Immediate (This Session) – DONE
1. ✅ Update obsolete paths in planning docs
2. ✅ Remove broken symlinks from docs/

### Short-term (Before All-Hands Agent Session)
3. **Update docs/WORKSPACE_MAP.md** – Change docs/operations → docs/ops references (5 min)
4. **Add navigation redirects** – Create docs/operations/README.md → docs/ops notice (2 min)

### Medium-term (Next Sprint)
5. Consider consolidation of docs/operations → docs/ops (after all references verified)

### Not Actionable Yet
- archive/ cleanup – defer until migration fully stabilized
- scripts/ symlinks – expected, document and move on

---

## Validation Checklist

- [x] Planning docs updated (epics.md, mvp-plan.md, stories.md)
- [x] Broken symlinks removed (docs/memory-hub/)
- [x] scripts/ symlinks analyzed (expected behavior, no action)
- [x] docs/ops vs operations documented (recommendation in progress)
- [x] Memory structure verified
- [x] Config files validated
- [ ] docs/WORKSPACE_MAP.md updated (next)
- [ ] docs/operations/README.md redirect created (next)

---

## Risk Assessment

**Low Risk Changes Made:**
- Path updates in markdown docs (no code affected)
- Symlink removal (one dead link)
- Documentation updates (reference only)

**No Agent Impact:**
- Backend/frontend code untouched
- Runtime behavior unchanged
- All infrastructure operational

---

*Audit completed by: Agent Audit Tool*  
*Next review: 2026-03-06 (post-agent session stabilization)*
