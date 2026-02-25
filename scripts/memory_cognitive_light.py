#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MEM_DIR = ROOT / "memory"
META = MEM_DIR / "meta" / "decay-scores.json"
LONG_TERM = ROOT / "MEMORY.md"

TAG_RE = re.compile(r"\[(decision|todo|risk|note)\]", re.IGNORECASE)


def recent_daily_files(from_days: int) -> list[Path]:
    cutoff = dt.date.today() - dt.timedelta(days=from_days)
    out: list[Path] = []
    for p in sorted(MEM_DIR.glob("*.md")):
        m = re.match(r"(\d{4})-(\d{2})-(\d{2})", p.stem)
        if not m:
            continue
        y, mo, d = map(int, m.groups())
        if dt.date(y, mo, d) >= cutoff:
            out.append(p)
    return out


def extract(lines: list[str], source: str):
    rows = []
    for i, line in enumerate(lines, start=1):
        t = TAG_RE.search(line)
        if not t:
            continue
        tag = t.group(1).lower()
        text = re.sub(r"\s+", " ", line.strip())
        rows.append({"tag": tag, "text": text, "source": f"{source}#{i}"})
    return rows


def load_meta() -> dict:
    if META.exists():
        return json.loads(META.read_text(encoding="utf-8"))
    return {"version": 1, "updated_at": None, "weights": {"decision": 1.0, "todo": 0.8, "risk": 0.9, "note": 0.6}, "items": {}}


def save_meta(meta: dict):
    META.parent.mkdir(parents=True, exist_ok=True)
    META.write_text(json.dumps(meta, indent=2), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description="Cognitive-light memory consolidation")
    ap.add_argument("--from-days", type=int, default=7)
    ap.add_argument("--apply", action="store_true", help="Append summary to MEMORY.md")
    args = ap.parse_args()

    files = recent_daily_files(args.from_days)
    findings = []
    for f in files:
        findings.extend(extract(f.read_text(encoding="utf-8", errors="ignore").splitlines(), f"memory/{f.name}"))

    meta = load_meta()
    items = meta.setdefault("items", {})

    for row in findings:
        key = row["text"][:140]
        entry = items.get(key, {"tag": row["tag"], "count": 0, "last_seen": None, "sources": []})
        entry["count"] += 1
        entry["last_seen"] = dt.datetime.now(dt.UTC).isoformat()
        if row["source"] not in entry["sources"]:
            entry["sources"].append(row["source"])
        items[key] = entry

    meta["updated_at"] = dt.datetime.now(dt.UTC).isoformat()
    save_meta(meta)

    by_priority = sorted(
        items.items(),
        key=lambda kv: (meta["weights"].get(kv[1].get("tag", "note"), 0.5) * kv[1].get("count", 1)),
        reverse=True,
    )

    top = by_priority[:10]
    print(f"Scanned files: {len(files)}")
    print(f"Tagged findings: {len(findings)}")
    print("Top candidates:")
    for text, info in top:
        print(f"- [{info.get('tag')}] x{info.get('count')}: {text}")

    if args.apply and top:
        section = ["", "## Cognitive-light weekly consolidation", f"- Window: last {args.from_days} days"]
        for text, info in top[:6]:
            section.append(f"- [{info.get('tag')}] {text}")
        LONG_TERM.write_text(LONG_TERM.read_text(encoding="utf-8") + "\n" + "\n".join(section) + "\n", encoding="utf-8")
        print(f"Appended summary to {LONG_TERM}")


if __name__ == "__main__":
    main()
