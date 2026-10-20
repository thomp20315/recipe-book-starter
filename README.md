# Family Recipe Book (starter template)

A private recipe book app for your family's phones, plus a shopping helper. Your **Grok Bot** keeps it up to date:
you paste a recipe link into the app, and a few minutes later the recipe (with a good food photo) is in the book.
You can rate recipes 1–10, filter by tags and ratings, build a shared shopping list, have the bot compare clean
ingredients and prices at your grocery stores, and have it fill your store carts. **It never checks out or orders
anything.** You always check out yourself.

This copy has **no recipes, photos, names or accounts in it**. You plug in your own.

---

## Contents
1. [What you get](#what-you-get)
2. [How it works](#how-it-works)
3. [Step-by-step setup](#step-by-step-setup) (steps 1–10)
4. [Day-to-day use](#day-to-day-use)
5. [Reference for the bot](#reference-for-the-bot)
6. [Troubleshooting](#troubleshooting)

---

## What you get
- **Recipe book**: newest recipes first, search (titles, ingredients, tags, who added it), tag filter chips.
- **Ratings out of 10** for each person (names set in `config.json`), an average badge on every card, and a
  **Rating** filter on the home page (minimum score, rated by, sort by Newest / Highest rated / A–Z).
- **Add Recipe** sheet: paste a link, optionally add a note, pick who added it and some tags (tags are tucked in a
  collapsible row so the sheet stays simple), then tap **Send**.
- **Shared shopping cart**: add a recipe's ingredients with one tap, add your own items, check things off. Each
  recipe's items are grouped and **collapsible**, with a **Collapse all** link.
- **"Let's go shopping"**: the bot checks your stores for the cleanest ingredients and best prices, then shows the
  **Top 3 stores**, the **Best 2-store split** and a **Custom 2-store split** (drag or tap any two stores). Every product
  and store gets a **clean score** (0–100).
- **Send to cart**: on any store result or split, tap **Send to cart** and the bot adds the items to that store's
  online cart in its own browser, using your store accounts. It never checks out.
- **Works like an app**: installs to the home screen, works offline for recipes you've already opened.

## How it works
```
 Your phones                     Supabase (free database)            Your Grok Bot (its own computer)
 ─────────────                   ────────────────────────            ────────────────────────────────
 Recipe Book app  ── writes ──►  recipe_queue        ◄── checks every 15 min ── adds recipe + photo,
 (GitHub Pages)                  shopping_requests   ◄──                         rebuilds, pushes to GitHub
                  ◄── reads ───  shopping_results    ──►  compares stores in its browser
                                 cart_requests       ◄──  fills store carts (never checks out)
                                 ratings, tags, cart_items, settings (shared live between phones)
```
- **The app** is a single web page (`index.html`) hosted free on **GitHub Pages**. `build.py` generates it from
  `recipes.json` (your recipes) and `config.json` (your family's settings). Recipes live in the repo; photos live in `images/`.
- **The database** is a free **Supabase** project. It holds everything the family changes from their phones: ratings,
  tags, the shopping list, and three *queues* (new recipe links, shopping requests and send-to-cart requests).
  `supabase.sql` creates all of it.
- **The bot** runs a **routine every 15 minutes** (you choose the hours). Each run it checks the three queues. If all
  are empty it does nothing and stays quiet. Otherwise it:
  1. **Recipe links**: reads the page or video, writes the recipe into `recipes.json`, picks the best photo of the
     finished food (not the creator's face), runs `build.py`, and pushes to GitHub. The book updates in a minute or two.
  2. **Shopping requests**: shops your stores' websites in its browser (signed in to your accounts so it sees your
     loyalty prices and digital coupons), scores each product's ingredients, and posts the comparison back to the app.
  3. **Send to cart**: adds the chosen products to the right store cart, then marks the request done or partial
     (with what it swapped or couldn't find). It never removes items already in your cart and never checks out.
- **Store logins** live only in the bot's computer browser. You sign in once, yourself. **Never paste passwords into chat.**
- **Recipe email inbox (optional)**: the bot can have its own email address. Forward recipe emails or links to it and the
  bot adds them to the book like a queue link.

---

## Step-by-step setup
Your Grok Bot can do most of this for you. Steps marked **(you)** need you to click something or sign in yourself.

### Step 1. GitHub: copy this repo and turn on Pages
1. **(you)** Create a free account at <https://github.com/signup> if you don't have one.
2. **(you)** On this repo's GitHub page, click **Use this template → Create a new repository** (or **Fork**).
   Name it `recipe-book` (any name works). Choose **Public** (free GitHub Pages needs a public repo on the free plan).
3. **(you)** In the new repo: **Settings → Pages → Build and deployment → Source: Deploy from a branch → Branch: `main`, folder `/ (root)` → Save**.
4. After a minute your app is live at `https://<your-username>.github.io/<repo-name>/`. It will show "No recipes yet".
5. **(you)** Connect GitHub to your Grok Bot when it asks, so it can push recipe updates to this repo.

> Your recipes and photos are visible to anyone who has the link (that's how free Pages works). Your ratings, cart and
> shopping data are in Supabase, not in the repo.

### Step 2. Supabase: create the database
1. **(you)** Create a free account at <https://supabase.com> → **New project**. Pick any name, a strong database password
   (save it in your password manager, the app doesn't need it), and the region closest to you.
2. Open **SQL Editor → New query**, paste the whole of [`supabase.sql`](supabase.sql), and click **Run**. It should say
   *Success. No rows returned*. It's safe to run again any time.
3. Go to **Project Settings → API** (or **Connect**). Copy:
   - the **Project URL** (looks like `https://abcdefgh.supabase.co`)
   - the **publishable key** (starts with `sb_publishable_`; older projects call it the `anon` `public` key)
4. Put them in `config.json` as `supabase_url` and `supabase_publishable_key`.

> The publishable key is designed to be public and is embedded in the website. **Never** put the `service_role` /
> secret key or your database password in `config.json` or anywhere in this repo.

### Step 3. Personalize `config.json`
| Setting | What it does | Example |
|---|---|---|
| `family_name` | Small heading above "Recipe Book" (leave `""` to hide it) | `"The Rivera Family"` |
| `app_name`, `short_name` | Page title, and the name under the home-screen icon | `"Recipe Book"`, `"Recipes"` |
| `raters` | Who rates recipes and the "Added by" buttons. `id` is stored in the database, so **don't change ids after you start rating**; labels can change any time | `[{"id":"p1","label":"Mom"},{"id":"p2","label":"Dad"},{"id":"p3","label":"Kids"}]` |
| `home_zip` | Prefills the zip code in the shopping cart | `"12345"` |
| `stores` | The stores the bot should shop. `id` is a short code used in results; `cart_url` is that store's cart page for the "Open cart" link | `{"id":"walmart","name":"Walmart","cart_url":"https://www.walmart.com/cart"}` |
| `store_name_words_to_hide` | Words trimmed from store names on small buttons | `["Supercenter"]` |
| `tags` | Your standard tag list (people can still add custom tags) | `["Dinner","Desserts",...]` |
| `theme_color` | Browser/app bar color | `"#faf8f5"` |

What counts as "clean" food is a **default** list in `clean.py` (seed oils, added sugar, gums, artificial additives,
non-organic where it matters...). Edit it to match your family; see [Clean score](#clean-score).

### Step 4. App photo / icon
The starter comes with a plain placeholder icon. To use your own photo (a pet, the kids, your kitchen...):
- Send the photo to your Grok Bot and ask it to make it the app icon, **or**
- run `python3 make_icon.py --photo my-photo.jpg` (center-crops to a square), or `python3 make_icon.py --text "AB"` for initials,
  **or** just replace `icon-source.png` with any square image (1024×1024 is best).

Then rebuild (step 5). `build.py` makes every icon size in `icons/` from `icon-source.png`.

### Step 5. Build and deploy
```bash
python3 -m pip install pillow   # once
python3 build.py                # makes index.html, sw.js, manifest.webmanifest, icons/
git add -A && git commit -m "Set up my recipe book" && git push
```
GitHub Pages republishes automatically in about a minute. The bot does this for you after every new recipe.

### Step 6. Install on your phones
- **iPhone/iPad**: open your Pages link in **Safari** → **Share** → **Add to Home Screen**.
- **Android**: open it in **Chrome** → **⋮** → **Install app** (or **Add to Home screen**).
Everyone in the family can install it; ratings, tags and the cart sync between phones.

### Step 7. Sign in to your grocery stores on the bot's computer
Only needed for shopping comparisons and **Send to cart**.
1. Ask your Grok Bot: *"Open the store sites I use so I can sign in."*
2. **(you)** Open the bot's computer (desktop) and sign in to each store yourself (for example H-E-B, Walmart, Target,
   Kroger, Sprouts, Amazon / Whole Foods). Set your home store / delivery or pickup location while you're there.
3. Two-factor codes: enter them yourself on the bot's screen, or use the bot's secure form. **Never send passwords or
   codes in chat.**
The logins stay in the bot's browser, so they persist. If a store signs out later, the bot will tell you and ask you to sign in again.

### Step 8. Turn on the routine
Ask your Grok Bot to create a routine using the prompt in [`ROUTINE.md`](ROUTINE.md). Suggested schedule: every 15
minutes during waking hours (e.g. 7 AM–10 PM). Shorter intervals react faster but cost more; empty checks are cheap
and silent.

### Step 9. (Optional) Recipe email inbox
Ask your Grok Bot to give itself an email address (you choose the name), and to add a second routine that checks that
inbox and treats every recipe link or recipe email it receives like an Add Recipe link. Then you can forward recipes from
email, or share links to that address from any app.

### Step 10. Import recipes you already have
- **A list of links**: paste them to the bot (or send them through Add Recipe one by one).
- **Another recipe app** (ReciMe, Paprika, Mela, Notes, a spreadsheet...): export or share what you can (file, links,
  screenshots) and ask the bot to import them. It writes each one into `recipes.json` with the format in
  [`recipe.example.json`](recipe.example.json), keeps your tags, finds a good food photo, and rebuilds.
- Ask the bot to mark duplicates and show you anything it couldn't read.

---

## Day-to-day use
- **Add a recipe**: tap **+ Add Recipe**, paste the link, tap **Send**. It appears within one routine cycle.
- **Rate**: open a recipe, tap a number 1–10 under each person. Tap the same number again to clear it.
- **Find something**: search box, tag chips, or **Rating** (e.g. 8+ by Kids, sorted Highest rated).
- **Shop**: on a recipe, tap **Add to Cart**. Open the cart (top right), enter your zip, tap **Let's go shopping**.
  Results appear in the cart in a few minutes: Top 3 stores, then the Best and Custom 2-store splits.
- **Send to cart**: tap **Send to cart** under a store or split and confirm. The status shows Queued → Adding… → Added.
  Then tap **Open … cart** and check out yourself.

---

## Reference for the bot

### Files
| File | Purpose |
|---|---|
| `config.json` | Family settings + Supabase URL/publishable key (read by `build.py` and `sb.py`) |
| `recipes.json` | All recipes (JSON array; shape in `recipe.example.json`). Starts empty |
| `images/` | Recipe photos (`images/<id>.jpg`, JPEG, long side ≤ 1200 px) |
| `build.py`, `design.css` | Generate `index.html`, `sw.js`, `manifest.webmanifest`, `icons/` |
| `icon-source.png`, `make_icon.py` | App icon source and placeholder/photo icon maker |
| `sb.py` | Tiny Supabase REST helper used by the queue scripts |
| `process_queue.py` | Recipe link queue |
| `shopping_queue.py` | Shopping requests/results (+ validation) |
| `cart_queue.py` | Send-to-cart requests |
| `clean.py` | Clean-score rubric (default preferences, editable) |
| `pick_food_frame.py` | Picks the best food frame from a video (not the creator's face) |
| `supabase.sql` | Full database schema, policies and triggers (no data) |
| `shopping_result.example.json` | Fake sample result for testing the layout |

### Supabase tables
| Table | Used for |
|---|---|
| `ratings` | `recipe_id`, `person` (rater id from config), `score` 1–10 (`stars` 1–5 kept in sync by a trigger) |
| `recipe_queue` | Links from Add Recipe (`url`, `notes`, `added_by`, `tags`, `status` pending/done/rejected) |
| `recipe_tags` | Shared tags per recipe (`tags` jsonb array) |
| `cart_items` | Shared shopping list (`recipe_id` or null, `text`, `checked`, `sort_order`) |
| `settings` | key `zip` |
| `shopping_requests` | "Let's go shopping" (`zip`, `items`, `status`, progress `stores_done`/`stores_total`/`current_store`) |
| `shopping_results` | One comparison per request (`result` jsonb) |
| `cart_requests` | Send to cart, one row per store (`items`, `status` queued/working/done/partial/failed, `added`, `failed`, `note`) |

### Recipe queue
- `python3 process_queue.py` prints pending rows.
- Add each recipe to `recipes.json` (+ photo in `images/`), then `python3 process_queue.py --done <queue_id>=<recipe_id>`
  (copies tags, stamps `added`, marks done). `--reject <id>` for duplicates or non-recipes.
- `python3 build.py`, commit, push.
- **Photo from a video** (Instagram, TikTok, YouTube, Facebook): don't use the cover image directly, since it's often the
  creator's face. Run
  `venv/bin/python pick_food_frame.py "<video_url>" images/<id>.jpg --cover /tmp/cover.jpg --title "<Recipe title>" --min 0.6`
  (exit 0 = saved; 2 = nothing scored ≥ 0.6, so try page images with `--score`, else use the cover; 1 = download failed).
  Then **look at the chosen image** and keep trying candidates until it clearly shows the finished food.
  Setup: `python3 -m venv venv && venv/bin/pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu && venv/bin/pip install open_clip_torch "opencv-python-headless<5" pillow yt-dlp` (needs `ffmpeg`).

### Shopping
- `python3 shopping_queue.py list` · `mark <id> processing|done|failed` · `progress <id> <done> <total> ["Store"]`
- `python3 shopping_queue.py validate result.json`, then `post-result <request_id> result.json` (marks the request done).
- Result shape: see `shopping_result.example.json`. `picks[].store`, `top3[]` and `hybrid.stores[]` refer to `stores[].id`.
  Unknown prices are `null`; never guess. Add `clean_score` (0–100) and `ingredient_flags[]` to picks and stores.
- The app shows: **Top 3 stores** (`top3`, otherwise cheapest first) → **2-store splits** (Best split from `hybrid`,
  then the Custom split the user builds) → All stores checked → notes.

### Clean score
Per pick: start at 100 and subtract each flag once (floor 0). Defaults (edit in `clean.py`):

| Flag | Penalty | Examples |
|---|---|---|
| `palm_or_seed_oil` | -20 | palm shortening, soybean, canola, corn, sunflower, safflower oil |
| `added_sugar` | -15 | cane or beet sugar, corn syrup, dextrose |
| `dough_conditioner_emulsifier` | -15 | DATEM, SSL, mono- and diglycerides, soy lecithin |
| `gum_stabilizer` | -10 | guar, xanthan, locust bean gum, carrageenan |
| `artificial_additive_preservative` | -20 | artificial colors/flavors, calcium propionate, sorbates, natamycin |
| `minor_aid` | -3 | added enzymes, citric acid, yeast extract, natural flavor |
| `non_organic` | -15 | non-organic produce, meat or dairy where it matters |
| `ultra_processed` | -10 | industrial formulations (commercial white buns, processed cheese) |

- **Store score**: mean of core-item pick scores (pantry and optional items excluded; missing items listed in `items_missing`).
- **In-store swaps**: choose the lowest `final_price + $0.25 × (100 − clean_score)`.
- **Best 2-store split (cleanest first, then price)**: only consider pairs that cover the most core items; for each item take
  the cleanest pick (within 3 points counts as tied, cheapest tied pick wins); choose the pair with the highest mean score
  (within 2 points counts as tied, lowest total wins). Report `savings_vs_best_single` against the cleanest single store.

### Send to cart
- `python3 cart_queue.py list [store]` (queued only, oldest first) · `show <id>` ·
  `mark <id> working|done|partial|failed [--added a.json] [--failed f.json] [--note "..."]`
- Mark a row `working` **before** touching the store (prevents duplicates if two runs overlap); only process `queued` rows.
- Add items in the bot's signed-in browser. **Never check out, never remove existing cart items.** Make close swaps when
  something is out of stock and say so in `--note`.

---

## Troubleshooting
| Problem | Fix |
|---|---|
| App says "Couldn't save" / ratings don't stick | `config.json` still has placeholders, or `supabase.sql` wasn't run. Fix, `python3 build.py`, push. |
| Tags say they need a database setup | Re-run `supabase.sql` in the Supabase SQL Editor. |
| New recipe doesn't show up | Wait a cycle, then close and reopen the app (it updates on open). Ask the bot whether the queue item was processed or rejected. |
| Pages link shows 404 | Settings → Pages: branch `main`, folder `/ (root)`; wait a minute; the repo must contain `index.html`. |
| Old version keeps showing | Close the app fully and reopen; on iPhone you may need to reopen twice. |
| Photo shows a person instead of food | Ask the bot to re-pick the photo for that recipe. |
| Shopping or Send to cart stuck on "Queued" | The routine may be outside its hours or paused, or a store signed out. Ask the bot to check. |
| Store asks for a code / login | Sign in yourself on the bot's computer, or through its secure form. Never paste it in chat. |
| Supabase project paused | Free projects pause after a week of no use. Open the Supabase dashboard and click **Restore**. |
| Want to change rater names | Change `label` in `config.json` and rebuild. Changing an `id` hides that person's old ratings. |
