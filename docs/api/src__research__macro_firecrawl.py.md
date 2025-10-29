# macro_firecrawl.py

## Function: `fc_extract`

Signature: `def fc_extract(...)->Dict[str, Any]`

Extrait des structures JSON à partir de pages web via Firecrawl SDK.

Inputs:
- `urls`: List[str]
- `prompt`: str
- `schema`: Dict
- `retries`: int = 2
- `timeout_s`: int = 40
Returns: `Dict[str, Any]`

## Function: `fc_search`

Signature: `def fc_search(...)->Dict[str, Any]`

Recherche web via Firecrawl SDK.

Inputs:
- `query`: str
- `limit`: int = 10
- `retries`: int = 1
Returns: `Dict[str, Any]`

## Class: `MacroData`

## Function: `get_economic_indicators`

Signature: `def get_economic_indicators(...)->Dict[str, Any]`

Inputs:
- (none)
Returns: `Dict[str, Any]`

## Function: `get_market_data`

Signature: `def get_market_data(...)->Dict[str, Any]`

Inputs:
- (none)
Returns: `Dict[str, Any]`

## Function: `get_news_impact`

Signature: `def get_news_impact(...)->Dict[str, Any]`

Inputs:
- (none)
Returns: `Dict[str, Any]`

## Function: `get_geopolitical_risks`

Signature: `def get_geopolitical_risks(...)->Dict[str, Any]`

Inputs:
- (none)
Returns: `Dict[str, Any]`

## Function: `get_commodity_prices`

Signature: `def get_commodity_prices(...)->Dict[str, Any]`

Inputs:
- (none)
Returns: `Dict[str, Any]`

## Function: `get_central_bank_activities`

Signature: `def get_central_bank_activities(...)->Dict[str, Any]`

Inputs:
- (none)
Returns: `Dict[str, Any]`

## Function: `get_economic_calendar`

Signature: `def get_economic_calendar(...)->Dict[str, Any]`

Inputs:
- (none)
Returns: `Dict[str, Any]`

## Function: `get_leading_indicators`

Signature: `def get_leading_indicators(...)->Dict[str, Any]`

Inputs:
- (none)
Returns: `Dict[str, Any]`

## Function: `get_sentiment_indicators`

Signature: `def get_sentiment_indicators(...)->Dict[str, Any]`

Inputs:
- (none)
Returns: `Dict[str, Any]`

## Function: `get_credit_conditions`

Signature: `def get_credit_conditions(...)->Dict[str, Any]`

Inputs:
- (none)
Returns: `Dict[str, Any]`

## Function: `get_supply_chain_metrics`

Signature: `def get_supply_chain_metrics(...)->Dict[str, Any]`

Inputs:
- (none)
Returns: `Dict[str, Any]`

## Function: `get_business_cycle_indicators`

Signature: `def get_business_cycle_indicators(...)->Dict[str, Any]`

Inputs:
- (none)
Returns: `Dict[str, Any]`

## Function: `get_forecast_scenarios`

Signature: `def get_forecast_scenarios(...)->Dict[str, Any]`

Inputs:
- (none)
Returns: `Dict[str, Any]`

## Function: `get_risk_metrics`

Signature: `def get_risk_metrics(...)->Dict[str, Any]`

Inputs:
- (none)
Returns: `Dict[str, Any]`

## Function: `get_monetary_conditions`

Signature: `def get_monetary_conditions(...)->Dict[str, Any]`

Inputs:
- (none)
Returns: `Dict[str, Any]`

## Function: `get_macro_data_firecrawl`

Signature: `def get_macro_data_firecrawl(...)->MacroData`

Inputs:
- (none)
Returns: `MacroData`

## Function: `save_macro_data`

Signature: `def save_macro_data(...)->None`

Inputs:
- `data`: MacroData
- `filename`: str = 'macro_data.json'
Returns: `None`
