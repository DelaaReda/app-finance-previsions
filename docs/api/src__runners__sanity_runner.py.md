# sanity_runner.py

Sanity Runner & Minimal Tests for Phases 1..5

Objectif:
- Importer les modules phase1_data, phase2_factor_models, phase3_macro, phase4_sentiment, phase5_fusion
- Exécuter un pipeline end-to-end (ou des mocks/degrafés si modules manquants)
- Logger les sorties & vérifier des invariants simples (smoke tests)
- Fournir quelques "unit tests" légers sans dépendre d'Internet (mode --offline)

Usage:
  python sanity_runner.py --ticker NGD.TO --log INFO
  python sanity_runner.py --ticker AAPL --offline

## Function: `setup_logger`

Signature: `def setup_logger(...)->None`

Inputs:
- `level`: str = 'INFO'
Returns: `None`

## Function: `mock_phase1_payload`

Signature: `def mock_phase1_payload(...)->Dict[str, Any]`

Inputs:
- `ticker`: str
Returns: `Dict[str, Any]`

## Function: `mock_phase2_payload`

Signature: `def mock_phase2_payload(...)->Dict[str, Any]`

Inputs:
- `ticker`: str
Returns: `Dict[str, Any]`

## Function: `mock_phase3_payload`

Signature: `def mock_phase3_payload(...)->Dict[str, Any]`

Inputs:
- `ticker`: str
Returns: `Dict[str, Any]`

## Function: `mock_phase4_payload`

Signature: `def mock_phase4_payload(...)->Dict[str, Any]`

Inputs:
- `ticker`: str
Returns: `Dict[str, Any]`

## Function: `dataclass_to_dict_safe`

Signature: `def dataclass_to_dict_safe(...)->Any`

Inputs:
- `obj`: Any
Returns: `Any`

## Function: `smoke_phase1`

Signature: `def smoke_phase1(...)->Dict[str, Any]`

Inputs:
- `ticker`: str
- `offline`: bool
Returns: `Dict[str, Any]`

## Function: `smoke_phase2`

Signature: `def smoke_phase2(...)->Dict[str, Any]`

Inputs:
- `ticker`: str
- `offline`: bool
Returns: `Dict[str, Any]`

## Function: `smoke_phase3`

Signature: `def smoke_phase3(...)->Dict[str, Any]`

Inputs:
- `ticker`: str
- `offline`: bool
Returns: `Dict[str, Any]`

## Function: `smoke_phase4`

Signature: `def smoke_phase4(...)->Dict[str, Any]`

Inputs:
- `ticker`: str
- `offline`: bool
Returns: `Dict[str, Any]`

## Function: `smoke_phase5`

Signature: `def smoke_phase5(...)->Any`

Inputs:
- `ticker`: str
- `p1`: Any
- `p2`: Any
- `p3`: Any
- `p4`: Any
Returns: `Any`

## Function: `unit_tests_format`

Signature: `def unit_tests_format(...)->None`

Inputs:
- `p1`: Any
- `p2`: Any
- `p3`: Any
- `p4`: Any
- `p5_out`: Any
Returns: `None`

## Function: `unit_tests_behavior`

Signature: `def unit_tests_behavior(...)->None`

Inputs:
- `p5_out`: Any
Returns: `None`

## Function: `main`

Signature: `def main(...)->Any`

Inputs:
- (none)
Returns: `Any`
