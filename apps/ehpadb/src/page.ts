// The one HTML page the Function serves at "/". It carries no data: a sign-in gate, the nav, an empty main area, and the
// bundled client script at /app.js. Colors follow the practice's Lapis palette (lapis-lazuli ground, bronze accent).
export function pageHtml(authUrl: string, idleMinutes: string): string {
  return `<!doctype html>
<html lang="en" data-auth-url="${attr(authUrl)}" data-idle-minutes="${attr(idleMinutes)}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<title>ehpa Practice Database</title>
<style>
:root{--bg:#0b1f4d;--bg-deep:#071538;--surface:#132c66;--surface-2:#1a387d;--line:#23418a;--line-strong:#3b5fae;--ink:#f2f5ff;--ink-2:#dde5fb;--muted:#b9c6ea;--dim:#8ea1d2;
  --accent:#cf9544;--on-accent:#0b1f4d;--accent-2:#79a6ff;--ok:#5fd394;--bad:#ff7b8a;--mono:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;--font:system-ui,-apple-system,"Segoe UI",sans-serif}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:500 15px/1.5 var(--font);-webkit-font-smoothing:antialiased}
.wrap{max-width:1180px;margin:0 auto;padding:18px 16px 90px}
.top{display:flex;align-items:center;justify-content:space-between;gap:14px;flex-wrap:wrap;margin-bottom:14px}
.brand{font:700 12px/1 var(--font);letter-spacing:.2em;text-transform:uppercase;color:var(--accent)}
h1{font-size:24px;margin:0 0 6px;line-height:1.15}h2{font-size:16px;margin:0}
.lead{color:var(--muted);max-width:70ch;margin:0 0 14px}
.btn{border:1px solid var(--line-strong);background:var(--surface);color:var(--ink);font:600 13.5px var(--font);padding:9px 14px;border-radius:999px;cursor:pointer}
.btn.primary{background:var(--accent);border-color:var(--accent);color:var(--on-accent)}
.status{font-size:13.5px;color:var(--muted);min-height:1.4em}.status.err{color:var(--bad)}.status.ok{color:var(--ok)}
.gate{max-width:420px;margin:60px auto;background:var(--surface);border:1px solid var(--line);border-radius:18px;padding:22px 24px}
.gate label{display:block;font-size:12.5px;color:var(--muted);margin:10px 0 4px}
.gate input{width:100%;background:var(--bg-deep);color:var(--ink);border:1px solid var(--line-strong);border-radius:10px;padding:9px 12px;font:500 14px var(--font)}
.gate .row{display:flex;gap:10px;align-items:center;justify-content:space-between;margin-top:14px}
.gate .small{font-size:12.5px;color:var(--dim)}
.rail{display:flex;gap:6px;flex-wrap:wrap;margin:4px 0 16px;border-bottom:1px solid var(--line);padding-bottom:10px}
.rail a{text-decoration:none;color:var(--muted);font:600 13.5px var(--font);padding:8px 13px;border-radius:999px;border:1px solid transparent;text-transform:capitalize}
.rail a:hover{color:var(--ink);border-color:var(--line-strong)}.rail a[aria-current]{background:var(--accent);color:var(--on-accent)}
.block{background:var(--surface);border:1px solid var(--line);border-radius:18px;padding:16px 18px;margin-bottom:14px;min-width:0}
.block header{display:flex;align-items:baseline;justify-content:space-between;gap:12px;flex-wrap:wrap;margin-bottom:10px}
.note{color:var(--muted);font-size:13px}.dim{color:var(--dim)}.foot{color:var(--dim);font-size:12.5px;margin-top:18px}
table{width:100%;border-collapse:collapse;font-size:13.5px}th{text-align:left;font:600 11px/1 var(--font);letter-spacing:.12em;text-transform:uppercase;color:var(--dim);padding:8px 10px;border-bottom:1px solid var(--line);white-space:nowrap}
td{padding:8px 10px;border-bottom:1px solid var(--line);vertical-align:top;color:var(--ink-2)}tbody tr:nth-child(odd) td{background:var(--surface-2)}
td.num,th.num{text-align:right;font-family:var(--mono);font-variant-numeric:tabular-nums}.tablewrap{overflow-x:auto}.tablewrap table{min-width:560px}
code{font-family:var(--mono);font-size:12px;background:var(--bg-deep);border:1px solid var(--line);border-radius:6px;padding:1px 6px;color:var(--ink-2)}
[hidden]{display:none!important}
</style>
</head>
<body>
<div class="wrap">
  <header class="top">
    <div><div class="brand">ehpa · Practice Database</div><div class="note">Neon Postgres · the practice's permanent store · sign-in required</div></div>
    <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap"><span id="who" class="note"></span><button class="btn" id="refresh" type="button">Refresh</button><button class="btn" id="signout" type="button">Sign out</button></div>
  </header>
  <div class="status" id="status"></div>

  <section id="gate" class="gate" hidden>
    <h1>Sign in</h1>
    <p class="note">One account, William's. The session ends after ${attr(idleMinutes)} minutes without activity.</p>
    <button class="btn primary" id="google" type="button" style="width:100%;margin:12px 0 6px;padding:12px">Continue with Google</button>
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
    <nav class="rail" id="nav" aria-label="Views"></nav>
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
