# Tags

The tag list lives in `config.json` → `tags`. Edit it, then run `python3 build.py`. Anyone can also add a custom
tag in the app; custom tags are kept as typed. The Add Recipe sheet shows your 6 most-used tags first, plus a **More** button.

## Where tags are stored
- Tags edited in the app are saved in the Supabase table `recipe_tags` (see `supabase.sql`), so every phone stays in sync.
- A recipe can also carry a `tags` array in `recipes.json` (the bot fills this when it adds a recipe from the queue).
  The app shows the Supabase value when one exists.

## Add Recipe queue
The Add Recipe sheet saves the chosen tags in `recipe_queue.tags`. `python3 process_queue.py --done <queue_id>=<recipe_id>`
copies them into `recipes.json` (known tags are normalized to the spelling in `config.json`).
