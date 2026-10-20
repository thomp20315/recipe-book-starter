"""Tiny Supabase REST helper shared by process_queue.py and shopping_queue.py (publishable key is public)."""
import json, urllib.request, urllib.parse
# Clean-food scoring rubric for shopping results lives in clean.py (clean_score 0-100, ingredient_flags).
import os
_here = os.path.dirname(os.path.abspath(__file__))
_cfg = json.load(open(os.path.join(_here, "config.json")))
SB_URL = _cfg["supabase_url"].rstrip("/")
SB_KEY = _cfg["supabase_publishable_key"]
if "YOUR-" in SB_URL or "YOUR-" in SB_KEY:
    raise SystemExit("config.json still has placeholder Supabase values. Fill in supabase_url and supabase_publishable_key (README step 2).")

def sb(path, method="GET", body=None, prefer=None):
    h = {"apikey": SB_KEY, "Content-Type": "application/json", "User-Agent": "recipe-book/1.0"}
    if prefer: h["Prefer"] = prefer
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(f"{SB_URL}/rest/v1/{path}", data=data, method=method, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            t = r.read().decode()
            return json.loads(t) if t else None
    except urllib.error.HTTPError as e:
        raise SystemExit(f"Supabase error {e.code}: {e.read().decode()[:500]}")

def ids(vals):
    out = []
    for v in vals:
        if not v.isdigit(): raise SystemExit(f"not a numeric id: {v}")
        out.append(v)
    return ",".join(out)
