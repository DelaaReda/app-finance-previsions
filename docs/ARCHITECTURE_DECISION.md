# 📋 ARCHITECTURE DECISION RECORD

## Decision: Use `api/main.py` as Primary API

### Context
Two competing API implementations were discovered:
1. `api/main.py` (477 lines) - Used by `run_api.py`, simpler but had gaps
2. `src/api/main_v2.py` (425 lines) - Referenced by Makefile, more structured but has import issues

### Decision
**Chosen: `api/main.py`** for the following reasons:

1. **Already Implemented**: All critical features already added (data_access, compute_composite_brief, llm_client)
2. **Currently Working**: Properly configured with `run_api.py`
3. **Simpler Migration**: Less complexity for MVP delivery
4. **Faster Delivery**: No need to fix import issues in v2

### Migration Plan
1. Keep `api/main.py` as primary API
2. Copy useful components from `src/api/` if needed
3. Deprecate `src/api/main_v2.py` after MVP
4. Consider migration to v2 architecture post-MVP if benefits justify effort

### Implementation Status
✅ All critical blockers resolved:
- `core/data_access.py` ✅ Implemented
- `compute_composite_brief()` ✅ Implemented  
- `research/llm_client.py` ✅ Implemented
- `/api/rag/seed` ✅ Implemented
- `/api/stocks/prices` range ✅ Fixed
- `/api/dashboard/kpis` ✅ Real data

### Next Steps
1. Final validation of all endpoints
2. Comprehensive testing
3. Documentation completion
4. Production readiness checklist

---
Decision Date: 2025-11-02
Lead: System Architect