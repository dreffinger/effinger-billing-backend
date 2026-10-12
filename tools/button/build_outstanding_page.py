#!/usr/bin/env python3
# PLAIN ENGLISH (builds the "Outstanding Claims" page - William 10/11/2026: "a new artifact with a summary of all outstanding
#   claims, midnight theme, two buttons, same as the rest")
# Decides: nothing. Takes outstanding_claims.json (from tools/button/outstanding_claims.py: the unpaid list summed up - chart and
#   visit ids, carriers, dates of service, dollars; no names) and writes the page HTML with that snapshot inside it. On the page a
#   saved GitHub token lets it pull reports/button/outstanding_latest.json from main, so every Billing Button run refreshes it.
#   python3 tools/button/build_outstanding_page.py <outstanding_claims.json> <out.html>
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fab  # noqa: E402

PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Outstanding Claims</title>
<meta name="description" content="Every open insurance balance of Effinger Health PA, summed by payer, age and month of service, from the AdvancedMD unpaid list - refreshed by every Billing Button run.">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Quicksand:wght@400;500;600;700&family=JetBrains+Mono:wght@500;600&display=swap">
<style>
/* layout: four tiles, the age bar, then payers (the table that answers "who owes us"), month of service, oldest / largest, and the
   searchable list of every visit. Midnight tokens from the ehpa Billing Button page; dark first, light when the device asks. */
