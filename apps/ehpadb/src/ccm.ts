// PLAIN ENGLISH: the CCM section of the site - the notes of the CCM Documentation Hub (https://claude.ai/artifact/GSd9jcvXoBmxc9NkX2mWmR),
// read from the ccm.* views tools/db/ccm_schema.sql builds in the practice's Neon database (ccm.notes with each note's status,
// ccm.signed_notes, ccm.patients, ccm.months for a note's text). READ-ONLY: every statement is a SELECT, and signing stays on the
// hub page (scripts/helpers/ccm_build.py verifies and records each signing; a signed note is final in the database).
//   GET /api/ccm/summary           counts by status, overall and per month, and when the notes were last built and signed
//   GET /api/ccm/month/:YYYY-MM    that month's notes: patient, birth date, chart, codes, location, status, who signed and when
//   GET /api/ccm/note/:id          one note (<chart>_<YYYY-MM>): its fields as drafted and, once signed, as signed
//   GET /api/ccm/patients          one row per patient: name, birth date, sex, chart, months of CCM and their states
//   GET /api/ccm/patient/:chart    one patient and every month of CCM on the chart
//   GET /api/ccm/signed            the newest 300 signings
// PATIENT DATA: these answers carry names and birth dates (the hub shows the same). They exist ONLY behind the gate in index.ts -
// a verified Neon Auth session whose email is on ALLOWED_EMAILS and confirmed - and every request is written to
// ops.app_access_log with its route (which names the chart or note asked for). Nothing of a patient is in this file, in the page
// "/" or in /app.js; responses are never cached (Cache-Control: no-store on everything).
import type { Hono } from "hono";
import type { Pool } from "pg";
import { CCM_HUB, CCM_HUB_BUILD } from "./links";

type AppVars = { Variables: { user: { id: string; email: string } } };

const MONTH_RE = /^\d{4}-(0[1-9]|1[0-2])$/;
const CHART_RE = /^[A-Za-z0-9.-]{1,40}$/;
const NOTE_RE = /^[A-Za-z0-9.-]{1,40}_\d{4}-(0[1-9]|1[0-2])$/;

const COUNTS = `count(*) as notes, count(*) filter (where status = 'ready to sign') as ready, count(*) filter (where status = 'flagged') as flagged,
  count(*) filter (where status = 'no name yet') as noname, count(*) filter (where status = 'signed') as signed`;
const arr = (inner: string, order: string) => `coalesce((select json_agg(t order by ${order}) from (${inner}) t), '[]'::json)`;
const one = (inner: string) => `(select row_to_json(t) from (${inner}) t)`;

const SUMMARY_SQL = `select json_build_object(
  'totals', ${one(`select ${COUNTS}, count(distinct chart_id) as patients, count(distinct month) as months from ccm.notes`)},
  'months', ${arr(`select to_char(month, 'YYYY-MM') as month, ${COUNTS} from ccm.notes group by month`, "t.month desc")},
  'built_at', (select max(built_at) from ccm.months),
  'last_signed_at', (select max(signed_at) from ccm.signed_notes),
  'last_recorded_at', (select max(recorded_at) from ccm.signed_notes),
  'evidence', (select count(*) from ccm.evidence),
  'faxes', (select count(*) from ccm.faxes)
) as doc`;

const MONTH_SQL = `select ${arr(`select n.note_id, n.chart_id, n.patient_name, to_char(n.birth_date, 'MM/DD/YYYY') as birth_date, n.codes, n.minutes, n.flag, n.insurance, n.status,
         to_char(n.written_on, 'MM/DD/YYYY') as written_on, n.signed_by, n.signed_at, m.fields->>'location' as location, m.fields->>'provider' as provider
  from ccm.notes n left join ccm.months m on m.note_id = n.note_id where n.month = to_date($1, 'YYYY-MM')`, "t.patient_name nulls last, t.chart_id")} as doc`;

const NOTE_SQL = `select json_build_object(
  'note', ${one(`select note_id, chart_id, to_char(month, 'YYYY-MM') as month, patient_name, to_char(birth_date, 'MM/DD/YYYY') as birth_date, codes, minutes, flag, insurance,
                        status, to_char(written_on, 'MM/DD/YYYY') as written_on, signed_by, signed_at, sha from ccm.notes where note_id = $1`)},
  'draft', ${one(`select fields, statement, built_at, fields_sha from ccm.months where note_id = $1`)},
  'signed', ${one(`select fields, signed_by, signed_at, to_char(written_on, 'MM/DD/YYYY') as written_on, sha, signed_via as via, recorded_at from ccm.signed_notes where note_id = $1`)}
) as doc`;

