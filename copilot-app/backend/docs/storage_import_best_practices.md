# 📚 Storage Import Best Practices - Documentation

## Overview
This document outlines the correct patterns for importing and using the storage layer in the Finance Copilot backend. Following these patterns ensures consistent data access and prevents path resolution issues across different deployment environments.

## Correct Import Paths

### For services and routes within `src/` directory:
```python
from backend.storage.io import load_json, save_json
from backend.storage.base import load_json as load_json_base, save_json as save_json_base
```

### For modules within `backend/` root but outside `src/`:
```python
from storage.io import load_json, save_json
```

## Why These Patterns Matter

1. **Path Consistency**: Ensures the backend always reads from the correct data directory regardless of where uvicorn starts from
2. **Never-Empty Contract**: Maintains the never-empty principle with proper fallbacks
3. **Deployment Safety**: Works consistently across different environments (dev, staging, prod)

## Common Import Issues & Solutions

### ❌ Wrong Pattern (causes path issues):
```python
# Problem: Relative import may fail depending on CWD
from storage.io import load_json
```

### ✅ Correct Pattern:
```python
# Solution: Absolute path import
from backend.storage.io import load_json
```

### ❌ Wrong Pattern (inconsistent file naming):
```python
# Problem: Loading without .json extension consistency
data = load_json("forecasts")  # May fail if file is named forecasts.json
```

### ✅ Correct Pattern:
```python
# Solution: Consistent naming convention
data = load_json("forecasts.json")  # Explicitly use .json extension
```

## Implementation Examples

### In Service Files (`src/services/`):
```python
from pathlib import Path
import sys

# Ensure backend root is in path (already done in main.py)
from backend.storage.io import load_json

def get_forecast_data():
    forecasts_data = load_json("forecasts.json")
    if forecasts_data:
        return forecasts_data.get("data", forecasts_data)
    else:
        return {"rows": [], "count": 0}  # Maintain never-empty contract
```

### In API Routes (`src/api/routes/`):
```python
from pathlib import Path
import sys

# Ensure backend root is in path
from backend.storage.io import load_json

@router.get("/forecasts")
async def get_forecasts():
    data = load_json("forecasts.json")
    if data:
        return _ok(data)
    else:
        return _ok({"rows": [], "count": 0, "message": "No forecasts available"})
```

## Quality Assurance

- ✅ All storage imports use absolute paths (backend.storage.*)
- ✅ File names include extension explicitly (.json) in load_json calls
- ✅ Fallback structures maintain never-empty contract
- ✅ Error handling prevents crashes (try/catch blocks)
- ✅ Data validation confirms expected structure before use

## Files Updated
These patterns have been applied to:
- `backend/src/api/services/forecast_service.py`
- `backend/src/api/services/macro_service.py` 
- `backend/src/core/data_loader.py`
- `backend/src/services/dashboard_service.py`
- `backend/src/api/main.py`
- And others identified in the audit

Following these patterns ensures data consistency and prevents the "file not found" issues that were occurring due to path resolution problems.