:root{--bg:#082f35;--bg-deep:#07292f;--surface:#214449;--surface-2:#2d5057;--line:#1d4b53;--line-strong:#3c6169;--ink:#f4f5f7;--ink-2:#dee2e6;--muted:#cacaca;--dim:#9da8b4;--on-accent:#082f35;--accent:#70d6f8;--accent-soft:#1f5a68;--magenta:#f841e0;--ok:#3dd475;--ok-soft:#164a41;--warn:#ffc409;--warn-soft:#3d4020;--bad:#df7079;--bad-soft:#3d1b22;--hero:#041d21;--grad:linear-gradient(135deg,#70d6f8 0%,#f841e0 100%);--font:'Quicksand',system-ui,-apple-system,'Segoe UI',sans-serif;--mono:'JetBrains Mono',ui-monospace,Menlo,Consolas,monospace;--r-md:8px;--r-lg:12px;--r-xl:18px;--pill:999px;color-scheme:dark}
@media (prefers-color-scheme:light){:root:not([data-theme="dark"]){--bg:#ffffff;--bg-deep:#f4f5f8;--surface:#ffffff;--surface-2:#f2f2f2;--line:#d7d8da;--line-strong:#bfbfbf;--ink:#082f35;--ink-2:#222428;--muted:#636469;--dim:#737478;--on-accent:#ffffff;--accent:#0054e9;--accent-soft:#e0f4fd;--magenta:#b5169b;--ok:#1b8037;--ok-soft:#dcfae6;--warn:#917005;--warn-soft:#fff3c4;--bad:#c5000f;--bad-soft:#fbdcdf;--hero:#082f35;--grad:linear-gradient(135deg,#0054e9 0%,#b5169b 100%);color-scheme:light}}
:root[data-theme="light"]{--bg:#ffffff;--bg-deep:#f4f5f8;--surface:#ffffff;--surface-2:#f2f2f2;--line:#d7d8da;--line-strong:#bfbfbf;--ink:#082f35;--ink-2:#222428;--muted:#636469;--dim:#737478;--on-accent:#ffffff;--accent:#0054e9;--accent-soft:#e0f4fd;--magenta:#b5169b;--ok:#1b8037;--ok-soft:#dcfae6;--warn:#917005;--warn-soft:#fff3c4;--bad:#c5000f;--bad-soft:#fbdcdf;--hero:#082f35;--grad:linear-gradient(135deg,#0054e9 0%,#b5169b 100%);color-scheme:light}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:500 15px/1.5 var(--font);-webkit-font-smoothing:antialiased}
.wrap{max-width:1120px;margin:0 auto;padding-block:18px 120px;padding-inline:16px}
h1,h2,h3{margin:0;text-wrap:balance;font-weight:700}
h1{font-size:26px;line-height:1.1} h2{font-size:17px} h3{font-size:15px}
a{color:var(--accent)}
.eyebrow{font:600 11px/1 var(--font);letter-spacing:.14em;text-transform:uppercase;color:var(--dim)}
.mono{font-family:var(--mono);font-variant-numeric:tabular-nums}
.top{display:flex;align-items:center;justify-content:space-between;gap:14px;flex-wrap:wrap;margin-bottom:18px}
.lockup{display:flex;align-items:center;gap:14px}
.mark{width:46px;height:46px;border-radius:12px;background:var(--hero);display:grid;place-items:center}
.mark svg{width:30px;height:30px}
.brand{font:700 12px/1 var(--font);letter-spacing:.2em;text-transform:uppercase;color:var(--accent)}
.tools{display:flex;gap:8px;flex-wrap:wrap}
.btn{border:1px solid var(--line-strong);background:var(--surface);color:var(--ink);font:600 13.5px var(--font);padding:9px 14px;border-radius:var(--pill);cursor:pointer;text-decoration:none}
.btn:hover{border-color:var(--accent)} .btn:focus-visible,select:focus-visible,input:focus-visible{outline:3px solid var(--magenta);outline-offset:2px}
.btn.primary{background:var(--accent);border-color:var(--accent);color:var(--on-accent)}
.sub{color:var(--muted);margin:0 0 18px;font-size:14px;max-width:72ch}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:10px;margin-bottom:14px}
.tile{background:var(--surface);border:1px solid var(--line);border-radius:var(--r-lg);padding:14px 16px}
.tile .eyebrow{margin-bottom:6px} .tile .v{font:700 24px/1.1 var(--mono)} .tile .v small{font:600 12px var(--font);color:var(--muted);margin-left:6px}
.tile.hot .v{color:var(--warn)}
section.block{margin-top:22px}
.block>h2{margin-bottom:10px;display:flex;align-items:baseline;gap:10px;flex-wrap:wrap} .block>h2 .eyebrow{margin-left:auto}
.card{background:var(--surface);border:1px solid var(--line);border-radius:var(--r-lg);padding:16px 18px}
.bar{display:flex;height:26px;border-radius:var(--pill);overflow:hidden;border:1px solid var(--line)}
.bar span{display:block;height:100%}
.legend{display:flex;gap:14px;flex-wrap:wrap;margin-top:10px;font-size:13px;color:var(--muted)}
.legend i{display:inline-block;width:12px;height:12px;border-radius:3px;margin-right:6px;vertical-align:-1px}
.tbl{overflow-x:auto} table{border-collapse:collapse;width:100%;font-size:13px;font-family:var(--mono);font-variant-numeric:tabular-nums}
th,td{text-align:left;padding:6px 8px;border-top:1px solid var(--line);vertical-align:top;white-space:nowrap} th{font:600 11px var(--font);letter-spacing:.08em;text-transform:uppercase;color:var(--dim);border-top:0;cursor:pointer}
td.num,th.num{text-align:right} td.name{font-family:var(--font);white-space:normal;min-width:160px}
tr.total td{font-weight:700;border-top:2px solid var(--line-strong)}
.months{display:flex;align-items:flex-end;gap:4px;height:140px;padding:6px 0 0}
.months .m{flex:1 1 0;display:flex;flex-direction:column;align-items:center;justify-content:flex-end;height:100%;min-width:0}
.months .m i{display:block;width:100%;background:var(--accent);border-radius:4px 4px 0 0;min-height:2px}
.months .m.old i{background:var(--warn)}
.months .m b{font:600 10px var(--mono);color:var(--dim);margin-top:4px;transform:rotate(-45deg);transform-origin:top left;white-space:nowrap}
.filters{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin-bottom:10px}
select,input[type=text],input[type=number],input[type=password]{font:500 14px var(--font);padding:8px 10px;border:1px solid var(--line-strong);border-radius:var(--r-md);background:var(--bg);color:var(--ink)}
.pill{display:inline-flex;align-items:center;border-radius:var(--pill);padding:3px 10px;font:700 12px var(--font)}
.pill.ok{background:var(--ok-soft);color:var(--ok)} .pill.warn{background:var(--warn-soft);color:var(--warn)} .pill.bad{background:var(--bad-soft);color:var(--bad)} .pill.dim{background:var(--surface-2);color:var(--muted)}
.note{color:var(--muted);font-size:13.5px} .note b{color:var(--ink)}
.status{font-size:13.5px;color:var(--muted);min-height:1.4em} .status.err{color:var(--bad)} .status.ok{color:var(--ok)}
.settings .field{display:flex;flex-direction:column;gap:6px;margin-top:10px}
ol.how{margin:8px 0 0;padding-left:20px;color:var(--muted);font-size:14px}
.two{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:14px}
@media (max-width:820px){.two{grid-template-columns:1fr}}
</style>
</head>
<body>
<div class="wrap">
  <header class="top">
    <div class="lockup">
      <div class="mark" aria-hidden="true"><svg viewBox="0 0 64 64" fill="none"><path d="M55.04 32A23.04 23.04 0 1 0 47.42 49.12" stroke="#70d6f8" stroke-width="5.4" stroke-linecap="round"/><path d="M32 19.84V44.16M19.84 32H44.16" stroke="#f841e0" stroke-width="6.2" stroke-linecap="round"/></svg></div>
      <div><div class="brand">ehpa</div><h1>Outstanding Claims</h1></div>
    </div>
    <div class="tools">
      <button class="btn" id="theme-btn" type="button">Theme</button>
      <button class="btn" id="refresh-btn" type="button" title="Pull the newest summary the Billing Button wrote to GitHub">Refresh from GitHub</button>
      <button class="btn" id="settings-btn" type="button">Token</button>
      <a class="btn" href="https://claude.ai/artifact/6aYHyrozpmiCCf6GbM95EN" target="_blank" rel="noopener">Money Ledger</a>
    </div>
  </header>
  <p class="sub">Every open insurance balance on the AdvancedMD unpaid list, summed by payer, by age of the date of service and by month of service. Chart and visit ids only. Snapshot <span class="mono" id="asof"></span><span id="src"></span>. Age counts from the date of service; a secondary claim is timely from the primary's remit, so the age buckets are a guide, not a verdict.</p>

  <div class="tiles" id="tiles"></div>

  <section class="block">
    <h2>By age of service <span class="eyebrow">share of the open dollars</span></h2>
    <div class="card"><div class="bar" id="agebar"></div><div class="legend" id="agelegend"></div></div>
  </section>

  <section class="block">
    <h2>By payer <span class="eyebrow">click a heading to sort</span></h2>
    <div class="card tbl"><table id="payers"><thead><tr><th data-k="carrier">Carrier</th><th data-k="name">Payer</th><th class="num" data-k="n">Visits</th><th class="num" data-k="dollars">Open $</th><th class="num" data-k="b0">0-30</th><th class="num" data-k="b1">31-60</th><th class="num" data-k="b2">61-90</th><th class="num" data-k="b3">91-180</th><th class="num" data-k="b4">181-365</th><th class="num" data-k="b5">365+</th><th class="num" data-k="oldest_days">Oldest (days)</th></tr></thead><tbody></tbody></table></div>
  </section>

  <section class="block">
    <h2>By month of service <span class="eyebrow">open dollars · amber = over a year old</span></h2>
    <div class="card"><div class="months" id="months"></div></div>
  </section>

  <section class="block two">
    <div class="card"><h3>Oldest open visits</h3><div class="tbl"><table id="oldest"><thead><tr><th>Visit</th><th>Chart</th><th>Carrier</th><th>DOS</th><th class="num">Days</th><th class="num">Open $</th></tr></thead><tbody></tbody></table></div></div>
    <div class="card"><h3>Largest open visits</h3><div class="tbl"><table id="largest"><thead><tr><th>Visit</th><th>Chart</th><th>Carrier</th><th>DOS</th><th class="num">Days</th><th class="num">Open $</th></tr></thead><tbody></tbody></table></div></div>
  </section>

  <section class="block">
    <h2>Every open visit <span class="eyebrow" id="rows-count"></span></h2>
    <div class="card">
      <div class="filters">
        <label>Carrier <select id="f-car"><option value="">all</option></select></label>
        <label>Older than <input type="number" id="f-days" min="0" step="30" value="0" style="width:90px"> days</label>
        <label>Chart or visit id <input type="text" id="f-q" placeholder="17472703 or 19456186" style="width:200px"></label>
        <button class="btn" id="f-all" type="button">Show all rows</button>
      </div>
      <div class="tbl"><table id="rows"><thead><tr><th data-k="visitid">Visit</th><th data-k="patientid">Chart</th><th data-k="carriercode">Carrier</th><th data-k="dos">DOS</th><th class="num" data-k="days">Days</th><th class="num" data-k="insbalance">Open $</th></tr></thead><tbody></tbody></table></div>
      <p class="note" id="rows-note"></p>
    </div>
  </section>

  <section class="block settings" id="settings" hidden>
    <h2>GitHub token</h2>
    <div class="card">
      <p class="note">With a <b>fine-grained personal access token</b> for this one repository (Contents: read), this page pulls <span class="mono">reports/button/outstanding_latest.json</span> from <span class="mono">main</span> - the summary every Billing Button run writes. The token stays in this browser only (localStorage).</p>
      <div class="field"><label for="tok">Token</label><input type="password" id="tok" autocomplete="off" placeholder="github_pat_…"></div>
      <div class="filters" style="margin-top:10px"><button class="btn primary" id="tok-save" type="button">Save in this browser</button><button class="btn" id="tok-forget" type="button">Forget</button></div>
      <div class="status" id="tok-status"></div>
    </div>
  </section>
</div>

<script id="data" type="application/json">__DATA__</script>
<script>
(function(){
  'use strict';
  const $=s=>document.querySelector(s);
  const esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
  const money=n=>{ const v=Number(n)||0; return (v<0?'-':'')+'$'+Math.abs(v).toLocaleString(undefined,{minimumFractionDigits:2,maximumFractionDigits:2}); };
  const money0=n=>'$'+Math.round(Number(n)||0).toLocaleString();
  const ls={get:k=>{try{return localStorage.getItem(k);}catch(e){return null;}}, set:(k,v)=>{try{localStorage.setItem(k,v);}catch(e){}}, del:k=>{try{localStorage.removeItem(k);}catch(e){}}};
  const REPO='dreffinger/effinger-billing-backend';
  const BUCKETS=['0-30','31-60','61-90','91-180','181-365','over 365'];
  const BCOL=['#3dd475','#70d6f8','#9da8b4','#ffc409','#f8a641','#df7079'];
  let D=JSON.parse(document.getElementById('data').textContent||'{}');

  const root=document.documentElement; const order=['auto','dark','light']; let theme=ls.get('ehpa-oc-theme')||'auto';
  function paintTheme(){ if(theme==='auto') root.removeAttribute('data-theme'); else root.setAttribute('data-theme',theme); $('#theme-btn').textContent='Theme: '+theme; }
  $('#theme-btn').addEventListener('click',()=>{ theme=order[(order.indexOf(theme)+1)%order.length]; ls.set('ehpa-oc-theme',theme); paintTheme(); }); paintTheme();

  let tok=ls.get('ehpa-oc-gh-token')||'';
  $('#settings-btn').addEventListener('click',()=>{ $('#settings').hidden=!$('#settings').hidden; if(!$('#settings').hidden) $('#tok').focus(); });
  $('#tok-save').addEventListener('click',()=>{ tok=$('#tok').value.trim(); if(!tok){ setTok('Paste a token first.',true); return; } ls.set('ehpa-oc-gh-token',tok); setTok('Saved in this browser.'); refresh(); });
  $('#tok-forget').addEventListener('click',()=>{ tok=''; ls.del('ehpa-oc-gh-token'); $('#tok').value=''; setTok('Forgotten.'); });
  function setTok(m,err){ const s=$('#tok-status'); s.textContent=m; s.className='status'+(err?' err':' ok'); }
  $('#refresh-btn').addEventListener('click',()=>{ if(!tok){ $('#settings').hidden=false; $('#tok').focus(); setTok('Save a token first.',true); return; } refresh(); });
  async function refresh(){ try{ const r=await fetch('https://api.github.com/repos/'+REPO+'/contents/reports/button/outstanding_latest.json?ref=main',{headers:{'Authorization':'Bearer '+tok,'Accept':'application/vnd.github.raw+json','X-GitHub-Api-Version':'2022-11-28'},cache:'no-store'}); if(!r.ok) throw new Error(r.status+' '+r.statusText); D=await r.json(); render('GitHub main'); $('#refresh-btn').textContent='Refreshed'; setTimeout(()=>{ $('#refresh-btn').textContent='Refresh from GitHub'; },2500); }catch(e){ $('#src').textContent=' · GitHub refresh failed: '+e.message; } }

  // sorting state
  let sortP={k:'dollars',d:-1}, sortR={k:'days',d:-1}, showAll=false;
  function render(src){
    $('#asof').textContent=D.as_of||''; $('#src').textContent=src?' · live from '+src+' ('+(D.at||'')+')':' · embedded when the page was built ('+(D.at||'')+')';
    const o=D.over_365||{};
    $('#tiles').innerHTML=
      '<div class="tile"><div class="eyebrow">Open insurance balance</div><div class="v">'+esc(money0(D.total))+'</div></div>'
     +'<div class="tile"><div class="eyebrow">Open visits</div><div class="v">'+esc((D.visits||0).toLocaleString())+'<small>'+esc((D.charts||0).toLocaleString())+' charts</small></div></div>'
     +'<div class="tile hot"><div class="eyebrow">Over a year from DOS</div><div class="v">'+esc(money0(o.dollars))+'<small>'+esc((o.n||0).toLocaleString())+' visits</small></div></div>'
     +'<div class="tile"><div class="eyebrow">Under 31 days</div><div class="v">'+esc(money0(((D.by_bucket||{})['0-30']||{}).dollars))+'<small>'+esc((((D.by_bucket||{})['0-30']||{}).n||0).toLocaleString())+' visits</small></div></div>';
    const bb=D.by_bucket||{}; const tot=D.total||1;
    $('#agebar').innerHTML=BUCKETS.map((b,i)=>'<span style="width:'+(100*((bb[b]||{}).dollars||0)/tot).toFixed(2)+'%;background:'+BCOL[i]+'" title="'+esc(b)+' days: '+esc(money((bb[b]||{}).dollars))+'"></span>').join('');
    $('#agelegend').innerHTML=BUCKETS.map((b,i)=>'<span><i style="background:'+BCOL[i]+'"></i>'+esc(b)+' days · '+esc(money0((bb[b]||{}).dollars))+' · '+esc(((bb[b]||{}).n||0))+' visits</span>').join('');
    // payers
    const P=(D.by_carrier||[]).map(c=>({carrier:c.carrier,name:c.name||'',n:c.n,dollars:c.dollars,oldest_days:c.oldest_days||0,b0:c.buckets['0-30']||0,b1:c.buckets['31-60']||0,b2:c.buckets['61-90']||0,b3:c.buckets['91-180']||0,b4:c.buckets['181-365']||0,b5:c.buckets['over 365']||0}));
    P.sort((a,b)=>{ const x=a[sortP.k],y=b[sortP.k]; return (x<y?-1:x>y?1:0)*sortP.d; });
    const sum=k=>P.reduce((s,c)=>s+(Number(c[k])||0),0);
    $('#payers tbody').innerHTML=P.map(c=>'<tr><td>'+esc(c.carrier)+'</td><td class="name">'+esc(c.name)+'</td><td class="num">'+c.n+'</td><td class="num">'+esc(money(c.dollars))+'</td>'+['b0','b1','b2','b3','b4','b5'].map(k=>'<td class="num">'+(c[k]?esc(money0(c[k])):'<span style="color:var(--dim)">–</span>')+'</td>').join('')+'<td class="num">'+c.oldest_days+'</td></tr>').join('')
      +'<tr class="total"><td>Total</td><td class="name">'+P.length+' payers</td><td class="num">'+sum('n')+'</td><td class="num">'+esc(money(sum('dollars')))+'</td>'+['b0','b1','b2','b3','b4','b5'].map(k=>'<td class="num">'+esc(money0(sum(k)))+'</td>').join('')+'<td></td></tr>';
    // months
    const M=D.by_month||[]; const mx=Math.max(1,...M.map(m=>m.dollars)); const cutoff=new Date(); cutoff.setDate(cutoff.getDate()-365); const cut=cutoff.toISOString().slice(0,7);
    $('#months').innerHTML=M.map(m=>'<div class="m'+(m.month<cut?' old':'')+'" title="'+esc(m.month)+': '+esc(money(m.dollars))+' · '+m.n+' visits"><i style="height:'+(100*m.dollars/mx).toFixed(1)+'%"></i><b>'+esc(m.month.slice(2))+'</b></div>').join('');
    const rowHtml=r=>'<tr><td>'+esc(r.visitid)+'</td><td>'+esc(r.patientid)+'</td><td>'+esc(r.carriercode)+'</td><td>'+esc(r.dos||'')+'</td><td class="num">'+esc(r.days??'')+'</td><td class="num">'+esc(money(r.insbalance))+'</td></tr>';
    $('#oldest tbody').innerHTML=(D.oldest||[]).slice(0,25).map(rowHtml).join('');
    $('#largest tbody').innerHTML=(D.largest||[]).slice(0,25).map(rowHtml).join('');
    // filters
    const sel=$('#f-car'); const cur=sel.value; sel.innerHTML='<option value="">all carriers</option>'+(D.by_carrier||[]).map(c=>'<option value="'+esc(c.carrier)+'">'+esc(c.carrier)+' · '+esc(c.name||'')+' ('+c.n+')</option>').join(''); sel.value=cur;
    renderRows();
  }
  function filtered(){ const car=$('#f-car').value, days=Number($('#f-days').value)||0, q=$('#f-q').value.trim();
    let R=(D.rows||[]).filter(r=>(!car||r.carriercode===car)&&((r.days||0)>=days)&&(!q||String(r.visitid).includes(q)||String(r.patientid).includes(q)));
    R.sort((a,b)=>{ const x=a[sortR.k]??'',y=b[sortR.k]??''; return (x<y?-1:x>y?1:0)*sortR.d; }); return R; }
  function renderRows(){ const R=filtered(); const show=showAll?R:R.slice(0,300); const dollars=R.reduce((s,r)=>s+(r.insbalance||0),0);
    $('#rows tbody').innerHTML=show.map(r=>'<tr><td>'+esc(r.visitid)+'</td><td>'+esc(r.patientid)+'</td><td>'+esc(r.carriercode)+'</td><td>'+esc(r.dos||'')+'</td><td class="num">'+esc(r.days??'')+'</td><td class="num">'+esc(money(r.insbalance))+'</td></tr>').join('');
    $('#rows-count').textContent=R.length.toLocaleString()+' visits · '+money(dollars); $('#rows-note').textContent=R.length>show.length?('Showing the first '+show.length+' of '+R.length+' - press "Show all rows" for every one.'):''; }
  ['f-car','f-days','f-q'].forEach(id=>$('#'+id).addEventListener('input',()=>{ showAll=false; renderRows(); }));
  $('#f-all').addEventListener('click',()=>{ showAll=true; renderRows(); });
  document.querySelectorAll('#payers th').forEach(th=>th.addEventListener('click',()=>{ const k=th.dataset.k; sortP= sortP.k===k?{k,d:-sortP.d}:{k,d:(k==='carrier'||k==='name')?1:-1}; render(); }));
  document.querySelectorAll('#rows th').forEach(th=>th.addEventListener('click',()=>{ const k=th.dataset.k; sortR= sortR.k===k?{k,d:-sortR.d}:{k,d:(k==='carriercode'||k==='dos')?1:-1}; renderRows(); }));
  render(''); if(tok) refresh();
})();
</script>
</body>
</html>
"""


def main():
    src, dst = sys.argv[1], sys.argv[2]
    data = json.load(open(src))
    html = PAGE.replace("__DATA__", json.dumps(data, separators=(",", ":")).replace("</", "<\\/"))
    html, what = fab.inject(html)
    open(dst, "w", encoding="utf-8").write(html)
    print("outstanding claims page -> %s (%d bytes; %s)" % (dst, len(html), what))


if __name__ == "__main__":
    main()
