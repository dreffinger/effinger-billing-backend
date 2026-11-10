with c as (select count(*) as n, count(*) filter (where live) as live_n, sum(settled) filter (where live) as settled from amd.charges),
o as (select count(*) filter (where relname !~ '_before_1110$' and relkind in ('v', 'm')) as live_rel, count(*) filter (where relname ~ '_before_1110$' and relkind in ('v', 'm')) as old_rel,
             count(*) filter (where relname !~ '_before_1110$' and relkind = 'i') as live_idx, count(*) filter (where relname ~ '_before_1110$' and relkind = 'i') as old_idx,
             count(*) filter (where relname ~ '_new_1110') as new_left from pg_class where relnamespace = 'amd'::regnamespace),
r as (select count(*) as n, string_agg(distinct reason_group, ' ' order by reason_group) as groups, count(*) filter (where reason_group || coalesce(carc, '') is distinct from reason_code) as bad from amd.payment_reasons),
ch as (select count(*) as n, count(*) filter (where oldest_charge is null) as no_date, count(*) filter (where oldest_charge = date '1900-01-01' or newest_charge = date '1900-01-01') as y1900, min(oldest_charge) as earliest from amd.charts),
u as (select count(*) as n, count(distinct chart_id) as charts, count(*) filter (where not void and paid <> 0) as money_n, sum(paid) filter (where not void) as money from amd.unapplied_payments),
f as (select count(*) as n, (select count(*) from pg_attribute where attrelid = 'amd.chart_facts'::regclass and attnum > 0 and not attisdropped) as ncols,
             (select count(*) from pg_attribute where attrelid in ('amd.chart_facts'::regclass, 'amd.v_chart_facts'::regclass) and attname in ('zip5', 'city') and not attisdropped) as zipcity from amd.chart_facts),
co as (select count(*) as n, sum(fee) as fee, sum(insurance_paid) as ins, sum(patient_paid) as pat, sum(written_off) as wo, sum(balance) as bal, sum(patient_responsibility) as pr,
              count(*) filter (where denial_codes is not null) as den,
              count(*) filter (where setting = 'nursing facility') as nf, count(*) filter (where setting = 'hospital') as ho, count(*) filter (where setting = 'assisted living') as al, count(*) filter (where setting = 'other') as ot from amd.charge_outcomes),
pl as (select count(*) as n, sum(lines) as lines, sum(lines_paid) as paid_lines from amd.paid_lines_monthly),
dep as (select count(*) as n from pg_depend d join pg_rewrite rw on d.classid = 'pg_rewrite'::regclass and d.objid = rw.oid join pg_class v on v.oid = rw.ev_class
         join pg_class ref on d.refclassid = 'pg_class'::regclass and ref.oid = d.refobjid
        where v.relnamespace = 'amd'::regnamespace and v.relname in ('facility_settings', 'charge_outcomes', 'paid_lines_monthly') and ref.relname ~ '_before_1110$'),
x as (
  select 1 as k, 'objects: live views+tables | kept | live indexes | old indexes | left _new_1110' as check_, o.live_rel || ' | ' || o.old_rel || ' | ' || o.live_idx || ' | ' || o.old_idx || ' | ' || o.new_left as value, '25 | 11 | 14 | 5 | 0' as expected from o
  union all select 2, 'charges: rows | live | settled on live', c.n || ' | ' || c.live_n || ' | ' || c.settled, '84617 | 68727 | 10042860.47' from c
  union all select 3, 'charges has a column paid (0 = no)', (select count(*) from pg_attribute where attrelid = 'amd.charges'::regclass and attname = 'paid' and not attisdropped)::text, '0'
  union all select 4, 'payments not void | write-offs not void', (select sum(paid) filter (where not void) from amd.payments) || ' | ' || (select sum(written_off) filter (where not void) from amd.writeoffs), '3757541.84 | 6285318.63'
  union all select 5, 'reason lines: rows | groups | group+carc not the code', r.n || ' | ' || r.groups || ' | ' || r.bad, '154197 | CO CR OA PI PR | 0' from r
  union all select 6, 'charts: rows | no date | 1900 left | earliest', ch.n || ' | ' || ch.no_date || ' | ' || ch.y1900 || ' | ' || ch.earliest, '11050 | 5534 | 0 | 2022-04-12' from ch
  union all select 7, 'unapplied: rows | charts | with money | money', u.n || ' | ' || u.charts || ' | ' || u.money_n || ' | ' || u.money, '310 | 133 | 149 | 9266.19' from u
  union all select 8, 'chart_facts: rows | columns | zip5/city columns', f.n || ' | ' || f.ncols || ' | ' || f.zipcity, '11050 | 12 | 0' from f
  union all select 9, 'charge_outcomes: rows | fee | ins paid | pat paid | written off | balance', co.n || ' | ' || co.fee || ' | ' || co.ins || ' | ' || co.pat || ' | ' || co.wo || ' | ' || co.bal, '68727 | 10521029.45 | 3756842.04 | 699.80 | 6285318.63 | 478168.98' from co
  union all select 10, 'charge_outcomes: patient_responsibility | rows with denial codes', co.pr || ' | ' || co.den, '1254499.51 | 24044' from co
  union all select 11, 'charge_outcomes by setting: nursing | hospital | assisted | other', co.nf || ' | ' || co.ho || ' | ' || co.al || ' | ' || co.ot, '31883 | 29774 | 5197 | 1873' from co
  union all select 12, 'paid_lines_monthly: rows | lines | paid lines', pl.n || ' | ' || pl.lines || ' | ' || pl.paid_lines, '6167 | 68727 | 46742' from pl
  union all select 13, 'analysis views reading a _before_1110 object', dep.n::text, '0' from dep
  union all select 14, 'schema comment says pseudonymous', (obj_description('amd'::regnamespace, 'pg_namespace') like '%PSEUDONYMOUS, NOT ANONYMOUS%')::text, 'true')
select k, check_, value, expected, (value = expected) as ok_on_prod from x order by k
