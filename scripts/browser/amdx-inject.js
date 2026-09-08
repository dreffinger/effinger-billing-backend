(function () {
  'use strict';
  const w = window;
  if (w.__amdxInstalled) return;
  w.__amdxInstalled = true;

  // ------------------------------------------------------------------
  // 1. POPUPS -> TABS.  AdvancedMD captures window.open at load time, so
  //    this has to run at document-start.  Dropping the "features" string
  //    makes Chrome open a normal tab next to the opener (same tab group).
  //    Every opened window is remembered in window.__popups so the opener
  //    can drive it by script.
  // ------------------------------------------------------------------
  const origOpen = w.open;
  w.__popups = [];
  w.open = function (url, name /* , features ignored */) {
    const p = origOpen.call(w, url, name);
    if (p) w.__popups.push(p);
    return p;
  };

  // ------------------------------------------------------------------
  // 2. Helpers
  // ------------------------------------------------------------------
  const $$ = (sel, root) => Array.prototype.slice.call((root || document).querySelectorAll(sel));
  const visible = (e) => !!e && e.getBoundingClientRect().width > 0;
  const txt = (e) => ((e && (e.textContent || e.value)) || '').replace(/\s+/g, ' ').trim();
  const btnByTitle = (re, root) => $$('button, input[type=button]', root).filter((b) => re.test(b.title || '')).find(visible);
  const btnByText = (re, root) => $$('button, input[type=button]', root).filter((b) => re.test(txt(b))).find(visible);
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  async function waitFor(fn, opts) {
    const o = Object.assign({ timeout: 15000, every: 200 }, opts || {});
    const t0 = Date.now();
    while (Date.now() - t0 < o.timeout) {
      try { const v = fn(); if (v) return v; } catch (e) { /* keep waiting */ }
      await wait(o.every);
    }
    throw new Error('AMDX timeout waiting: ' + (fn.name || fn.toString().slice(0, 60)));
  }
  const setVal = (input, value) => {
    input.focus();
    input.value = value;
    input.dispatchEvent(new Event('input', { bubbles: true }));
    input.dispatchEvent(new Event('change', { bubbles: true }));
    input.blur();
    return input.value;
  };
  const walkFrames = (win, fn, depth) => {
    depth = depth || 0;
    for (let i = 0; i < win.frames.length; i++) {
      const f = win.frames[i];
      try { fn(f); } catch (e) { /* cross-origin */ }
      try { if (depth < 6) walkFrames(f, fn, depth + 1); } catch (e) { /* ignore */ }
    }
  };

  // ------------------------------------------------------------------
  // 3. The macro object
  // ------------------------------------------------------------------
  const AMDX = {
    version: '1.0.2',

    page() {
      const p = location.pathname;
      if (/clm_claimscenter/.test(p)) return 'claims';
      if (/actv_chargeentry/.test(p)) return 'editvisit';
      if (/actv_chargedetail/.test(p)) return 'chargedetail';
      if (/actv_extrainfo/.test(p)) return 'extrainfo';
      if (/legacy_history/.test(p)) return 'history';
      if (/amds\/pm\/app/.test(p)) return 'pmapp';
      return 'other';
    },

    // ---- popup handles (children opened from THIS page) ----
    popups() { return w.__popups.filter((p) => { try { return !p.closed; } catch (e) { return false; } }); },
    lastPopup() { const ps = this.popups(); return ps.length ? ps[ps.length - 1] : null; },

    // ================= CLAIMS CENTER =================
    tab(name) {
      const map = { charge: 0, inspector: 1, submission: 2, unbilled: 3, exclusions: 4, alerts: 5, edi: 6 };
      const el = document.getElementById('mytabs-tab' + map[name]);
      if (!el) throw new Error('no tab ' + name);
      el.click();
      return txt(el);
    },
    counts() {
      const t = document.body.innerText;
      const out = {};
      ['Charge Review', 'Claim Inspector', 'Unbilled', 'Exclusions', 'Run Alerts'].forEach((k) => {
        const m = t.match(new RegExp(k + '\\s*(\\d+)'));
        out[k] = m ? +m[1] : null;
      });
      return out;
    },
    // every claim row in the visible grid (Charge Review / Claim Inspector / Unbilled)
    rows() {
      return $$('tr').filter(visible)
        .filter((t) => Array.prototype.some.call(t.cells, (c) => /^\d{8}$/.test(txt(c))))
        .map((t) => {
          const c = Array.prototype.map.call(t.cells, txt);
          const vi = c.findIndex((x) => /^\d{8}$/.test(x));
          const n = t.nextElementSibling ? Array.prototype.map.call(t.nextElementSibling.cells, txt) : [];
          return {
            visit: c[vi], provider: c[vi + 1], patient: c[vi + 2], carrier: c[vi + 3],
            error: c[vi + 4] || '', count: c[vi + 5] || '',
            dos: n.find((x) => /^\d{2}\/\d{2}\/\d{4}$/.test(x)) || '',
            proc: n.find((x) => /^\d{5}$/.test(x)) || '',
            modifiers: n[3] || '',
            dx: n.find((x) => /^[A-Z]\d{2}/.test(x)) || '',
            checked: !!(t.querySelector('input[type=checkbox]') || {}).checked,
            tr: t,
          };
        });
    },
    summary() { return this.rows().map((r) => `${r.visit} ${r.provider} ${r.patient} ${r.dos} ${r.proc} | ${r.error.slice(0, 40)} (${r.count})`); },
    byPatient() {
      const m = {};
      this.rows().forEach((r) => { (m[r.patient] = m[r.patient] || []).push(`${r.visit} ${r.proc} ${r.dos}`); });
      return m;
    },
    row(visit) {
      const r = this.rows().find((x) => x.visit === String(visit));
      if (!r) throw new Error('visit not in grid: ' + visit);
      return r;
    },
    select(visit) { const r = this.row(visit); r.tr.cells[3].click(); return r.patient + ' ' + r.dos + ' ' + r.proc; },
    check(visit, on) {
      if (on === undefined) on = true;
      const cb = this.row(visit).tr.querySelector('input[type=checkbox]');
      if (cb && cb.checked !== on) cb.click();
      return cb ? cb.checked : null;
    },
    // Unbilled tab: select an error row (e.g. /Insurance order is missing/)
    errorRow(re) {
      const tr = $$('tr').filter(visible).find((t) => t.cells.length <= 6 && re.test(t.textContent));
      if (!tr) throw new Error('error row not found');
      tr.cells[0].click(); tr.click();
      return txt(tr);
    },
    batches() {
      return $$('tr').filter(visible).filter((t) => t.cells.length <= 4 && /^\d{2}\/\d{2}\/\d{4}$/.test(txt(t.cells[0]))).map((t) => Array.prototype.map.call(t.cells, txt).join(' | '));
    },
    viewDetails(visit) { if (visit) this.select(visit); btnByTitle(/View details of the selected visit/).click(); return 'opening Edit Visit ' + (visit || ''); },
    patient(visit) { if (visit) this.select(visit); btnByTitle(/Open the patient from the selected visit/).click(); return 'opening chart'; },
    viewErrors(visit) { if (visit) this.select(visit); btnByText(/View Errors/).click(); },
    // Reinspect checked claims; pass an array of visit #s to check them first. Auto-answers the confirm.
    reinspect(visits) {
      (visits || []).forEach((v) => this.check(v, true));
      const oc = w.confirm; w.confirm = () => true;
      try { btnByTitle(/Reinspect/).click(); } finally { setTimeout(() => { w.confirm = oc; }, 5000); }
      return 'reinspect sent for ' + (visits || ['checked rows']).join(',');
    },
    // Unbilled: mark checked claims Complete (auto-answers the confirm)
    complete(visits) {
      (visits || []).forEach((v) => this.check(v, true));
      const oc = w.confirm; w.confirm = () => true;
      try { btnByText(/^Complete$/).click(); } finally { setTimeout(() => { w.confirm = oc; }, 5000); }
      return 'complete sent';
    },
    // Charge Review: select-all then Approve (auto-answers the confirm)
    approveAll() {
      const all = $$('input[type=checkbox]').filter(visible)[0];
      if (all && !all.checked) all.click();
      const oc = w.confirm; w.confirm = () => true;
      try { btnByTitle(/Approve all checked visits/).click(); } finally { setTimeout(() => { w.confirm = oc; }, 5000); }
      return 'approve sent';
    },
    refresh() { const b = btnByText(/^Refresh$/); if (b) b.click(); return !!b; },

    // ================= EDIT VISIT / CHARGE DETAIL =================
    visit() {
      const g = document.getElementById('divGrid');
      return {
        visit: (document.getElementById('selVisit') || {}).value || (document.title.match(/Visit #: (\d+)/) || [])[1],
        dos: (document.getElementById('txtBeginDate') || {}).value,
        pos: (document.getElementById('selPOS') || {}).value,
        dx: this.dxCodes(),
        grid: g ? txt(g) : '',
        title: document.title,
      };
    },
    dxCodes() { return $$('input[type=text]').filter((i) => /^[A-Z]\d{2}(\.\w+)?$/.test(i.value)).map((i) => i.value); },
    modifiers() { return $$('input[type=text]').filter((i) => /^\d{2}$/.test(i.value)).map((i) => i.value); },
    // Remove (or replace) a diagnosis code in the Edit Visit form.  Does NOT save — call saveCharge() after.
    removeDx(code, replaceWith) {
      const more = btnByTitle(/additional ICD-10 diagnosis codes/);
      if (more) more.click();
      const inp = $$('input[type=text]').find((i) => i.value.replace(/\./g, '') === String(code).replace(/\./g, ''));
      if (!inp) throw new Error('code not on form: ' + code);
      setVal(inp, replaceWith || '');
      return this.dxCodes();
    },
    // Add modifier 25 to the first empty Modifier box (Charge Review 99489 fix). Does NOT save.
    setModifier25() {
      const inputs = $$('input[type=text]').filter(visible);
      // modifier boxes sit right after the procedure code box
      const proc = inputs.find((i) => /^\d{5}$/.test(i.value));
      const idx = inputs.indexOf(proc);
      const mod = inputs.slice(idx + 1, idx + 5).find((i) => i.value === '');
      if (!mod) throw new Error('no empty modifier box');
      return setVal(mod, '25');
    },
    saveCharge() { const b = btnByTitle(/Save charge data to the in-process grid/) || btnByText(/^Save$/); b.click(); return 'saved: ' + txt(document.getElementById('divGrid') || {}); },
    editCharge() { btnByTitle(/Edit the selected charge/).click(); },
    // OK = post & close.  Picks the REAL OK (not AMD's hidden "OK & Stay").
    ok() {
      const b = $$('button').filter(visible).find((x) => /^OK$/i.test(txt(x).replace(/\s/g, '')) && !/okStay/i.test(x.getAttribute('onclick') || ''));
      if (!b) throw new Error('OK button not found');
      b.click();
      return 'ok clicked';
    },
    cancel() { (btnByTitle(/Cancel all changes/) || btnByText(/^Cancel$/)).click(); return 'cancel'; },
    closeDetail() { btnByText(/^Close$/).click(); return 'close'; },

    // Open Extra Information (as a tab, tracked) and resolve with its window once the form is loaded.
    async extraInfo() {
      const before = this.popups().length;
      const b = btnByTitle(/Edit Extra Information/) || btnByText(/Extra Info/);
      if (!b) throw new Error('Extra Info button not found');
      b.click();
      const p = await waitFor(() => { const ps = this.popups(); return ps.length > before ? ps[ps.length - 1] : null; });
      await waitFor(() => p.document && p.document.getElementById('hospitalizationfrom'));
      await wait(400);
      return p;
    },
    // Read the hospitalization dates and close the Extra Info box without changes.
    async readHospDate() {
      const p = await this.extraInfo();
      const d = p.document;
      const out = { visit: d.getElementById('txtVisit').value, from: d.getElementById('hospitalizationfrom').value, to: d.getElementById('hospitalizationto').value };
      Array.prototype.find.call(d.querySelectorAll('button'), (b) => /^Close$/.test(txt(b))).click();
      return out;
    },
    // THE Block-A macro: open Extra Info, set the first Hospitalization Dates box, Save & Close, verify closed.
    async setHospDate(date) {
      if (!/^\d{2}\/\d{2}\/\d{4}$/.test(date)) throw new Error('date must be MM/DD/YYYY');
      const p = await this.extraInfo();
      const d = p.document;
      const f = d.getElementById('hospitalizationfrom');
      const visit = d.getElementById('txtVisit').value;
      const before = f.value;
      setVal(f, date);
      Array.prototype.find.call(d.querySelectorAll('button'), (b) => /Save\s*&\s*Cl/.test(txt(b))).click();
      await waitFor(() => p.closed, { timeout: 10000 });
      return { visit, before, after: date, closed: true };
    },
    // One-shot Block-A fix for the open Edit Visit: date -> OK.  Returns when the window has posted.
    async fixHospDateAndOk(date) {
      const r = await this.setHospDate(date);
      await wait(500);
      this.ok();
      return r;
    },

    // ================= PM APP (chart / History) =================
    charts() { return $$('li.uib-tab').filter(visible).map((l) => ({ name: txt(l).slice(0, 30), active: /active/.test(l.className) })); },
    // Close a chart tab WITHOUT the bubbling click that closes everything.
    closeChart(nameRe) {
      const li = $$('li.uib-tab').filter(visible).find((l) => nameRe.test(txt(l)));
      if (!li) throw new Error('chart tab not found');
      const x = li.querySelector('.amds-click-out-x');
      x.dispatchEvent(new MouseEvent('click', { bubbles: false, cancelable: true }));
      return 'closed ' + txt(li).slice(0, 30);
    },
    openDialogNames() {
      return $$('a').filter(visible).filter((a) => /Patients currently open/.test((a.closest('.container-fluid') || {}).textContent || '')).map(txt);
    },
    // Click the left-menu "History" item wherever it lives.
    openHistory() {
      let el = null;
      const scan = (doc) => { if (el) return; el = Array.prototype.find.call(doc.querySelectorAll('span'), (e) => e.childElementCount === 0 && txt(e) === 'History' && visible(e)); };
      scan(document);
      walkFrames(w, (f) => scan(f.document));
      if (!el) throw new Error('History menu item not visible');
      el.click(); (el.closest('a,li,div[role]') || el.parentElement).click();
      return 'history clicked';
    },
    historyFrame() {
      let h = null;
      walkFrames(w, (f) => { if (/legacy_history/.test(f.location.href) && visible(f.frameElement)) h = f; });
      return h;
    },
    // Parse the visible History grid: code, I, B, A, date, provider, facility, visit.
    history(limit) {
      const h = this.historyFrame();
      if (!h) throw new Error('History frame not visible (call openHistory first)');
      const rows = $$('tr', h.document).filter((t) => /\d{2}\/\d{2}\/\d{4}/.test(t.textContent));
      return rows.slice(0, limit || 40).map((t) => {
        const c = Array.prototype.map.call(t.cells, txt).filter((x) => x);
        return { code: c[1], I: c[2], B: c[3], A: c[4], date: c[5], provider: c[6], facility: c[7], visit: c[8] };
      });
    },
    // Admission date for a flagged DOS: walk up (newer -> older) from that DOS to the first 99221-99223.
    admissionDate(dos) {
      const hist = this.history(60);
      let seen = false;
      for (const r of hist) {
        if (r.date === dos) seen = true;
        if (!seen) continue;
        if (/^9922[123]$/.test(r.code)) return { admission: r.date, visit: r.visit, needsDate: hist.filter((x) => x.B === 'N' && /^99(22[123]|23[123]|23[89])$/.test(x.code)).map((x) => x.visit + ' ' + x.date) };
      }
      return { admission: null, note: 'no 99223 found walking up from ' + dos + ' — read the date off a B=Y visit with historyDetail()', needsDate: hist.filter((x) => x.B === 'N').map((x) => x.visit + ' ' + x.date) };
    },
    // Open Charge Detail for a History row (opens as a tab thanks to the patch).
    historyDetail(visit) {
      const h = this.historyFrame();
      const tr = $$('tr', h.document).find((t) => new RegExp(visit).test(t.textContent));
      if (!tr) throw new Error('visit not in history: ' + visit);
      tr.cells[1].click(); tr.click();
      h.document.getElementById('btnHisDetail').click();
      return 'opening Charge Detail ' + visit;
    },
    help() {
      return Object.keys(AMDX).filter((k) => typeof AMDX[k] === 'function').join(', ');
    },
  };

  w.AMDX = AMDX;
  // small on-page marker so Claude can confirm the script is active
  const mark = () => { try { document.documentElement.setAttribute('data-amdx', AMDX.version); } catch (e) { /* ignore */ } };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mark); else mark();
})();
