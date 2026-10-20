"""Clean-food scoring rubric (used by shopping_queue.py validation and result audits).

DEFAULT PREFERENCES: this is a starting point, not a rule. Edit PENALTY below (and the matching list in this docstring
and README "Clean score") to match what your family wants to avoid. Set a penalty to 0 to ignore that flag.
If you add a new flag name, also add its label to FL in build.py so the app can show it.

Per pick: start at 100, subtract once per flag class present, floor at 0.
  palm_or_seed_oil              -20  palm oil/shortening, soybean, canola, corn, sunflower, safflower, cottonseed oil
  added_sugar                   -15  cane/beet sugar, corn syrup, dextrose (date/fruit paste and honey as an ingredient don't count)
  dough_conditioner_emulsifier  -15  DATEM, ammonium sulfate, SSL, mono- and diglycerides, soy lecithin, other emulsifiers
  gum_stabilizer                -10  guar, xanthan, locust/carob bean, gellan, carrageenan, agar; anti-caking starch or cellulose
  artificial_additive_preservative -20  artificial colors/flavors, calcium propionate, sorbates, sulfites, natamycin, BHT
  minor_aid                      -3  added enzymes, ascorbic acid, citric acid, calcium chloride, yeast extract, caramel color, natural flavor
  non_organic                   -15  non-organic produce, meat, or dairy where it matters (thick-skinned onion, garlic, citrus exempt;
                                     100% grass-fed beef and pasture-raised eggs count as organic-equivalent)
  ultra_processed               -10  industrial formulation (e.g. commercial white rolls/buns, processed cheese)
Store score: unweighted mean of core-item pick scores (pantry and optional items excluded). Missing items get weight 0
and are listed in items_missing; picks whose ingredient list couldn't be verified are scored on what is known and marked.
Ranking value (lower is better): value = total * (1 + 0.5 * (100 - store_score) / 100) + sum of the cheapest other-store
price for each missing item. So a score of 80 adds a 10% penalty to the total.
Per-item choice (hybrid, in-store swaps): pick the lowest adjusted price = final_price + 0.25 * (100 - clean_score),
so each clean point is worth $0.25 and a cleaner pick wins unless the price gap is large.
"""
PENALTY = {"palm_or_seed_oil": 20, "added_sugar": 15, "dough_conditioner_emulsifier": 15, "gum_stabilizer": 10,
           "artificial_additive_preservative": 20, "minor_aid": 3, "non_organic": 15, "ultra_processed": 10}
POINT_VALUE = 0.25          # $ per clean point in per-item choices
RANK_WEIGHT = 0.5           # fraction of total added at clean score 0

def score(flags):
    return max(0, 100 - sum(PENALTY[f] for f in set(flags)))

def adjusted_price(final_price, clean_score):
    return final_price + POINT_VALUE * (100 - clean_score)

def store_score(scores):
    s = [x for x in scores if isinstance(x, (int, float))]
    return round(sum(s) / len(s)) if s else None

def rank_value(total, store_clean, missing_fill=0.0):
    return total * (1 + RANK_WEIGHT * (100 - store_clean) / 100) + missing_fill

def band(s):
    return "green" if s >= 85 else "amber" if s >= 65 else "red"
