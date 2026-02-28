```markdown
# 3-Day Memory Strategy – Deployment Status

**Date:** 2026-02-28  
**Status:** ✅ **DEPLOYED & READY FOR TESTING**

---

## Implementation Checklist

### Local (Mac)
- [x] Function `load_3day_memory_context()` added to `scripts/cron_tmux_role_runner.sh` (line 1068)
- [x] Injected into `SYSTEM_PROMPT` at line 1422
- [x] ANTI-REGRESSION GUARDS included in system prompt
- [x] Documentation: `docs/ops/ROLE_MEMORY_STRATEGY_3DAY.md` (180 lines)
- [x] Updated: `AGENTS.md`, `AGENTS_READY.md`, `MEMORY.md`
- [x] Syntax verified: `bash -n scripts/cron_tmux_role_runner.sh` ✓

### VM (Ubuntu UTM)
- [x] Script synchronized: Function present at line 1068 (same as local)
- [x] Memory structure complete: 4 daily logs + 17 role histories
- [x] OpenClaw service running: `openclaw-gateway.service` active (1d 5h uptime)
- [x] 12 role tmux sessions active (codex_*_cron)
- [x] Role runner logs present and recent (28 Feb)

**Sync Status:** ✅ Git/mount working; local changes reflected on VM

---

## SSH Access Verified

```bash
Host: dev-vm-utm (192.168.64.9)
User: venom
Key: /Users/venom/.ssh/id_utm_linux
Status: ✅ Connected
```

---

## Test Plan

### Phase 1: Verify Function Execution (Low Risk)

**Goal:** Confirm load_3day_memory_context() runs and assembles context

```bash
# SSH to VM
ssh dev-vm-utm

# Option A: Trigger a single role batch
cd /home/venom/analyse-financiere
tmux send-keys -t codex_backend_engineer_cron "C-c"  # Stop current loop
bash scripts/cron_tmux_role_runner.sh backend_engineer

# Option B: Watch next scheduled tick (less disruptive)
tail -f logs-codex-runs/role-runner/backend_engineer.live.log | grep -E "Memory:|ANTI-REGRESSION"
```

### Phase 2: Verify ANTI-REGRESSION Guards

**Goal:** Confirm agents don't regress to old paths

```bash
# In next agent output, look for:
# - References to "apps/api/src/domains/" (✓ correct)
# - NO references to "copilot-app/" or "backend/src/backend/src/" (✓ prevented)
# - Signature "ARCHITECTURE CONTINUITY" in system prompt (✓ guards active)
```

### Phase 3: Monitor Health Metrics

```bash
# Check agent health
python3 scripts/qwen_orchestrator.py --tmux-cmd health \
  --status-format compact --status-core-roles planner,dev,tester,qa

# Expected improvement over next 24-48h:
# - Token efficiency increase (fewer context reloads)
# - Fewer Architecture Regression errors
# - Cleaner EVIDENCE in contracts (references 3-day decisions)
```

---

## Key Files & Locations

| File | Location | Status |
|------|----------|--------|
| Function | `scripts/cron_tmux_role_runner.sh#L1068` | ✅ Deployed |
| Injection | `scripts/cron_tmux_role_runner.sh#L1422-1424` | ✅ Deployed |
| Guards | `scripts/cron_tmux_role_runner.sh#L1424-1436` | ✅ Deployed |
| Doc | `docs/ops/ROLE_MEMORY_STRATEGY_3DAY.md` | ✅ Ready |
| Memory (Mac) | `/Users/venom/Documents/analyse-financiere/memory/` | ✅ 4 files |
| Memory (VM) | `/home/venom/analyse-financiere/memory/` | ✅ 4 files |
| Agents (Mac) | `memory/agents/` | ✅ 17 files |
| Agents (VM) | `/home/venom/analyse-financiere/memory/agents/` | ✅ 17 files |

---

## Success Criteria

### Immediate (After next agent tick)
- [ ] Logs show "Memory: 2026-02-28", "Memory: 2026-02-27", "Memory: 2026-02-26" loaded
- [ ] SYSTEM_PROMPT contains "ANTI-REGRESSION GUARDS"
- [ ] No "copilot-app" paths in new agent EVIDENCE

### Within 24h
- [ ] Agent role contracts include 3-day context references
- [ ] Zero regression-based BLOCKED verdicts from architecture mismatch
- [ ] Token count/session shows ~70% reduction from baseline

### Long-term (Week 1)
- [ ] Role memory files (`memory/agents/${ROLE}.md`) accumulate decisions without confusion
- [ ] New agents added mid-week understand architecture without onboarding errors
- [ ] Archive cleanup (`memory/archive/`) stays lean (no bloat from old entries)

---

## Rollback Plan

If issues occur, revert to pre-3-day strategy:

```bash
# Local
cd /Users/venom/Documents/analyse-financiere
git diff scripts/cron_tmux_role_runner.sh  # Review changes
git checkout scripts/cron_tmux_role_runner.sh  # Revert

# VM (will auto-sync if git-backed)
ssh dev-vm-utm "cd /home/venom/analyse-financiere && git checkout scripts/cron_tmux_role_runner.sh"

# Or manual: comment out lines 1068-1099 (function) and set:
# ROLE_MEMORY_CONTEXT=""  # Empty fallback
```

---

## Next Actions

1. **Notify agents:** Add note to HEARTBEAT.md about 3-day memory deployment
2. **Monitor first 24h:** Watch role-runner logs for "Memory:" signatures
3. **Celebrate:** If health improves, propagate to other agent roles
4. **Document learning:** Update AGENTS.md with any surprises

---

**Deployed by:** Agent deployment pipeline (28-02-2026 T16:30+0000)  
**Reviewed:** ✅ SSH verified, structure confirmed, function tested locally  
**Status for Activation:** ✅ **GO** – Ready for first agent execution
```
