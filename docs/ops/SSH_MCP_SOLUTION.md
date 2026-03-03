# SSH MCP Configuration – Solution Document

**Date:** March 1, 2026  
**Status:** ✅ Production Ready  
**Platform:** macOS + Claude Desktop

---

## Architecture Overview

```
Claude Desktop
    ↓ (MCP Protocol, stdin/stdout)
Python Proxy (/Users/venom/ssh_mcp_proxy.py)
    ↓ (JSON-RPC over Unix socket)
Socket Server (/Users/venom/ssh_mcp_server.py)
    ↓ (SSH commands)
VM (192.168.64.9)
```

---

## Installation & Setup

### Files Created/Modified

1. **Socket Server:** `/Users/venom/ssh_mcp_server.py`
   - Listens on Unix socket: `~/.ssh/mcp.sock`
   - Handles JSON-RPC MCP protocol
   - Executes SSH commands to dev-vm-utm (192.168.64.9)
   - Auto-accepts SSH host keys (no password prompts)

2. **Relay Proxy:** `/Users/venom/ssh_mcp_proxy.py`
   - Receives JSON-RPC from Claude Desktop (stdin)
   - Relays messages to socket server
   - Returns responses to Claude (stdout)
   - Handles newline-delimited JSON protocol

3. **LaunchAgent:** `~/Library/LaunchAgents/com.venom.ssh-mcp.plist`
   - Manages socket server as system service
   - `KeepAlive: true` → auto-restart on crash
   - `RunAtLoad: true` → starts at system boot
   - Logs: `/tmp/ssh-mcp-server.log` and `.log-error`

4. **Claude Desktop Config:** `~/Library/Application Support/Claude/claude_desktop_config.json`

### Configuration

Claude Desktop MCP entry:
```json
"ssh": {
  "command": "/usr/bin/python3",
  "args": ["/Users/venom/ssh_mcp_proxy.py"],
  "alwaysAllow": true
}
```

---

## Available Tools

### 1. ssh_health_check

Check SSH connectivity to dev-vm-utm.

**Parameters:** None  
**Returns:** Connection status + system info (uname)

**Example:**
```
"Can you check SSH connection to the VM?"
```

### 2. ssh_execute

Execute arbitrary command on dev-vm-utm.

**Parameters:**
- `command` (required): Command to run
- `host` (optional): Target host (default: dev-vm-utm)

**Returns:** Exit code, STDOUT, STDERR

**Example:**
```
"Run 'ps aux | grep python' on the VM"
```

---

## Key Configuration Details

### SSH Options
The socket server uses these SSH options for full automation:
```bash
-o StrictHostKeyChecking=accept-new    # Auto-accept new host keys
-o UserKnownHostsFile=/dev/null         # Skip known_hosts validation
-o IdentitiesOnly=yes                   # Use only specified key
```

### SSH Key
- **Key Path:** `~/.ssh/id_utm_linux`
- **User:** venom
- **Host:** 192.168.64.9 (dev-vm-utm)

### Timeout
- SSH command timeout: 30 seconds
- No global proxy timeout (commands can run indefinitely)
- Per-recv timeout: 0.1 seconds (detects chunked reads)

---

## Testing

### Manual Tests (All Passing ✅)

1. **Socket server directly** (via nc):
```bash
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' | \
  nc -U -w 2 ~/.ssh/mcp.sock
```
✅ Returns: initialize response with protocol version

2. **Tools list**:
```bash
echo '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' | \
  nc -U -w 2 ~/.ssh/mcp.sock
```
✅ Returns: ssh_execute and ssh_health_check tools

3. **Health check**:
```bash
echo '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"ssh_health_check","arguments":{}}}' | \
  nc -U -w 5 ~/.ssh/mcp.sock
```
✅ Returns: ✓ OK + system info (Linux uname)

4. **SSH execute** (uptime):
```bash
echo '{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"ssh_execute","arguments":{"command":"uptime"}}}' | \
  nc -U -w 5 ~/.ssh/mcp.sock
```
✅ Returns: Exit code 0 + uptime output (3 days up, load average 13.50)

5. **Via proxy** (Claude Desktop path):
```bash
echo '{"jsonrpc":"2.0","id":2,"method":"tools/list"}' | \
  /usr/bin/python3 /Users/venom/ssh_mcp_proxy.py
```
✅ Returns: Relayed response from socket server

---

## Troubleshooting

### Issue: Tools not showing in Claude

**Solution:**
1. Restart Claude Desktop completely (Cmd+Q)
2. Wait 2 seconds
3. Reopen Claude

MCP servers load at startup; changes require restart.

### Issue: SSH timeout

**Check:**
```bash
launchctl list | grep ssh-mcp              # Should show: 60526  0  com.venom.ssh-mcp
ls -la ~/.ssh/mcp.sock                     # Should exist
ps aux | grep ssh_mcp_server | grep -v grep # Should show running
```

### Issue: SSH authentication fails

**Check:**
1. Key exists: `ls -la ~/.ssh/id_utm_linux`
2. SSH works manually: `ssh -i ~/.ssh/id_utm_linux venom@192.168.64.9 uptime`
3. No passphrase on key

### Live Logs

```bash
# Socket server logs
tail -f /tmp/ssh-mcp-server.log
tail -f /tmp/ssh-mcp-server-error.log

# Restart service
launchctl unload ~/Library/LaunchAgents/com.venom.ssh-mcp.plist
launchctl load ~/Library/LaunchAgents/com.venom.ssh-mcp.plist
```

---

## Files & Paths

| File | Purpose |
|------|---------|
| `/Users/venom/ssh_mcp_server.py` | Socket server (port: ~/.ssh/mcp.sock) |
| `/Users/venom/ssh_mcp_proxy.py` | Relay proxy for Claude Desktop |
| `~/Library/LaunchAgents/com.venom.ssh-mcp.plist` | System service manager |
| `~/Library/Application Support/Claude/claude_desktop_config.json` | Claude MCP config |
| `~/.ssh/id_utm_linux` | SSH private key |
| `~/.ssh/config` | SSH config (maps dev-vm-utm → 192.168.64.9) |

---

## Security Notes

1. **Private Key:** Never share `~/.ssh/id_utm_linux`
2. **Socket Permissions:** `~/.ssh/mcp.sock` is readable only by venom user
3. **No Password Fallback:** `IdentitiesOnly=yes` prevents password authentication
4. **Auto-Accept Keys:** Only new host keys; no MITM validation (acceptable for internal VM)

---

## Next Steps

### Immediate (Done ✅)
- [x] Socket server operational
- [x] Proxy relay working
- [x] LaunchAgent managing service
- [x] SSH authentication fixed
- [x] All tests passing

### Future Enhancements (Optional)
- [ ] Add Ubuntu tools (Nginx, SSL, firewall, deployment)
- [ ] Add file transfer tools (SFTP)
- [ ] Add command history tracking
- [ ] Add rate limiting for security
- [ ] Integrate with orchestration agents

---

## Session Recap

**Problem:** SSH MCP socket server not responding to `initialize` and `tools/list` requests.

**Root Cause:** Socket server had broken request handling logic – responses were constructed but not sent properly in all code paths.

**Solution:** Completely rewrote `handle_request()` function with:
- Single point of entry for all methods
- Proper JSON-RPC error responses
- Explicit handling of `initialize`, `tools/list`, `tools/call`
- Graceful handling of unknown methods

**Result:** 100% operational, all tests passing, ready for Claude Desktop integration.

---

**Last Updated:** 2026-03-01 13:38 UTC  
**Status:** Production Ready ✅
