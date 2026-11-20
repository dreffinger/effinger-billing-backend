// The one HTML page the Function serves at "/". It carries no data: a sign-in gate, the color scheme switcher, the application
// bar, an empty main area, and the bundled client script at /app.js. Colors: the five ehpa color schemes of the Practice
// Database page (palettes.ts - Lapis, Midnight, Navy, Plum, Light), Light unless the viewer picked another; /theme.js applies
// the remembered pick before the first paint. The header buttons to the practice's claude.ai pages are filled in after
// sign-in from /api/links, so this page names none of them.
// The same shell holds every application: the hub, Universal Practice Optimization, Practice Optimization for this practice,
// the ehpa Practice Database (the dashboard and the Practice Database page's views), the CCM notes and Learn; client.ts
// decides which one the address asks for.
import { paletteCss, PALETTES, DEFAULT_PALETTE } from "./palettes";

export function pageHtml(authUrl: string, idleMinutes: string, practice: string): string {
  const pal = PALETTES.map(([k, label, ground, edge]) => `<button type="button" data-pal="${k}" aria-pressed="${k === DEFAULT_PALETTE}"><i style="background:${ground};border-color:${edge}"></i>${label}</button>`).join("");
  return `<!doctype html>
<html lang="en" data-ehpa="${DEFAULT_PALETTE}" data-auth-url="${attr(authUrl)}" data-idle-minutes="${attr(idleMinutes)}" data-practice="${attr(practice)}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<title>ehpa Practice Applications</title>
<script src="/theme.js"></script>
<style>
${paletteCss()}
:root{--mono:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;--font:system-ui,-apple-system,"Segoe UI",sans-serif;--pill:999px;--r:14px;--r-lg:18px}
.chart svg{display:block;width:100%;height:auto}.bar{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;margin:6px 0 14px}
.seg{display:inline-flex;border:1px solid var(--line-strong);border-radius:999px;padding:3px;gap:3px;background:var(--surface);flex-wrap:wrap}
.seg button{border:0;background:transparent;color:var(--muted);font:600 13px var(--font);padding:7px 14px;border-radius:999px;cursor:pointer}.seg button[aria-pressed="true"]{background:var(--accent);color:var(--on-accent)}
.legend{display:flex;gap:16px;flex-wrap:wrap;font-size:12.5px;color:var(--muted);margin:0 0 6px}.legend i{display:inline-block;width:11px;height:11px;border-radius:3px;margin-right:6px;vertical-align:-1px;box-shadow:inset 0 0 0 1px var(--cascade-edge)}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:500 15px/1.5 var(--font);-webkit-font-smoothing:antialiased;
  background-image:linear-gradient(var(--grid) 1px,transparent 1px),linear-gradient(90deg,var(--grid) 1px,transparent 1px);background-size:28px 28px}
a{color:var(--accent)}a:hover{color:var(--ink)}:focus-visible{outline:2px solid var(--accent-2);outline-offset:2px;border-radius:6px}
.wrap{max-width:1180px;margin:0 auto;padding:18px 16px 90px}
.top{display:flex;align-items:center;justify-content:space-between;gap:14px;flex-wrap:wrap;margin-bottom:12px}
.brand{font:700 12px/1 var(--font);letter-spacing:.2em;text-transform:uppercase;color:var(--accent)}.brand a{color:inherit;text-decoration:none}
h1{font-size:26px;margin:0 0 8px;line-height:1.15;text-wrap:balance}h2{font-size:16px;margin:0}h3{font-size:15px;margin:0 0 4px}
p{margin:0 0 10px}.lead{color:var(--muted);max-width:76ch;margin:0 0 16px;font-size:16px}
.btn{display:inline-block;border:1px solid var(--line-strong);background:var(--surface);color:var(--ink);font:600 13.5px var(--font);padding:9px 14px;border-radius:999px;cursor:pointer;text-decoration:none}
.btn:hover{border-color:var(--accent-2)}.btn.primary{background:var(--accent);border-color:var(--accent);color:var(--on-accent)}.btn[disabled]{opacity:.6;cursor:default}
.status{font-size:13.5px;color:var(--muted);min-height:1.4em}.status.err{color:var(--bad)}.status.ok{color:var(--ok)}
.gate{max-width:440px;margin:48px auto;background:var(--surface);border:1px solid var(--line);border-radius:18px;padding:24px 26px}
.gate label{display:block;font-size:12.5px;color:var(--muted);margin:10px 0 4px}
.gate input{width:100%;background:var(--bg-deep);color:var(--ink);border:1px solid var(--line-strong);border-radius:10px;padding:9px 12px;font:500 14px var(--font)}
.gate .row{display:flex;gap:10px;align-items:center;justify-content:space-between;margin-top:14px;flex-wrap:wrap}
.gate .small{font-size:12.5px;color:var(--dim)}.gate ul{margin:10px 0 0;padding-left:18px;color:var(--muted);font-size:13.5px}
.appbar{display:flex;gap:4px;flex-wrap:wrap;margin:0 0 8px;border-bottom:1px solid var(--line-strong);padding-bottom:8px}
.appbar a{text-decoration:none;color:var(--ink-2);font:650 14px var(--font);padding:9px 14px;border-radius:10px;border:1px solid transparent}
.appbar a:hover{border-color:var(--line-strong)}.appbar a[aria-current]{background:var(--surface-2);border-color:var(--line-strong);color:var(--ink);box-shadow:inset 0 -3px 0 var(--accent)}
.rail{display:flex;gap:6px;flex-wrap:wrap;margin:4px 0 18px;border-bottom:1px solid var(--line);padding-bottom:10px}
.rail a{text-decoration:none;color:var(--muted);font:600 13.5px var(--font);padding:8px 13px;border-radius:999px;border:1px solid transparent}
.rail a:hover{color:var(--ink);border-color:var(--line-strong)}.rail a[aria-current]{background:var(--accent);color:var(--on-accent)}
.block{background:var(--surface);border:1px solid var(--line);border-radius:18px;padding:16px 18px;margin-bottom:14px;min-width:0}
.block>header{display:flex;align-items:baseline;justify-content:space-between;gap:12px;flex-wrap:wrap;margin-bottom:10px}
.note{color:var(--muted);font-size:13px}.dim{color:var(--dim)}.foot{color:var(--dim);font-size:12.5px;margin-top:18px;max-width:90ch}.big{font:700 16px var(--font);color:var(--ink)}
table{width:100%;border-collapse:collapse;font-size:13.5px}th{text-align:left;font:600 11px/1.2 var(--font);letter-spacing:.1em;text-transform:uppercase;color:var(--dim);padding:8px 10px;border-bottom:1px solid var(--line);white-space:nowrap}
td{padding:9px 10px;border-bottom:1px solid var(--line);vertical-align:top;color:var(--ink-2)}tbody tr:nth-child(odd) td{background:var(--surface-2)}tbody tr:last-child td{border-bottom:0}
td.num,th.num{text-align:right;font-family:var(--mono);font-variant-numeric:tabular-nums}.tablewrap{overflow-x:auto}.tablewrap table{min-width:560px}
code{font-family:var(--mono);font-size:12px;background:var(--bg-deep);border:1px solid var(--line);border-radius:6px;padding:1px 6px;color:var(--ink-2)}
[hidden]{display:none!important}
/* cards, tiles, chips */
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:12px;margin:0 0 16px}.cards.hub{grid-template-columns:repeat(auto-fit,minmax(280px,1fr))}
.card{display:flex;flex-direction:column;gap:6px;background:var(--surface);border:1px solid var(--line);border-radius:16px;padding:16px 18px;text-decoration:none;color:var(--ink-2);min-width:0}
.card:hover{border-color:var(--accent);color:var(--ink)}.card h3,.card h2{color:var(--ink);margin:0}.card h2{font-size:19px;line-height:1.2}.card p{margin:0;font-size:13.5px;color:var(--muted)}
.card-k{font:700 12px var(--mono);color:var(--accent);letter-spacing:.08em}.card-f{margin-top:auto;padding-top:8px;font-size:12.5px;color:var(--dim)}
.card.big{padding:20px 22px;gap:9px}.card.big p{font-size:14.5px}.card .cta{font:650 13.5px var(--font);color:var(--accent);margin-top:6px}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:10px;margin:0 0 16px}
.tile{background:var(--surface);border:1px solid var(--line);border-radius:14px;padding:12px 14px;min-width:0}.tile-l{font:600 11px/1.2 var(--font);letter-spacing:.1em;text-transform:uppercase;color:var(--dim)}
.tile-v{font:750 24px/1.15 var(--font);margin-top:5px;overflow-wrap:anywhere}.tile-s{font-size:12.5px;color:var(--muted);margin-top:3px}
.tile.accent{border-color:var(--accent)}.tile.accent .tile-v{color:var(--accent)}.tile.warn .tile-v{color:var(--warn)}.tile.bad .tile-v{color:var(--bad)}.tile.ok .tile-v{color:var(--ok)}
.chips{display:flex;gap:6px;flex-wrap:wrap;align-items:center;margin:4px 0}
.chip{display:inline-flex;align-items:center;gap:6px;font:600 12px/1 var(--font);padding:5px 10px;border-radius:999px;border:1px solid var(--line-strong);color:var(--ink-2);background:var(--bg-deep);text-decoration:none;white-space:normal;max-width:100%;line-height:1.25}
.chip i{width:8px;height:8px;border-radius:50%;background:var(--dim);flex:none}.chip.soft{color:var(--muted);border-color:var(--line)}
.st-green i,.vd-supported i{background:var(--ok)}.st-amber i,.vd-partly i{background:var(--warn)}.st-red i,.vd-contradicted i,.vd-outdated i{background:var(--bad)}
.st-red,.sev-critical,.sev-high,.vd-contradicted,.vd-outdated{border-color:var(--bad)}.st-amber,.sev-medium,.vd-partly{border-color:var(--warn)}.st-green,.vd-supported{border-color:var(--ok)}
.sev-critical i,.sev-high i{background:var(--bad)}.sev-medium i{background:var(--warn)}.sev-low i{background:var(--dim)}.sev-critical{background:var(--bad-soft)}
.ap-core{border-color:var(--accent);color:var(--accent)}.ap-not_applicable{color:var(--dim);border-style:dashed}
.kind-revenue{border-color:var(--ok);color:var(--ok)}.kind-risk{border-color:var(--bad);color:var(--bad)}.kind-cost{border-color:var(--accent-2);color:var(--accent-2)}.kind-value{border-color:var(--accent);color:var(--accent)}.kind-capability{border-color:var(--cascade);color:var(--cascade)}
.score{font-family:var(--mono);letter-spacing:.08em;color:var(--accent);white-space:nowrap}
/* long-form content */
.two{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:14px}.two>.block{margin-bottom:14px}
ul.bullets,ol.steps{margin:0 0 6px;padding-left:20px}ul.bullets li,ol.steps li{margin:5px 0;color:var(--ink-2)}ul.bullets.ok li::marker{color:var(--ok)}ul.bullets.bad li::marker{color:var(--bad)}
ul.evidence{font-size:13.5px;color:var(--muted)}ul.evidence li{color:var(--muted)}ul.sources{margin:8px 0 0;padding-left:18px;font-size:12.5px;color:var(--dim)}
.metric{border-top:1px solid var(--line);padding:14px 0 6px}.metric:first-of-type{border-top:0;padding-top:2px}.metric>header{display:flex;justify-content:space-between;gap:10px;flex-wrap:wrap;align-items:baseline}.metric h3{font-size:15.5px}
.bench{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:8px;margin:8px 0}.bench div{background:var(--bg-deep);border:1px solid var(--line);border-radius:10px;padding:8px 10px}
.bench dt,.kv dt{font:600 11px/1.2 var(--font);letter-spacing:.1em;text-transform:uppercase;color:var(--dim);margin-bottom:3px}.bench dd,.kv dd{margin:0;color:var(--ink-2)}
.kv{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:10px;margin:8px 0}.kv.wide{grid-template-columns:1fr}.kv.wide div{display:grid;grid-template-columns:minmax(120px,200px) 1fr;gap:12px;border-top:1px solid var(--line);padding-top:8px}
.formula{background:var(--bg-deep);border:1px solid var(--line);border-left:3px solid var(--accent);border-radius:8px;padding:9px 12px;margin:8px 0}.formula-l{font:600 11px/1.2 var(--font);letter-spacing:.1em;text-transform:uppercase;color:var(--dim);margin-bottom:4px}.formula-e{font-family:var(--mono);font-size:13.5px;color:var(--ink);overflow-wrap:anywhere}
.callout{border:1px solid var(--line-strong);border-left:4px solid var(--accent-2);background:var(--bg-deep);border-radius:10px;padding:10px 14px;margin:10px 0}.callout p{margin:4px 0 0}.callout.warn{border-left-color:var(--warn)}.callout.key{border-left-color:var(--accent)}.callout.risk{border-left-color:var(--bad)}
pre.code{background:var(--bg-deep);border:1px solid var(--line);border-radius:10px;padding:12px 14px;overflow-x:auto;font:12.5px/1.5 var(--mono);color:var(--ink-2);margin:8px 0}pre.code code{background:none;border:0;padding:0;font-size:inherit}
.quiz{border:1px dashed var(--line-strong);border-radius:12px;padding:12px 14px;margin:10px 0}.quiz-q{font-weight:650}.quiz-c{display:flex;gap:8px;flex-wrap:wrap}.quiz .btn{border-radius:10px;text-align:left}.quiz .btn.right{border-color:var(--ok);color:var(--ok)}.quiz .btn.wrong{border-color:var(--bad);color:var(--bad)}.quiz-why{margin:10px 0 0}
.crumbs{font-size:13px;color:var(--dim);margin:0 0 8px;display:flex;gap:8px;flex-wrap:wrap}.crumbs a{color:var(--muted)}.crumbs .sep{color:var(--line-strong)}
.pager{display:flex;justify-content:space-between;gap:12px;margin:18px 0;flex-wrap:wrap}
.filters{display:flex;gap:12px;flex-wrap:wrap;align-items:flex-end;margin:0 0 14px}.filters label{min-width:0;max-width:100%;flex:0 1 auto}.filters select,.filters input,.work select,.work textarea{max-width:100%;min-width:0;width:100%}.work-edit,.work-main,.work-edit label{min-width:0;max-width:100%}.chips{min-width:0;max-width:100%}.filters label,.work-edit label{display:flex;flex-direction:column;gap:4px;font:600 11px/1.2 var(--font);letter-spacing:.1em;text-transform:uppercase;color:var(--dim)}
select,input[type=search],textarea{background:var(--bg-deep);color:var(--ink);border:1px solid var(--line-strong);border-radius:10px;padding:8px 10px;font:500 14px var(--font);min-width:0}input[type=search]{min-width:240px}textarea{width:100%;resize:vertical}
.reading{display:grid;grid-template-columns:220px minmax(0,1fr);gap:18px;align-items:start}.reading>*{min-width:0}.toc{position:sticky;top:12px;font-size:13.5px;background:var(--surface);border:1px solid var(--line);border-radius:14px;padding:12px 14px}.toc ol{margin:8px 0 0;padding-left:18px}.toc li{margin:5px 0}.toc a{color:var(--muted);text-decoration:none}.toc a:hover{color:var(--ink)}.prose p,.prose li{max-width:78ch}
@media (max-width:820px){.reading{grid-template-columns:1fr}.toc{position:static}.kv.wide div{grid-template-columns:1fr;gap:2px}}
/* practice pages */
.area{border-top:1px solid var(--line);padding:12px 0 4px}.area:first-of-type{border-top:0;padding-top:0}.area>header{display:flex;justify-content:space-between;gap:10px;flex-wrap:wrap;align-items:baseline}.area h3 a{color:var(--ink);text-decoration:none}.area h3 a:hover{color:var(--accent-2)}
.rank{display:inline-grid;place-items:center;min-width:26px;height:26px;border-radius:50%;background:var(--accent);color:var(--on-accent);font:750 13px var(--font);margin-right:10px}
.stack{display:flex;height:12px;border-radius:999px;overflow:hidden;background:var(--bg-deep);gap:2px;min-width:120px}.seg-red{background:var(--bad)}.seg-amber{background:var(--warn)}.seg-green{background:var(--ok)}.seg-unknown{background:var(--line-strong)}
.lanes{display:grid;grid-template-columns:repeat(auto-fit,minmax(290px,1fr));gap:14px;align-items:start}.lane{background:var(--bg-deep);border:1px solid var(--line);border-radius:18px;padding:14px}.lane>header{display:flex;justify-content:space-between;align-items:baseline;gap:8px;margin-bottom:10px}
.proj{background:var(--surface);border:1px solid var(--line);border-radius:14px;padding:12px 14px;margin-bottom:10px}.proj details{margin:6px 0}.proj summary{cursor:pointer;color:var(--accent-2);font-size:13.5px}
.progress{height:8px;border-radius:999px;background:var(--bg-deep);overflow:hidden;margin:8px 0 4px}.progress span{display:block;height:100%;background:var(--ok)}
.work{display:grid;grid-template-columns:minmax(0,1fr) 300px;gap:16px;background:var(--surface);border:1px solid var(--line);border-left:4px solid var(--line-strong);border-radius:14px;padding:14px 16px;margin-bottom:10px}
.work.st-doing{border-left-color:var(--accent-2)}.work.st-waiting{border-left-color:var(--warn)}.work.st-done{border-left-color:var(--ok);opacity:.78}.work.st-dropped{opacity:.6}
.work-edit{display:flex;flex-direction:column;gap:8px}.work-msg.ok{color:var(--ok)}.work-msg.err{color:var(--bad)}@media (max-width:820px){.work{grid-template-columns:minmax(0,1fr)}}
.vchart{display:flex;flex-direction:column;gap:10px;margin:6px 0}.vrow{display:grid;grid-template-columns:minmax(120px,220px) minmax(0,1fr) minmax(120px,190px);gap:12px;align-items:center}.vlabel{font-size:13.5px;color:var(--muted)}.vrow.strong .vlabel{color:var(--ink);font-weight:700}
.vtrack{position:relative;height:18px;background:var(--bg-deep);border-radius:999px}.vband{position:absolute;top:4px;bottom:4px;background:var(--accent-2);border-radius:999px;opacity:.75}.vrow.strong .vband{background:var(--accent);opacity:1;top:2px;bottom:2px}
.vdot{position:absolute;top:50%;width:12px;height:12px;margin:-6px 0 0 -6px;border-radius:50%;background:var(--ink);border:2px solid var(--bg)}.vnum{font:700 14px var(--mono);text-align:right}.vnum .note{font-weight:500;font-family:var(--font)}
@media (max-width:700px){.vrow{grid-template-columns:1fr}.vnum{text-align:left}}
/* the header: the color scheme switcher (the Practice Database page's, lines 66-69 there) and the buttons to the practice's pages */
.tools{display:flex;gap:10px;align-items:center;flex-wrap:wrap;justify-content:flex-end;min-width:0;max-width:100%}
.pal{display:inline-flex;border:1px solid var(--line-strong);border-radius:var(--pill);padding:3px;gap:3px;background:var(--surface);flex-wrap:wrap;max-width:100%}
.pal button{border:0;background:transparent;color:var(--muted);font:600 12.5px var(--font);padding:6px 10px;border-radius:var(--pill);cursor:pointer;display:inline-flex;align-items:center;gap:6px}
.pal button i{width:12px;height:12px;border-radius:50%;display:inline-block;border:1px solid rgba(255,255,255,.35)}
.pal button[aria-pressed="true"]{background:var(--accent);color:var(--on-accent)} .pal button[aria-pressed="true"] i{border-color:var(--on-accent)}
.links{display:flex;gap:8px;flex-wrap:wrap;margin:0 0 12px}.links .btn{display:inline-flex;align-items:center;gap:6px}.btn .ext{font-size:12px;opacity:.75}
/* the Practice Database page's pieces (tools/db/practice_db_page.html): pills, bar rows, health checks, page cards, census sections */
.mono{font-family:var(--mono);font-variant-numeric:tabular-nums}.eyebrow{font:600 11px/1 var(--font);letter-spacing:.14em;text-transform:uppercase;color:var(--dim)}
.pill{display:inline-flex;align-items:center;gap:6px;border-radius:var(--pill);padding:3px 10px;font:700 12px var(--font);letter-spacing:.02em;white-space:nowrap}
.pill.ok,.pill.signed{background:var(--ok-soft);color:var(--ok)}.pill.warn,.pill.flagged{background:var(--warn-soft);color:var(--warn)}.pill.bad{background:var(--bad-soft);color:var(--bad)}.pill.run,.pill.ready{background:var(--accent-soft);color:var(--accent)}.pill.dim,.pill.noname{background:var(--surface-2);color:var(--muted)}
.grid2{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:14px;margin-bottom:14px}.grid2>.block{margin-bottom:0}@media (max-width:420px){.grid2{grid-template-columns:minmax(0,1fr)}}
.hbars{display:grid;gap:7px}.hb{display:grid;grid-template-columns:minmax(120px,46%) minmax(0,1fr) auto;gap:10px;align-items:center;font-size:13.5px;min-width:0}
.hb .nm{color:var(--ink-2);line-height:1.25;overflow-wrap:anywhere}.hb .tr{height:12px;background:var(--surface-2);border-radius:6px;overflow:hidden;position:relative}
.hb .tr i{position:absolute;inset:0 auto 0 0;background:var(--accent);border-radius:6px;min-width:4px}.hb .tr i.alt{background:var(--accent-2)}.hb .tr i.ok{background:var(--ok)}.hb .tr i.warn{background:var(--warn)}.hb .tr i.bad{background:var(--bad)}.hb .tr i.dim{background:var(--line-strong)}
.hb .vl{font-family:var(--mono);font-variant-numeric:tabular-nums;color:var(--ink);font-size:13px;white-space:nowrap}.hb .vl small{color:var(--dim);font:500 11.5px var(--mono);margin-left:6px}
.health{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:8px}@media (max-width:420px){.health{grid-template-columns:minmax(0,1fr)}}
.hc{display:grid;grid-template-columns:auto 1fr;gap:10px;align-items:start;background:var(--surface-2);border:1px solid var(--line);border-radius:12px;padding:10px 12px;min-width:0}
.hc .dot{width:12px;height:12px;border-radius:50%;margin-top:5px;background:var(--dim)}.hc.ok .dot{background:var(--ok)}.hc.warn .dot{background:var(--warn)}.hc.bad .dot{background:var(--bad)}
.hc b{display:block;font-size:13.5px}.hc span{color:var(--muted);font-size:12.5px;overflow-wrap:anywhere}
.pages{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:8px}
.pages a{display:flex;flex-direction:column;gap:3px;text-decoration:none;color:var(--ink);background:var(--surface-2);border:1px solid var(--line);border-radius:12px;padding:10px 12px;min-width:0}
.pages a:hover{border-color:var(--accent)}.pages .nm{display:flex;justify-content:space-between;gap:8px;font-weight:700;font-size:13.5px}.pages .kd{font:600 10.5px var(--font);letter-spacing:.12em;text-transform:uppercase;color:var(--accent)}.pages .nt{color:var(--muted);font-size:12.5px}
.censuscat{border:1px solid var(--line);background:var(--surface);border-radius:var(--r);padding:12px 14px;margin:0 0 14px;display:grid;gap:9px}
.csecs{display:flex;gap:7px;flex-wrap:wrap}.csec{border:1px dashed var(--line-strong);color:var(--muted);border-radius:var(--pill);padding:5px 11px;font:600 12.5px var(--font)}.csec.cur{border-style:solid;border-color:var(--accent);background:var(--accent);color:var(--on-accent)}
.chipbtn{border:1px solid var(--line-strong);background:var(--surface);color:var(--muted);border-radius:var(--pill);padding:5px 11px;font:600 12.5px var(--font);cursor:pointer;display:inline-flex;gap:6px;align-items:center}
.chipbtn[aria-pressed="true"]{background:var(--accent);color:var(--on-accent);border-color:var(--accent)}.chipbtn .n{font-family:var(--mono)}
tr.click{cursor:pointer}tr.click:hover td{background:var(--accent-soft)}tr.exp td{background:var(--bg-deep)!important;color:var(--ink-2);font-size:13px}
.weeknote{margin:12px 0 0;max-width:78ch;color:var(--ink-2);font-size:14px;line-height:1.55}
details.more{margin:0 0 14px}details.more>summary{cursor:pointer;color:var(--accent);font:600 13.5px var(--font);padding:8px 0}
.browser{display:grid;grid-template-columns:minmax(220px,300px) minmax(0,1fr);gap:14px}@media (max-width:760px){.browser{grid-template-columns:minmax(0,1fr)}}
.doclist{display:flex;flex-direction:column;gap:4px;max-height:520px;overflow:auto;border:1px solid var(--line);border-radius:12px;padding:6px;background:var(--bg-deep)}
.doclist button{text-align:left;border:1px solid transparent;background:transparent;color:var(--ink-2);font:500 13px var(--mono);padding:7px 9px;border-radius:8px;cursor:pointer;display:flex;justify-content:space-between;gap:8px;overflow-wrap:anywhere}
.doclist button:hover{border-color:var(--line-strong)}.doclist button[aria-pressed="true"]{background:var(--accent-soft);border-color:var(--accent);color:var(--ink)}.doclist button small{color:var(--dim);font-size:11.5px;white-space:nowrap}
pre.json{margin:0;background:var(--bg-deep);border:1px solid var(--line);border-radius:12px;padding:12px 14px;font:500 12.5px/1.45 var(--mono);color:var(--ink-2);overflow:auto;max-height:560px;white-space:pre}
pre.json .k{color:var(--accent-2)}pre.json .s{color:var(--ok)}pre.json .nn{color:var(--accent)}pre.json .b{color:var(--warn)}
/* CCM notes: months beside the month's notes, and the note itself as on paper (white in every color scheme - it is the printed note) */
.ccm{display:grid;grid-template-columns:250px minmax(0,1fr);gap:16px;align-items:start}@media (max-width:820px){.ccm{grid-template-columns:minmax(0,1fr)}}
.months{border:1px solid var(--line);border-radius:var(--r);background:var(--surface);overflow:auto;max-height:72vh}@media (max-width:820px){.months{max-height:none}}
.months a{display:grid;grid-template-columns:1fr auto;gap:2px 10px;padding:9px 14px;border-top:1px solid var(--line);text-decoration:none;color:var(--ink)}.months a:first-child{border-top:0}
.months a:hover{background:var(--surface-2)}.months a[aria-current]{background:var(--accent-soft);box-shadow:inset 3px 0 0 var(--accent)}
.months .mn{font-weight:700}.months .mc{font:500 12.5px var(--mono);color:var(--muted);text-align:right}.months .ms{grid-column:1/-1;font-size:12px;color:var(--dim)}
.flagtext{font-size:12.5px;color:var(--warn);margin-top:3px;max-width:52ch}
.paper{background:#fff;color:#111;border-radius:6px;box-shadow:0 12px 40px rgba(0,0,0,.18);padding:26px 26px 30px 64px;position:relative;font:12.5px/1.42 Arial,Helvetica,sans-serif;overflow:hidden;margin:0 0 14px;color-scheme:light}
.paper .side{position:absolute;left:16px;top:50%;writing-mode:vertical-rl;transform:rotate(180deg) translateY(50%);font-size:13.5px;white-space:nowrap;color:#111}.paper .side.draft{color:#b14d00;font-weight:700;letter-spacing:.06em}
.paper .ptop{display:flex;justify-content:space-between;gap:12px;font-size:11.5px;flex-wrap:wrap}.paper .head{text-align:center;margin:6px 0 14px}.paper .head h2{font:400 22px Arial,Helvetica,sans-serif;color:#666;margin:0 0 4px}
.paper .pgrid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:6px 18px;margin-bottom:14px}.paper .pgrid b{display:inline-block;min-width:74px}
.paper h3{font:700 15px Arial,Helvetica,sans-serif;margin:18px 0 6px;color:#111}.paper table{border-collapse:collapse;width:100%;font-size:12px}.paper .tablewrap table{min-width:0}
.paper td,.paper th{text-align:left;padding:3px 8px 3px 0;border-bottom:1px solid #ddd;font:400 12px Arial,Helvetica,sans-serif;color:#111;background:#fff!important;letter-spacing:0;text-transform:none;white-space:normal}.paper th{font-weight:700}
.paper .late{border:1px solid #999;padding:10px 12px;margin-top:6px}.paper .late p{margin:0 0 8px;color:#111}.paper .late p:last-child{margin:0}.paper ul{padding-left:18px;margin:4px 0}.paper li{color:#111}
.paper .sig{margin-top:38px;border-top:1px solid #333;width:min(280px,100%);padding-top:4px;font-size:11.5px}.paper .pfoot{margin-top:26px;text-align:center;font-size:11px;color:#444}
@media (max-width:640px){.paper{padding:20px 16px 24px 46px}.paper .pgrid{grid-template-columns:minmax(0,1fr)}.hb{grid-template-columns:minmax(100px,40%) minmax(0,1fr) auto}.pal,.seg{border-radius:14px}}
/* the Insurance Refresh Board in the dashboard (read-only cards; every class starts with rb-). Palette tokens only, so it follows the
   five schemes like every other page. Its Stedi lookups and API results share --accent-2, as on the board they share one blue
   (--cascade is a pale chart fill on Light and does not read as text there) */
.rb-asof{font-size:13px;color:var(--muted);max-width:90ch;margin:0 0 12px}.rb-asof.stale{color:var(--warn)}
.rb-tools{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin:0 0 10px}.rb-tools input{flex:1 1 260px;border-radius:999px;padding:9px 14px;font-size:16px;-webkit-appearance:none;appearance:none}.rb-tools input::placeholder{color:var(--muted)}
.rb-count{font-size:12.5px;color:var(--dim);margin:0 0 8px}.rb-empty{color:var(--muted);padding:18px 4px}
.rb-card{background:var(--surface);border:1px solid var(--line);border-radius:14px;padding:14px 16px;margin:0 0 10px;display:grid;grid-template-columns:minmax(190px,1.1fr) minmax(240px,2fr) 84px 132px;gap:12px 18px;align-items:start}
.rb-card>*{min-width:0}.rb-card.t-done{opacity:.8}.rb-card.is-new{border-color:var(--accent);box-shadow:inset 4px 0 0 var(--accent)}.rb-wide{grid-column:1/-1}
.rb-who{font-weight:700;font-size:16px;overflow-wrap:anywhere}
.rb-fac{display:flex;flex-wrap:wrap;align-items:center;gap:6px 8px;margin:0 0 8px}
.rb-fac .fname{font:700 12.5px/1.2 var(--font);background:var(--bg-deep);border:1px solid var(--line);border-radius:6px;padding:4px 8px;max-width:100%;overflow-wrap:anywhere}
.rb-fac .fkind{font:700 10.5px/1 var(--font);letter-spacing:.07em;text-transform:uppercase;border-radius:999px;padding:5px 8px;white-space:nowrap;background:var(--surface-2);color:var(--muted)}
.rb-fac .fkind.snf{color:var(--accent-2)}.rb-fac .fkind.alf{color:var(--accent)}.rb-fac .fkind.hosp,.rb-fac .fkind.irf{color:var(--bad)}
.rb-fac .fdos{font:11.5px var(--mono);color:var(--muted)}.rb-fac .fres{flex:1 1 100%;font-size:12px;color:var(--muted);margin-top:-3px}.rb-fac .fres b{font-weight:600;color:var(--ink)}
.rb-fac.unknown .fname{color:var(--muted);font-weight:600;border-style:dashed}
.rb-idline{margin-top:5px;font-family:var(--mono);font-size:12.5px;line-height:1.6;color:var(--ink-2)}.rb-idline .part{display:inline-block;max-width:100%;overflow-wrap:anywhere}
.rb-idline .k{color:var(--dim);font-family:var(--font);font-size:10.5px;letter-spacing:.06em;text-transform:uppercase;font-weight:700;margin-right:4px}
.rb-idline .sep{color:var(--line-strong);margin:0 6px}.rb-idline .car{color:var(--muted);font-family:var(--font);font-size:12px}
.rb-lead{display:block;font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:var(--dim);font-weight:700;margin-bottom:3px}.rb-card.is-new .rb-lead{color:var(--accent)}
.rb-ask{font-size:16px;font-weight:600;line-height:1.35;overflow-wrap:anywhere}
.rb-need .rest,.rb-need .why,.rb-need .facs{margin-top:6px;font-size:13.5px;color:var(--ink-2);white-space:pre-wrap;overflow-wrap:anywhere}.rb-need .why,.rb-need .facs{color:var(--muted)}
.rb-amt{font:600 15px var(--mono);text-align:right;font-variant-numeric:tabular-nums}
.rb-pill{display:inline-block;border-radius:999px;padding:3px 10px;font-size:12px;font-weight:700;white-space:nowrap;border:1px solid transparent}
.rb-pill.william{color:var(--accent);border-color:var(--accent)}.rb-pill.claude{color:var(--accent-2);border-color:var(--accent-2)}.rb-pill.done{color:var(--ok);border-color:var(--ok)}
.rb-pill.new{background:var(--accent);color:var(--on-accent);margin-right:6px}.rb-upd{margin-top:6px;font-size:12px;color:var(--dim)}
.rb-last{font-size:13px;color:var(--ink-2);border-top:1px dashed var(--line);padding-top:10px;overflow-wrap:anywhere}
.rb-by{font-weight:700;margin-right:8px}.rb-by.w{color:var(--accent)}.rb-by.c{color:var(--accent-2)}.rb-at{color:var(--dim);font-size:12px;margin-left:8px}
.rb-more .btn{padding:6px 12px;font-size:12.5px}.rb-detail{border-top:1px dashed var(--line);padding-top:4px}
.rb-thread,.rb-trail,.rb-api{display:flex;flex-direction:column;gap:6px;margin-top:10px}.rb-th{font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:var(--dim);font-weight:700}
.rb-tnote{font-size:13.5px;white-space:pre-wrap;overflow-wrap:anywhere}.rb-trail{border-left:2px solid var(--line-strong);padding-left:10px}
.rb-trail .tr{display:grid;grid-template-columns:16px minmax(90px,170px) 1fr;gap:6px;font-size:12.5px;line-height:1.4;align-items:baseline}
.rb-trail .src{font-weight:600;overflow-wrap:anywhere}.rb-trail .res{color:var(--muted);overflow-wrap:anywhere}.rb-trail .ic{font-weight:700;text-align:center;color:var(--dim)}
.rb-trail .tr.ok .ic{color:var(--ok)}.rb-trail .tr.no .ic{color:var(--bad)}.rb-trail .tr.human .ic{color:var(--accent)}.rb-trail .tr.stedi .ic{color:var(--accent-2)}.rb-th .rb-key{color:var(--accent-2)}
.rb-api .ab{background:var(--bg-deep);border:1px solid var(--line);border-left:4px solid var(--accent-2);border-radius:8px;padding:8px 12px}
.rb-api .ah{display:flex;justify-content:space-between;gap:10px;font:700 12px var(--font);letter-spacing:.05em;text-transform:uppercase;color:var(--accent-2);margin-bottom:3px}
.rb-api .ax{font-family:var(--mono);font-size:12.5px;white-space:pre-wrap;word-break:break-word;color:var(--ink-2)}
@media (max-width:860px){.rb-card{grid-template-columns:1fr}.rb-amt{text-align:left}}
@media (max-width:560px){.rb-trail .tr{grid-template-columns:16px 1fr}.rb-trail .res{grid-column:2}}
</style>
</head>
<body>
<div class="wrap">
  <header class="top">
    <div><div class="brand"><a href="#home">ehpa · Practice Applications</a></div><div class="note">Runs inside the practice's Neon project · sign-in required</div></div>
    <div class="tools">
      <div class="pal" role="group" aria-label="Color scheme" id="pal">${pal}</div>
      <div id="session" hidden style="display:flex;gap:8px;align-items:center;flex-wrap:wrap"><span id="who" class="note"></span><button class="btn" id="refresh" type="button">Refresh</button><button class="btn" id="signout" type="button">Sign out</button></div>
    </div>
  </header>
  <nav class="links" id="links" aria-label="The practice's pages on claude.ai" hidden></nav>
  <nav class="appbar" id="appbar" aria-label="Applications" hidden></nav>
  <div class="status" id="status" role="status" aria-live="polite"></div>

  <section id="gate" class="gate" hidden>
    <h1>Sign in to the practice applications</h1>
    <p class="note">One sign-in opens everything the practice runs here. The session ends after ${attr(idleMinutes)} minutes without activity.</p>
    <ul><li>Universal Practice Optimization</li><li>Practice Optimization for this practice</li><li>ehpa Practice Database (the billing dashboard and the Practice Database page's views)</li><li>CCM notes (read-only; signing stays on the CCM Documentation Hub)</li><li>Learn</li></ul>
    <button class="btn primary" id="google" type="button" style="width:100%;margin:14px 0 6px;padding:12px">Continue with Google</button>
    <p class="small" style="text-align:center;margin:0 0 6px">or use an email and password</p>
    <form id="form-signin">
      <label for="si-email">Email</label><input id="si-email" name="email" type="email" autocomplete="username" required>
      <label for="si-password">Password</label><input id="si-password" name="password" type="password" autocomplete="current-password" required minlength="8">
      <div class="row"><button class="btn primary" type="submit">Sign in</button><button class="btn" type="button" id="toggle-signup">First time? Create the account</button></div>
    </form>
    <form id="form-signup" hidden>
      <label for="su-name">Name</label><input id="su-name" name="name" type="text" autocomplete="name" required>
      <label for="su-email">Email</label><input id="su-email" name="email" type="email" autocomplete="username" required>
      <label for="su-password">Password (12 or more characters)</label><input id="su-password" name="password" type="password" autocomplete="new-password" required minlength="12">
      <div class="row"><button class="btn primary" type="submit">Create account and sign in</button><span class="small">Only the practice's listed email sees any data.</span></div>
    </form>
  </section>

  <section id="app" hidden>
    <nav class="rail" id="nav" aria-label="Sections" hidden></nav>
    <main id="main"></main>
  </section>
</div>
<script src="/app.js" defer></script>
</body>
</html>`;
}

function attr(s: string): string {
  return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c] as string);
}
