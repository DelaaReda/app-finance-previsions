# MCP SSH Quick Reference (TL;DR)

## What is it?
Claude can now execute SSH commands on `dev-vm-utm` via MCP (Model Context Protocol).

## How to use it

### In Claude Desktop, just ask:

```
"Check if OpenClaw is running"
"Show me the last 50 log lines"
"What agents are active?"
"Pull latest changes from Git"
"Restart the orchestrator"
```

Claude automatically uses SSH to run commands on the VM.

## Setup Status
✅ SSH MCP Server: `/Users/venom/ssh_mcp_server.py`  
✅ Claude Config: `~/Library/Application Support/Claude/claude_desktop_config.json`  
✅ SSH Key: `/Users/venom/.ssh/id_utm_linux`  
✅ VM Target: `venom@dev-vm-utm` (192.168.64.9)  

## Must do ONCE
**Restart Claude Desktop:** ⌘Q then reopen

## Common Commands via Claude

Examples you can ask Claude:

**Status Checks:**
```
"Is the VM running?"
"Check if OpenClaw service is active"
"How many agents are running?"
```

**Logs & Diagnostics:**
```
"Show last 100 lines of agent logs"
"Check for errors in the past hour"
"Show me the Git log"
```

**Git Operations:**
```
"Pull latest from origin"
"Check Git status"
"Show what branch we're on"
```

**Admin Tasks:**
```
"Restart OpenClaw"
"Kill all tmux sessions"
"Check disk usage"
```

## Behind the Scenes Architecture

```
Claude Desktop (Mac)
    ↓ (via MCP)
    ↓
SSH Server Script
    ↓ (SSH protocol)
    ↓
dev-vm-utm (VM)
    ↓
Command execution
    ↓
Results back → Claude
```

## If something breaks

**Claude says "SSH tool not available":**
1. Quit Claude (⌘Q)
2. Relaunch Claude
3. Wait 5 seconds
4. Try again

**Connection refused:**
```bash
# Test SSH directly first
ssh -i ~/.ssh/id_utm_linux venom@dev-vm-utm "echo test"
```

If that works but Claude fails → restart Claude

## More Info
See: `/home/venom/analyse-financiere/docs/ops/MCP_SSH_CONFIGURATION_GUIDE.md`

---

**TL;DR:** MCP lets Claude run commands on the VM. Just ask it naturally in the chat. ✨
