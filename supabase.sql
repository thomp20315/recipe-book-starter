-- Recipe Book: full Supabase schema, from zero. Safe to rerun. Contains NO data.
-- Supabase Dashboard -> SQL Editor -> New query -> paste this whole file -> Run.
--
-- Security model: this is a private family app with no logins. The publishable (anon) key is
-- embedded in the website, and these policies let anyone holding it read/write ONLY these tables.
-- Don't store anything sensitive here, and keep your site URL within the family.

create extension if not exists pgcrypto;

-- Keep updated_at current
create or replace function public.touch_updated_at() returns trigger
language plpgsql as $$ begin new.updated_at := now(); return new; end $$;

-- ---------------------------------------------------------------- ratings
-- One row per recipe + rater. `person` is a rater id from config.json (e.g. p1, p2, p3).
-- `score` is 1-10. Legacy `stars` (1-5) is kept in sync by a trigger so older app versions still work.
create table if not exists public.ratings (
  id          bigint generated always as identity primary key,
  recipe_id   text not null,
  person      text not null check (length(person) between 1 and 40),
  score       smallint check (score between 1 and 10),
  stars       smallint check (stars between 1 and 5),
  updated_at  timestamptz not null default now(),
  unique (recipe_id, person)
);
create or replace function public.ratings_sync_score() returns trigger language plpgsql as $$
begin
  if new.score is null and new.stars is null then
    raise exception 'score (1-10) is required';
  end if;
  if new.score is null or (tg_op = 'UPDATE' and new.score is not distinct from old.score
                           and new.stars is distinct from old.stars) then
    new.score := new.stars * 2;
  end if;
  new.stars := greatest(1, least(5, ceil(new.score / 2.0)::int));
  return new;
end $$;
drop trigger if exists ratings_sync_score on public.ratings;
create trigger ratings_sync_score before insert or update on public.ratings
  for each row execute function public.ratings_sync_score();
drop trigger if exists ratings_touch on public.ratings;
create trigger ratings_touch before update on public.ratings
  for each row execute function public.touch_updated_at();

-- ---------------------------------------------------------------- recipe_queue
-- Links sent from the app's Add Recipe sheet. The bot's routine picks up status = 'pending'.
create table if not exists public.recipe_queue (
  id          bigint generated always as identity primary key,
  url         text not null check (url ~* '^https?://'),
  notes       text not null default '',
  added_by    text check (added_by is null or length(added_by) between 1 and 40),
  tags        jsonb not null default '[]'::jsonb,
  status      text not null default 'pending' check (status in ('pending','done','rejected')),
  created_at  timestamptz not null default now()
);
create index if not exists recipe_queue_status_idx on public.recipe_queue (status, created_at);

-- ---------------------------------------------------------------- recipe_tags
-- Shared, editable tags per recipe (overlays any tags in recipes.json).
create table if not exists public.recipe_tags (
  recipe_id   text primary key,
  tags        jsonb not null default '[]'::jsonb,
  updated_at  timestamptz not null default now()
);
create index if not exists recipe_tags_gin on public.recipe_tags using gin (tags);
drop trigger if exists recipe_tags_touch on public.recipe_tags;
create trigger recipe_tags_touch before update on public.recipe_tags
  for each row execute function public.touch_updated_at();

-- ---------------------------------------------------------------- cart_items
-- Shared shopping list. recipe_id null = a custom item typed into the cart.
create table if not exists public.cart_items (
  id            uuid primary key default gen_random_uuid(),
  recipe_id     text,
  recipe_title  text,
  text          text not null check (length(trim(text)) > 0),
  checked       boolean not null default false,
  sort_order    double precision not null default extract(epoch from now()),
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now()
);
create index if not exists cart_items_sort_idx on public.cart_items (sort_order);
drop trigger if exists cart_items_touch on public.cart_items;
create trigger cart_items_touch before update on public.cart_items
  for each row execute function public.touch_updated_at();

