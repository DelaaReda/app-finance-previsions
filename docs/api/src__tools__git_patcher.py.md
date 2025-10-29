# git_patcher.py

## Function: `current_branch`

Signature: `def current_branch(...)->str`

Inputs:
- `cwd`: Optional[str] = None
Returns: `str`

## Function: `create_branch`

Signature: `def create_branch(...)->str`

Inputs:
- `name`: str
- `checkout`: bool = True
- `cwd`: Optional[str] = None
Returns: `str`

## Function: `apply_unified_diff`

Signature: `def apply_unified_diff(...)->str`

Inputs:
- `diff_text`: str
- `commit_message`: Optional[str] = None
- `cwd`: Optional[str] = None
Returns: `str`

## Function: `commit_all`

Signature: `def commit_all(...)->str`

Inputs:
- `message`: str
- `cwd`: Optional[str] = None
Returns: `str`
