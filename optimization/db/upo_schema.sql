-- PLAIN ENGLISH (Universal Practice Optimization on the ehpa Practice Database, William 11/10/2026: "do a universal practice
-- optimization outline in the neon database and in the universal optimisation app ... apply it to my practice with
-- recommendations and work lists and projects").
-- Decides: nothing about billing. This file builds the `upo` schema in the practice's Neon Postgres (project ehpa-database).
-- Two layers live in it:
--   UNIVERSAL  - the framework that applies to any practice: domains -> categories -> metrics, each with its sources; the
--                vendor library crosswalk and its fact-check; the learning modules. No practice data in these tables.
--   PRACTICE   - one practice's application of the framework, keyed by practice code ('ehpa'): which categories apply and how
--                the practice stands on each, its metric values, risk findings, recommendations, projects, the work list and
--                the valuation. Aggregates only: dollars, counts, rates. NEVER a patient name, date of birth, member id or
--                chart-level row - the same rule as the ehpa.* views.
-- Applied by `python3 optimization/tools/upo_load.py schema` (idempotent: create-if-not-exists / create-or-replace only).
-- Rows are loaded from the JSON seed files under optimization/ by `upo_load.py load` (upserts; a reload never duplicates).
-- The app (apps/ehpadb) only SELECTs from upo.* and UPDATEs upo.worklist_items (status, note) for the signed-in owner.
create schema if not exists upo;

-- ---- universal layer ---------------------------------------------------------------------------------------------------------
create table if not exists upo.domains (
  slug text primary key,
  ord int not null,
  name text not null,
  summary text not null,
  why_it_matters text,
  owner_role text,
  frameworks jsonb not null default '[]'::jsonb,        -- recognized bodies of knowledge this domain maps to
  updated_at timestamptz not null default now()
);

create table if not exists upo.categories (
  slug text primary key,
  domain_slug text not null references upo.domains(slug) on update cascade on delete cascade,
  ord int not null,
  name text not null,
  summary text not null,
  good_looks_like jsonb not null default '[]'::jsonb,   -- ["..."]
  failure_modes jsonb not null default '[]'::jsonb,     -- ["..."]
  key_questions jsonb not null default '[]'::jsonb,     -- ["..."]
  actions jsonb not null default '[]'::jsonb,           -- [{"action","detail","cadence","effort","impact"}]
  applies_when text,                                    -- which practices this matters to, and when it does not
  vendor_refs jsonb not null default '[]'::jsonb,       -- [{"item","note"}] titles in the purchased library that cover it
  sources jsonb not null default '[]'::jsonb,           -- [source slug]
  evidence_note text,
  updated_at timestamptz not null default now()
);
create index if not exists categories_domain_idx on upo.categories(domain_slug, ord);

create table if not exists upo.metrics (
  slug text primary key,
  category_slug text not null references upo.categories(slug) on update cascade on delete cascade,
  ord int not null default 0,
  name text not null,
  definition text not null,
  formula text,
  unit text,                                            -- percent | days | dollars | ratio | count | text
  direction text check (direction in ('higher','lower','range','info')),
  cadence text,
  benchmark_best text,
  benchmark_typical text,
  benchmark_red text,
  benchmark_note text,
  confidence text check (confidence in ('high','medium','low','none')),
  sources jsonb not null default '[]'::jsonb,           -- [source slug]
  data_hint text,                                       -- where a practice finds the inputs
  vendor_claim text,                                    -- what the purchased library states, when it differs or adds
  vendor_verdict text,
  updated_at timestamptz not null default now()
);
create index if not exists metrics_category_idx on upo.metrics(category_slug, ord);

create table if not exists upo.sources (
  slug text primary key,
  title text not null,
  publisher text,
  year text,
  url text,
  kind text check (kind in ('primary','secondary','vendor','practice')),
  note text
);

create table if not exists upo.vendor_items (
  slug text primary key,
  vendor text not null,
  bundle text,
  title text not null,
  doc_type text,
  pages int,
  words int,
  list_price_usd numeric,
  quality_score int,
  specificity_score int,
  practice_relevance_score int,
  summary text,
  top_ideas jsonb not null default '[]'::jsonb,
  red_flags jsonb not null default '[]'::jsonb,
  domains jsonb not null default '[]'::jsonb,
  claims_checked int not null default 0,
  claims_supported int not null default 0,
  claims_partly int not null default 0,
  claims_contradicted int not null default 0,
  claims_outdated int not null default 0,
  claims_unverifiable int not null default 0,
  verdict text
);

create table if not exists upo.vendor_claims (
  id text primary key,                                  -- <item slug>:<claim id>
  item_slug text not null references upo.vendor_items(slug) on update cascade on delete cascade,
  claim text not null,
  kind text,
  stakes text,
  verdict text,
  correct_statement text,
  source_title text,
  source_url text,
  confidence text,
  practice_impact text
);
create index if not exists vendor_claims_item_idx on upo.vendor_claims(item_slug);

create table if not exists upo.learning_modules (
  slug text primary key,
  ord int not null,
  title text not null,
  audience text,
  summary text,
  minutes int,
  body jsonb not null,                                  -- {"sections":[{"heading","blocks":[...]}]} rendered by the app
  artifact_url text,
  updated_at timestamptz not null default now()
);

-- ---- practice layer ----------------------------------------------------------------------------------------------------------
create table if not exists upo.practices (
  code text primary key,
  name text not null,
  specialty text,
  setting text,
  profile jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now()
);

create table if not exists upo.practice_categories (
  practice text not null references upo.practices(code) on delete cascade,
  category_slug text not null references upo.categories(slug) on update cascade on delete cascade,
  applicability text not null check (applicability in ('core','relevant','minor','not_applicable')),
  status text not null check (status in ('green','amber','red','unknown','na')),
  priority int,
  assessment text,
  evidence jsonb not null default '[]'::jsonb,          -- ["fact with number and date"]
  next_step text,
  updated_at timestamptz not null default now(),
  primary key (practice, category_slug)
);

create table if not exists upo.practice_metrics (
  practice text not null references upo.practices(code) on delete cascade,
  metric_slug text not null references upo.metrics(slug) on update cascade on delete cascade,
  as_of date not null,
  value numeric,
  value_text text,
  status text check (status in ('green','amber','red','unknown','na')),
  basis text check (basis in ('measured','estimated','unknown')),
  note text,
  source text,
  primary key (practice, metric_slug, as_of)
);

create table if not exists upo.risk_findings (
  id text primary key,
  practice text not null references upo.practices(code) on delete cascade,
  ord int not null,
  title text not null,
  severity text check (severity in ('critical','high','medium','low')),
  likelihood text check (likelihood in ('high','medium','low','unknown')),
  category_slug text references upo.categories(slug) on update cascade on delete set null,
  what_we_see text,                                     -- the pattern in the practice's own aggregates
  rule text,                                            -- the requirement, with its citation
  exposure text,
  recommended_review text,
  control text,
  sources jsonb not null default '[]'::jsonb,
  status text not null default 'open' check (status in ('open','reviewing','resolved','accepted')),
  updated_at timestamptz not null default now()
);

create table if not exists upo.recommendations (
  id text primary key,
  practice text not null references upo.practices(code) on delete cascade,
  ord int not null,
  kind text check (kind in ('revenue','risk','cost','value','capability')),
  category_slug text references upo.categories(slug) on update cascade on delete set null,
  title text not null,
  why text,
  what jsonb not null default '[]'::jsonb,              -- ["step"]
  impact_low numeric,
  impact_high numeric,
  impact_basis text,
  effort text,
  horizon text,
  owner text,
  project_slug text,
  confidence text
);

create table if not exists upo.projects (
  practice text not null references upo.practices(code) on delete cascade,
  slug text not null,
  ord int not null,
  title text not null,
  objective text,
  category_slug text references upo.categories(slug) on update cascade on delete set null,
  priority text check (priority in ('now','next','later')),
  status text not null default 'proposed' check (status in ('proposed','active','paused','done','dropped')),
  impact_low numeric,
  impact_high numeric,
  impact_note text,
  owner text,
  start_by date,
  target_date date,
  success_measures jsonb not null default '[]'::jsonb,
  steps jsonb not null default '[]'::jsonb,
  updated_at timestamptz not null default now(),
  primary key (practice, slug)
);

create table if not exists upo.worklist_items (
  id text primary key,
  practice text not null references upo.practices(code) on delete cascade,
  project_slug text,
  ord int not null,
  title text not null,
  detail text,
  owner text,                                           -- william | claude | pam | cpa | attorney | staff
  due date,
  status text not null default 'open' check (status in ('open','doing','waiting','done','dropped')),
  note text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  updated_by text
);
create index if not exists worklist_practice_idx on upo.worklist_items(practice, status, due);

create table if not exists upo.valuations (
  practice text not null references upo.practices(code) on delete cascade,
  as_of date not null,
  method text not null,                                 -- 'summary' is the reconciled conclusion; the others are the approaches behind it
  low numeric,
  base numeric,
  high numeric,
  inputs jsonb not null default '{}'::jsonb,
  bridge jsonb not null default '[]'::jsonb,            -- [{"label","amount","note"}] from earnings to enterprise value to owner proceeds
  notes text,
  primary key (practice, as_of, method)
);

create table if not exists upo.meta (
  key text primary key,
  value jsonb not null,
  updated_at timestamptz not null default now()
);

-- Who may touch it. The engine's role (ehpa_routine, the NEON_DATABASE_URL credential) applies this file and loads the seeds; the
-- app's role (the database owner Neon injects into the Function) reads everything and may change only the status and note of a
-- work-list row. Both grants are written so the file works whichever of the two roles applies it.
grant usage on schema upo to ehpa_routine, neondb_owner;
grant select, insert, update, delete on all tables in schema upo to ehpa_routine;
grant select on all tables in schema upo to neondb_owner;
grant update (status, note, updated_at, updated_by) on upo.worklist_items to neondb_owner;
