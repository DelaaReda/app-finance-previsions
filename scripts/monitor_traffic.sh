#!/usr/bin/env bash
set -euo pipefail

SAMPLES="${1:-5}"
if ! [[ "$SAMPLES" =~ ^[0-9]+$ ]]; then
  echo "Usage: $0 [samples]"
  echo "  samples: number of 1s nettop samples (default: 5)"
  exit 1
fi

echo "=== Traffic Monitor ==="
echo "Time: $(date)"
echo

echo "=== External ESTABLISHED TCP ==="
if lsof -nP -iTCP -sTCP:ESTABLISHED >/tmp/traffic_established.txt 2>/dev/null; then
  if [[ $(wc -l < /tmp/traffic_established.txt) -le 1 ]]; then
    echo "No established TCP connections."
  else
    python3 - <<'PY'
import re
from collections import defaultdict
p='/tmp/traffic_established.txt'
lines=open(p).read().splitlines()[1:]
by=defaultdict(list)
for ln in lines:
    parts=ln.split()
    if len(parts)<9:
        continue
    cmd,pid=parts[0],parts[1]
    conn=' '.join(parts[8:])
    m=re.search(r'->([^ ]+) \(ESTABLISHED\)$', conn)
    remote=m.group(1) if m else conn
    key=f"{cmd}({pid})"
    if remote not in by[key]:
        by[key].append(remote)
for proc,remotes in sorted(by.items(), key=lambda kv: len(kv[1]), reverse=True):
    print(f"- {proc}: {', '.join(remotes)}")
PY
  fi
else
  echo "Unable to read TCP established sockets."
fi

echo
echo "=== LISTEN TCP (non-loopback only) ==="
if lsof -nP -iTCP -sTCP:LISTEN >/tmp/traffic_listen.txt 2>/dev/null; then
  head -n 1 /tmp/traffic_listen.txt
  grep -E 'LISTEN' /tmp/traffic_listen.txt | grep -Ev '127\.0\.0\.1:|\[::1\]:' || true
else
  echo "Unable to read TCP listeners."
fi

echo
echo "=== Top Talkers (${SAMPLES}s window) ==="
if command -v nettop >/dev/null 2>&1; then
  if nettop -P -d -L "$SAMPLES" -n -x >/tmp/traffic_nettop.csv 2>/dev/null; then
    python3 - <<'PY'
from collections import defaultdict
rows=open('/tmp/traffic_nettop.csv').read().splitlines()
if len(rows) <= 1:
    print('No nettop data.')
    raise SystemExit(0)
agg=defaultdict(lambda:[0,0])
for ln in rows[1:]:
    parts=ln.split(',')
    if len(parts) < 6:
        continue
    proc=parts[1].strip()
    try:
        bi=int(parts[4]); bo=int(parts[5])
    except ValueError:
        continue
    agg[proc][0]+=bi; agg[proc][1]+=bo
for proc,(bi,bo) in sorted(agg.items(), key=lambda kv: kv[1][0]+kv[1][1], reverse=True)[:12]:
    total=bi+bo
    if total == 0:
        continue
    print(f"- {proc}: in={bi} out={bo} total={total}")
PY
  else
    echo "nettop returned no data."
  fi
else
  echo "nettop not available."
fi

echo
echo "=== Firewall ==="
/usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate 2>/dev/null || true
/usr/libexec/ApplicationFirewall/socketfilterfw --getblockall 2>/dev/null || true
/usr/libexec/ApplicationFirewall/socketfilterfw --getstealthmode 2>/dev/null || true

echo
echo "=== Suggested actions ==="
echo "- Kill non-loopback listeners you don't need: lsof -nP -iTCP -sTCP:LISTEN"
echo "- Stop OpenClaw gateway: openclaw gateway stop"
echo "- Stop WhatsApp desktop if not needed."
echo "- Quit VS Code to drop its dynamic *:<port> listeners."
