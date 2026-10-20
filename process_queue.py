#!/usr/bin/env python3
"""Add Recipe queue (Supabase table recipe_queue).

  python3 process_queue.py                         # print pending rows as JSON (includes `tags`)
  python3 process_queue.py --done ID [ID..]        # mark rows done
  python3 process_queue.py --done ID=RECIPE_ID ..  # copy the row's tags into recipes.json for RECIPE_ID, then mark done
  python3 process_queue.py --tags ID RECIPE_ID     # only copy the row's tags into recipes.json
  python3 process_queue.py --reject ID [..]        # mark rows rejected (e.g. duplicates)

Tags come from the row's `tags` array, or from a "Tags: a, b" line in notes (fallback used
before the tags column existed). Known tags are normalized to their canonical spelling; custom
tags are kept. --done/--tags also stamp `added` (UTC ISO now) if missing. Run `python3 build.py` afterwards.
"""
import datetime, json, re, sys
from sb import sb, ids

import os
KNOWN = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json"))).get("tags") or []  # canonical tag spellings

def row_tags(row):
    t = row.get("tags") or []
    if isinstance(t, str): t = [t]
    m = re.search(r"^Tags:\s*(.+)$", row.get("notes") or "", re.M)
    if m: t = list(t) + [x for x in m.group(1).split(",")]
    out = []
    for x in t:
        x = re.sub(r"\s+", " ", str(x)).strip()[:40]
        if not x: continue
        x = next((k for k in KNOWN if k.lower() == x.lower()), x)
        if x not in out: out.append(x)
    return out

def copy_tags(qid, rid):
    rows = sb(f"recipe_queue?id=eq.{int(qid)}&select=*")
    if not rows: sys.exit(f"queue row {qid} not found")
    t = row_tags(rows[0])
    R = json.load(open("recipes.json"))
    r = next((x for x in R if x["id"] == rid), None)
    if not r: sys.exit(f"recipe {rid} not in recipes.json")
    if not r.get("added"):  # newest-first ordering on the home page
        r["added"] = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    if t:
        cur = r.get("tags") or []
        r["tags"] = cur + [x for x in t if x not in cur]
    json.dump(R, open("recipes.json", "w"), indent=1, ensure_ascii=False)
    return t

a = sys.argv[1:]
if not a:
    print(json.dumps(sb("recipe_queue?status=eq.pending&order=created_at.asc&select=*"), indent=2, ensure_ascii=False))
elif a[0] == "--tags" and len(a) == 3:
    print(json.dumps({"recipe": a[2], "tags_added": copy_tags(a[1], a[2])}))
elif a[0] in ("--done", "--reject") and len(a) > 1:
    st = "done" if a[0] == "--done" else "rejected"; qids = []; copied = {}
    for x in a[1:]:
        q, _, rid = x.partition("=")
        if rid and st == "done": copied[rid] = copy_tags(q, rid)
        qids.append(q)
    rows = sb(f"recipe_queue?id=in.({ids(qids)})", "PATCH", {"status": st}, "return=representation")
    print(json.dumps({"updated": [r["id"] for r in rows], "status": st, "tags_copied": copied}))
else:
    sys.exit(__doc__)
