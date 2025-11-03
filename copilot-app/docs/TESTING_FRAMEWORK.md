# 🧪 TESTING FRAMEWORK - FINANCE COPILOT

## 📋 OVERVIEW

This document explains how to use the comprehensive testing framework for the Finance Copilot application. The framework includes multiple layers of testing to ensure the application works correctly from backend to frontend.

## 🛠️ TESTING TOOLS AVAILABLE

### 1. **Unit Tests** (`tests/`)
- Location: `tests/test_*.py`
- Run with: `make test` or `pytest tests/`
- Tests individual components and functions

### 2. **Integration Tests** (`scripts/`)
- Location: `scripts/test_*.py`
- Run individually or with master runner
- Tests complete workflows and data flows

### 3. **API Tests** (`api/tests/`)
- Location: `api/tests/`
- Run with: `make test-api`
- Tests API endpoints and responses

### 4. **End-to-End Tests** (`webapp/tests/`)
- Location: `webapp/tests/`
- Run with: `cd webapp && npm test`
- Tests frontend components and user flows

## 🚀 QUICK START - RUNNING ALL TESTS

### Option 1: Master Test Runner (Recommended)
```bash
# Run all tests with one command
cd /Users/venom/Documents/analyse-financiere
python scripts/master_test_runner.py
```

### Option 2: Individual Test Scripts
```bash
# Run specific test scripts
python scripts/test_ui_components.py
python scripts/test_ui_runner.py
python scripts/quick_api_test.py
python scripts/integration_test.py
```

### Option 3: Traditional Make Commands
```bash
# Run standard test suite
make test
make it-integration  # Requires AF_ALLOW_INTERNET=1
```

## 📊 TEST CATEGORIES

### 1. **API Layer Tests**
Tests the backend API endpoints and data flow:

```bash
# Test API endpoints
python scripts/quick_api_test.py

# Expected output:
# 📡 Testing Health Check...
# ✅ Health Check: SUCCESS
# 📡 Testing Dashboard KPIs...
# ✅ Dashboard KPIs: SUCCESS
# 📡 Testing Weekly Brief...
# ✅ Weekly Brief: SUCCESS
```

### 2. **UI Component Tests**
Tests frontend components and their integration with backend:

```bash
# Test UI components
python scripts/test_ui_components.py

# Expected output:
# 🧩 Testing UI Component: Dashboard KPIs
# ✅ Dashboard KPIs: SUCCESS
# 🧩 Testing UI Component: Weekly Market Brief
# ✅ Weekly Market Brief: SUCCESS
```

### 3. **Integration Tests**
Tests complete data flow from data sources to UI:

```bash
# Test complete integration
python scripts/integration_test.py

# Expected output:
# 🧪 API to Frontend Integration: SUCCESS
# 🔄 Data Consistency: SUCCESS
# 🚶 User Journey Simulation: SUCCESS
```

### 4. **Smoke Tests**
Quick validation that critical paths work:

```bash
# Run smoke test
make smoke

# Expected output:
# 🚀 Running smoke tests...
# ✅ API health check passed
# ✅ Dashboard loads successfully
# ✅ Market brief generates
# ✅ All tests passed!
```

## 🔍 DETAILED TESTING PROCEDURES

### 1. **Pre-Flight Check**
Before running any tests, ensure the application is properly set up:

```bash
# Check dependencies
pip list | grep -E "(fastapi|pandas|numpy|yfinance|duckdb)"

# Check environment
ls -la .env  # Should exist
ls -la data/  # Should contain RAG data

# Check API availability
curl -s http://localhost:8050/health | jq '.ok'
```

### 2. **Running Unit Tests**
```bash
# Run all unit tests
make test

# Run specific test module
pytest tests/test_core_data_access.py -v

# Run tests with coverage
pytest --cov=src tests/ --cov-report=html
```

### 3. **Running Integration Tests**
```bash
# Run integration tests (requires internet)
AF_ALLOW_INTERNET=1 make it-integration

# Run specific integration test
AF_ALLOW_INTERNET=1 pytest tests/it_integration/ -v
```

### 4. **Manual API Testing**
```bash
# Test health endpoint
curl http://localhost:8050/health

# Test dashboard KPIs
curl http://localhost:8050/api/dashboard/kpis

# Test weekly brief
curl http://localhost:8050/api/brief/weekly

# Test copilot ask
curl -X POST http://localhost:8050/api/copilot/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"What is the current inflation rate?"}'
```

