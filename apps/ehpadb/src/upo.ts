// PLAIN ENGLISH: the Universal Practice Optimization routes of the ehpa app. Everything here sits behind the same gate as the
// dashboard (/api/* needs a verified Neon Auth JWT for an allowed email - see index.ts) and reads the `upo` schema that
// optimization/db/upo_schema.sql builds and optimization/tools/upo_load.py fills from the seed files.
//   GET  /api/upo/universal            the framework for any practice: domains, categories, metrics, sources
//   GET  /api/upo/library              the purchased vendor library: one row per document, plus every fact-checked claim
//   GET  /api/upo/learn                the learning modules
//   GET  /api/upo/practice/:code       one practice's application: standing per category, metric values, risk findings,
//                                      recommendations, projects, the work list and the valuation
//   POST /api/upo/practice/:code/worklist/:id   {status, note} - the ONLY write: the owner moves a work-list row along
// The practice tables hold aggregates only (dollars, counts, rates) - never a patient name, date of birth or member id.
import type { Hono } from "hono";
import type { Pool } from "pg";

const PRACTICE_RE = /^[a-z0-9]{2,20}$/;
const ITEM_RE = /^[A-Za-z0-9][A-Za-z0-9._:-]{0,79}$/;
const STATUSES = new Set(["open", "doing", "waiting", "done", "dropped"]);

// one statement -> one JSON array (never null)
const arr = (inner: string) => `coalesce((select json_agg(t) from (${inner}) t), '[]'::json)`;

const UNIVERSAL_SQL = `select json_build_object(
  'domains', ${arr(`select d.slug, d.ord, d.name, d.summary, d.why_it_matters, d.owner_role, d.frameworks from upo.domains d order by d.ord`)},
  'categories', ${arr(`select c.slug, c.domain_slug, c.ord, c.name, c.summary, c.good_looks_like, c.failure_modes, c.key_questions, c.actions, c.applies_when, c.vendor_refs, c.sources, c.evidence_note
                       from upo.categories c join upo.domains d on d.slug = c.domain_slug order by d.ord, c.ord`)},
  'metrics', ${arr(`select m.slug, m.category_slug, m.ord, m.name, m.definition, m.formula, m.unit, m.direction, m.cadence, m.benchmark_best, m.benchmark_typical, m.benchmark_red, m.benchmark_note,
                           m.confidence, m.sources, m.data_hint, m.vendor_claim, m.vendor_verdict
                    from upo.metrics m join upo.categories c on c.slug = m.category_slug join upo.domains d on d.slug = c.domain_slug order by d.ord, c.ord, m.ord`)},
  'sources', ${arr(`select slug, title, publisher, year, url, kind, note from upo.sources order by publisher nulls last, title`)},
  'meta', coalesce((select json_object_agg(key, value) from upo.meta), '{}'::json)
) as doc`;

const LIBRARY_SQL = `select json_build_object(
  'items', ${arr(`select slug, vendor, bundle, title, doc_type, pages, words, list_price_usd, quality_score, specificity_score, practice_relevance_score, summary, top_ideas, red_flags, domains,
                         claims_checked, claims_supported, claims_partly, claims_contradicted, claims_outdated, claims_unverifiable, verdict
                  from upo.vendor_items order by bundle, title`)},
  'claims', ${arr(`select id, item_slug, claim, kind, stakes, verdict, correct_statement, source_title, source_url, confidence, practice_impact from upo.vendor_claims order by item_slug, id`)},
  'meta', coalesce((select json_object_agg(key, value) from upo.meta where key like 'library%'), '{}'::json)
) as doc`;

const LEARN_SQL = `select json_build_object(
  'modules', ${arr(`select slug, ord, title, audience, summary, minutes, body, artifact_url from upo.learning_modules order by ord`)}
) as doc`;

