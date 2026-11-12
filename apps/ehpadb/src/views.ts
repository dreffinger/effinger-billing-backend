// Every view the app shows, as read-only SQL over the ehpa.* views (tools/db/neon_schema.sql) and the ops.* tables (Approvals reads
// its two documents from raw.documents directly - see there why). One view =
// one title, one note, and sections of {heading, columns, rows, kinds}; the browser renders them generically. Chart ids, dates of
// service, codes and dollars only - the queries never select a patient name, date of birth or member id.
import type { Pool } from "pg";
import { SAFE_NUM, NEWEST_APPROVALS } from "./sql";

export type Kind = "text" | "int" | "money" | "when";
export type SectionSpec = { heading: string; note?: string; sql: string; kinds?: Record<string, Kind> };
export type ChartSpec = { id: string; kind: "days" | "pairs"; title: string; note?: string; fill?: string; sql: string };
export type ViewSpec = { title: string; note?: string; sections: SectionSpec[]; charts?: ChartSpec[] };

// the feed's per-day rollups: one row per calendar day with the entered visits, their charge lines, dollars and distinct charts,
// plus the encounters NOT entered (diagnosis, CPT, deceased, skipped, failed, no chart) - the artifact page's day charts, in SQL
const DAY_ROLLUP = (dayExpr: string) => `
  select day::text as date,
         count(*) filter (where status = 'entered') as visits,
         coalesce(sum(coalesce(array_length(cpts, 1), 0)) filter (where status = 'entered'), 0) as lines,
         round(coalesce(sum(fee) filter (where status = 'entered'), 0)) as dollars,
         count(distinct chart_id) filter (where status = 'entered') as patients,
         count(*) filter (where status in ('dx', 'deceased', 'cpt', 'skipped', 'failed', 'nochart')) as notin
  from (select ${dayExpr} as day, status, cpts, fee, chart_id from ehpa.feed_charges) f
  where day is not null group by day order by day`;
// the day (Eastern time) a batch was pulled into AdvancedMD: the batch's recorded time, else its run stamp (20261031T0312Z -> Oct 30
// 11:12 PM ET), else the 10/28 backlog (stamp 1028). pdb.ts uses the same expression for the Census inputs view.
export const PULLED_DAY = `coalesce((batch_at at time zone 'America/New_York')::date,
  case when batch_stamp ~ '^[0-9]{8}T[0-9]{4}Z' then (((substr(batch_stamp, 1, 4) || '-' || substr(batch_stamp, 5, 2) || '-' || substr(batch_stamp, 7, 2) || ' ' || substr(batch_stamp, 10, 2) || ':' || substr(batch_stamp, 12, 2) || ':00+00')::timestamptz) at time zone 'America/New_York')::date
       when batch_stamp ~ '^[0-9]{4}$' then make_date(extract(year from now())::int, substr(batch_stamp, 1, 2)::int, substr(batch_stamp, 3, 2)::int) end)`;

