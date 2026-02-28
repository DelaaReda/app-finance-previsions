# LLM Agent Mode: DEV vs PROD

**Date:** 2025-12-07  
**File:** `src/analytics/econ_llm_agent.py`

---

## 🎯 Purpose

The econ_llm_agent now supports **two modes** for LLM model selection:

1. **DEV Mode** (default): Fast, lightweight models for rapid development
2. **PROD Mode**: Power models with best quality (g4f_model_watcher integration)

---

## 🚀 Quick Switch

### **Development (Fast, Default)**
```bash
export ECON_AGENT_MODE=dev
```

### **Production (Best Quality)**
```bash
export ECON_AGENT_MODE=prod
```

Or edit `.env`:
```bash
ECON_AGENT_MODE=dev  # or prod
```

---

## 📊 Mode Comparison

| Feature | DEV Mode | PROD Mode |
|---------|----------|-----------|
| **Models** | gpt-4o-mini, gpt-3.5-turbo, mistral-small | DeepSeek-V3, R1, Qwen, Claude, etc |
| **Timeout** | 10s | 15s |
| **Max Tokens** | 800 | 2048 |
| **Char Budget** | 30K | 60K |
| **Model Limit** | 3 models | 18 models |
| **Dynamic Loading** | ❌ Disabled | ✅ Enabled (g4f_model_watcher) |
| **Typical Latency** | 3-5s | 10-30s |
| **Best For** | Development, testing, iteration | Production, best quality analysis |

---

## 🔧 How It Works

### **DEV Mode**
```python
# Hardcoded fast models (no dynamic loading)
DEV_MODELS = [
    "gpt-4o-mini",
    "gpt-3.5-turbo", 
    "mistralai/Mistral-Small-3.2-24B-Instruct-2506",
]

# Skip g4f_model_watcher (faster startup)
# Use lower limits everywhere
```

### **PROD Mode**
```python
# Use g4f_model_watcher.py to get latest working models
# Priority: DeepSeek > Qwen > LLaMA > Claude > Mistral

# Models from:
1. agents/g4f_model_watcher.py -> ensure_working_models()
2. data/llm/models/working.json (cached working models)
3. POWER_NOAUTH_MODELS (static fallback)
```

---

## 🎨 DEV Models Rationale

**Why gpt-4o-mini?**
- Fast (2-4s typical response)
- Good quality for basic tasks
- Available via g4f without auth
- Widely supported

**Why gpt-3.5-turbo?**
- Ultra-fast fallback (1-3s)
- Stable, reliable
- Low latency

**Why mistral-small?**
- Good balance speed/quality
- European alternative
- Strong reasoning for finance

---

## 🏗️ Architecture

```
econ_llm_agent.py
├── MODE = os.getenv("ECON_AGENT_MODE", "dev")
├── 
├── if MODE == "dev":
│   ├── Use DEV_MODELS (3 fast models)
│   ├── Skip g4f_model_watcher
│   └── Lower timeouts/limits
│
└── if MODE == "prod":
    ├── Load from:
    │   ├── g4f_model_watcher.ensure_working_models()
    │   ├── data/llm/models/working.json
    │   └── POWER_NOAUTH_MODELS (fallback)
    ├── Dynamic model ranking
    └── Full timeouts/limits
```

---

## 🔄 Switching Example

### **Scenario: Development → Production**

**During Development:**
```bash
# .env
ECON_AGENT_MODE=dev

# Result:
# ✅ 3-5s response times
# ✅ Iterate quickly
# ✅ gpt-4o-mini for basic testing
```

**Before Production Deploy:**
```bash
# .env
ECON_AGENT_MODE=prod

# Result:
# ✅ Best quality models (DeepSeek-V3, R1)
# ✅ Full context (60K chars)
# ✅ Longer but higher quality responses
```

---

## 📝 Environment Variables

### **Primary Control**
```bash
ECON_AGENT_MODE=dev  # or prod
```