const PRACTICE_SQL = `select json_build_object(
  'practice', (select row_to_json(p) from (select code, name, specialty, setting, profile, updated_at from upo.practices where code = $1) p),
  'categories', ${arr(`select pc.category_slug, c.name as category, c.domain_slug, d.name as domain, d.ord as domain_ord, c.ord as category_ord, pc.applicability, pc.status, pc.priority, pc.assessment, pc.evidence, pc.next_step
                       from upo.practice_categories pc join upo.categories c on c.slug = pc.category_slug join upo.domains d on d.slug = c.domain_slug
                       where pc.practice = $1 order by d.ord, c.ord`)},
  'metrics', ${arr(`select pm.metric_slug, m.name, m.category_slug, c.name as category, c.domain_slug, m.unit, m.direction, m.definition, m.formula, m.benchmark_best, m.benchmark_typical, m.benchmark_red, m.benchmark_note,
                           pm.as_of, pm.value, pm.value_text, pm.status, pm.basis, pm.note, pm.source
                    from upo.practice_metrics pm join upo.metrics m on m.slug = pm.metric_slug join upo.categories c on c.slug = m.category_slug join upo.domains d on d.slug = c.domain_slug
                    where pm.practice = $1 and pm.as_of = (select max(x.as_of) from upo.practice_metrics x where x.practice = pm.practice and x.metric_slug = pm.metric_slug)
                    order by d.ord, c.ord, m.ord`)},
  'risks', ${arr(`select r.id, r.ord, r.title, r.severity, r.likelihood, r.category_slug, c.name as category, r.what_we_see, r.rule, r.exposure, r.recommended_review, r.control, r.sources, r.status
                  from upo.risk_findings r left join upo.categories c on c.slug = r.category_slug where r.practice = $1 order by r.ord`)},
  'recommendations', ${arr(`select r.id, r.ord, r.kind, r.category_slug, c.name as category, r.title, r.why, r.what, r.impact_low, r.impact_high, r.impact_basis, r.effort, r.horizon, r.owner, r.project_slug, r.confidence
                            from upo.recommendations r left join upo.categories c on c.slug = r.category_slug where r.practice = $1 order by r.ord`)},
  'projects', ${arr(`select p.slug, p.ord, p.title, p.objective, p.category_slug, p.priority, p.status, p.impact_low, p.impact_high, p.impact_note, p.owner, p.start_by, p.target_date, p.success_measures, p.steps,
                            (select count(*) from upo.worklist_items w where w.practice = p.practice and w.project_slug = p.slug) as items,
                            (select count(*) from upo.worklist_items w where w.practice = p.practice and w.project_slug = p.slug and w.status = 'done') as items_done
                     from upo.projects p where p.practice = $1 order by p.ord`)},
  'worklist', ${arr(`select w.id, w.project_slug, w.ord, w.title, w.detail, w.owner, w.due, w.status, w.note, w.updated_at, w.updated_by from upo.worklist_items w where w.practice = $1 order by w.ord`)},
  'valuations', ${arr(`select v.as_of, v.method, v.low, v.base, v.high, v.inputs, v.bridge, v.notes from upo.valuations v
                       where v.practice = $1 and v.as_of = (select max(as_of) from upo.valuations where practice = $1) order by (v.method = 'summary') desc, v.method`)},
  'meta', coalesce((select json_object_agg(key, value) from upo.meta where key like 'practice:' || $1 || ':%'), '{}'::json)
) as doc`;

// the hub's one-line counts: small enough to ask for on every visit to the home page
const SUMMARY_SQL = `select json_build_object(
  'universal', json_build_object('domains', (select count(*) from upo.domains), 'categories', (select count(*) from upo.categories), 'metrics', (select count(*) from upo.metrics), 'sources', (select count(*) from upo.sources)),
  'library', json_build_object('items', (select count(*) from upo.vendor_items), 'claims', (select count(*) from upo.vendor_claims)),
  'learn', json_build_object('modules', (select count(*) from upo.learning_modules)),
  'practice', (select json_build_object('code', p.code, 'name', p.name,
      'areas_red', (select count(*) from upo.practice_categories where practice = p.code and status = 'red' and applicability <> 'not_applicable'),
      'areas_amber', (select count(*) from upo.practice_categories where practice = p.code and status = 'amber' and applicability <> 'not_applicable'),
      'areas_green', (select count(*) from upo.practice_categories where practice = p.code and status = 'green' and applicability <> 'not_applicable'),
      'risks_high', (select count(*) from upo.risk_findings where practice = p.code and severity in ('critical', 'high')),
      'work_open', (select count(*) from upo.worklist_items where practice = p.code and status not in ('done', 'dropped')),
      'projects_now', (select count(*) from upo.projects where practice = p.code and priority = 'now'),
      'value_low', v.low, 'value_base', v.base, 'value_high', v.high)
    from upo.practices p left join lateral (select low, base, high from upo.valuations where practice = p.code and method = 'summary' order by as_of desc limit 1) v on true
    where p.code = $1),
  'database', (select json_build_object('last_run_at', at, 'outstanding_total', outstanding_total) from ehpa.billing_runs where outstanding_total is not null order by at desc limit 1)
) as doc`;

