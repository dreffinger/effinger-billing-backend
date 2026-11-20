// The Insurance Refresh Board inside the dashboard: the state behind its filters and search box, and one card's notes fetched
// when the card is opened. ../boardview.ts draws everything; this file only keeps what was chosen and repaints. It is the one
// dashboard page that shows patients, so nothing of it is written to the browser's storage, the rows are dropped when the page is
// left, and signing out also drops what was typed into the search box. A card's notes are asked for with the card id in the body
// of a POST, never in the address.
import { apiPost } from "./core";
import { boardShellHtml, boardListHtml, boardCountText, cardHtml, searching, type Board, type BoardState, type CardDetail } from "../boardview";

let board: Board | null = null;
const state: BoardState = { filter: "william", query: "", open: new Set(), details: new Map() };
let searchTimer: number | undefined;
const stopSearchTimer = () => { if (searchTimer) { window.clearTimeout(searchTimer); searchTimer = undefined; } };

// the dashboard calls this with every view it draws: the board's rows are kept for the filters, any other view drops them
export function boardBlock(b: Board | undefined): string {
  board = b || null; state.open.clear(); state.details.clear();   // fresh rows: a card's notes are asked for again
  return board ? `<div id="board">${boardShellHtml(board, state)}</div>` : "";
}
// Refresh and leaving the page drop the rows; signing out (all) also forgets the search text and the filter
export function forgetBoard(all = false) {
  stopSearchTimer();
  board = null; state.open.clear(); state.details.clear();
  if (all) { state.query = ""; state.filter = "william"; }
}

// A repaint replaces nodes. When the keyboard was on a card's Show/Hide button (the only thing in a card that takes it), it is put
// back on the same card's button, so Enter and Space keep working and a screen reader reads the button's new state.
const cardBtn = (id: string) => Array.from(document.querySelectorAll<HTMLElement>("#board-list button[data-card]")).find((b) => b.dataset.card === id);
function syncChips() {
  const on = searching(state);   // while a search is typed no filter is in force, so none shows as pressed
  document.querySelectorAll<HTMLElement>("#board-f button").forEach((b) => b.setAttribute("aria-pressed", String(!on && b.dataset.f === state.filter)));
}
function paintList() {
  const el = document.getElementById("board-list");
  if (!el || !board) return;
  const active = document.activeElement as HTMLElement | null;
  const had = active && el.contains(active) ? active.dataset.card : undefined;
  el.innerHTML = boardListHtml(board, state);
  const count = document.getElementById("board-count");
  if (count) count.textContent = boardCountText(board, state);
  if (had) (cardBtn(had) || document.getElementById("board-q"))?.focus({ preventScroll: true });   // its card left the list: back to the search box
}
function paintCard(id: string) {
  if (!board) return;
  const c = board.items.find((x) => x.id === id);
  const el = Array.from(document.querySelectorAll<HTMLElement>("#board-list article.rb-card")).find((a) => a.dataset.id === id);
  if (!c || !el) return;
  const had = el.contains(document.activeElement);
  el.outerHTML = cardHtml(c, state);
  if (had) cardBtn(id)?.focus({ preventScroll: true });
}
async function toggleCard(id: string) {
  if (state.open.has(id)) { state.open.delete(id); paintCard(id); return; }
  state.open.add(id);
  const have = state.details.get(id);
  if (have === "loading" || (have && !("error" in have))) { paintCard(id); return; }   // on its way, or already here
  state.details.set(id, "loading"); paintCard(id);
  const shown = board;
  try {
    const d = await apiPost<CardDetail>("/api/board/item", { id });
    if (board !== shown) return;   // the page was left, refreshed or signed out of while this was on its way
    state.details.set(id, d);
  } catch (e: any) {
    if (board !== shown) return;
    state.details.set(id, { error: e?.message || String(e) });
  }
  paintCard(id);
}

document.addEventListener("click", (ev) => {
  const t = ev.target as HTMLElement;
  const f = t.closest("#board-f button") as HTMLElement | null;
  if (f && f.dataset.f) {
    // choosing a filter is also the way out of a search: the box is emptied, so the filter that shows as pressed is the one in force
    state.filter = f.dataset.f; state.query = ""; stopSearchTimer();
    const q = document.getElementById("board-q") as HTMLInputElement | null;
    if (q) q.value = "";
    syncChips(); paintList();
    return;
  }
  const more = t.closest("#board-list button[data-card]") as HTMLElement | null;
  if (more && more.dataset.card) void toggleCard(more.dataset.card);
});
document.addEventListener("input", (ev) => {
  const q = ev.target as HTMLInputElement | null;
  if (!q || q.id !== "board-q") return;
  stopSearchTimer();
  searchTimer = window.setTimeout(() => { searchTimer = undefined; if (!board) return; state.query = q.value; syncChips(); paintList(); }, 120);
});
// the rows do not outlive the page: any address that is not the board's drops them
addEventListener("hashchange", () => { if (!/^#\/?(db\/)?insurance_refresh$/.test(location.hash)) forgetBoard(); });
