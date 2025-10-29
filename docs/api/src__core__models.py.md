# models.py

Core financial data structures and models.

## Class: `FinancialMetric`

Represents a single financial metric with value and metadata

### Method: `FinancialMetric.to_dict`

Signature: `def to_dict(...)->Dict`

Convert to dictionary representation

Inputs:
- (none)
Returns: `Dict`

### Method: `FinancialMetric.from_dict`

Signature: `def from_dict(...)->'FinancialMetric'`

Create from dictionary representation

Inputs:
- `data`: Dict
Returns: `'FinancialMetric'`

## Class: `CompanyFinancials`

Container for company financial data and metrics

### Method: `CompanyFinancials.add_metric`

Signature: `def add_metric(...)->None`

Add a financial metric

Inputs:
- `metric`: FinancialMetric
Returns: `None`

### Method: `CompanyFinancials.get_metric`

Signature: `def get_metric(...)->Optional[FinancialMetric]`

Get most recent metric by name and period

Inputs:
- `name`: str
- `period`: str = 'TTM'
Returns: `Optional[FinancialMetric]`

### Method: `CompanyFinancials.to_dict`

Signature: `def to_dict(...)->Dict`

Convert to dictionary representation

Inputs:
- (none)
Returns: `Dict`

### Method: `CompanyFinancials.from_dict`

Signature: `def from_dict(...)->'CompanyFinancials'`

Create from dictionary representation

Inputs:
- `data`: Dict
Returns: `'CompanyFinancials'`

## Class: `FinancialAnalysis`

Container for financial analysis results

### Method: `FinancialAnalysis.add_peer`

Signature: `def add_peer(...)->None`

Add peer company analysis

Inputs:
- `peer`: CompanyFinancials
Returns: `None`

### Method: `FinancialAnalysis.add_score`

Signature: `def add_score(...)->None`

Add analysis score

Inputs:
- `name`: str
- `score`: float
Returns: `None`

### Method: `FinancialAnalysis.add_insight`

Signature: `def add_insight(...)->None`

Add analysis insight

Inputs:
- `category`: str
- `message`: str
- `confidence`: float = 1.0
- `source`: Optional[str] = None
Returns: `None`

### Method: `FinancialAnalysis.to_dict`

Signature: `def to_dict(...)->Dict`

Convert analysis to dictionary representation

Inputs:
- (none)
Returns: `Dict`

### Method: `FinancialAnalysis.from_dict`

Signature: `def from_dict(...)->'FinancialAnalysis'`

Create from dictionary representation

Inputs:
- `data`: Dict
Returns: `'FinancialAnalysis'`

## Class: `FeatureBundle`

Unified features passed to IA/Arbitre.

- macro: output of phase3_macro.get_macro_features() (dict-like)
- technical: indicators/metrics for a ticker (dict-like)
- fundamentals: basic financials/ratios (dict-like)
- news: aggregated news signals (e.g., from analytics.market_intel.build_unified_features)
- meta: optional context

### Method: `FeatureBundle.to_dict`

Signature: `def to_dict(...)->Dict[str, Any]`

Inputs:
- (none)
Returns: `Dict[str, Any]`
