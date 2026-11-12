// PLAIN ENGLISH: the Practice Database page (tools/db/practice_db_page.html, https://claude.ai/artifact/QrLJpUcpFv3cFRB9xHfLyk)
// mirrored on this site. That page reads its own claude.ai database; these routes read the same documents from Neon - the
// ehpa.* views tools/db/neon_schema.sql builds over raw.documents (source practice_db) and the ops.* tables - so the views the
// page has (Overview, Census inputs, Billing runs, ERA, Approvals, Raw data, Mirror & sources) can be drawn here.
//   GET /api/pdb/overview                      the figures behind the Overview tiles and its "Is it working?" checks, the page links
//   GET /api/pdb/feed?from=YYYY-MM-DD&to=...   Census inputs: the feed charges of the window (by date of service, or by the day
//                                              they were pulled into AdvancedMD), the merged lookups, files, checks, cascade
//                                              nights, holds and the last 15 days of runs; no from/to = everything on hand
//   GET /api/pdb/runs        GET /api/pdb/run/:stamp       Billing runs, and one run's steps, waiting list and errors
//   GET /api/pdb/era         GET /api/pdb/era/:stamp       ERA posting runs, and one run's posted lines and audit flags
//   GET /api/pdb/approvals                     the approval packages of the newest snapshot
//   GET /api/pdb/mirror                        where each copy lives, the copies of the other pages, routines, master data
//   GET /api/pdb/data  /data/:collection  /doc/:collection/:id   the practice database's own documents, as stored
// Every route sits behind the gate in index.ts (/api/*: a verified Neon Auth session, an allowed and confirmed email; each
// request written to ops.app_access_log). Read-only: every statement here is a SELECT. Chart ids, dates of service, codes and
// dollars only - no route selects a patient name, birth date or member id, and the copies of the other boards
// (artifact_copies, which can carry names) are left out of Raw data.
import type { Hono } from "hono";
import type { Pool } from "pg";
import { PULLED_DAY } from "./views";
import { SAFE_NUM, NEWEST_APPROVALS, dbFail } from "./sql";
import { PAGES, MIRROR_LINKS, ROUTINES, routineUrl, githubFile, APPROVALS_PAGE, PRACTICE_DB_PAGE } from "./links";

type AppVars = { Variables: { user: { id: string; email: string } } };

// a run made by the GitHub Actions billing engine carries its Actions run as run_url; anything else is a Claude run (the page's rule)
const ENGINE = `(coalesce(run_url, '') ~ 'github\\.com/[^ ]*/actions/')`;
const NOT_ENTERED = `('dx', 'deceased', 'cpt', 'skipped', 'failed', 'nochart')`;
const arr = (inner: string) => `coalesce((select json_agg(t) from (${inner}) t), '[]'::json)`;
const one = (inner: string) => `(select row_to_json(t) from (${inner}) t)`;

const DAY_RE = /^\d{4}-\d{2}-\d{2}$/;
const STAMP_RE = /^[A-Za-z0-9._:+-]{1,100}$/;
const DOC_RE = /^[A-Za-z0-9._:@+-]{1,160}$/;

// the practice database's own collections (the page's Raw data list) - artifact_copies (copies of other boards) is left out
export const RAW_COLLECTIONS: [string, string][] = [
  ["feed_batches", "one Claimocity ingest batch: every feed message and its AdvancedMD outcome"],
  ["feed_checks", "one line per feed run - what the bucket held and when it was checked"],
  ["billing_runs", "one Billing Button / scheduled billing run"],
  ["era_runs", "one run's ERA posting work"],
  ["snapshots", "approvals, repo head and other point-in-time copies"],
  ["practice", "master data: carriers, facilities, practice"],
  ["artifact_index", "one line per copied page: its collections and counts"],
  ["sync_runs", "one line per practice database sync: boards checked, collections copied or unchanged"],
  ["cascade_runs", "one nightly insurance cascade run: pairs checked, visits changed, dollars re-sent, what was done"],
];
const RAW_NAMES = new Set(RAW_COLLECTIONS.map(([c]) => c));

