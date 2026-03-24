# Forecast Layer Coverage Matrix

Updated: 2026-03-02
Mode: analysis and prediction only.

## Layers

- `LAYER-1` Company
- `LAYER-2` Sector
- `LAYER-3` Country
- `LAYER-4` Continent
- `LAYER-5` World
- `DRIVER-A` Geopolitical conflict
- `DRIVER-B` Law and regulation changes
- `DRIVER-C` Insider behavior
- `DRIVER-D` Supply chain and commodities
- `DRIVER-E` Macro regimes
- `DRIVER-F` Event timing horizons

## Batch coverage map

- `BATCH-29..35`: forecast quality core (`LAYER-1`, `LAYER-2`, `DRIVER-E`, `DRIVER-F`)
- `BATCH-36..40`: uncertainty and forecast validation platform (`LAYER-1..2`, `DRIVER-E`, provenance)
- `BATCH-41`: free source mesh for `LAYER-1..5` + all drivers
- `BATCH-42`: `DRIVER-A` on `LAYER-3..5` with sector exposure
- `BATCH-43`: `DRIVER-B` on `LAYER-2..4` and company impact links
- `BATCH-44`: `DRIVER-C` on `LAYER-1` and sector spillover
- `BATCH-45`: `DRIVER-D` from `LAYER-5` to `LAYER-1`
- `BATCH-46`: hierarchical `LAYER-3..5` macro regime forecasts
- `BATCH-47`: transmission `LAYER-2` to `LAYER-1`
- `BATCH-48`: `DRIVER-F` matrix across all forecast horizons
- `BATCH-49`: fusion and attribution across all layers and drivers
- `BATCH-50`: final multi-layer gate and quality trend

## Minimum acceptance by layer

- Company (`L1`): forecast + uncertainty + provenance mandatory
- Sector (`L2`): transmission and event sensitivity mandatory
- Country (`L3`): policy and geopolitical context mandatory
- Continent (`L4`): regime and conflict aggregation mandatory
- World (`L5`): top-down macro and risk regime mandatory

## Cross-layer consistency checks

- World to country direction mismatch must be flagged.
- Sector to company impact must include transmission confidence.
- Legal/policy effects must include jurisdiction scope.
- Insider effects must never override global macro context without caveat.

## Free data compliance

- Every layer must map to at least one free/public source family.
- Any non-free source in nominal runtime path fails compliance gate.
