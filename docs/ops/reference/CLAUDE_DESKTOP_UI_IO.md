# Claude Desktop UI I/O (Input -> Output)

## Purpose
This feature encapsulates Claude Desktop automation as a simple I/O function:
- **Input**: a prompt string
- **Output**: extracted response text + extracted actions + metadata artifacts

It simulates a normal desktop user flow:
1. Focus Claude window
2. Type prompt in UI composer
3. Click send
4. Extract progress repeatedly from UI (clipboard selection) while Claude is working
5. Compute response delta vs baseline (important for `same` chat mode)
6. Stop when output stabilizes (or max wait is reached)

Direct extraction is the default path.
OCR is disabled by default and can be enabled only for **debug on error**.

## One Command
```bash
scripts/claude_desktop_ui_io.sh --input "repond pong puis liste actions en 3 puces"
```

Optional:
```bash
scripts/claude_desktop_ui_io.sh \
  --input "resume ce que tu as fait en 5 points" \
  --chat-mode new \
  --max-wait 240 \
  --poll 12 \
  --auto-always-allow \
  --stable-polls 2 \
  --print-output
```

Permanent MCP authorization config:
```bash
scripts/claude_desktop_configure_always_allow.sh
```

YOLO mode (aggressive no-prompt setup):
```bash
scripts/claude_desktop_enable_yolo_mode.sh
```

## Contract (Input / Output)
### Input
- Required:
  - `--input "prompt text"`
- Optional:
  - `--chat-mode same|new`
    - `same`: continue in current chat
    - `new`: force a new chat before sending
  - `--same-chat` / `--new-chat` aliases
  - `--max-wait N` (max total wait in seconds, default `180`)
  - `--wait N` (alias for `--max-wait`)
  - `--poll N` (poll interval for progressive extraction, default `10`)
  - `--stable-polls N` (stop after `N` unchanged polls, default `2`)
  - `--debug-ocr-on-error` (debug fallback only; disabled by default)
  - `--auto-always-allow` (default enabled; tries to auto-click permission prompts)
  - `--no-auto-always-allow` (disable auto-click handler)
  - `--auto-allow-cooldown N` (seconds between auto-click attempts, default `4`)
  - `--out-dir PATH` (default `logs-codex-runs`)
  - `--print-output` (echo extracted response to stdout)

### Output
Each run creates stable artifacts:
- `claude-ui-io-YYYYMMDD-HHMMSS.input.txt`
- `claude-ui-io-YYYYMMDD-HHMMSS.response.txt`
- `claude-ui-io-YYYYMMDD-HHMMSS.actions.txt`
- `claude-ui-io-YYYYMMDD-HHMMSS.meta.env`

And prints paths:
- `io_input=...`
- `io_output=...`
- `io_actions=...`
- `io_meta=...`
- `io_screenshot=...`
- `io_progress_log=...`
- `io_snapshots_dir=...`
- `io_stop_reason=...`
- `io_error_detected=...`
- `io_auto_always_allow=...`
- `io_auto_allow_detected=...`
- `io_auto_allow_attempts=...`

`meta.env` includes:
- extraction source (`direct`)
- chat mode used (`same` or `new`)
- screenshot path
- source files used for response/actions
- poll metrics and stop reason
- auto-allow policy and click-attempt counters
- optional debug OCR path (only if enabled and error detected)

## Main Scripts
- Wrapper I/O:
  - `scripts/claude_desktop_ui_io.sh`
- Low-level UI automation + capture:
  - `scripts/claude_desktop_ui_send_and_capture.sh`
- Config helper (MCP no-auth prompts):
  - `scripts/claude_desktop_configure_always_allow.sh`
- Aggressive no-prompt helper (MCP + bypass permission mode):
  - `scripts/claude_desktop_enable_yolo_mode.sh`

## Notes
- This is UI automation; timing/network/rate-limit can affect response completeness.
- For long tasks on free tier, increase max wait and keep polling:
  - `--max-wait 420 --poll 15`
- Use `io_progress_log` and `io_snapshots_dir` to monitor progress while Claude works.
- After changing MCP `alwaysAllow`, restart Claude Desktop once.
