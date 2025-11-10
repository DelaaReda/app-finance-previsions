# FRONTEND DATA DEBUG PROTOCOL

Documentation for troubleshooting frontend data issues and transitioning from mock to real data.

## 🔧 CLI Protocol for Unlocking Pages

### Check Current Data Status
```bash
# Check if API endpoints are returning real data
curl -s http://localhost:8050/api/forecasts | jq '{ok, count: (.data.rows | length), source}'
curl -s http://localhost:8050/api/news/feed | jq '{ok, count: (.data.articles | length), source}'  
curl -s http://localhost:8050/api/macro/series | jq '{ok, count: ((.data.series // .data).CPIAUCSL.observations // []).length, source}'
```

### Verify Endpoints Are Not Returning Mocks
```bash
# Check for mock indicators in responses
curl -s http://localhost:8050/api/forecasts | jq 'if .data | has("is_mock") then .data.is_mock else "no_mock_indicator" end'
curl -s http://localhost:8050/api/news/feed | jq 'if .data | has("mock_data") then .data.mock_data else "no_mock_indicator" end'
```

## 🚦 Troubleshooting Page Loading Issues

### Common Frontend Loading Problems
1. **Loading Indefinitely (Spinner)**: Usually means API call is failing or taking too long
2. **Empty States**: Data returned but no items to display
3. **Error States**: Explicit error messages from the API
4. **Never-Empty Contract Violations**: Unexpected null/undefined values causing crashes

### Debug Steps for Each Issue Type

#### Loading Indefinitely
```bash
# 1. Check if backend is running
curl -I http://localhost:8050/health

# 2. Test specific endpoint
time curl -s http://localhost:8050/api/forecasts | jq '.data | length'

# 3. Check network tab equivalent via CLI
curl -w "@curl-format.txt" -s -o /dev/null http://localhost:8050/api/forecasts
```

#### Empty States
```bash
# Check if data exists but isn't being displayed properly
curl -s http://localhost:8050/api/forecasts | jq '{ 
  ok, 
  count: .data.rows | length, 
  has_rows: (.data.rows | length) > 0,
  first_row: .data.rows[0] // "no_rows"
}'

# Verify data filtering isn't removing all items
curl -s "http://localhost:8050/api/forecasts" | jq '.data.rows | map(select(.ticker)) | length'
```

#### Error States
```bash
# Check for error details in API response
curl -s http://localhost:8050/api/forecasts | jq '{ 
  ok, 
  error: .data.error // .error // "no_error_field", 
  message: .data.message // .message // "no_message_field" 
}'
```

## 🚫 Banning Mocks: Transition Protocol

### Identifying Mock Data Patterns
Mock data typically has these characteristics:
- Same timestamp for all records
- Predictable values (round numbers, sequential IDs)
- `is_mock: true` or `source: "mock"` field
- Limited variety in content

### Verification Commands
```bash
# Check for mock indicators in various APIs
curl -s http://localhost:8050/api/forecasts | jq '
  .data.rows[0] | 
  . as $first | 
  {
    has_mock_indicator: (.is_mock // .source // .data_source) | contains("mock"),
    timestamp_variety: ([.data.rows[].calculation_timestamp] | unique | length) > 1,
    ticker_variety: ([.data.rows[].ticker] | unique | length) > 3,
    is_real_data: ([$first.direction, $first.confidence, $first.expected_return] | map(. != null and . != "")) | all
  }
'

# Validate news data is real
curl -s http://localhost:8050/api/news/feed | jq '
  .data.articles[0] as $first |
  {
    has_real_content: ($first.title // $first.headline) | length > 10,
    has_valid_timestamp: ($first.pubDate // $first.timestamp) | test("\\d{4}-\\d{2}-\\d{2}"),
    source_variety: ([.data.articles[].source] | unique | length) > 2,
    has_actual_links: [$first.link] | all(. != "javascript:void(0)")
  }
'
```

## 🐛 Debugging Specific Pages

## ⚡ Snapshot-Powered Endpoints (Macro, Forecasts, Brief)

The heaviest APIs now load straight from cached JSON snapshots so the UI never waits on live scrapers:

| Endpoint | Snapshot file | Refresh job |
| --- | --- | --- |
| `/api/macro/series` | `copilot-app/backend/data/macro_series.json` | `python jobs/macro_series_snapshot.py` |
| `/api/forecasts` | `copilot-app/backend/data/forecasts.json` | `python jobs/forecasts.py` |
| `/api/brief/weekly` + `/api/brief/daily` | `copilot-app/backend/data/brief_weekly.json` (daily falls back here) | `python jobs/weekly_brief.py` |

### CLI loop to validate cache → API alignment
```bash
cd copilot-app/backend

# 1. Inspect the snapshot (should exist + contain rows)
jq '.data.rows | length' data/forecasts.json

# 2. Hit the endpoint (should match the file count)
curl -s http://localhost:8050/api/forecasts | jq '{count: (.data.rows | length), source: .data.source}'

# 3. Regenerate if empty; API will serve it instantly afterwards
python jobs/forecasts.py && curl -s http://localhost:8050/api/forecasts | jq '.data.count'
```

When a snapshot is missing, the API now triggers the corresponding job **once** then falls back to the cached file, so cold-start debugging is simply:

```bash
cd copilot-app/backend
python jobs/macro_series_snapshot.py && python jobs/weekly_brief.py && python jobs/forecasts.py
```

If the job fails, check `/tmp/macro_series_snapshot.log` or the job's stdout (each job already logs tickers/series processed).

