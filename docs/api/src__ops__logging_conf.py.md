# logging_conf.py

## Function: `setup_app_logger`

Signature: `def setup_app_logger(...)->logging.Logger`

Inputs:
- `name`: str = 'app'
- `level`: Any = logging.INFO
Returns: `logging.Logger`

## Function: `log_activity`

Signature: `def log_activity(...)->Any`

Inputs:
- `event`: str
- `details`: dict
Returns: `Any`
