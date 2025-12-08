#!/usr/bin/env python3
"""
Profiling script to find bottlenecks in enrichment functions.
Run: python3 profile_enrichments.py
"""

import sys
import time
import cProfile
import pstats
from io import StringIO

sys.path.insert(0, '/Users/venom/Documents/analyse-financiere/copilot-app/backend/src')

from services.judge_pipeline import (
    compute_fusion_score,
    get_tech_enriched,
    get_fundamental_minimal,
)

print("=" * 80)
print("PROFILING ENRICHMENT FUNCTIONS - BOTTLENECK ANALYSIS")
print("=" * 80)

# Test data
test_phases = {
    "fundamental": {"score": 0.7, "summary": ["test"]},
    "technical": {"score": 0.6, "summary": ["test"]},
    "macro": {"score": 0.65, "summary": ["test"]},
    "sentiment": {"score": 0.5, "summary": ["test"]},
}

judge_features = {
    "computed_at": "2025-11-26T00:00:00Z",
    "tickers": {}  # Force live calculation
}

# Warm up
for _ in range(3):
    compute_fusion_score(test_phases)

print("\n" + "=" * 80)
print("TEST 1: compute_fusion_score() - 100 iterations")
print("=" * 80)

profiler = cProfile.Profile()
profiler.enable()

t0 = time.perf_counter()
for _ in range(100):
    result = compute_fusion_score(test_phases)
elapsed = (time.perf_counter() - t0) * 1000

profiler.disable()

s = StringIO()
ps = pstats.Stats(profiler, stream=s).sort_stats('cumulative')
ps.print_stats(10)
print(s.getvalue())

print(f"\n✓ Total time: {elapsed:.2f}ms for 100 calls")
print(f"✓ Average: {elapsed/100:.4f}ms per call")
print(f"✓ Throughput: {100000/elapsed:.0f} calls/second")

# Test 2: get_tech_enriched (will hit yfinance - slow!)
print("\n" + "=" * 80)
print("TEST 2: get_tech_enriched() - 1 call (AAPL live)")
print("=" * 80)

profiler2 = cProfile.Profile()
profiler2.enable()

t0 = time.perf_counter()
tech_result = get_tech_enriched("AAPL", judge_features)
elapsed = (time.perf_counter() - t0) * 1000

profiler2.disable()

s2 = StringIO()
ps2 = pstats.Stats(profiler2, stream=s2).sort_stats('cumulative')
ps2.print_stats(15)
print(s2.getvalue())

print(f"\n✓ Time: {elapsed:.2f}ms")
print(f"✓ Result source: {tech_result.get('source')}")
print(f"✓ RSI: {tech_result.get('rsi')}")

# Test 3: get_fundamental_minimal
print("\n" + "=" * 80)
print("TEST 3: get_fundamental_minimal() - 1 call (AAPL live)")
print("=" * 80)

profiler3 = cProfile.Profile()
profiler3.enable()

t0 = time.perf_counter()
fund_result = get_fundamental_minimal("AAPL")
elapsed = (time.perf_counter() - t0) * 1000

profiler3.disable()

s3 = StringIO()
ps3 = pstats.Stats(profiler3, stream=s3).sort_stats('cumulative')
ps3.print_stats(15)
print(s3.getvalue())

print(f"\n✓ Time: {elapsed:.2f}ms")
if "error" not in fund_result:
    print(f"✓ PE Ratio: {fund_result.get('pe_ratio')}")
    print(f"✓ Valuation: {fund_result.get('valuation_signal')}")
else:
    print(f"✗ Error: {fund_result.get('error')}")

# Test 4: Full pipeline simulation
print("\n" + "=" * 80)
print("TEST 4: FULL ENRICHMENT PIPELINE - 10 tickers")
print("=" * 80)

tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "META", "NVDA", "AMD", "NFLX", "DIS"]

t0 = time.perf_counter()
results = []

for ticker in tickers:
    ticker_start = time.perf_counter()
    
    fusion = compute_fusion_score(test_phases)
    tech = get_tech_enriched(ticker, judge_features)
    fund = get_fundamental_minimal(ticker)
    
    ticker_time = (time.perf_counter() - ticker_start) * 1000
    
    results.append({
        "ticker": ticker,
        "time_ms": ticker_time,
        "fusion_ok": "score" in fusion,
        "tech_ok": "error" not in tech,
        "fund_ok": "error" not in fund,
    })
    
    print(f"{ticker:6s}: {ticker_time:7.1f}ms - " + 
          f"Fusion:{'✓' if results[-1]['fusion_ok'] else '✗'} " +
          f"Tech:{'✓' if results[-1]['tech_ok'] else '✗'} " +
          f"Fund:{'✓' if results[-1]['fund_ok'] else '✗'}")

total_time = (time.perf_counter() - t0) * 1000

print(f"\n{'=' * 80}")
print(f"PIPELINE SUMMARY:")
print(f"  Total time: {total_time:.1f}ms for {len(tickers)} tickers")
print(f"  Average: {total_time/len(tickers):.1f}ms per ticker")
print(f"  Min: {min(r['time_ms'] for r in results):.1f}ms")
print(f"  Max: {max(r['time_ms'] for r in results):.1f}ms")
print(f"  Throughput: {len(tickers)/(total_time/1000):.2f} tickers/second")

# Success rates
fusion_success = sum(1 for r in results if r['fusion_ok'])
tech_success = sum(1 for r in results if r['tech_ok'])
fund_success = sum(1 for r in results if r['fund_ok'])

print(f"\nSUCCESS RATES:")
print(f"  Fusion: {fusion_success}/{len(tickers)} ({fusion_success/len(tickers)*100:.0f}%)")
print(f"  Tech: {tech_success}/{len(tickers)} ({tech_success/len(tickers)*100:.0f}%)")
print(f"  Fund: {fund_success}/{len(tickers)} ({fund_success/len(tickers)*100:.0f}%)")

print(f"\n{'=' * 80}")
print("BOTTLENECK IDENTIFICATION:")
print("=" * 80)

# Identify bottleneck
avg_time = total_time / len(tickers)
if avg_time > 2000:
    print("🔴 CRITICAL: Average >2s per ticker - yfinance calls are the bottleneck")
    print("   → Recommendation: Add caching or parallel execution")
elif avg_time > 1000:
    print("🟡 WARNING: Average >1s per ticker - acceptable but can improve")
    print("   → Recommendation: Consider retry with timeout")
else:
    print("🟢 OK: Average <1s per ticker - performance acceptable")

print("\n" + "=" * 80)
print("PROFILING COMPLETE")
print("=" * 80)