### Forecasts Page Debug
```bash
# Test forecasts endpoint with various filters
curl -s "http://localhost:8050/api/forecasts" | jq '
{
  status: .ok,
  count: .data.rows | length,
  tickers_present: ([.data.rows[].ticker] | unique) | length,
  has_confidence: ([.data.rows[].confidence] | all(. > 0 and . <= 1)),
  has_valid_returns: ([.data.rows[].expected_return] | any(. != null))
}
'
```

### News Page Debug
```bash
# Test news endpoint for real data
curl -s "http://localhost:8050/api/news/feed" | jq '
{
  status: .ok,
  count: .data.articles | length,
  has_real_titles: ([.data.articles[].title] | map(length > 10) | all),
  has_valid_dates: ([.data.articles[].pubDate] | all(test("\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}"))?,
  sources_count: ([.data.articles[].source] | unique | length)
}
'
```

### Macro Page Debug
```bash
# Test macro endpoint for real data
curl -s "http://localhost:8050/api/macro/series" | jq '
{
  status: .ok,
  series_count: [."CPIAUCSL", ."UNRATE", .data.CPIAUCSL, .data.UNRATE] | map(select(. != null)) | length,
  has_observations: (.data.CPIAUCSL.observations // .CPIAUCSL.observations // []).length > 0,
  dates_recent: ((.data.CPIAUCSL.observations // .CPIAUCSL.observations // [])[-1].date // "") > "2025-01-01"
}
'
```

### Recommendations Widget Debug
```bash
# Refresh supporting data then generate fresh recommendations snapshot
cd copilot-app/backend
source .venv/bin/activate
python jobs/forecasts.py
python - <<'PY'
import asyncio, sys
sys.path.append('copilot-app/backend')
from services.recommendations_service import RecommendationsService

async def main():
    svc = RecommendationsService()
    data = await svc.generate_daily_recommendations(limit=3)
    print(f"Generated {len(data.get('recommendations', []))} recommendations")
asyncio.run(main())
PY

# API response now serves the cached snapshot instantly
curl -s http://localhost:8050/api/recommendations/daily | jq '.data.recommendations'
```

## 🧪 Testing Never-Empty Contract

### Safe Access Validation
```bash
# Test that APIs return proper structure even without data
curl -s "http://localhost:8050/api/forecasts" | jq '
{
  has_data_field: has("data"),
  has_rows_if_ok: if .ok then (.data | has("rows") or has("articles") or has("series")) else true end,
  is_never_empty: (.data | has("rows") or has("articles") or has("series")) or (.data == {})
}
'
```

### Edge Case Testing
```bash
# Test with restrictive filters to ensure structure remains
curl -s "http://localhost:8050/api/forecasts?ticker=NONSENSE" | jq '
{
  status: .ok,
  structure_intact: (.data | has("rows") or has("articles") or has("count") or has("message")),
  no_crashes: (.data | type) | in("object", "array")
}
'
```

## 🧰 Debugging Tools & Scripts

### Quick Health Check Script
```bash
#!/bin/bash
# frontend-health-check.sh

echo "=== Frontend Data Health Check ==="

echo "Testing /api/forecasts..."
fc_resp=$(curl -s http://localhost:8050/api/forecasts)
fc_ok=$(echo $fc_resp | jq -r '.ok')
fc_count=$(echo $fc_resp | jq -r '.data.rows | length // 0')
echo "  Status: $fc_ok, Count: $fc_count"

echo "Testing /api/news/feed..."
news_resp=$(curl -s http://localhost:8050/api/news/feed)
news_ok=$(echo $news_resp | jq -r '.ok')
news_count=$(echo $news_resp | jq -r '.data.articles | length // 0')
echo "  Status: $news_ok, Count: $news_count"

echo "Testing /api/macro/series..."
macro_resp=$(curl -s http://localhost:8050/api/macro/series)
macro_ok=$(echo $macro_resp | jq -r '.ok // "N/A"')
echo "  Status: $macro_ok"

echo "=== Data Validation Complete ==="
```

### Mock Detection Script
```bash
#!/bin/bash
# detect-mocks.sh

detect_mocks_in_response() {
  local endpoint=$1
  local response=$(curl -s "http://localhost:8050$endpoint")
  
  local has_mock_indicators=$(echo $response | jq 'select(.data | has("is_mock") or has("source") or has("mock_data")) | .data.is_mock // .data.source // .data.mock_data')
  local has_pattern_indicators=$(echo $response | jq 'select(.data.rows // .data.articles | length > 0) | .data.rows // .data.articles | .[0:2] | map(.timestamp // .pubDate) | unique | length < 2')
  
  echo "Endpoint: $endpoint"
  echo "  Has Mock Indicators: $has_mock_indicators"
  echo "  Has Pattern Indicators: $has_pattern_indicators"
}

# Test all major endpoints
detect_mocks_in_response "/api/forecasts"
detect_mocks_in_response "/api/news/feed" 
detect_mocks_in_response "/api/macro/series"
```

## 📋 Troubleshooting Checklist

### Before Reporting an Issue:
- [ ] Confirm backend is running (`curl -I http://localhost:8050/health`)
- [ ] Test the specific API endpoint directly with `curl`
- [ ] Verify response structure matches API documentation
- [ ] Check for mock indicators in the response
- [ ] Test without filters to ensure base functionality
- [ ] Check if it's a frontend render issue or data availability issue

### Common Solutions:
1. **Restart backend** to refresh data feeds
2. **Run data generation jobs** if endpoints return empty
3. **Check .env variables** for any mocking toggles
4. **Clear browser cache** and reload
5. **Verify CORS settings** if calling from different origin

This protocol ensures smooth transition from mock to real data and helps troubleshoot frontend data loading issues systematically.
