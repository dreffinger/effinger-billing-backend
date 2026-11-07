-- PLAIN ENGLISH (ehpa Practice Database on Neon - the typed layer, William 11/6/2026).
-- raw.documents keeps every document exactly as its source wrote it (one JSONB body per collection/doc_id, loaded by
-- tools/db/neon_db.py). This file builds the ehpa.* VIEWS that turn those documents into rows a report can query: one row per
-- billing run, per run step, per ERA line, per CARC code on a line, per feed charge, per cascade night, per approval package,
-- per routine run. Views, not copies: a reload of raw.documents is immediately visible, and nothing here can drift from the source.
-- Applied by `python3 tools/db/neon_db.py init` (idempotent: every statement is CREATE OR REPLACE). No PHI in names or comments;
-- the rows carry chart ids, dates of service, codes and dollars - the same fields the registers on main carry.
create schema if not exists ehpa;

-- ---- the practice database's own collections (source practice_db) ------------------------------------------------------------
create or replace view ehpa.billing_runs as
select doc_id as stamp,
       (body->>'at')::timestamptz as at,
       (body->>'started')::timestamptz as started,
       (body->>'ended')::timestamptz as ended,
       body->>'mode' as mode, body->>'status' as status, body->>'headline' as headline, body->>'note' as note, body->>'run_url' as run_url,
       body->'summary' as summary,
       body->'summary'->'columns' as columns,
       (body->'summary'->'columns'->'before'->>'charge_review')::int as charge_review_before, (body->'summary'->'columns'->'after'->>'charge_review')::int as charge_review_after,
       (body->'summary'->'columns'->'before'->>'claim_inspector')::int as claim_inspector_before, (body->'summary'->'columns'->'after'->>'claim_inspector')::int as claim_inspector_after,
       (body->'summary'->'columns'->'before'->>'unbilled')::int as unbilled_before, (body->'summary'->'columns'->'after'->>'unbilled')::int as unbilled_after,
       (body->'summary'->'columns'->'before'->>'exclusions')::int as exclusions_before, (body->'summary'->'columns'->'after'->>'exclusions')::int as exclusions_after,
       body->'summary'->'era' as era,
       (body->'summary'->'era'->'before'->>'unposted')::numeric as era_unposted_before, (body->'summary'->'era'->'after'->>'unposted')::numeric as era_unposted_after,
       (body->'summary'->'era'->'before'->>'checks')::int as era_checks_before, (body->'summary'->'era'->'after'->>'checks')::int as era_checks_after,
       body->'summary'->'outstanding' as outstanding,
       (body->'summary'->'outstanding'->>'total')::numeric as outstanding_total, (body->'summary'->'outstanding'->>'visits')::int as outstanding_visits,
       (body->'summary'->'outstanding'->>'charts')::int as outstanding_charts, (body->'summary'->'outstanding'->'over_365'->>'dollars')::numeric as outstanding_over_365_dollars,
       (body->'summary'->'outstanding'->'over_365'->>'n')::int as outstanding_over_365_visits,
       body->'summary'->'denials' as denials,
       (body->'summary'->'denials'->>'actionable')::int as denials_actionable, (body->'summary'->'denials'->>'actionable_amt')::numeric as denials_actionable_dollars,
       (body->'summary'->'denials'->>'visits')::int as denials_visits,
       (body->'summary'->'posted'->>'pay')::numeric as posted_pay, (body->'summary'->'resent'->>'dollars')::numeric as resent_dollars, (body->'summary'->'resent'->>'visits')::int as resent_visits,
       (body->'summary'->'written_off'->>'dollars')::numeric as written_off_dollars, (body->'summary'->'written_off'->>'count')::int as written_off_count,
       body->'summary'->'aging' as aging, (body->'summary'->'aging'->>'total')::numeric as aging_total,
       jsonb_array_length(coalesce(body->'steps', '[]'::jsonb)) as steps,
       jsonb_array_length(coalesce(body->'packages', '[]'::jsonb)) as packages,
       jsonb_array_length(coalesce(body->'waiting', '[]'::jsonb)) as waiting,
       jsonb_array_length(coalesce(body->'errors', '[]'::jsonb)) as errors,
       body->>'_swept_by' as swept_by, loaded_at
from raw.documents where source = 'practice_db' and collection = 'billing_runs';