const OVERVIEW_SQL = `select json_build_object(
  'docs', coalesce((select json_object_agg(collection, n) from (select collection, count(*) as n from raw.documents where source = 'practice_db' group by collection) x), '{}'::json),
  'neon', json_build_object('documents', (select count(*) from raw.documents), 'sources', (select count(distinct source) from raw.documents), 'last_load', (select max(at) from ops.load_log)),
  'feed', (select json_build_object('rows', count(*), 'entered', count(*) filter (where status = 'entered'), 'not_entered', count(*) filter (where status in ${NOT_ENTERED}),
                                    'entered_dollars', coalesce(sum(fee) filter (where status = 'entered'), 0)) from ehpa.feed_charges),
  'batches', (select json_build_object('n', count(*), 'incomplete', coalesce(json_agg(stamp) filter (where messages is not null and messages <> rows), '[]'::json))
              from (select b.stamp, nullif(regexp_replace(coalesce(b.counts->>'messages', ''), '[^0-9]', '', 'g'), '')::int as messages,
                           (select count(*) from ehpa.feed_charges c where regexp_replace(c.batch_stamp, '\\.p[0-9]+$', '') = b.stamp) as rows
                    from ehpa.feed_batches b) x),
  'last_check', ${one(`select stamp, at, result, newest_file, line from ehpa.feed_checks order by at desc nulls last limit 1`)},
  'last_run', ${one(`select stamp, at, mode, status, headline from ehpa.billing_runs order by at desc nulls last limit 1`)},
  'last_engine', ${one(`select stamp, at, note from ehpa.billing_runs where ${ENGINE} order by at desc nulls last limit 1`)},
  'last_era', ${one(`select stamp, at, line_count, paid_total from ehpa.era_runs where coalesce(line_count, 0) > 0 and not coalesce(dry, false) order by at desc nulls last limit 1`)},
  'approvals', ${one(`select at, counts, dollars_waiting from ehpa.approval_snapshots order by at desc nulls last limit 1`)},
  'repo', ${one(`select body->>'head' as head, body->>'last_commit' as last_commit, body->'counts' as counts, body->>'at' as at from raw.documents
                 where source = 'practice_db' and collection = 'snapshots' and body->>'kind' = 'repo' order by body->>'at' desc nulls last limit 1`)},
  'cascade', ${one(`select night, at, checked, changed, dollars_resent from ehpa.cascade_nights where at is not null order by at desc limit 1`)},
  'copies', json_build_object('pages', (select count(distinct body->>'slug') from raw.documents where source = 'practice_db' and collection = 'artifact_index'),
                              'last_sync', ${one(`select body->>'at' as at, body->'boards_checked' as boards_checked, body->'collections_changed' as collections_changed,
                                                         body->'collections_unchanged' as collections_unchanged
                                                  from raw.documents where source = 'practice_db' and collection = 'sync_runs' order by body->>'at' desc nulls last limit 1`)})
) as doc`;

// the feed charges with the day each was pulled into AdvancedMD (Eastern time)
const CHARGES = `select f.batch_stamp, f.batch_at, f.row_no, f.chart_id, f.visit_id, f.dos, f.cpts, f.dx, f.facility_id, f.pos, f.lead_carrier, f.clinician, f.fee,
                        f.status, f.hold, f.why, f.verdict, f.newchart, f.feed_file, ${PULLED_DAY} as pd
                 from ehpa.feed_charges f`;
const LOOKUP = (k: string) => `coalesce((select json_object_agg(key, value) from (select distinct on (e.key) e.key, e.value from ehpa.feed_batches b
   cross join lateral jsonb_each(case when jsonb_typeof(b.lookups->'${k}') = 'object' then b.lookups->'${k}' else '{}'::jsonb end) e order by e.key, b.at desc nulls last) x), '{}'::json)`;
