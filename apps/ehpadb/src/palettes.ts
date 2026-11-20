// PLAIN ENGLISH: the five ehpa color schemes, the same ones the Practice Database page offers (tools/db/practice_db_page.html,
// the :root[data-ehpa=...] token blocks and the switcher), with Light as the default here (William 11/12/2026: "same color
// options as all of them default to light"). The tokens below are copied from that page word for word -
// tools/selftest/test_ehpadb_app.py fails if the two drift apart. The viewer's pick is remembered in this browser only
// (localStorage, key ehpa-palette); nothing about it reaches the server.
//   PALETTES      the switcher's buttons: key, label, swatch ground, swatch edge (the page's order)
//   paletteCss()  the token blocks; :root carries Light, so the page is Light before any script runs
//   themeJs()     served as /theme.js and loaded in <head> before the body: applies the remembered pick before the first paint
//                 (the Content-Security-Policy allows scripts from this origin only, so it cannot be an inline script)

export const PALETTE_KEY = "ehpa-palette";
export const DEFAULT_PALETTE = "light";

export const PALETTES: [string, string, string, string][] = [
  ["lapis", "Lapis", "#0b1f4d", "#cf9544"],
  ["midnight", "Midnight", "#082f35", "#70d6f8"],
  ["navy", "Navy", "#253e59", "#70d6f8"],
  ["plum", "Plum", "#181924", "#9be8e2"],
  ["light", "Light", "#ffffff", "#0054e9"],
];

// token blocks exactly as on the Practice Database page (lines 22-36 there), one line per palette
export const TOKENS: Record<string, string> = {
  lapis: "--bg:#0b1f4d;--bg-deep:#071538;--surface:#132c66;--surface-2:#1a387d;--line:#23418a;--line-strong:#3b5fae;--ink:#f2f5ff;--ink-2:#dde5fb;--muted:#b9c6ea;--dim:#8ea1d2; --accent:#cf9544;--on-accent:#0b1f4d;--accent-soft:rgba(207,149,68,.18);--accent-2:#79a6ff;--ok:#5fd394;--ok-soft:rgba(95,211,148,.16);--warn:#f5b84d;--warn-soft:rgba(245,184,77,.16); --bad:#ff7b8a;--bad-soft:rgba(255,123,138,.16);--pulled:#8fc7a6;--grad:linear-gradient(135deg,#cf9544 0%,#79a6ff 100%);--grid:rgba(255,255,255,.06);color-scheme:dark",
  midnight: "--bg:#082f35;--bg-deep:#07292f;--surface:#214449;--surface-2:#2d5057;--line:#1d4b53;--line-strong:#3c6169;--ink:#f4f5f7;--ink-2:#dee2e6;--muted:#cacaca;--dim:#9da8b4; --accent:#70d6f8;--on-accent:#082f35;--accent-soft:#1f5a68;--accent-2:#f841e0;--ok:#3dd475;--ok-soft:#164a41;--warn:#ffc409;--warn-soft:#3d4020;--bad:#df7079;--bad-soft:#3d1b22; --pulled:#7fbfa0;--grad:linear-gradient(135deg,#70d6f8 0%,#f841e0 100%);--grid:rgba(255,255,255,.06);color-scheme:dark",
  navy: "--bg:#253e59;--bg-deep:#21374e;--surface:#304861;--surface-2:#3b516a;--line:#1f3450;--line-strong:#465b72;--ink:#ffffff;--ink-2:#dee2e6;--muted:#cacaca;--dim:#989aa2; --accent:#70d6f8;--on-accent:#082f35;--accent-soft:#2a4f68;--accent-2:#f841e0;--ok:#3dd475;--ok-soft:#1f4a3c;--warn:#ffc409;--warn-soft:#4a4020;--bad:#e58f95;--bad-soft:#4d1f2a; --pulled:#86c3a4;--grad:linear-gradient(135deg,#70d6f8 0%,#f841e0 100%);--grid:rgba(255,255,255,.07);color-scheme:dark",
  plum: "--bg:#181924;--bg-deep:#1d122e;--surface:#2c2933;--surface-2:#232529;--line:#3c3941;--line-strong:#626468;--ink:#ffffff;--ink-2:#d1d2d3;--muted:#adaeaf;--dim:#77787a; --accent:#9be8e2;--on-accent:#19171d;--accent-soft:#243a3f;--accent-2:#f841e0;--ok:#50ef73;--ok-soft:#173a1d;--warn:#ffd442;--warn-soft:#3d3616;--bad:#ff877a;--bad-soft:#3f1f22; --pulled:#8ccaa8;--grad:linear-gradient(135deg,#9be8e2 0%,#f841e0 100%);--grid:rgba(255,255,255,.07);color-scheme:dark",
  light: "--bg:#ffffff;--bg-deep:#f4f5f8;--surface:#ffffff;--surface-2:#f2f2f2;--line:#d7d8da;--line-strong:#bfbfbf;--ink:#082f35;--ink-2:#222428;--muted:#636469;--dim:#737478; --accent:#0054e9;--on-accent:#ffffff;--accent-soft:#e0f4fd;--accent-2:#b4169e;--ok:#1b8037;--ok-soft:#dcfae6;--warn:#917005;--warn-soft:#fff3c4;--bad:#c5000f;--bad-soft:#fbdcdf; --pulled:#4e8f6e;--grad:linear-gradient(135deg,#0054e9 0%,#70d6f8 100%);--grid:rgba(8,47,53,.08);color-scheme:light",
};
// the nightly cascade chart's two purples (the page's lines 38-39): pale on the dark grounds, a deeper pair with an edge on Light
export const CASCADE_DARK = "--cascade:#d9ccfa;--cascade-2:#b9a2f2;--cascade-edge:transparent";
export const CASCADE_LIGHT = "--cascade:#ddd2f8;--cascade-2:#b49cee;--cascade-edge:#9a80e0";

// (functions, not constants, so the browser bundle - which imports only the key and the list - does not carry the CSS)
export function paletteCss(): string {
  return [
    `:root{${TOKENS[DEFAULT_PALETTE]};${CASCADE_LIGHT}}`,
    ...PALETTES.map(([k]) => `:root[data-ehpa="${k}"]{${TOKENS[k]};${k === "light" ? CASCADE_LIGHT : CASCADE_DARK}}`),
  ].join("\n");
}

export function themeJs(): string {
  const keys = PALETTES.map(([k]) => k);
  return `(function(){var k=${JSON.stringify(PALETTE_KEY)},ok=${JSON.stringify(keys)},p=null;try{p=localStorage.getItem(k)}catch(e){}document.documentElement.setAttribute("data-ehpa",ok.indexOf(p)>=0?p:${JSON.stringify(DEFAULT_PALETTE)})})();\n`;
}