create or replace view ehpa.billing_run_steps as
select d.doc_id as stamp, s.ordinality as step_no, s.value->>'name' as name, s.value->>'title' as title, s.value->>'status' as status,
       s.value->>'summary' as summary, s.value->'counts' as counts, s.value->'dollars' as dollars, s.value->'lines' as lines, s.value->'errors' as errors,
       (s.value->>'started')::timestamptz as started, (s.value->>'ended')::timestamptz as ended
from raw.documents d cross join lateral jsonb_array_elements(coalesce(d.body->'steps', '[]'::jsonb)) with ordinality as s(value, ordinality)
where d.source = 'practice_db' and d.collection = 'billing_runs';

create or replace view ehpa.era_runs as
select doc_id as stamp, (body->>'at')::timestamptz as at, (body->>'dry')::boolean as dry,
       (body->'checks_before'->>'count')::int as checks_before, (body->'checks_before'->>'total')::numeric as checks_before_total,
       (body->'checks_after'->>'count')::int as checks_after, (body->'checks_after'->>'total')::numeric as checks_after_total,
       (body->>'line_count')::int as line_count, (body->>'paid_total')::numeric as paid_total, body->'outcomes' as outcomes,
       (body->'audit'->>'rows')::int as audit_rows, jsonb_array_length(coalesce(body->'audit'->'flags', '[]'::jsonb)) as audit_flags,
       body->>'_swept_by' as swept_by, loaded_at
from raw.documents where source = 'practice_db' and collection = 'era_runs';

create or replace view ehpa.era_lines as
select d.doc_id as run_stamp, (d.body->>'at')::timestamptz as run_at, l.ordinality as line_no,
       l.value->>'check' as check_id, l.value->>'p' as chart_id, l.value->>'v' as visit_id, l.value->>'cpt' as cpt,
       nullif(l.value->>'dos', '')::date as dos, (l.value->>'paid')::numeric as paid, (l.value->>'status')::int as claim_status,
       (select array_agg(x) from jsonb_array_elements_text(coalesce(l.value->'carcs', '[]'::jsonb)) x) as carcs,
       l.value->>'outcome' as outcome, (l.value->>'primary')::boolean as is_primary
from raw.documents d cross join lateral jsonb_array_elements(coalesce(d.body->'lines', '[]'::jsonb)) with ordinality as l(value, ordinality)
where d.source = 'practice_db' and d.collection = 'era_runs';

create or replace view ehpa.era_line_carcs as
select run_stamp, run_at, line_no, check_id, chart_id, visit_id, cpt, dos, paid, claim_status, outcome, c as carc,
       substr(c, 1, 2) as carc_group, nullif(regexp_replace(c, '^[A-Z]+', ''), '')::int as carc_code
from ehpa.era_lines cross join lateral unnest(coalesce(carcs, array[]::text[])) as c;

create or replace view ehpa.cascade_nights as
select doc_id as stamp, (body->>'at')::timestamptz as at, nullif(body->>'date', '')::date as night,
       (body->>'checked')::int as checked, (body->>'flagged')::int as flagged, (body->>'lookups')::int as lookups, (body->>'changed')::int as changed,
       (body->>'dollars')::numeric as dollars_resent, (body->>'era_posted')::numeric as era_posted, (body->>'writeoffs')::numeric as writeoffs,
       (body->>'stedi_cost')::numeric as stedi_cost, body->>'done' as done, body->>'note' as note, body->>'commit' as commit_sha, loaded_at
from raw.documents where source = 'practice_db' and collection = 'cascade_runs';

create or replace view ehpa.feed_batches as
select doc_id as stamp, (body->>'at')::timestamptz as at, (body->>'built')::timestamptz as built, (body->>'live')::boolean as live,
       nullif(body->>'dmin', '')::date as dos_min, nullif(body->>'dmax', '')::date as dos_max, body->'files' as files, body->'counts' as counts,
       jsonb_array_length(coalesce(body->'rows', '[]'::jsonb)) as charges, body->'lookups' as lookups, loaded_at
from raw.documents where source = 'practice_db' and collection = 'feed_batches' and doc_id !~ '\.p[0-9]+$';