### **All ECON_AGENT Variables** (optional overrides)
```bash
ECON_AGENT_MODE=dev                    # Mode selector (NEW)
ECON_AGENT_CHAR_BUDGET=30000          # Context size (auto-set by mode)
ECON_AGENT_MAX_TOKENS=800             # Max response tokens (auto-set)
ECON_AGENT_TIMEOUT=10                 # Timeout in seconds (auto-set)
ECON_AGENT_TEMPERATURE=0.2            # LLM temperature
ECON_AGENT_RETRIES=1                  # Retries per model
ECON_AGENT_MAX_MODELS=3               # Max models to try (auto-set)
ECON_AGENT_MAX_DYNAMIC=2              # Max dynamic models (auto-set)
ECON_AGENT_MODELS=custom,list         # Manual model override (ignores mode!)
ECON_AGENT_DYNAMIC_MODELS=1           # Enable dynamic loading (disabled in dev)
```

---

## 🧪 Testing Both Modes

### **Test DEV Mode**
```bash
export ECON_AGENT_MODE=dev
cd backend
.venv/bin/python3 -c "
from src.analytics.econ_llm_agent import EconomicAnalyst, MODE
print(f'Mode: {MODE}')
agent = EconomicAnalyst()
print(f'Models: {agent.model_candidates[:3]}')
"
# Expected: Mode: dev, Models: ['gpt-4o-mini', 'gpt-3.5-turbo', ...]
```

### **Test PROD Mode**
```bash
export ECON_AGENT_MODE=prod
cd backend
.venv/bin/python3 -c "
from src.analytics.econ_llm_agent import EconomicAnalyst, MODE
print(f'Mode: {MODE}')  
agent = EconomicAnalyst()
print(f'Models: {agent.model_candidates[:3]}')
"
# Expected: Mode: prod, Models: ['deepseek...', 'qwen...', ...]
```

---

## 🎯 Recommendations

### **Use DEV Mode When:**
- ✅ Developing new features
- ✅ Testing /api/judge endpoint
- ✅ Iterating on prompts
- ✅ Running unit tests
- ✅ Local development
- ✅ Need fast feedback (<5s)

### **Use PROD Mode When:**
- ✅ Production deployment
- ✅ Quality matters most
- ✅ Final validation before release
- ✅ Benchmarking model quality
- ✅ Customer-facing analysis
- ✅ Latency is acceptable (10-30s)

---

## 🔐 No Breaking Changes

**Backward Compatible:**
- Default: `ECON_AGENT_MODE=dev` (safe, fast)
- Existing code works without changes
- `.env` without `ECON_AGENT_MODE` → defaults to dev
- All env var overrides still work

**To Restore Old Behavior:**
```bash
# Force production mode (like before)
export ECON_AGENT_MODE=prod
```

---

## 📚 Related Files

- `src/analytics/econ_llm_agent.py` - Main agent with mode logic
- `src/agents/g4f_model_watcher.py` - Dynamic model discovery (prod only)
- `data/llm/models/working.json` - Cached working models (prod only)
- `.env` - Configuration (ECON_AGENT_MODE=)

---

## 💡 Pro Tips

### **Faster Development**
```bash
# Minimum latency for dev iterations
export ECON_AGENT_MODE=dev
export ECON_AGENT_TIMEOUT=5
export ECON_AGENT_MAX_TOKENS=500
```

### **Best Quality (Slower)**
```bash
# Maximum quality for production
export ECON_AGENT_MODE=prod
export ECON_AGENT_TIMEOUT=30
export ECON_AGENT_MAX_TOKENS=3000
export ECON_AGENT_MAX_MODELS=24
```

### **Hybrid (Custom Models)**
```bash
# Override mode with specific models
export ECON_AGENT_MODELS="gpt-4o,claude-3.5-sonnet,deepseek-v3"
# (This ignores MODE and uses your list)
```

---

**Last Updated:** 2025-12-07  
**Status:** ✅ Implemented and Ready for Use