const PATIENTS_SQL = `select ${arr(`select ch.chart_id, p.name, to_char(p.birth_date, 'MM/DD/YYYY') as birth_date, p.sex, count(n.note_id) as months,
         count(n.note_id) filter (where n.status = 'signed') as signed, count(n.note_id) filter (where n.status = 'ready to sign') as ready,
         count(n.note_id) filter (where n.status = 'flagged') as flagged, count(n.note_id) filter (where n.status = 'no name yet') as noname,
         to_char(min(n.month), 'YYYY-MM') as first_month, to_char(max(n.month), 'YYYY-MM') as last_month
  from (select chart_id from ccm.patients union select chart_id from ccm.notes) ch
  left join ccm.patients p on p.chart_id = ch.chart_id left join ccm.notes n on n.chart_id = ch.chart_id
  group by ch.chart_id, p.name, p.birth_date, p.sex`, "t.name nulls last, t.chart_id")} as doc`;

const PATIENT_SQL = `select json_build_object(
  'patient', ${one(`select chart_id, name, to_char(birth_date, 'MM/DD/YYYY') as birth_date, sex, read_at from ccm.patients where chart_id = $1`)},
  'notes', ${arr(`select n.note_id, to_char(n.month, 'YYYY-MM') as month, n.codes, n.minutes, n.flag, n.insurance, n.status, to_char(n.written_on, 'MM/DD/YYYY') as written_on,
                         n.signed_by, n.signed_at, m.fields->>'location' as location
                  from ccm.notes n left join ccm.months m on m.note_id = n.note_id where n.chart_id = $1`, "t.month desc")}
) as doc`;

const SIGNED_SQL = `select ${arr(`select s.note_id, s.chart_id, p.name as patient_name, to_char(s.month, 'YYYY-MM') as month, to_char(s.written_on, 'MM/DD/YYYY') as written_on,
         s.signed_by, s.signed_at, s.signed_via as via, s.recorded_at
  from ccm.signed_notes s left join ccm.patients p on p.chart_id = s.chart_id order by s.signed_at desc nulls last, s.note_id limit 300`, "t.signed_at desc nulls last, t.note_id")} as doc`;

export function registerCcm(app: Hono<AppVars>, pool: Pool) {
  const q = async (sql: string, params: unknown[] = []) => (await pool.query(sql, params)).rows[0]?.doc ?? null;
  const fail = (c: any, what: string, e: any) => { console.error(what, e?.message); return c.json({ error: "the database answered with an error for " + what }, 500); };
  const links = { hub: CCM_HUB, build: CCM_HUB_BUILD };

  app.get("/api/ccm/summary", async (c) => {
    try { return c.json({ ...(await q(SUMMARY_SQL)), ...links }); } catch (e) { return fail(c, "the CCM summary", e); }
  });
  app.get("/api/ccm/month/:month", async (c) => {
    const month = c.req.param("month");
    if (!MONTH_RE.test(month)) return c.json({ error: "no such month" }, 404);
    try { return c.json({ month, notes: await q(MONTH_SQL, [month]), ...links }); } catch (e) { return fail(c, "the month's notes", e); }
  });
  app.get("/api/ccm/note/:id", async (c) => {
    const id = c.req.param("id");
    if (!NOTE_RE.test(id)) return c.json({ error: "no such note" }, 404);
    try {
      const doc = await q(NOTE_SQL, [id]);
      if (!doc || !doc.note) return c.json({ error: "no such note" }, 404);
      return c.json({ ...doc, ...links });
    } catch (e) { return fail(c, "the note", e); }
  });
  app.get("/api/ccm/patients", async (c) => {
    try { return c.json({ patients: await q(PATIENTS_SQL), ...links }); } catch (e) { return fail(c, "the patients", e); }
  });
  app.get("/api/ccm/patient/:chart", async (c) => {
    const chart = c.req.param("chart");
    if (!CHART_RE.test(chart)) return c.json({ error: "no such patient" }, 404);
    try {
      const doc = await q(PATIENT_SQL, [chart]);
      if (!doc || (!doc.patient && !(doc.notes || []).length)) return c.json({ error: "no such patient" }, 404);
      return c.json({ ...doc, chart, ...links });
    } catch (e) { return fail(c, "the patient", e); }
  });
  app.get("/api/ccm/signed", async (c) => {
    try { return c.json({ signed: await q(SIGNED_SQL), ...links }); } catch (e) { return fail(c, "the signings", e); }
  });
}