create or replace view ehpa.feed_charges as
select d.doc_id as batch_stamp, (d.body->>'at')::timestamptz as batch_at, r.ordinality as row_no,
       r.value->>'p' as chart_id, r.value->>'v' as visit_id, nullif(r.value->>'d', '')::date as dos,
       (select array_agg(x) from jsonb_array_elements_text(coalesce(r.value->'c', '[]'::jsonb)) x) as cpts,
       (select array_agg(x) from jsonb_array_elements_text(coalesce(r.value->'dx', '[]'::jsonb)) x) as dx,
       r.value->>'fac' as facility_id, d.body->'lookups'->'fac'->>(r.value->>'fac') as facility,
       r.value->>'pos' as pos, r.value->>'lead' as lead_carrier, d.body->'lookups'->'car'->>(r.value->>'lead') as lead_carrier_name,
       r.value->>'prov' as clinician, (r.value->>'fee')::numeric as fee, r.value->>'s' as status, r.value->>'hold' as hold, r.value->>'why' as why,
       r.value->>'verdict' as verdict, r.value->>'newchart' as newchart, nullif(r.value->>'admit', '')::date as admit, r.value->>'file' as feed_file,
       r.value->>'f' as facility_code, (r.value->>'u')::int as u, r.value->'ch' as charges
from raw.documents d cross join lateral jsonb_array_elements(coalesce(d.body->'rows', '[]'::jsonb)) with ordinality as r(value, ordinality)
where d.source = 'practice_db' and d.collection = 'feed_batches';

create or replace view ehpa.feed_checks as
select doc_id as stamp, (body->>'at')::timestamptz as at, body->>'result' as result, body->>'line' as line, (body->>'live')::boolean as live,
       (body->>'exit')::int as exit_code, (body->>'files_registered')::int as files_registered, (body->>'files_new')::int as files_new,
       body->>'newest_file' as newest_file, (body->>'visits')::int as visits, (body->>'dollars')::numeric as dollars, (body->>'messages')::int as messages,
       (body->>'new_charts')::int as new_charts, loaded_at
from raw.documents where source = 'practice_db' and collection = 'feed_checks';

create or replace view ehpa.approval_snapshots as
select doc_id, (body->>'at')::timestamptz as at, body->>'stamp' as stamp, body->'counts' as counts, (body->>'dollars_waiting')::numeric as dollars_waiting,
       jsonb_array_length(coalesce(body->'rows', '[]'::jsonb)) as packages
from raw.documents where source = 'practice_db' and collection = 'snapshots' and body->>'kind' = 'approvals';

-- the approval packages as of the NEWEST snapshot (one row per package)
create or replace view ehpa.approvals as
select r.value->>'id' as package_id, r.value->>'stamp' as stamp, (r.value->>'at')::timestamptz as at, r.value->>'what' as what,
       nullif(regexp_replace(r.value->>'dollars', '[^0-9.\-]', '', 'g'), '')::numeric as dollars, r.value->>'status' as status,
       r.value->>'answer' as answer, r.value->>'reason' as reason, r.value->>'ui' as ui, r.value->>'cmd' as cmd, d.doc_id as snapshot
from (select * from raw.documents where source = 'practice_db' and collection = 'snapshots' and body->>'kind' = 'approvals' order by written_at desc nulls last, doc_id desc limit 1) d
cross join lateral jsonb_array_elements(coalesce(d.body->'rows', '[]'::jsonb)) r(value);

create or replace view ehpa.practice_master as
select doc_id as name, body->'data' as data, body->>'source' as source, loaded_at
from raw.documents where source = 'practice_db' and collection = 'practice';