export const FEED_COLUMNS = ["batch", "bat", "p", "v", "d", "c", "dx", "fac", "pos", "lead", "prov", "fee", "s", "hold", "why", "verdict", "newchart", "file", "pd"];
const FEED_SQL = `with c as (${CHARGES}), w as (
    select * from c where $1::date is null or (dos between $1::date and $2::date) or (pd between $1::date and $2::date)
    order by dos desc nulls last, batch_stamp, row_no limit 20001)
select json_build_object(
  'columns', '${JSON.stringify(FEED_COLUMNS)}'::json,
  'rows', coalesce((select json_agg(json_build_array(batch_stamp, batch_at, chart_id, visit_id, dos, cpts, dx, facility_id, pos, lead_carrier, clinician, fee, status, hold, why, verdict, newchart, feed_file, pd)
                                    order by dos desc nulls last, batch_stamp, row_no) from (select * from w limit 20000) x), '[]'::json),
  'truncated', (select count(*) > 20000 from w),
  'on_hand', (select json_build_object('rows', count(*), 'dos_min', min(dos), 'dos_max', max(dos), 'pulled_min', min(pd), 'pulled_max', max(pd)) from c),
  'batches', (select count(*) from ehpa.feed_batches),
  'lookups', json_build_object('fac', ${LOOKUP("fac")}, 'car', ${LOOKUP("car")}, 'prov', ${LOOKUP("prov")}),
  'files', ${arr(`select b.stamp, f.value->>'date' as date, f.value->>'messages' as messages, f.value->>'name' as name
                  from ehpa.feed_batches b cross join lateral jsonb_array_elements(case when jsonb_typeof(b.files) = 'array' then b.files else '[]'::jsonb end) f
                  order by f.value->>'date' nulls last, b.stamp`)},
  'holds', ${arr(`select chart_id, hold, dos from (select distinct on (chart_id) chart_id, hold, dos from ehpa.feed_charges
                  where status = 'entered' and coalesce(hold, '') <> '' order by chart_id, dos desc nulls last) h order by dos desc nulls last, chart_id`)},
  'checks', ${arr(`select stamp, at, result, line, files_new, newest_file, visits, dollars from ehpa.feed_checks order by at desc nulls last limit 80`)},
  'cascade', ${arr(`select night, at, checked, changed, dollars_resent as dollars, done, note from ehpa.cascade_nights where at is not null order by at desc limit 400`)},
  'days', ${arr(`select day, sum(engine) as engine, sum(eng_cascade) as eng_cascade, sum(claude) as claude, max(last_at) as last_at,
                        sum(feed) as feed, sum(ingested) as ingested, sum(visits) as visits, sum(era_lines) as era_lines, sum(era_paid) as era_paid
                 from (select (at at time zone 'America/New_York')::date as day, count(*) filter (where ${ENGINE}) as engine,
                              count(*) filter (where ${ENGINE} and coalesce(note, '') ~ 'cascade') as eng_cascade, count(*) filter (where not ${ENGINE}) as claude, max(at) as last_at,
                              0 as feed, 0 as ingested, 0 as visits, 0 as era_lines, 0::numeric as era_paid
                       from ehpa.billing_runs where at >= now() - interval '16 days' group by 1
                       union all
                       select (at at time zone 'America/New_York')::date, 0, 0, 0, null::timestamptz, count(*), count(*) filter (where result = 'ingested'),
                              coalesce(sum(visits) filter (where result = 'ingested'), 0), 0, 0
                       from ehpa.feed_checks where at >= now() - interval '16 days' group by 1
                       union all
                       select (at at time zone 'America/New_York')::date, 0, 0, 0, null::timestamptz, 0, 0, 0, coalesce(sum(line_count), 0), coalesce(sum(paid_total), 0)
                       from ehpa.era_runs where at >= now() - interval '16 days' and not coalesce(dry, false) group by 1) u
                 group by day order by day desc`)}
) as doc`;

const RUNS_SQL = `select json_build_object(
  'totals', (select json_build_object('runs', count(*), 'live', count(*) filter (where mode = 'live'), 'failed', count(*) filter (where status ~* 'fail|error|refused'),
                                      'packages', coalesce(sum(packages), 0), 'engine', count(*) filter (where ${ENGINE})) from ehpa.billing_runs),
  'runs', ${arr(`select stamp, at, mode, status, headline, note, ${ENGINE} as engine, columns, era, packages, waiting, errors, steps
                 from ehpa.billing_runs order by at desc nulls last limit 300`)}
) as doc`;

const RUN_SQL = `select json_build_object('stamp', d.doc_id, 'at', d.body->>'at', 'run_url', d.body->>'run_url', 'source', d.body->>'source',
  'steps', ${arr(`select step_no, name, title, status, summary, errors from ehpa.billing_run_steps where stamp = $1 order by step_no`)},
  'waiting', case when jsonb_typeof(d.body->'waiting') = 'array' then d.body->'waiting' else '[]'::jsonb end,
  'errors', case when jsonb_typeof(d.body->'errors') = 'array' then d.body->'errors' else '[]'::jsonb end) as doc
from raw.documents d where d.source = 'practice_db' and d.collection = 'billing_runs' and d.doc_id = $1`;

