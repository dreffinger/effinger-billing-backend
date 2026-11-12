// Small SQL pieces shared by views.ts and pdb.ts (read-only).
// SAFE_NUM: a dollars text as a number only when it IS one number ("$1,052.90" -> 1052.90); anything else ("$52.80 ... -$17.50") is
// null instead of an error. ehpa.approvals and ehpa.approval_cards cast with a looser rule and fail on such texts (11/12/2026).
// NEWEST_APPROVALS: the newest approvals snapshot document - the same rule as the ehpa.approvals view (newest written first).
export const SAFE_NUM = (expr: string) =>
  `(case when regexp_replace(coalesce(${expr}, ''), '[$,[:space:]]', '', 'g') ~ '^-?[0-9]+([.][0-9]+)?$' then regexp_replace(${expr}, '[$,[:space:]]', '', 'g')::numeric end)`;
export const NEWEST_APPROVALS = `(select doc_id, body from raw.documents where source = 'practice_db' and collection = 'snapshots' and body->>'kind' = 'approvals'
  order by written_at desc nulls last, doc_id desc limit 1)`;
