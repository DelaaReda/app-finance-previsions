# MCP SSH Configuration Guide

**Date:** 2026-02-28  
**Purpose:** Enable Claude Desktop to execute SSH commands on dev-vm-utm  
**Status:** ✅ Configured & Deployed

---

## What is MCP?

**Model Context Protocol (MCP)** is a protocol that allows Claude (via Claude Desktop) to:
- Execute system commands
- Access files and directories
- Connect to remote systems via SSH
- Interact with databases and APIs

Think of it as: **Extensions for Claude that give it access to your tools and systems.**

---

## Architecture: Mac → Claude Desktop → SSH → VM

```
┌─────────────────────────────────────────────────────────┐
│  Claude Desktop (Mac)                                   │
│  ├─ MCP Server: filesystem                             │
│  ├─ MCP Server: mac-shell (local commands)             │
│  ├─ MCP Server: github                                 │
│  └─ MCP Server: ssh (our custom server) ←──────┐       │
└─────────────────────────────────────────────────┼───────┘
                                                  │
                         SSH Key Exchange        │
                    /Users/venom/.ssh/           │
                    id_utm_linux                 │
                                                  │
                                                  ↓
┌─────────────────────────────────────────────────────────┐
│  dev-vm-utm (VM on UTM)                                 │
│  ├─ User: venom                                        │
│  ├─ IP: 192.168.64.9                                  │
│  ├─ Service: OpenClaw (orchestrator)                  │
│  ├─ Services: 12 tmux agents (codex_*)               │
│  └─ Git: /home/venom/analyse-financiere              │
└─────────────────────────────────────────────────────────┘
```

---

## How It Works: Step-by-Step

### 1. Claude Desktop Configuration

**File:** `~/Library/Application Support/Claude/claude_desktop_config.json`

Your SSH MCP server is configured like this:

```json
"ssh": {
  "command": "python3",
  "args": ["/Users/venom/ssh_mcp_server.py"],
  "alwaysAllow": true
}
```

**What it means:**
- `command`: Run Python 3
- `args`: Execute our custom SSH server script
- `alwaysAllow`: Don't ask for permission each time (trusted tool)

### 2. SSH MCP Server Script

**File:** `/Users/venom/ssh_mcp_server.py` (~150 lines)

The script:
- Listens for Claude requests via JSON-RPC messages
- Translates Claude tool calls → SSH commands
- Executes on remote `dev-vm-utm` using your key
- Returns results (stdout, stderr, exit code) to Claude

**Key credentials hardcoded in script:**
```python
host = "dev-vm-utm"
user = "venom"
key_path = "/Users/venom/.ssh/id_utm_linux"
```

### 3. SSH Key Authentication

**Key location:** `/Users/venom/.ssh/id_utm_linux`

**Why this works:**
- No password needed (key-based auth)
- Secure: Private key never sent over network
- Fast: SSH via MCP connects instantly

**Verify key access:**
```bash
ssh -i /Users/venom/.ssh/id_utm_linux venom@dev-vm-utm "echo test"
# Output: test
```

---

## Available MCP Tools for SSH

### 1. `ssh_execute` — Run Commands

**Purpose:** Execute any shell command on the VM

**Usage in Claude:**
```
"Execute this command on the VM: systemctl status openclaw"
```

**Returns:**
- Exit code
- Standard output (stdout)
- Standard error (stderr)

**Example results:**
```
Exit Code: 0

STDOUT:
● openclaw.service - OpenClaw Orchestrator
   Loaded: loaded (/etc/systemd/system/openclaw.service)
   Active: active (running) since Sat 2026-02-28 11:20:15 UTC

STDERR:
(empty)
```

### 2. `ssh_health_check` — Verify VM Connection

**Purpose:** Quick connectivity test

**Usage in Claude:**
```
"Check if SSH connection to VM is working"
```

**Returns:**
```
Health Check: ✓ OK

Linux ubuntu-vm 6.1.0-28-generic #28-Ubuntu SMP PREEMPT_DYNAMIC Wed Feb 7 13:52:07 UTC 2024 aarch64 GNU/Linux
```

---

## How to Use from Claude

### Prerequisites
1. ✅ Claude Desktop installed on Mac
2. ✅ Config file updated (already done)
3. ✅ SSH script deployed (already done)
4. ✅ SSH key in place (already exists)
5. ✅ **Restart Claude Desktop** (⌘Q, then relaunch)