const POSTED = `coalesce(line_count, 0) > 0 and not coalesce(dry, false)`;
const ERA_SQL = `select json_build_object(
  'totals', (select json_build_object('runs', count(*), 'lines', coalesce(sum(line_count) filter (where ${POSTED}), 0), 'paid', coalesce(sum(paid_total) filter (where ${POSTED}), 0)) from ehpa.era_runs),
  'last_posting', ${one(`select stamp, at, line_count, paid_total from ehpa.era_runs where ${POSTED} order by at desc nulls last limit 1`)},
  'unposted_now', ${one(`select stamp, at, checks_after, checks_after_total from ehpa.era_runs where checks_after is not null order by at desc nulls last limit 1`)},
  'runs', ${arr(`select stamp, at, dry, checks_before, checks_before_total, checks_after, checks_after_total, line_count, paid_total, outcomes, audit_flags
                 from ehpa.era_runs order by at desc nulls last limit 120`)}
) as doc`;

const ERA_RUN_SQL = `select json_build_object(
  'lines', ${arr(`select line_no, check_id, chart_id, visit_id, cpt, dos, paid, claim_status, carcs, outcome from ehpa.era_lines where run_stamp = $1 order by line_no limit 120`)},
  'total', (select count(*) from ehpa.era_lines where run_stamp = $1),
  'flags', (select case when jsonb_typeof(d.body->'audit'->'flags') = 'array' then d.body->'audit'->'flags' else '[]'::jsonb end
            from raw.documents d where d.source = 'practice_db' and d.collection = 'era_runs' and d.doc_id = $1)
) as doc`;

// The packages of the newest approvals snapshot, read from the document itself: ehpa.approvals casts each package's dollars text
// to a number and fails when a package names several amounts ("$52.80 ... -$17.50 ..."), so the amount is a number here only when
// the text is one number (SAFE_NUM), and the text itself is kept beside it (dollars_text). Same snapshot rule as the view.
const APPROVALS_SQL = `with snap as ${NEWEST_APPROVALS}
select json_build_object(
  'snapshot', ${one(`select s.doc_id, s.at, s.counts, s.dollars_waiting, s.packages from ehpa.approval_snapshots s join snap on snap.doc_id = s.doc_id`)},
  'rows', ${arr(`select r.value->>'id' as package_id, r.value->>'stamp' as stamp, r.value->>'at' as at, r.value->>'what' as what, r.value->>'ui' as ui,
                        ${SAFE_NUM("r.value->>'dollars'")} as dollars, r.value->>'dollars' as dollars_text, r.value->>'status' as status, r.value->>'answer' as answer, r.value->>'reason' as reason
                 from snap cross join lateral jsonb_array_elements(case when jsonb_typeof(snap.body->'rows') = 'array' then snap.body->'rows' else '[]'::jsonb end) r(value)
                 order by r.value->>'at' desc nulls last, r.value->>'id'`)}
) as doc`;

const MIRROR_SQL = `select json_build_object(
  'copies', ${arr(`select * from (select distinct on (body->>'slug') body->>'slug' as slug, body->>'title' as title, body->>'url' as url, body->>'at' as at, body->'collections' as collections
                   from raw.documents where source = 'practice_db' and collection = 'artifact_index' order by body->>'slug', body->>'at' desc nulls last) x order by title`)},
  'last_sync', ${one(`select body->>'at' as at, body->'boards_checked' as boards_checked, body->'collections_changed' as collections_changed, body->'collections_unchanged' as collections_unchanged
                      from raw.documents where source = 'practice_db' and collection = 'sync_runs' order by body->>'at' desc nulls last limit 1`)},
  'repo', ${one(`select body->>'repo' as repo, body->>'head' as head, body->>'last_commit' as last_commit, body->'counts' as counts, body->>'at' as at
                 from raw.documents where source = 'practice_db' and collection = 'snapshots' and body->>'kind' = 'repo' order by body->>'at' desc nulls last limit 1`)},
  'practice', ${arr(`select name, case jsonb_typeof(data) when 'array' then jsonb_array_length(data) when 'object' then (select count(*) from jsonb_object_keys(data)) end as entries, source, loaded_at
                     from ehpa.practice_master order by name`)}
) as doc`;

const DATA_SQL = `select coalesce(json_object_agg(collection, json_build_object('documents', n, 'newest', newest, 'bytes', bytes)), '{}'::json) as doc
from (select collection, count(*) as n, max(written_at) as newest, sum(octet_length(body::text)) as bytes from raw.documents
      where source = 'practice_db' and collection = any($1::text[]) group by collection) x`;
const DATA_LIST_SQL = `select ${arr(`select doc_id, written_at, loaded_at, octet_length(body::text) as bytes, body->>'source' as source from raw.documents
                                   where source = 'practice_db' and collection = $1 order by written_at desc nulls last, doc_id desc limit 500`)} as doc`;
