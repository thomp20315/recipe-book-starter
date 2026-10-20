#!/usr/bin/env python3
"""Send-to-cart jobs (Supabase table cart_requests). Adds to carts only; NEVER checks out.

  python3 cart_queue.py list [store]                  # queued rows as JSON (oldest first)
  python3 cart_queue.py show <id>
  python3 cart_queue.py mark <id> queued|working|done|partial|failed [--added added.json] [--failed failed.json] [--note "text"]
      added/failed files: JSON arrays (e.g. the items[] entries, optionally with a "reason")
"""
import json, sys
from sb import sb, ids

STATUSES = ("queued", "working", "done", "partial", "failed")

def _arr(path):
    v = json.load(open(path))
    if not isinstance(v, list): raise SystemExit(f"{path} must contain a JSON array")
    return v

a = sys.argv[1:]
if a[:1] == ["list"] and len(a) <= 2:
    q = "cart_requests?status=eq.queued&order=created_at.asc&select=*"
    if len(a) == 2: q += "&store=eq." + a[1]
    print(json.dumps(sb(q), indent=2, ensure_ascii=False))
elif a[:1] == ["show"] and len(a) == 2:
    print(json.dumps(sb(f"cart_requests?id=eq.{ids([a[1]])}&select=*"), indent=2, ensure_ascii=False))
elif a[:1] == ["mark"] and len(a) >= 3 and a[2] in STATUSES:
    patch, rest = {"status": a[2]}, a[3:]
    while rest:
        k = rest.pop(0)
        if not rest: raise SystemExit(f"{k} needs a value")
        v = rest.pop(0)
        if k == "--added": patch["added"] = _arr(v)
        elif k == "--failed": patch["failed"] = _arr(v)
        elif k == "--note": patch["note"] = v
        else: raise SystemExit(f"unknown option {k}")
    rows = sb(f"cart_requests?id=eq.{ids([a[1]])}", "PATCH", patch, "return=representation")
    print(json.dumps({"updated": [r["id"] for r in rows], "status": a[2]}))
else:
    sys.exit(__doc__)