### 5. **Frontend Testing**
```bash
# Run frontend unit tests
cd webapp && npm test

# Run frontend E2E tests
cd webapp && npm run test:e2e

# Check frontend build
cd webapp && npm run build
```

## 🎯 TEST SCENARIOS

### Scenario 1: New Feature Development
When adding a new feature, follow this testing workflow:

1. **Write unit tests** for new functions
2. **Test API endpoints** manually with curl
3. **Verify frontend integration** with React components
4. **Run integration tests** to ensure data flow
5. **Execute smoke tests** for quick validation

### Scenario 2: Bug Fixing
When fixing a bug, follow this process:

1. **Reproduce the issue** manually
2. **Write a test** that captures the bug
3. **Fix the code** to make the test pass
4. **Run related tests** to prevent regressions
5. **Validate the fix** with manual testing

### Scenario 3: Performance Optimization
When optimizing performance:

1. **Run baseline tests** to measure current performance
2. **Profile the code** with performance tools
3. **Implement optimizations**
4. **Run performance tests** to verify improvements
5. **Check for regressions** with full test suite

## 📈 MONITORING TEST RESULTS

### Test Output Interpretation
```bash
# Success indicators:
✅ PASS - Test completed successfully
🎉 ALL TESTS PASSED - No failures
🚀 READY FOR DEPLOYMENT - All criteria met

# Warning indicators:
⚠️  WARNING - Non-critical issue detected
🚧 SKIPPED - Test intentionally bypassed

# Failure indicators:
❌ FAIL - Test failed
💥 ERROR - Unexpected exception
⏰ TIMEOUT - Test took too long
```

### Continuous Integration
The project includes GitHub Actions workflows for automated testing:

- **`ci.yml`** - Runs on every push/pull request
- **`nightly.yml`** - Runs integration tests nightly
- **`release.yml`** - Runs full test suite on tagged releases

## 🛡️ QUALITY GATES

### Minimum Requirements for Merge
Before merging any code, ensure:

1. **✅ All unit tests pass** (`make test`)
2. **✅ Smoke tests pass** (`make smoke`)
3. **✅ No linting errors** (`make lint`)
4. **✅ Code coverage ≥ 80%**
5. **✅ Documentation updated**

### Production Deployment Checklist
Before deploying to production:

1. **✅ All integration tests pass** (`make it-integration`)
2. **✅ API health check passes**
3. **✅ Frontend builds successfully**
4. **✅ Performance benchmarks met**
5. **✅ Security scan clean**
6. **✅ Backup procedures tested**

## 📚 TROUBLESHOOTING

### Common Test Failures

#### 1. **Import Errors**
```bash
# Symptom:
ModuleNotFoundError: No module named 'core.data_access'

# Solution:
pip install -r requirements.txt
pip install -r requirements-api.txt
```

#### 2. **API Connection Failures**
```bash
# Symptom:
ConnectionError: Failed to connect to localhost:8050

# Solution:
python run_api.py  # Start the API server
```

#### 3. **Missing Environment Variables**
```bash
# Symptom:
KeyError: 'FRED_API_KEY'

# Solution:
cp .env.sample .env
# Edit .env with your actual API keys
```

#### 4. **Data Access Issues**
```bash
# Symptom:
DataAccessError: No data available for SPY

# Solution:
Check internet connection
Verify API keys in .env
Run data seeding: python scripts/populate_rag_store.py
```

### Debugging Tips

1. **Enable verbose logging**:
   ```bash
   export LOG_LEVEL=DEBUG
   python run_api.py
   ```

2. **Run tests with detailed output**:
   ```bash
   pytest -v -s tests/
   ```

3. **Check specific test failures**:
   ```bash
   pytest --tb=long tests/test_specific_module.py
   ```

4. **Profile performance issues**:
   ```bash
   python -m cProfile -o profile.out run_api.py
   ```

## 📞 SUPPORT

If you encounter any issues with the testing framework:

1. **Check the logs**: `tail -f logs/api.log`
2. **Review recent changes**: `git log --oneline -10`
3. **Verify dependencies**: `pip list | grep -E "(fastapi|pandas|numpy)"`
4. **Contact support**: Open an issue in the repository

## 🎉 CELEBRATING SUCCESS

When all tests pass:
```
🎉 ALL TESTS PASSED!
🚀 Application is ready for deployment
📊 Coverage: 92% (excellent!)
✅ No critical issues detected
```

This means your Finance Copilot application is working correctly from data ingestion to UI presentation!