export const VIEWS: Record<string, ViewSpec> = {
  overview: {
    title: "Overview",
    note: "What the database holds and the newest numbers the engine reported.",
    charts: [
      { id: "pulled", kind: "days", fill: "pulled", title: "Encounters by date pulled into AdvancedMD",
        note: "The day each visit came through the Claimocity connection and was entered in AdvancedMD (Eastern time); today's pull sits at the right edge. Amber = not entered.",
        sql: DAY_ROLLUP(PULLED_DAY) },
      { id: "dos", kind: "days", fill: "accent", title: "Encounters by date of service",
        note: "The same visits by the day the patient was seen. Amber = not entered.",
        sql: DAY_ROLLUP("dos") },
      { id: "cascade", kind: "pairs", title: "Nightly insurance cascade: cases checked and changed",
        note: "One pair of bars per night (the run starts at 05:35 UTC, 12:35 AM Eastern in winter). Checked = visit-and-plan pairs the run verified with AdvancedMD or Stedi. Changed = visits it fixed in AdvancedMD (re-pointed, re-routed or re-sent). A grey dash means no run is recorded for that night.",
        sql: `select night::text as date, checked, changed, dollars_resent as dollars, done, at::text as at from ehpa.cascade_nights where night is not null order by night` },
    ],
    sections: [
      { heading: "Latest billing run", note: "from ehpa.billing_runs (the engine's own summary)", kinds: { outstanding_total: "money", outstanding_over_365_dollars: "money", denials_actionable_dollars: "money", era_unposted_after: "money", at: "when" },
        sql: `select stamp, at, mode, status, outstanding_total, outstanding_visits, outstanding_over_365_dollars, denials_actionable, denials_actionable_dollars, era_unposted_after,
                     charge_review_after as charge_review, claim_inspector_after as claim_inspector, unbilled_after as unbilled, exclusions_after as exclusions
              from ehpa.billing_runs where outstanding_total is not null order by at desc limit 1` },
      { heading: "Routine runs", note: "ops.routine_runs - every routine that logged itself", kinds: { finished_at: "when" },
        sql: `select routine, stamp, status, finished_at, headline from ops.routine_runs order by finished_at desc limit 10` },
      { heading: "What is in the database", note: "ops.v_health - documents per source and collection", kinds: { documents: "int", newest_written: "when", last_loaded: "when", bytes: "int" },
        sql: `select source, collection, documents, newest_written, last_loaded, bytes from ops.v_health order by source, collection` },
      { heading: "Recent loads", note: "ops.load_log", kinds: { inserted: "int", updated: "int", unchanged: "int", at: "when" },
        sql: `select at, command, source, inserted, updated, unchanged, loaded_by from ops.load_log order by at desc limit 15` },
    ],
  },
  ar: {
    title: "Accounts receivable",
    note: "Open insurance balances by age and payer, and the aging scan's recommendation on every unpaid visit.",
    sections: [
      { heading: "Open balance by age", note: "ehpa.outstanding_claims (the Outstanding Claims dataset)", kinds: { visits: "int", dollars: "money", share_pct: "int" },
        sql: `select age_bucket, count(*) as visits, round(sum(ins_balance),2) as dollars, round(100*sum(ins_balance)/nullif((select sum(ins_balance) from ehpa.outstanding_claims),0)) as share_pct
              from ehpa.outstanding_claims group by age_bucket order by min(days_old)` },
      { heading: "Open balance by payer", kinds: { visits: "int", dollars: "money", over_120: "money", over_120_pct: "int", oldest_days: "int" },
        sql: `select o.carrier_code, coalesce(max(c.carrier_name), max(b.carrier_name), o.carrier_code) as carrier, count(*) as visits, round(sum(o.ins_balance),2) as dollars,
                     round(sum(o.ins_balance) filter (where o.days_old > 120),2) as over_120, round(100*sum(o.ins_balance) filter (where o.days_old > 120)/nullif(sum(o.ins_balance),0)) as over_120_pct, max(o.days_old) as oldest_days
              from ehpa.outstanding_claims o left join ehpa.carriers c on c.carrier_code = o.carrier_code left join ehpa.outstanding_by_carrier b on b.carrier_code = o.carrier_code
              group by o.carrier_code order by dollars desc limit 20` },
      { heading: "Aging scan verdicts", note: "ehpa.ar_aging_by_recommendation (the ar aging report)", kinds: { visits: "int", balance: "money", balance_over_365: "money" },
        sql: `select as_of, recommendation, visits, balance, balance_over_365 from ehpa.ar_aging_by_recommendation order by balance desc` },
      { heading: "Correct and resend: the reasons", kinds: { visits: "int", balance: "money" },
        sql: `select left(why, 90) as why, count(*) as visits, round(sum(balance),2) as balance from ehpa.ar_aging_rows where recommendation = 'CORRECT & RESEND' group by 1 order by 3 desc limit 15` },
      { heading: "Outstanding total by day", note: "the engine's summary per run, newest first", kinds: { outstanding_total: "money", visits: "int", over_365: "money" },
        sql: `select (at at time zone 'America/New_York')::date as day, round(max(outstanding_total),2) as outstanding_total, max(outstanding_visits) as visits, round(max(outstanding_over_365_dollars),2) as over_365
              from ehpa.billing_runs where outstanding_total is not null group by 1 order by 1 desc limit 30` },
    ],
  },
  denials: {
    title: "Denials",
    note: "The Working Denials triage: every denied visit with its reason code, open balance and next action.",
    sections: [
      { heading: "By reason code (CARC)", kinds: { visits: "int", open_balance: "money", timely: "int" },
        sql: `select carc, count(*) as visits, round(sum(open_balance),2) as open_balance, count(*) filter (where timely) as timely, string_agg(distinct status, ', ') as statuses
              from ehpa.denial_visits group by carc order by open_balance desc nulls last limit 25` },
      { heading: "By status and disposition", kinds: { visits: "int", open_balance: "money", amount: "money" },
        sql: `select status, dispo, count(*) as visits, round(sum(open_balance),2) as open_balance, round(sum(amount),2) as amount from ehpa.denial_visits group by 1,2 order by open_balance desc nulls last` },
      { heading: "Open, largest first", note: "chart and visit ids only", kinds: { open_balance: "money", amount: "money", age_days: "int" },
        sql: `select visit_id, chart_id, dos, cpt, carrier, carc, rarc, open_balance, amount, age_days, timely, status, dispo, action, left(reason, 80) as reason
              from ehpa.denial_visits where status = 'OPEN' order by open_balance desc nulls last limit 100` },
    ],
  },
  era: {
    title: "ERA posting",
    note: "Remittances the runs posted: checks, lines, paid dollars and the adjustment codes on every line.",
    sections: [
      { heading: "Recent posting runs", kinds: { at: "when", checks_before: "int", checks_after: "int", line_count: "int", paid_total: "money", audit_flags: "int" },
        sql: `select stamp, at, checks_before, checks_after, line_count, paid_total, audit_flags, dry from ehpa.era_runs where line_count > 0 order by at desc limit 25` },
      { heading: "Adjustment codes, all lines", note: "ehpa.era_line_carcs", kinds: { lines: "int", visits: "int", paid: "money", zero_paid_lines: "int" },
        sql: `select carc, count(*) as lines, count(distinct visit_id) as visits, round(sum(paid),2) as paid, count(*) filter (where paid = 0) as zero_paid_lines, min(dos) as oldest_dos, max(dos) as newest_dos
              from ehpa.era_line_carcs group by carc order by lines desc limit 30` },
      { heading: "Lines paid at zero, newest first", kinds: { paid: "money", run_at: "when" },
        sql: `select run_at, check_id, chart_id, visit_id, cpt, dos, paid, claim_status, carcs, outcome from ehpa.era_lines where paid = 0 order by run_at desc limit 100` },
      { heading: "Paid by month", kinds: { lines: "int", paid: "money", denied_lines: "int" },
        sql: `select run_month, count(*) as lines, round(sum(paid),2) as paid, count(*) filter (where paid = 0) as denied_lines from ehpa.era_line_outcomes group by 1 order by 1 desc` },
    ],
  },
  feed: {
    title: "Claimocity feed",
    note: "What the hospital charge feed sent and what AdvancedMD did with each charge.",
    sections: [
      { heading: "Ingest batches", kinds: { at: "when", charges: "int" },
        sql: `select stamp, at, live, dos_min, dos_max, charges, counts->>'entered' as entered, counts->>'dollars' as dollars, counts->>'holds' as holds, counts->>'new_charts' as new_charts from ehpa.feed_batches order by at desc limit 15` },
      { heading: "Outcomes", kinds: { charges: "int", fee: "money" },
        sql: `select status, count(*) as charges, round(sum(fee),0) as fee from ehpa.feed_charges group by status order by charges desc` },
      { heading: "By facility and lead payer (entered charges)", kinds: { charges: "int", fee: "money" },
        sql: `select coalesce(facility, facility_id) as facility, coalesce(lead_carrier_name, lead_carrier) as lead_payer, count(*) as charges, round(sum(fee),0) as fee
              from ehpa.feed_charges where status = 'entered' group by 1,2 order by fee desc limit 25` },
      { heading: "Newest charges", kinds: { fee: "money", batch_at: "when" },
        sql: `select batch_at, chart_id, visit_id, dos, cpts, coalesce(facility, facility_id) as facility, coalesce(lead_carrier_name, lead_carrier) as lead_payer, clinician, fee, status, hold, why
              from ehpa.feed_charges order by batch_at desc, row_no limit 100` },
      { heading: "Bucket checks", kinds: { at: "when", visits: "int", dollars: "money", files_new: "int" },
        sql: `select stamp, at, result, visits, dollars, files_new, newest_file, left(line, 120) as line from ehpa.feed_checks order by at desc limit 20` },
    ],
  },
  cascade: {
    title: "Nightly insurance cascade",
    note: "Each night: pairs checked, rows flagged, visits re-pointed, dollars re-sent.",
    sections: [
      { heading: "Nights", kinds: { checked: "int", flagged: "int", lookups: "int", changed: "int", dollars_resent: "money", era_posted: "money", writeoffs: "money", stedi_cost: "money", at: "when" },
        sql: `select night, at, checked, flagged, lookups, changed, dollars_resent, era_posted, writeoffs, stedi_cost, done, note from ehpa.cascade_nights order by night desc limit 60` },
    ],
  },
  // Read from the documents themselves: ehpa.approvals and ehpa.approval_cards cast each dollars text to a number and fail when a
  // package names several amounts (found 11/12/2026: 31 of the 94 packages do), so these two tables answered with an error. Here an
  // amount counts only when its text is one number (SAFE_NUM); the text itself stays in the Approvals view's own table.
  approvals: {
    title: "Approvals",
    note: "The Mandatory Approvals packages as the newest snapshot recorded them, and the board's own cards.",
    sections: [
      { heading: "Packages, waiting first", note: "dollars only where a package names one amount", kinds: { dollars: "money", at: "when" },
        sql: `select r.value->>'id' as package_id, (r.value->>'at')::timestamptz as at, r.value->>'status' as status, ${SAFE_NUM("r.value->>'dollars'")} as dollars,
                     left(r.value->>'what', 140) as what, left(r.value->>'answer', 60) as answer, left(r.value->>'reason', 80) as reason
              from ${NEWEST_APPROVALS} d cross join lateral jsonb_array_elements(case when jsonb_typeof(d.body->'rows') = 'array' then d.body->'rows' else '[]'::jsonb end) r(value)
              order by (r.value->>'status' = 'waiting') desc, (r.value->>'at')::timestamptz desc nulls last limit 100` },
      { heading: "Board cards by status", note: "dollars only where a card names one amount", kinds: { cards: "int", dollars: "money" },
        sql: `select body->>'status' as status, count(*) as cards, round(sum(${SAFE_NUM("body->>'dollars'")}), 2) as dollars
              from raw.documents where source = 'mandatory_approvals' and collection = 'approvals' group by 1 order by cards desc` },
    ],
  },
  routines: {
    title: "Routines",
    note: "Every run that logged itself into the permanent store, and every load.",
    sections: [
      { heading: "Routine runs", kinds: { finished_at: "when", started_at: "when" },
        sql: `select routine, stamp, status, started_at, finished_at, headline, commit_sha from ops.routine_runs order by finished_at desc limit 50` },
      { heading: "Loads", kinds: { at: "when", inserted: "int", updated: "int", unchanged: "int", bytes: "int", duration_ms: "int" },
        sql: `select at, command, source, inserted, updated, unchanged, bytes, duration_ms, loaded_by from ops.load_log order by at desc limit 50` },
      { heading: "App sign-ins and requests", note: "ops.app_access_log", kinds: { at: "when", status: "int", ms: "int" },
        sql: `select at, user_email, route, status, ms from ops.app_access_log order by at desc limit 50` },
    ],
  },
  credentialing: {
    title: "Credentialing",
    note: "The Credentialing Board cards as copied into the store.",
    sections: [
      { heading: "Cards", sql: `select section, name, holder, cycle, due, left(due_note, 80) as due_note, need, turn, updated from ehpa.credentialing_items order by due nulls last, section, name limit 100` },
    ],
  },
  treasury: {
    title: "Treasury",
    note: "Bank deposits reconciled to remittances: the findings and the deposit groups.",
    sections: [
      { heading: "Findings", kinds: { n: "int", amount: "money" }, sql: `select severity, title, n, amount, left(what, 120) as what, left(action, 100) as action from ehpa.treasury_findings order by amount desc nulls last` },
      { heading: "Deposit groups", kinds: { n: "int", amount: "money" }, sql: `select label, family, status, cadence, n, amount from ehpa.treasury_groups order by amount desc nulls last` },
    ],
  },
};

const KIND_ALIAS: Record<string, Kind> = { dollars: "money", balance: "money", paid: "money", fee: "money", amount: "money", open_balance: "money", visits: "int", lines: "int", charges: "int", cards: "int", n: "int", checked: "int", flagged: "int", changed: "int" };

export async function runView(pool: Pool, name: string) {
  const spec = VIEWS[name];
  if (!spec) return null;
  const sections = [];
  for (const s of spec.sections) {
    const r = await pool.query({ text: s.sql, rowMode: "array" });
    const columns = r.fields.map((f) => f.name);
    const kinds = columns.map((c) => (s.kinds && s.kinds[c]) || KIND_ALIAS[c] || "text");
    sections.push({ heading: s.heading, note: s.note, columns, rows: r.rows.slice(0, 500), kinds });
  }
  const charts = [];
  for (const ch of spec.charts || []) {
    const r = await pool.query(ch.sql);
    charts.push({ id: ch.id, kind: ch.kind, title: ch.title, note: ch.note, fill: ch.fill, rows: r.rows });
  }
  return { title: spec.title, note: spec.note, charts, sections, generated_at: new Date().toISOString() };
}