-- ---- the other boards, as the daily sync copies them (source = the board's slug; one row per document) -----------------------
create or replace view ehpa.board_documents as
select source as board, collection, doc_id, body, written_at, loaded_at
from raw.documents where source not in ('practice_db', 'repo');

-- carriers lookup from the practice master data: carriers.json is {"carN": [code, name, ...]}
create or replace view ehpa.carriers as
select e.key as carrier_id, e.value->>0 as carrier_code, e.value->>1 as carrier_name, e.value as raw
from raw.documents d cross join lateral jsonb_each(d.body->'data') e
where d.source = 'practice_db' and d.collection = 'practice' and d.doc_id = 'carriers' and jsonb_typeof(e.value) = 'array';

-- the Outstanding Claims report (every open insurance balance), from the newest copy of the page's embedded dataset
create or replace view ehpa.outstanding_claims as
select d.doc_id as snapshot, nullif(d.body->>'as_of', '')::date as as_of, r.value->>'visitid' as visit_id, r.value->>'patientid' as chart_id,
       nullif(r.value->>'dos', '')::date as dos, (r.value->>'days')::int as days_old, (r.value->>'insbalance')::numeric as ins_balance,
       r.value->>'carriercode' as carrier_code,
       case when (r.value->>'days')::int <= 30 then '0-30' when (r.value->>'days')::int <= 60 then '31-60' when (r.value->>'days')::int <= 90 then '61-90'
            when (r.value->>'days')::int <= 120 then '91-120' when (r.value->>'days')::int <= 365 then '121-365' else '365+' end as age_bucket
from (select * from raw.documents where source = 'outstanding_claims' and collection = 'embedded' order by loaded_at desc limit 1) d
cross join lateral jsonb_array_elements(coalesce(d.body->'rows', '[]'::jsonb)) r(value);

create or replace view ehpa.outstanding_by_carrier as
select d.doc_id as snapshot, c.value->>'carrier' as carrier_code, c.value->>'name' as carrier_name, (c.value->>'n')::int as visits,
       (c.value->>'dollars')::numeric as dollars, (c.value->>'oldest_days')::int as oldest_days, c.value->'buckets' as buckets
from (select * from raw.documents where source = 'outstanding_claims' and collection = 'embedded' order by loaded_at desc limit 1) d
cross join lateral jsonb_array_elements(coalesce(d.body->'by_carrier', '[]'::jsonb)) c(value);

create or replace view ehpa.outstanding_by_month as
select d.doc_id as snapshot, m.value->>'month' as month, (m.value->>'n')::int as visits, (m.value->>'dollars')::numeric as dollars
from (select * from raw.documents where source = 'outstanding_claims' and collection = 'embedded' order by loaded_at desc limit 1) d
cross join lateral jsonb_array_elements(coalesce(d.body->'by_month', '[]'::jsonb)) m(value);

-- the Working Denials triage dataset: one row per denied visit (names stay in raw, not here)
create or replace view ehpa.denial_visits as
select d.doc_id as snapshot, nullif(d.body->>'asof', '')::date as as_of, v.value->>'visitid' as visit_id, v.value->>'pid' as chart_id,
       nullif(v.value->>'dos', '')::date as dos, v.value->>'cpt' as cpt, v.value->>'carrier' as carrier, v.value->>'carc' as carc, v.value->>'rarc' as rarc,
       v.value->'codes' as codes, (v.value->>'amt')::numeric as amount, (v.value->>'billed')::numeric as billed, (v.value->>'open_balance')::numeric as open_balance,
       v.value->>'status' as status, v.value->>'dispo' as dispo, v.value->>'action' as action, v.value->>'reason' as reason, (v.value->>'timely')::boolean as timely,
       nullif(v.value->>'denied_on', '')::date as denied_on, nullif(v.value->>'last_billed', '')::date as last_billed, (v.value->>'age')::int as age_days, v.value->>'check' as check_id
from (select * from raw.documents where source = 'working_denials' and collection = 'embedded' order by loaded_at desc limit 1) d
cross join lateral jsonb_array_elements(coalesce(d.body->'visits', '[]'::jsonb)) v(value);

-- the Insurance Refresh Board rows (who needs a coverage check); identifiers and names stay in raw
create or replace view ehpa.insurance_refresh_items as
select doc_id, body->>'amdid' as chart_id, body->>'status' as status, body->>'need' as need, body->>'why' as why, body->>'inscarrier' as carrier,
       body->'insplans' as insplans, nullif(regexp_replace(body->>'amount', '[^0-9.\-]', '', 'g'), '')::numeric as amount,
       nullif(body->>'lastdos', '')::date as last_dos, body->>'lastfac' as last_facility, body->>'facility' as facility, body->'checks' as checks,
       body->>'created' as created, body->>'updated' as updated, written_at, loaded_at
from raw.documents where source = 'insurance_refresh_board' and collection = 'items';

create or replace view ehpa.approval_cards as
select doc_id as package_id, body->>'at' as at, body->>'status' as status, body->>'what' as what,
       nullif(regexp_replace(body->>'dollars', '[^0-9.\-]', '', 'g'), '')::numeric as dollars, body->>'command' as command, body->>'reason' as reason,
       body->>'run' as run, body->>'answeredAt' as answered_at, body->>'answeredBy' as answered_by, body->>'doneAt' as done_at, body->>'doneBy' as done_by, body->>'note' as note
from raw.documents where source = 'mandatory_approvals' and collection = 'approvals';

create or replace view ehpa.credentialing_items as
select doc_id, body->>'name' as name, body->>'section' as section, body->>'holder' as holder, body->>'cycle' as cycle, body->>'due' as due,
       body->>'dueNote' as due_note, body->>'need' as need, body->>'turn' as turn, body->>'verify' as verify, body->'checks' as checks, body->>'updated' as updated
from raw.documents where source = 'credentialing_board' and collection = 'cred';

create or replace view ehpa.treasury_findings as
select d.doc_id as snapshot, d.body->>'asof' as as_of, f.value->>'key' as key, f.value->>'sev' as severity, f.value->>'title' as title, f.value->>'what' as what,
       f.value->>'action' as action, f.value->>'owner' as owner, (f.value->>'n')::int as n, (f.value->>'amount')::numeric as amount
from (select * from raw.documents where source = 'treasury_payments' and collection = 'embedded' order by loaded_at desc limit 1) d
cross join lateral jsonb_array_elements(coalesce(d.body->'findings', '[]'::jsonb)) f(value);

create or replace view ehpa.treasury_groups as
select d.doc_id as snapshot, g.value->>'label' as label, g.value->>'family' as family, g.value->>'status' as status, g.value->>'cadence' as cadence,
       (g.value->>'n')::int as n, (g.value->>'amt')::numeric as amount
from (select * from raw.documents where source = 'treasury_payments' and collection = 'embedded' order by loaded_at desc limit 1) d
cross join lateral jsonb_array_elements(coalesce(d.body->'groups', '[]'::jsonb)) g(value);

-- the A/R aging report (reports/aging + the "ar aging artifact" page): one row per unpaid visit with the recommendation the scan gave it
create or replace view ehpa.ar_aging_rows as
select d.doc_id as snapshot, coalesce(nullif(d.body->>'asof', ''), nullif(d.body->>'today', ''))::date as as_of,
       r.value->>'visitid' as visit_id, r.value->>'pid' as chart_id, nullif(r.value->>'dos', '')::date as dos, nullif(r.value->>'sent', '')::date as last_sent,
       (r.value->>'days_dos')::int as days_since_dos, (r.value->>'days_sent')::int as days_since_sent, r.value->>'b_dos' as bucket_dos, r.value->>'b_sent' as bucket_sent,
       r.value->>'payer' as payer, r.value->>'pr' as primary_carrier, r.value->>'secondary' as secondary, (r.value->>'fee')::numeric as fee, (r.value->>'bal')::numeric as balance,
       r.value->'cpts' as cpts, r.value->'mods' as modifiers, r.value->'carcs' as carcs, (r.value->>'denied')::boolean as denied, r.value->>'paid_by' as paid_by,
       nullif(r.value->>'paid_on', '')::date as paid_on, r.value->>'rec' as recommendation, r.value->>'why' as why, r.value->>'rule' as rule, nullif(r.value->>'dod', '')::date as dod
from (select * from raw.documents where source = 'ar_aging' and collection = 'embedded' order by loaded_at desc limit 1) d
cross join lateral jsonb_array_elements(coalesce(d.body->'rows', '[]'::jsonb)) r(value);

create or replace view ehpa.ar_aging_by_recommendation as
select snapshot, as_of, recommendation, count(*) as visits, round(sum(balance), 2) as balance, round(sum(balance) filter (where days_since_dos > 365), 2) as balance_over_365
from ehpa.ar_aging_rows group by 1, 2, 3;

-- the app's access trail (apps/ehpadb): who asked for what, when, with what result
create table if not exists ops.app_access_log (
  id bigserial primary key, at timestamptz not null default now(), user_email text, user_id text, route text, status integer, ms integer);
create index if not exists app_access_log_at_idx on ops.app_access_log (at desc);

-- ---- what ran, and what was loaded ---------------------------------------------------------------------------------------------------
create or replace view ehpa.routine_runs as
select id, routine, stamp, started_at, finished_at, status, headline, summary, session_url, commit_sha, loaded_by from ops.routine_runs;

-- A/R convenience: paid vs denied per ERA line, with the CARC family
create or replace view ehpa.era_line_outcomes as
select run_stamp, run_at, check_id, chart_id, visit_id, cpt, dos, paid, claim_status, outcome, carcs,
       case when paid > 0 then 'paid' when outcome ilike '%posted%' and coalesce(array_length(carcs, 1), 0) > 0 then 'adjusted_or_denied' else coalesce(outcome, 'unknown') end as kind,
       date_trunc('month', run_at)::date as run_month,
       case when dos is not null then (run_at::date - dos) end as days_dos_to_remit
from ehpa.era_lines;

grant usage on schema ehpa to ehpa_routine;
grant select on all tables in schema ehpa to ehpa_routine;