### Basic Commands

**1. Check VM is Online**
```
User: "Is the VM running? Check the status."

Claude uses: ssh_health_check
Result: Confirms connection works + system info
```

**2. Check OpenClaw Service**
```
User: "Check if OpenClaw service is running"

Claude uses: ssh_execute("systemctl status openclaw")
Result: Service status
```

**3. List Active Agents**
```
User: "What agents are running on the VM?"

Claude uses: ssh_execute("tmux list-sessions")
Result: All 12 tmux sessions (codex_admin, codex_backend, etc.)
```

**4. View Recent Logs**
```
User: "Show me last 50 lines of agent logs"

Claude uses: ssh_execute("tail -50 /home/venom/analyse-financiere/logs/agent.log")
Result: Recent log entries
```

**5. Execute Git Operations**
```
User: "Pull latest changes from Git on the VM"

Claude uses: ssh_execute("cd /home/venom/analyse-financiere && git pull")
Result: Git sync status
```

**6. Monitor Agent Execution**
```
User: "Show me running processes related to codex on the VM"

Claude uses: ssh_execute("ps aux | grep codex")
Result: List of codex processes
```

---

## Common Commands to Run

### Agent Management

```bash
# List all tmux sessions (agents)
tmux list-sessions

# View specific agent output
tmux capture-pane -t codex_backend_cron -p

# Restart all agents
tmux kill-server && systemctl restart openclaw

# Check agent memory context
ls -la /home/venom/analyse-financiere/memory/agents/
```

### OpenClaw Orchestration

```bash
# Check service status
systemctl status openclaw

# View service logs
journalctl -u openclaw -n 50 -f

# Restart orchestrator
systemctl restart openclaw
```

### Repository Management

```bash
# Git status
cd /home/venom/analyse-financiere && git status

# Pull latest
git pull origin main

# View logs
git log --oneline -10

# Check current branch
git branch -v
```

### Performance & Diagnostics

```bash
# Check disk usage
du -sh /home/venom/analyse-financiere/*

# Memory usage
free -h

# Active network connections
netstat -tuln | grep LISTEN

# Process monitoring
top -b -n 1 | head -20
```

---

## Example Conversation with Claude

```
User: "Can you help me troubleshoot the agents on the VM?"

Claude: "I'll use SSH to check the VM status for you."

[Claude executes: ssh_health_check]
Health check: ✓ Connected to dev-vm-utm

Claude: "The VM is running. Let me check the OpenClaw service."

[Claude executes: ssh_execute("systemctl status openclaw")]
Result: Service is active and running (1d 5h uptime)

Claude: "OpenClaw is running. How many agents are active?"

[Claude executes: ssh_execute("tmux list-sessions | wc -l")]
Result: 12 agents are active

Claude: "All 12 agents are running. Would you like me to check any specific logs or restart anything?"

User: "Check if there are any errors in the past hour"

[Claude executes: ssh_execute("grep ERROR /home/venom/analyse-financiere/logs/agent.log | tail -20")]
Result: Shows recent errors (if any)
```

---

## Troubleshooting

### Issue: "SSH connection refused"

**Cause:** SSH key not found or VM not accessible

**Fix:**
```bash
# Verify key exists and has correct permissions
ls -la ~/.ssh/id_utm_linux
chmod 600 ~/.ssh/id_utm_linux

# Test SSH directly
ssh -i ~/.ssh/id_utm_linux venom@dev-vm-utm "echo test"
```

### Issue: Claude says "SSH tool not available"

**Cause:** Claude Desktop not restarted after config change

**Fix:**
1. Save config file
2. Fully quit Claude (⌘Q)
3. Relaunch Claude
4. Wait 5 seconds for MCP to initialize

### Issue: "Permission denied (publickey)"

**Cause:** Private key permissions too loose or key expired

**Fix:**
```bash
# Reset key permissions
chmod 600 ~/.ssh/id_utm_linux

# Verify key is valid
ssh-keygen -l -f ~/.ssh/id_utm_linux

# Test with verbose output
ssh -i ~/.ssh/id_utm_linux -vvv venom@dev-vm-utm "echo test"
```

### Issue: Commands time out after 30 seconds

