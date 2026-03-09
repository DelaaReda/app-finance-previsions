#!/usr/bin/env node
/**
 * BATCH-61-DEV-03: Daily Brief Contract Integration Test
 * 
 * Verifies the /api/brief/daily endpoint returns a valid daily market brief
 * with all required fields: summary, macro_signals, sector_rotation, etc.
 * 
 * Contract requirements:
 * - ok: true
 * - data.summary: string < 200 words
 * - data.macro_signals: array
 * - data.sector_rotation: { top: [], bottom: [] }
 * - data.generated_at: ISO timestamp
 * - data.source: array
 */

import assert from 'node:assert';
import { test } from 'node:test';

const API_BASE = process.env.API_BASE || 'http://localhost:8050';

async function fetchJson(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
  return res.json();
}

test('GET /api/brief/daily returns valid contract', async () => {
  const response = await fetchJson(`${API_BASE}/api/brief/daily`);
  
  // Top-level contract
  assert.strictEqual(response.ok, true, 'Response must have ok=true');
  assert.ok(response.data, 'Response must have data object');
  
  const data = response.data;
  
  // Summary contract
  assert.ok(typeof data.summary === 'string' && data.summary.length > 0, 'summary must be non-empty string');
  const wordCount = data.summary.split(/\s+/).length;
  assert.ok(wordCount <= 200, `summary must be <= 200 words, got ${wordCount}`);
  
  // Macro signals contract
  assert.ok(Array.isArray(data.macro_signals), 'macro_signals must be an array');
  
  // Sector rotation contract
  assert.ok(typeof data.sector_rotation === 'object' && data.sector_rotation !== null, 'sector_rotation must be object');
  assert.ok(Array.isArray(data.sector_rotation.top), 'sector_rotation.top must be array');
  assert.ok(Array.isArray(data.sector_rotation.bottom), 'sector_rotation.bottom must be array');
  
  // Metadata contract
  assert.ok(typeof data.generated_at === 'string' && data.generated_at.length > 0, 'generated_at must be non-empty string');
  assert.ok(Array.isArray(data.source), 'source must be array');
  
  console.log('✓ Daily brief contract validated');
  console.log(`  - summary: ${wordCount} words`);
  console.log(`  - macro_signals: ${data.macro_signals.length} indicators`);
  console.log(`  - sector_rotation: ${data.sector_rotation.top.length} top, ${data.sector_rotation.bottom.length} bottom`);
  console.log(`  - source: ${data.source.join(', ')}`);
});

test('GET /api/brief/daily summary is market-relevant', async () => {
  const response = await fetchJson(`${API_BASE}/api/brief/daily`);
  const summary = response.data.summary.toLowerCase();
  
  // Check for market-relevant keywords
  const marketKeywords = [
    'market', 'bullish', 'bearish', 'risk', 'signal',
    'haussier', 'baissier', 'marché', 'risque', 'opportunité'
  ];
  
  const hasRelevantContent = marketKeywords.some(kw => summary.includes(kw));
  assert.ok(hasRelevantContent, 'Summary should contain market-relevant content');
  
  console.log('✓ Daily brief contains market-relevant content');
});

test('GET /api/brief/daily freshness is reasonable', async () => {
  const response = await fetchJson(`${API_BASE}/api/brief/daily`);
  const data = response.data;
  
  // Check freshness field if present
  if (data.freshness) {
    // Freshness can be a category (fresh/stale/unknown/empty/error) or a timestamp
    const validCategories = ['fresh', 'stale', 'unknown', 'empty', 'error'];
    const isCategory = validCategories.includes(data.freshness);
    const isTimestamp = typeof data.freshness === 'string' && data.freshness.match(/^\d{4}-\d{2}-\d{2}T/);
    
    assert.ok(isCategory || isTimestamp, 'freshness must be a category or ISO timestamp');
    console.log(`✓ Freshness: ${data.freshness} (${isTimestamp ? 'timestamp' : 'category'})`);
  } else {
    console.log('ℹ Freshness field not present (optional)');
  }
});