const DATA_DOC_SQL = `select json_build_object('collection', collection, 'doc_id', doc_id, 'written_at', written_at, 'loaded_at', loaded_at, 'sha256', body_sha256, 'body', body) as doc
from raw.documents where source = 'practice_db' and collection = $1 and doc_id = $2`;

export function registerPdb(app: Hono<AppVars>, pool: Pool) {
  const q = async (sql: string, params: unknown[] = []) => (await pool.query(sql, params)).rows[0]?.doc ?? null;
  const fail = dbFail;   // logs the route pattern and SQLSTATE only, never the error's message (sql.ts)

  app.get("/api/pdb/overview", async (c) => {
    try {
      const doc = await q(OVERVIEW_SQL);
      return c.json({ ...doc, pages: PAGES, practice_db_page: PRACTICE_DB_PAGE });
    } catch (e) { return fail(c, "the overview", e); }
  });

  app.get("/api/pdb/feed", async (c) => {
    const from = c.req.query("from") || "", to = c.req.query("to") || "";
    if ((from || to) && !(DAY_RE.test(from) && DAY_RE.test(to) && from <= to)) return c.json({ error: "from and to must be days (YYYY-MM-DD), from first" }, 400);
    try { return c.json({ ...(await q(FEED_SQL, [from || null, to || null])), from: from || null, to: to || null }); }
    catch (e) { return fail(c, "the census inputs", e); }
  });

  app.get("/api/pdb/runs", async (c) => { try { return c.json(await q(RUNS_SQL)); } catch (e) { return fail(c, "the billing runs", e); } });
  app.get("/api/pdb/run/:stamp", async (c) => {
    const stamp = c.req.param("stamp");
    if (!STAMP_RE.test(stamp)) return c.json({ error: "no such run" }, 404);
    try {
      const doc = await q(RUN_SQL, [stamp]);
      if (!doc) return c.json({ error: "no such run" }, 404);
      return c.json({ ...doc, source_url: githubFile(String(doc.source || "")) });
    } catch (e) { return fail(c, "the run", e); }
  });

  app.get("/api/pdb/era", async (c) => { try { return c.json(await q(ERA_SQL)); } catch (e) { return fail(c, "the ERA runs", e); } });
  app.get("/api/pdb/era/:stamp", async (c) => {
    const stamp = c.req.param("stamp");
    if (!STAMP_RE.test(stamp)) return c.json({ error: "no such ERA run" }, 404);
    try { return c.json(await q(ERA_RUN_SQL, [stamp])); } catch (e) { return fail(c, "the ERA run", e); }
  });

  app.get("/api/pdb/approvals", async (c) => {
    try { return c.json({ ...(await q(APPROVALS_SQL)), page: APPROVALS_PAGE }); } catch (e) { return fail(c, "the approvals", e); }
  });

  app.get("/api/pdb/mirror", async (c) => {
    try {
      const doc = await q(MIRROR_SQL);
      return c.json({ ...doc, links: MIRROR_LINKS, routines: ROUTINES.map(([name, ref, what]) => ({ name, ref, what, url: routineUrl(ref) })) });
    } catch (e) { return fail(c, "the mirror", e); }
  });

  app.get("/api/pdb/data", async (c) => {
    try { return c.json({ collections: RAW_COLLECTIONS, counts: await q(DATA_SQL, [[...RAW_NAMES]]) }); } catch (e) { return fail(c, "the collections", e); }
  });
  app.get("/api/pdb/data/:collection", async (c) => {
    const coll = c.req.param("collection");
    if (!RAW_NAMES.has(coll)) return c.json({ error: "no such collection" }, 404);
    try { return c.json({ collection: coll, docs: await q(DATA_LIST_SQL, [coll]) }); } catch (e) { return fail(c, "the collection", e); }
  });
  app.get("/api/pdb/doc/:collection/:id", async (c) => {
    const coll = c.req.param("collection"), id = c.req.param("id");
    if (!RAW_NAMES.has(coll) || !DOC_RE.test(id)) return c.json({ error: "no such document" }, 404);
    try {
      const doc = await q(DATA_DOC_SQL, [coll, id]);
      if (!doc) return c.json({ error: "no such document" }, 404);
      const src = doc.body && typeof doc.body === "object" ? String((doc.body as any).source || "") : "";
      return c.json({ ...doc, source_url: githubFile(src) });
    } catch (e) { return fail(c, "the document", e); }
  });
}