-- ---------------------------------------------------------------- settings
-- Simple key/value settings (the app stores key 'zip').
create table if not exists public.settings (
  key         text primary key,
  value       text,
  updated_at  timestamptz not null default now()
);
drop trigger if exists settings_touch on public.settings;
create trigger settings_touch before update on public.settings
  for each row execute function public.touch_updated_at();

-- ---------------------------------------------------------------- shopping_requests
-- "Let's go shopping" taps. The bot's routine picks up status = 'pending'.
create table if not exists public.shopping_requests (
  id              bigint generated always as identity primary key,
  zip             text check (zip ~ '^[0-9]{5}$'),
  items           jsonb not null default '[]'::jsonb,   -- [{text, recipe_id, recipe_title}]
  requested_by    text,
  status          text not null default 'pending' check (status in ('pending','processing','done','failed')),
  stores_done     integer,           -- optional progress shown in the app while shopping
  stores_total    integer,
  current_store   text,
  created_at      timestamptz not null default now()
);
create index if not exists shopping_requests_status_idx on public.shopping_requests (status, created_at);

-- ---------------------------------------------------------------- shopping_results
-- One store comparison per request (`result` jsonb; see shopping_result.example.json).
create table if not exists public.shopping_results (
  id          bigint generated always as identity primary key,
  request_id  bigint references public.shopping_requests(id) on delete set null,
  zip         text,
  result      jsonb not null,
  created_at  timestamptz not null default now()
);
create index if not exists shopping_results_created_idx on public.shopping_results (created_at desc);

-- ---------------------------------------------------------------- cart_requests
-- "Send to cart" taps: one row per store. The bot adds items to the store cart in its browser
-- and NEVER checks out. Status: queued -> working -> done | partial | failed.
create table if not exists public.cart_requests (
  id                   bigint generated always as identity primary key,
  created_at           timestamptz not null default now(),
  updated_at           timestamptz not null default now(),
  shopping_request_id  bigint references public.shopping_requests(id) on delete set null,
  result_id            bigint references public.shopping_results(id) on delete set null,
  source               text,            -- which button: store:<id> | hyb | cust:<a>+<b>
  store                text not null,   -- stores[].id from the result
  store_name           text,
  items                jsonb not null default '[]'::jsonb,  -- [{name, product, url, qty, unit, price}]
  status               text not null default 'queued' check (status in ('queued','working','done','partial','failed')),
  added                jsonb not null default '[]'::jsonb,
  failed               jsonb not null default '[]'::jsonb,
  note                 text
);
create index if not exists cart_requests_status_idx on public.cart_requests (status, created_at);
create index if not exists cart_requests_result_idx on public.cart_requests (result_id, created_at desc);
drop trigger if exists cart_requests_touch on public.cart_requests;
create trigger cart_requests_touch before update on public.cart_requests
  for each row execute function public.touch_updated_at();

-- ---------------------------------------------------------------- access (RLS)
do $$
declare t text;
begin
  foreach t in array array['ratings','recipe_queue','recipe_tags','cart_items','settings',
                           'shopping_requests','shopping_results','cart_requests'] loop
    execute format('alter table public.%I enable row level security', t);
    execute format('grant select, insert, update, delete on public.%I to anon, authenticated', t);
    execute format('drop policy if exists family_all on public.%I', t);
    execute format('create policy family_all on public.%I for all to anon, authenticated using (true) with check (true)', t);
  end loop;
end $$;
grant usage, select on all sequences in schema public to anon, authenticated;

-- ---------------------------------------------------------------- realtime (optional live updates)
do $$
declare t text;
begin
  if exists (select 1 from pg_publication where pubname = 'supabase_realtime') then
    foreach t in array array['ratings','recipe_queue','recipe_tags','cart_items','settings',
                             'shopping_requests','shopping_results','cart_requests'] loop
      if not exists (select 1 from pg_publication_tables
                     where pubname = 'supabase_realtime' and schemaname = 'public' and tablename = t) then
        execute format('alter publication supabase_realtime add table public.%I', t);
      end if;
    end loop;
  end if;
end $$;

-- Refresh the REST API schema cache
notify pgrst, 'reload schema';
