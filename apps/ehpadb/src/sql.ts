// Small SQL pieces shared by views.ts and pdb.ts (read-only), and dbFail - how a route answers a failed query (pdb.ts, ccm.ts, upo.ts,
// and /api/view/:name in index.ts).
// SAFE_NUM: a dollars text as a number only when it IS one number ("$1,052.90" -> 1052.90); anything else ("$52.80 ... -$17.50") is
// null instead of an error. ehpa.approvals and ehpa.approval_cards cast with a looser rule and fail on such texts (11/12/2026).
// NEWEST_APPROVALS: the newest approvals snapshot document - the same rule as the ehpa.approvals view (newest written first).
import type { Context } from "hono";
import { routePath } from "hono/route";

export const SAFE_NUM = (expr: string) =>
  `(case when regexp_replace(coalesce(${expr}, ''), '[$,[:space:]]', '', 'g') ~ '^-?[0-9]+([.][0-9]+)?$' then regexp_replace(${expr}, '[$,[:space:]]', '', 'g')::numeric end)`;
export const NEWEST_APPROVALS = `(select doc_id, body from raw.documents where source = 'practice_db' and collection = 'snapshots' and body->>'kind' = 'approvals'
  order by written_at desc nulls last, doc_id desc limit 1)`;

// dbFail (review of 11/12/2026): the Function's log gets the method, the route as registered ("/api/ccm/note/:id" - never the chart,
// note or run asked for) and the SQLSTATE (e.g. 22007), nothing else. Never the error's message or detail: Postgres repeats the value
// it choked on there ('invalid input syntax for type date: "..."'), and on the CCM routes and the Insurance Refresh Board's list
// (/api/view/insurance_refresh) that value can be a birth date or a name - PHI must never reach the logs. The caller gets a fixed
// sentence naming what failed. (11/13/2026) The gate's own two queries in index.ts, the account lookup and the access-trail insert,
// log sqlState too, and nothing else.
export const sqlState = (e: unknown) => { const code = String((e as { code?: unknown } | null)?.code ?? ""); return /^[0-9A-Z]{5}$/.test(code) ? code : "no-sqlstate"; };
export function dbFail(c: Context<any, any, any>, what: string, e: unknown) {
  console.error("database error", c.req.method, routePath(c), sqlState(e));
  return c.json({ error: "the database answered with an error for " + what }, 500);
}
