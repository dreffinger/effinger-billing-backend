// The Insurance Refresh Board for the app: the board's cards, read from the practice's Neon copy (ehpa.insurance_refresh_cards, built
// in tools/db/neon_schema.sql over the documents the daily practice-database sync copies in). READ-ONLY: the board on claude.ai stays
// the place where notes are posted and patients are handed to Claude; this is the same cards on the practice's own store.
// UNLIKE the app's other views this one carries patient names, dates of birth and insurance ids - a card is a patient. Two shapes
// leave here: the list (every card, compact: no note thread, no lookup trail) and ONE card's detail, asked for by id in a POST body
// so that an id (which can spell a patient's name) never sits in a URL or in the access log.
import type { Pool } from "pg";

export const BOARD_URL = "https://claude.ai/artifact/NXKjnsha2dTyGHsiB4k6zg";

const LIST_SQL = `select doc_id as id, patient, chart_id as chart, dob, turn, need, why, amount::float8 as amount, insid, inscarrier, mbi, insplans,
       facnow, facilities, lastfac, lastdos, facility, updated, notes_n, checks_n, api_n, is_new,
       last_note_who, last_note_at, left(last_note_text, 280) as last_note_text, coalesce(length(last_note_text) > 280, false) as last_note_more
  from ehpa.insurance_refresh_cards`;
// when the nightly copy last ran for the board (it logs itself even when nothing changed), and when a card last changed in the copy
const SYNC_SQL = `select (select max(at) from ops.load_log where source = 'insurance_refresh_board' and command like 'load-docs%') as synced_at,
       (select max(loaded_at) from ehpa.insurance_refresh_cards) as changed_at`;
const ITEM_SQL = `select doc_id as id, chart_id as chart, notes, checks, api from ehpa.insurance_refresh_cards where doc_id = $1`;

export async function runBoard(pool: Pool) {
  const cards = await pool.query(LIST_SQL);
  const sync = await pool.query(SYNC_SQL);
  const iso = (v: unknown) => (v instanceof Date ? v.toISOString() : v ? String(v) : null);
  return { url: BOARD_URL, synced_at: iso(sync.rows[0]?.synced_at), changed_at: iso(sync.rows[0]?.changed_at), items: cards.rows };
}

const TIC = new Set(["ok", "no", "na", "human"]);
const str = (v: unknown) => (v === null || v === undefined ? "" : String(v));
const rec = (v: unknown): Record<string, unknown> | null => (v && typeof v === "object" && !Array.isArray(v) ? (v as Record<string, unknown>) : null);
const list = (v: unknown): unknown[] => (Array.isArray(v) ? v : []);

// checks[] entries come in two shapes: the board's {ok, src, result, when} and the billing run's {result, step, text, at}
// (boards/templates/tracker.html normCheck - same rule here, so the trail reads the same in both places)
export function normCheck(c: unknown) {
  const o = rec(c);
  if (!o) return { k: "na", src: "", res: "", when: "", at: "" };
  const stepStyle = !o.src && (o.step !== undefined || TIC.has(str(o.result)));
  const k = stepStyle ? (TIC.has(str(o.result)) ? str(o.result) : "na") : TIC.has(str(o.ok)) ? str(o.ok) : "na";
  return { k, src: str(o.src || o.step || ""), res: stepStyle ? str(o.text || "") : str(o.result || ""), when: str(o.when || ""), at: str(o.at || "") };
}

export async function boardItem(pool: Pool, id: string) {
  const r = await pool.query(ITEM_SQL, [id]);
  const row = r.rows[0];
  if (!row) return null;
  return {
    id: str(row.id),
    chart: str(row.chart),
    notes: list(row.notes).map(rec).filter((n): n is Record<string, unknown> => !!n).map((n) => ({ who: str(n.who), at: str(n.at), text: str(n.text) })),
    checks: list(row.checks).map(normCheck),
    api: list(row.api).map(rec).filter((x): x is Record<string, unknown> => !!x).map((x) => ({ src: str(x.src) || "API result", at: str(x.at), text: str(x.text) })),
  };
}
