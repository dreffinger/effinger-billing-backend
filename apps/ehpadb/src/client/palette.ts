// The color scheme switcher in the header (the Practice Database page's, its lines 379-380): a press sets data-ehpa on <html>
// and remembers the pick in this browser (localStorage); /theme.js applies it again before the first paint of the next visit.
// Light unless the viewer picked another. Charts and pages are drawn with the CSS tokens, so they follow the switch at once.
import { PALETTE_KEY, DEFAULT_PALETTE, PALETTES } from "../palettes";

const KEYS = PALETTES.map(([k]) => k);

export function initPalette() {
  const root = document.documentElement;
  const paint = () => {
    const cur = root.getAttribute("data-ehpa") || DEFAULT_PALETTE;
    document.querySelectorAll<HTMLElement>("#pal button").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.pal === cur)));
  };
  document.querySelectorAll<HTMLElement>("#pal button").forEach((b) => b.addEventListener("click", () => {
    const p = KEYS.includes(b.dataset.pal || "") ? (b.dataset.pal as string) : DEFAULT_PALETTE;
    root.setAttribute("data-ehpa", p);
    try { localStorage.setItem(PALETTE_KEY, p); } catch { /* a private window keeps it for this visit only */ }
    paint();
  }));
  paint();
}
