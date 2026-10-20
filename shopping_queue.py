#!/usr/bin/env python3
"""Shopping requests / results (Supabase tables shopping_requests, shopping_results).

  python3 shopping_queue.py list                        # pending requests as JSON
  python3 shopping_queue.py mark <id> processing|done|failed
  python3 shopping_queue.py progress <id> <stores_done> <stores_total> ["Store now being shopped"]   # progress bar in the app
  python3 shopping_queue.py post-result <request_id> <file.json>   # validate, insert result, mark request done
  python3 shopping_queue.py validate <file.json>                   # check a result file without posting
"""
import json, sys
from sb import sb, ids
from clean import PENALTY  # clean-score rubric: see clean.py

NUM = (int, float)
def _num(v, nullable=True): return (v is None and nullable) or (isinstance(v, NUM) and not isinstance(v, bool))

def validate(r):
    e = []
    st, pk = r.get("stores"), r.get("picks")
    if not isinstance(st, list): e.append("'stores' must be an array")
    if not isinstance(pk, list): e.append("'picks' must be an array")
    if e: return e
    ids = set()
    for i, s in enumerate(st):
        if not s.get("id") or not s.get("name"): e.append(f"stores[{i}] needs id and name")
        ids.add(s.get("id"))
        for k in ("distance_mi", "subtotal", "coupon_savings", "total"):
            if not _num(s.get(k)): e.append(f"stores[{i}].{k} must be a number or null")
        if "items_found" in s and not _num(s["items_found"]): e.append(f"stores[{i}].items_found must be a number")
        if "clean_score" in s and s["clean_score"] is not None and not (_num(s["clean_score"]) and 0 <= s["clean_score"] <= 100): e.append(f"stores[{i}].clean_score must be 0-100 or null")
        if "items_missing" in s and not isinstance(s["items_missing"], list): e.append(f"stores[{i}].items_missing must be an array")
    for i, p in enumerate(pk):
        if p.get("store") not in ids: e.append(f"picks[{i}].store '{p.get('store')}' is not a stores[].id")
        for k in ("item", "product"):
            if not p.get(k): e.append(f"picks[{i}] needs {k}")
        for k in ("price", "final_price"):
            if not _num(p.get(k)): e.append(f"picks[{i}].{k} must be a number or null")
        if p.get("url") and not str(p["url"]).startswith(("http://", "https://")): e.append(f"picks[{i}].url must be http(s)")
        if p.get("clean_score") is not None and not (_num(p["clean_score"]) and 0 <= p["clean_score"] <= 100): e.append(f"picks[{i}].clean_score must be 0-100 or null")
        fl = p.get("ingredient_flags")
        if fl is not None and (not isinstance(fl, list) or any(f not in PENALTY for f in fl)): e.append(f"picks[{i}].ingredient_flags must be a list of: " + ", ".join(PENALTY))
        c = p.get("coupon")
        if c is not None:
            if not isinstance(c, dict): e.append(f"picks[{i}].coupon must be an object or null"); continue
            if c.get("type") not in ("digital", "manufacturer", "weekly_ad", "sale"): e.append(f"picks[{i}].coupon.type must be digital|manufacturer|weekly_ad|sale")
            if not _num(c.get("savings")): e.append(f"picks[{i}].coupon.savings must be a number or null")
            if c.get("source_url") and not str(c["source_url"]).startswith(("http://", "https://")): e.append(f"picks[{i}].coupon.source_url must be http(s)")
    if r.get("cheapest_store") is not None and r["cheapest_store"] not in ids: e.append("cheapest_store is not a stores[].id")
    if "top3" in r:
        if not isinstance(r["top3"], list) or len(r["top3"]) > 3 or any(x not in ids for x in r["top3"]): e.append("top3 must be up to 3 stores[].id values")
    h = r.get("hybrid")
    if h is not None:
        if not isinstance(h, dict): e.append("hybrid must be an object or null")
        else:
            hs = h.get("stores")
            if not isinstance(hs, list) or len(hs) != 2 or any(x not in ids for x in hs): e.append("hybrid.stores must be 2 stores[].id values")
            for j, a in enumerate(h.get("assignments") or []):
                if not a.get("item") or a.get("store") not in (hs or []): e.append(f"hybrid.assignments[{j}] needs item and a store from hybrid.stores")
            for k in ("subtotal", "coupon_savings", "total", "savings_vs_best_single"):
                if not _num(h.get(k)): e.append(f"hybrid.{k} must be a number or null")
    return e

a = sys.argv[1:]
if a[:1] == ["list"]:
    print(json.dumps(sb("shopping_requests?status=eq.pending&order=created_at.asc&select=*"), indent=2, ensure_ascii=False))
elif a[:1] == ["mark"] and len(a) == 3 and a[2] in ("pending", "processing", "done", "failed"):
    rows = sb(f"shopping_requests?id=eq.{ids([a[1]])}", "PATCH", {"status": a[2]}, "return=representation")
    print(json.dumps({"updated": [r["id"] for r in rows], "status": a[2]}))
elif a[:1] == ["progress"] and len(a) in (4, 5) and a[2].isdigit() and a[3].isdigit():
    patch = {"stores_done": int(a[2]), "stores_total": int(a[3]), "current_store": a[4] if len(a) == 5 else None}
    rows = sb(f"shopping_requests?id=eq.{ids([a[1]])}", "PATCH", patch, "return=representation")
    print(json.dumps({"updated": [r["id"] for r in rows], **patch}))
elif a[:1] == ["post-result"] and len(a) == 3:
    rid = ids([a[1]]); result = json.load(open(a[2]))
    errs = validate(result)
    if errs: sys.exit("invalid result JSON:\n  - " + "\n  - ".join(errs))
    req = sb(f"shopping_requests?id=eq.{rid}&select=zip")
    zip_ = result.get("zip") or (req[0]["zip"] if req else None)
    row = sb("shopping_results", "POST", {"request_id": int(rid), "zip": zip_, "result": result}, "return=representation")
    sb(f"shopping_requests?id=eq.{rid}", "PATCH", {"status": "done"}, "return=minimal")
    print(json.dumps({"result_id": row[0]["id"], "request_id": int(rid), "request_status": "done"}))
elif a[:1] == ["validate"] and len(a) == 2:
    errs = validate(json.load(open(a[1])))
    print("OK" if not errs else "INVALID:\n  - " + "\n  - ".join(errs)); sys.exit(1 if errs else 0)
else:
    sys.exit(__doc__)