type AppVars = { Variables: { user: { id: string; email: string } } };

export function registerUpo(app: Hono<AppVars>, pool: Pool, defaultPractice: string) {
  const one = async (sql: string, params: unknown[] = []) => (await pool.query(sql, params)).rows[0]?.doc ?? null;
  const fail = (c: any, what: string, e: any) => { console.error(what, e?.message); return c.json({ error: "the database answered with an error for " + what }, 500); };

  app.get("/api/upo/summary", async (c) => {
    const code = c.req.query("practice") || defaultPractice;
    if (!PRACTICE_RE.test(code)) return c.json({ error: "no such practice" }, 404);
    try { return c.json(await one(SUMMARY_SQL, [code])); } catch (e) { return fail(c, "the summary", e); }
  });

  app.get("/api/upo/universal", async (c) => { try { return c.json(await one(UNIVERSAL_SQL)); } catch (e) { return fail(c, "the universal framework", e); } });
  app.get("/api/upo/library", async (c) => { try { return c.json(await one(LIBRARY_SQL)); } catch (e) { return fail(c, "the library", e); } });
  app.get("/api/upo/learn", async (c) => { try { return c.json(await one(LEARN_SQL)); } catch (e) { return fail(c, "the learning modules", e); } });

  app.get("/api/upo/practice/:code", async (c) => {
    const code = c.req.param("code");
    if (!PRACTICE_RE.test(code)) return c.json({ error: "no such practice" }, 404);
    try {
      const doc = await one(PRACTICE_SQL, [code]);
      if (!doc || !doc.practice) return c.json({ error: "no such practice" }, 404);
      return c.json(doc);
    } catch (e) { return fail(c, "the practice", e); }
  });

  // the one write: the signed-in owner changes a work-list row's status and/or note
  app.post("/api/upo/practice/:code/worklist/:id", async (c) => {
    const code = c.req.param("code"), id = c.req.param("id");
    if (!PRACTICE_RE.test(code) || !ITEM_RE.test(id)) return c.json({ error: "no such work-list item" }, 404);
    let body: any;
    try { body = await c.req.json(); } catch { return c.json({ error: "send JSON: {status, note}" }, 400); }
    if (!body || typeof body !== "object" || Array.isArray(body)) return c.json({ error: "send JSON: {status, note}" }, 400);
    const status = body.status === undefined ? null : String(body.status);
    const note = body.note === undefined ? null : String(body.note);
    if (status === null && note === null) return c.json({ error: "nothing to change" }, 400);
    if (status !== null && !STATUSES.has(status)) return c.json({ error: "status must be one of open, doing, waiting, done, dropped" }, 400);
    if (note !== null && note.length > 2000) return c.json({ error: "the note is longer than 2,000 characters" }, 400);
    try {
      const r = await pool.query(
        `update upo.worklist_items set status = coalesce($3, status), note = coalesce($4, note), updated_at = now(), updated_by = $5
         where practice = $1 and id = $2 returning id, status, note, updated_at, updated_by`,
        [code, id, status, note, c.get("user").email]);
      if (!r.rows.length) return c.json({ error: "no such work-list item" }, 404);
      return c.json(r.rows[0]);
    } catch (e) { return fail(c, "the work list", e); }
  });
}