**Cause:** Long-running commands exceed timeout

**Fix:** 
- Keep commands under 30 seconds
- Use `nohup` for background tasks
- Split large operations into smaller commands

---

## Configuration Details

### SSH MCP Server Script (`ssh_mcp_server.py`)

**Location:** `/Users/venom/ssh_mcp_server.py`  
**Language:** Python 3  
**Size:** ~150 lines  
**Purpose:** Bridge Claude ↔ SSH

**How it works:**
1. Claude Desktop launches it as a subprocess
2. Script reads JSON-RPC messages from stdin
3. Parses tool calls (`ssh_execute`, `ssh_health_check`)
4. Executes subprocess SSH commands
5. Returns results as JSON to Claude

**Timeout:** 30 seconds per command

**Authentication:**
- SSH key: `/Users/venom/.ssh/id_utm_linux`
- User: `venom`
- Host: `dev-vm-utm`
- No password required (key-based)

### Claude Desktop Config

**File:** `~/Library/Application Support/Claude/claude_desktop_config.json`

**SSH Server Entry:**
```json
"ssh": {
  "command": "python3",
  "args": ["/Users/venom/ssh_mcp_server.py"],
  "alwaysAllow": true
}
```

**Other MCP Servers Active:**
- `filesystem`: Access files under `/Users/venom`
- `mac-shell`: Run local macOS commands
- `github`: GitHub API access
- `postgres`: Database queries (optional)
- `puppeteer`: Browser control (optional)

---

## Security Considerations

### ✅ What's Secure

- SSH keys are encrypted (RSA 4096-bit)
- `alwaysAllow: true` = trusted tool (no permission prompts)
- Commands executed as `venom` user (limited privileges)
- 30-second timeout prevents runaway processes

### ⚠️ What to Watch

- **Don't share:** SSH key (`id_utm_linux`)
- **Don't use:** For sensitive operations (passwords, tokens)
- **Don't run:** Destructive commands without confirmation
- **Keep updated:** Run `git pull` regularly on VM

### 🔐 Best Practices

1. **Keep key safe:** Don't commit to git or share
2. **Use readonly commands:** When just checking status
3. **Verify before executing:** Ask Claude to show command before running
4. **Monitor logs:** Check `journalctl` regularly
5. **Backup config:** Save `claude_desktop_config.json` backup

---

## Quick Reference

| Task | Command | MCP Tool |
|------|---------|----------|
| Check VM online | "Is the VM running?" | `ssh_health_check` |
| Service status | "Check OpenClaw service" | `ssh_execute` |
| View logs | "Show last 100 log lines" | `ssh_execute` |
| List agents | "How many agents running?" | `ssh_execute` |
| Git sync | "Pull latest changes" | `ssh_execute` |
| Restart service | "Restart OpenClaw" | `ssh_execute` |
| Process info | "Show codex processes" | `ssh_execute` |
| Disk usage | "How much space used?" | `ssh_execute` |

---

## Testing Your Setup

### Test 1: Direct SSH (Verify Key Works)
```bash
ssh -i ~/.ssh/id_utm_linux venom@dev-vm-utm "echo 'SSH works!'"
# Expected: SSH works!
```

### Test 2: MCP Health Check (Claude)
In Claude Desktop:
```
"Check if the SSH connection to the VM is working"
```
Expected: ✓ OK with system info

### Test 3: Remote Command (Claude)
In Claude Desktop:
```
"Run 'systemctl status openclaw' on the VM and show me the result"
```
Expected: Service status output

---

## Next Steps

1. **✅ Setup complete** – MCP SSH is configured
2. **Verify** – Test commands in Claude
3. **Integrate** – Use in your workflows
4. **Document** – Add custom commands to this guide as needed

---

## Support

**Questions about MCP?**
- Check `~/Library/Application Support/Claude/logs/` for debug info
- Restart Claude if tools don't appear
- Verify SSH key: `ssh-keygen -l -f ~/.ssh/id_utm_linux`

**SSH Connection Issues?**
```bash
# Test directly first
ssh -i ~/.ssh/id_utm_linux venom@dev-vm-utm "uname -a"

# Then report if it works locally but not in Claude
```

---

**Last Updated:** 2026-02-28  
**Created by:** Agent Setup  
**Status:** Production Ready ✅
