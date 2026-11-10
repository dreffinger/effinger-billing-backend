-- migrate_1110.sql  -  corrections to the AdvancedMD history definitions (schema amd), 11/10/2026.
-- Takes a database that holds the definitions of the morning of 11/10/2026 (amd_history.sql, amd_history2.sql, amd_analysis.sql as first
-- deployed) to the corrected ones. After it, the database equals one built fresh from the corrected files in this folder, plus the old
-- objects kept under names that end in _before_1110.
--
-- What it corrects (ids are the checkers'):
--   CF-01  amd.charges.paid is fee minus balance, not money paid         -> the column is named settled, with a column comment
--   CF-02  reason codes that start with a letter were split wrongly      -> reason_group = first two characters, carc = the rest
--   CF-03  charts with no charge showed 1900-01-01                       -> no value
--   CF-04  unapplied payments sat in no table                            -> amd.v_unapplied_payments and amd.unapplied_payments
--   CF-05  payment and write-off dates are days of entry                 -> column comments (the column names stay)
--   second layer: amd.chart_facts named the columns zip5 and city        -> the columns are gone, the comments say what is held
--   amd.facility_settings: the five nursing buildings are set by building code (same output columns)
--   schema comment: pseudonymous, not anonymous
--
-- How it works. Nothing is removed and nothing is changed in place:
--   A. the corrected views and tables are built NEXT TO the old ones, under names that end in _new_1110 (the old ones keep working)
--   B. unapplied payments are added (new objects)
--   C. the names are swapped: old -> ..._before_1110, new -> the usual name. Each swap is ONE statement, so there is no moment without amd.charges
--   D. the three analysis views are re-created so that they read the NEW tables (same output columns, same order)
--   E. the old analysis definitions are kept as ..._before_1110 views, for comparison
--   F. comments
--   G. statistics for the planner
--   The first and the last statement only LOOK (they change nothing): the first stops if this is not a database with the old definitions,
--   the last stops with an error if the end state is not the expected one.
-- Every statement is its own request. Each can be run alone, in this order. Run twice, the second run changes nothing: steps A and C look
-- first whether the swap was already made, the other statements give the same result each time.
-- It writes only to schema amd. It reads raw.documents and writes nothing there.
-- Do NOT run it on a database built fresh from the corrected files: it is only for a database that still holds the old definitions.
-- After it, do not apply the OLD definition files again (orig/): put the corrected files of this folder in their place.
-- Run: python3 neon_exec.py <target> --file migrate_1110.sql        Check: verify_1110.sql (read-only)

-- 0. start check (looks only, changes nothing). Stops with an error when the amd tables are missing, or when amd.charges has no column
-- paid and no old table was kept: such a database was not built from the old files and there is nothing to migrate.
do $mig$
 begin
  if to_regclass('amd.charges') is null or to_regclass('amd.v_charges') is null or to_regclass('amd.charts') is null
     or to_regclass('amd.payment_reasons') is null or to_regclass('amd.chart_facts') is null or to_regclass('amd.payments') is null or to_regclass('amd.writeoffs') is null then
    raise exception 'migrate_1110 stopped: the amd tables are not all there. This file is for a database that holds the definitions of the morning of 11/10/2026.';
  end if;
  if to_regclass('amd.charges_before_1110') is null
     and not exists (select 1 from pg_attribute where attrelid = 'amd.charges'::regclass and attname = 'paid' and not attisdropped) then
    raise exception 'migrate_1110 stopped: amd.charges has no column paid and no old table was kept. Nothing to migrate here.';
  end if;
 end $mig$;

-- A1. charts: build the corrected live view and the corrected table next to the old ones (CF-03: a chart with no charge shows no date in place of 1900-01-01).
-- Skipped when the swap was already made (amd.charts_before_1110 exists). The old amd.charts is not touched here.
do $mig$
 begin
  if to_regclass('amd.charts_before_1110') is null then
    create or replace view amd.v_charts_new_1110 as
    select d.doc_id as chart_id,
           (d.body->>'_written')::timestamptz as pulled_at,
           (d.body->>'pages')::int as pages,
           jsonb_array_length(d.body->'charges') as charge_lines,
           nullif(nullif(d.body->'summary'->>'oldestcharge', '')::timestamp::date, date '1900-01-01') as oldest_charge,
           nullif(nullif(d.body->'summary'->>'newestcharge', '')::timestamp::date, date '1900-01-01') as newest_charge,
           case when d.body->'summary'->>'suminscharges' ~ '^-?\d+(\.\d+)?$' then (d.body->'summary'->>'suminscharges')::numeric end as insurance_charges,
           case when d.body->'summary'->>'sumpatcharges' ~ '^-?\d+(\.\d+)?$' then (d.body->'summary'->>'sumpatcharges')::numeric end as patient_charges,
           case when d.body->'summary'->>'suminspayments' ~ '^-?\d+(\.\d+)?$' then (d.body->'summary'->>'suminspayments')::numeric end as insurance_payments,
           case when d.body->'summary'->>'sumpatpayments' ~ '^-?\d+(\.\d+)?$' then (d.body->'summary'->>'sumpatpayments')::numeric end as patient_payments,
           case when d.body->'summary'->>'suminswriteoffs' ~ '^-?\d+(\.\d+)?$' then (d.body->'summary'->>'suminswriteoffs')::numeric end as insurance_writeoffs,
           case when d.body->'summary'->>'sumpatwriteoffs' ~ '^-?\d+(\.\d+)?$' then (d.body->'summary'->>'sumpatwriteoffs')::numeric end as patient_writeoffs,
           case when d.body->'summary'->>'suminsbal' ~ '^-?\d+(\.\d+)?$' then (d.body->'summary'->>'suminsbal')::numeric end as insurance_balance,
           case when d.body->'summary'->>'sumpatbal' ~ '^-?\d+(\.\d+)?$' then (d.body->'summary'->>'sumpatbal')::numeric end as patient_balance,
           jsonb_array_length(coalesce(d.body->'unapplied_payments', '[]'::jsonb)) as unapplied_payments
    from raw.documents d
    where d.source = 'amd_history' and d.collection = 'txhistory';
    create materialized view if not exists amd.charts_new_1110 as select * from amd.v_charts_new_1110;
  end if;
 end $mig$;

-- A2. charges: build the corrected live view and the corrected table next to the old ones (CF-01: the column paid becomes settled (it is fee minus balance, not money paid)).
-- Skipped when the swap was already made (amd.charges_before_1110 exists). The old amd.charges is not touched here.
do $mig$
 begin
  if to_regclass('amd.charges_before_1110') is null then
    create or replace view amd.v_charges_new_1110 as
    select d.doc_id as chart_id,
           c->>'id' as charge_id,
           c->>'visit' as visit_id,
           case when c->>'dos' ~ '^\d{2}/\d{2}/\d{4}$' then to_date(c->>'dos', 'MM/DD/YYYY') end as dos,
           c->>'proccode' as cpt,
           nullif(c->>'modifiers', '') as modifiers,
           case when c->>'fee' ~ '^-?\d+(\.\d+)?$' then (c->>'fee')::numeric end as fee,
           case when c->>'paid' ~ '^-?\d+(\.\d+)?$' then (c->>'paid')::numeric end as settled,
           case when c->>'insbal' ~ '^-?\d+(\.\d+)?$' then (c->>'insbal')::numeric end as insurance_balance,
           case when c->>'patbal' ~ '^-?\d+(\.\d+)?$' then (c->>'patbal')::numeric end as patient_balance,
           case when c->>'totbal' ~ '^-?\d+(\.\d+)?$' then (c->>'totbal')::numeric end as balance,
           nullif(c->>'carrier', '') as carrier,
           nullif(c->>'subcarriercode', '') as subcarrier,
           case when c->>'billdate' ~ '^\d{2}/\d{2}/\d{4}$' then to_date(c->>'billdate', 'MM/DD/YYYY') end as bill_date,
           case when c->>'billdate' !~ '^\d{2}/\d{2}/\d{4}$' then nullif(c->>'billdate', '') end as bill_status,
           case when c->>'agingdate' ~ '^\d{2}/\d{2}/\d{4}$' then to_date(c->>'agingdate', 'MM/DD/YYYY') end as aging_date,
           nullif(c->>'createtime', '')::timestamp as entered_at,
           c->>'provcode' as provider,
           c->>'npi' as npi,
           c->>'faccode' as facility_code,
           c->>'facname' as facility,
           (c->>'void') = '1' as void,
           ((c->>'void') is distinct from '1' and left(coalesce(c->>'fee', ''), 1) <> '-') as live,
           nullif(c->>'payerinfo', '') as payer_info,
           jsonb_array_length(coalesce(c->'payments', '[]'::jsonb)) as payment_lines,
           jsonb_array_length(coalesce(c->'writeoffs', '[]'::jsonb)) as writeoff_lines
    from raw.documents d
    cross join lateral jsonb_array_elements(d.body->'charges') c
    where d.source = 'amd_history' and d.collection = 'txhistory';
    create materialized view if not exists amd.charges_new_1110 as select * from amd.v_charges_new_1110;
    create index if not exists amd_charges_chart_idx_new_1110 on amd.charges_new_1110 (chart_id);
    create index if not exists amd_charges_dos_idx_new_1110 on amd.charges_new_1110 (dos);
    create index if not exists amd_charges_cpt_idx_new_1110 on amd.charges_new_1110 (cpt, dos);
    create index if not exists amd_charges_id_idx_new_1110 on amd.charges_new_1110 (charge_id);
  end if;
 end $mig$;

-- A3. payment_reasons: build the corrected live view and the corrected table next to the old ones (CF-02: reason_group = first two characters, carc = the rest).
-- Skipped when the swap was already made (amd.payment_reasons_before_1110 exists). The old amd.payment_reasons is not touched here.
do $mig$
 begin
  if to_regclass('amd.payment_reasons_before_1110') is null then
    create or replace view amd.v_payment_reasons_new_1110 as
    select d.doc_id as chart_id,
           c->>'id' as charge_id,
           case when c->>'dos' ~ '^\d{2}/\d{2}/\d{4}$' then to_date(c->>'dos', 'MM/DD/YYYY') end as dos,
           c->>'proccode' as cpt,
           p->>'id' as payment_id,
           case when p->>'date' ~ '^\d{2}/\d{2}/\d{4}$' then to_date(p->>'date', 'MM/DD/YYYY') end as payment_date,
           nullif(p->>'carrier', '') as carrier,
           (p->>'void') = '1' as void,
           r->>'code' as reason_code,
           left(r->>'code', 2) as reason_group,
           nullif(substr(r->>'code', 3), '') as carc,
           case when r->>'amount' ~ '^-?\d+(\.\d+)?$' then (r->>'amount')::numeric end as amount
    from raw.documents d
    cross join lateral jsonb_array_elements(d.body->'charges') c
    cross join lateral jsonb_array_elements(coalesce(c->'payments', '[]'::jsonb)) p
    cross join lateral jsonb_array_elements(coalesce(p->'reasons', '[]'::jsonb)) r
    where d.source = 'amd_history' and d.collection = 'txhistory';
    create materialized view if not exists amd.payment_reasons_new_1110 as select * from amd.v_payment_reasons_new_1110;
    create index if not exists amd_payment_reasons_charge_idx_new_1110 on amd.payment_reasons_new_1110 (charge_id);
  end if;
 end $mig$;

-- A4. chart_facts: build the corrected live view and the corrected table next to the old ones (second layer: the columns zip5 and city are taken out).
-- Skipped when the swap was already made (amd.chart_facts_before_1110 exists). The old amd.chart_facts is not touched here.
do $mig$
 begin
  if to_regclass('amd.chart_facts_before_1110') is null then
    create or replace view amd.v_chart_facts_new_1110 as
    select d.doc_id as chart_id,
           (d.body->>'_written')::timestamptz as pulled_at,
           nullif(d.body->'patient'->>'sex', '') as sex,
           case when d.body->'patient'->>'birth_year' ~ '^(19|20)\d{2}$' then (d.body->'patient'->>'birth_year')::int end as birth_year,
           (d.body->'patient'->>'deceased_flag') = '1' as deceased,
           nullif(d.body->'patient'->>'inactive', '') as inactive,
           nullif(d.body->'patient'->>'state', '') as state,
           nullif(d.body->'patient'->>'profile', '') as profile,
           nullif(d.body->'patient'->>'finclasscode', '') as financial_class,
           nullif(d.body->'patient'->>'insorder', '') as insurance_order,
           jsonb_array_length(coalesce(d.body->'plans', '[]'::jsonb)) as plans,
           case when d.body->'account'->>'laststmtdate' ~ '^\d{2}/\d{2}/\d{4}' then to_date(left(d.body->'account'->>'laststmtdate', 10), 'MM/DD/YYYY') end as last_statement_date
      from raw.documents d
     where d.source = 'amd_history' and d.collection = 'chartfacts';
    create materialized view if not exists amd.chart_facts_new_1110 as select * from amd.v_chart_facts_new_1110;
  end if;
 end $mig$;

-- B1. unapplied payments (CF-04): the live view. New object, nothing replaced.
create or replace view amd.v_unapplied_payments as
select d.doc_id as chart_id,
       p->>'id' as payment_id,
       case when p->>'date' ~ '^\d{2}/\d{2}/\d{4}$' then to_date(p->>'date', 'MM/DD/YYYY') end as payment_date,
       nullif(p->>'createtime', '')::timestamp as posted_at,
       case when p->>'amount' ~ '^-?\d+(\.\d+)?$' then (p->>'amount')::numeric end as amount_raw,
       -case when p->>'amount' ~ '^-?\d+(\.\d+)?$' then (p->>'amount')::numeric end as paid,
       nullif(p->>'carrier', '') as carrier,
       nullif(p->>'paycode', '') as pay_code,
       nullif(p->>'source', '') as source,
       nullif(p->>'checknumber', '') as check_number,
       nullif(p->>'provcode', '') as provider,
       (p->>'void') = '1' as void,
       (p->>'voidoffset') = '1' as void_offset
from raw.documents d
cross join lateral jsonb_array_elements(coalesce(d.body->'unapplied_payments', '[]'::jsonb)) p
where d.source = 'amd_history' and d.collection = 'txhistory';

-- B2. unapplied payments: the table, filled now (a fresh database creates it empty and the refresh script fills it).
create materialized view if not exists amd.unapplied_payments as select * from amd.v_unapplied_payments;

-- B3. unapplied payments: index by chart.
create index if not exists amd_unapplied_payments_chart_idx on amd.unapplied_payments (chart_id);

-- C1. charts: swap the names in ONE statement. Old view, table and indexes get the ending _before_1110 and stay as they are.
-- The corrected ones take the usual names. Runs only when the corrected table is waiting and the swap was not made yet.
do $mig$
 begin
  if to_regclass('amd.charts_new_1110') is not null and to_regclass('amd.charts_before_1110') is null then
    alter view amd.v_charts rename to v_charts_before_1110;
    alter materialized view amd.charts rename to charts_before_1110;
    alter view amd.v_charts_new_1110 rename to v_charts;
    alter materialized view amd.charts_new_1110 rename to charts;
  end if;
 end $mig$;

-- C2. charges: swap the names in ONE statement. Old view, table and indexes get the ending _before_1110 and stay as they are.
-- The corrected ones take the usual names. Runs only when the corrected table is waiting and the swap was not made yet.
do $mig$
 begin
  if to_regclass('amd.charges_new_1110') is not null and to_regclass('amd.charges_before_1110') is null then
    alter view amd.v_charges rename to v_charges_before_1110;
    alter materialized view amd.charges rename to charges_before_1110;
    alter index amd.amd_charges_chart_idx rename to amd_charges_chart_idx_before_1110;
    alter index amd.amd_charges_dos_idx rename to amd_charges_dos_idx_before_1110;
    alter index amd.amd_charges_cpt_idx rename to amd_charges_cpt_idx_before_1110;
    alter index amd.amd_charges_id_idx rename to amd_charges_id_idx_before_1110;
    alter view amd.v_charges_new_1110 rename to v_charges;
    alter materialized view amd.charges_new_1110 rename to charges;
    alter index amd.amd_charges_chart_idx_new_1110 rename to amd_charges_chart_idx;
    alter index amd.amd_charges_dos_idx_new_1110 rename to amd_charges_dos_idx;
    alter index amd.amd_charges_cpt_idx_new_1110 rename to amd_charges_cpt_idx;
    alter index amd.amd_charges_id_idx_new_1110 rename to amd_charges_id_idx;
  end if;
 end $mig$;

-- C3. payment_reasons: swap the names in ONE statement. Old view, table and indexes get the ending _before_1110 and stay as they are.
-- The corrected ones take the usual names. Runs only when the corrected table is waiting and the swap was not made yet.
do $mig$
 begin
  if to_regclass('amd.payment_reasons_new_1110') is not null and to_regclass('amd.payment_reasons_before_1110') is null then
    alter view amd.v_payment_reasons rename to v_payment_reasons_before_1110;
    alter materialized view amd.payment_reasons rename to payment_reasons_before_1110;
    alter index amd.amd_payment_reasons_charge_idx rename to amd_payment_reasons_charge_idx_before_1110;
    alter view amd.v_payment_reasons_new_1110 rename to v_payment_reasons;
    alter materialized view amd.payment_reasons_new_1110 rename to payment_reasons;
    alter index amd.amd_payment_reasons_charge_idx_new_1110 rename to amd_payment_reasons_charge_idx;
  end if;
 end $mig$;

-- C4. chart_facts: swap the names in ONE statement. Old view, table and indexes get the ending _before_1110 and stay as they are.
-- The corrected ones take the usual names. Runs only when the corrected table is waiting and the swap was not made yet.
do $mig$
 begin
  if to_regclass('amd.chart_facts_new_1110') is not null and to_regclass('amd.chart_facts_before_1110') is null then
    alter view amd.v_chart_facts rename to v_chart_facts_before_1110;
    alter materialized view amd.chart_facts rename to chart_facts_before_1110;
    alter view amd.v_chart_facts_new_1110 rename to v_chart_facts;
    alter materialized view amd.chart_facts_new_1110 rename to chart_facts;
  end if;
 end $mig$;

-- D1. facility_settings: re-created on the NEW amd.charges, with the five nursing buildings set by building code. Same output columns.
create or replace view amd.facility_settings as
select f.facility_code, f.facility, f.charge_lines, f.first_dos, f.last_dos,
       case when f.facility_code in ('BRYNW', 'C', 'ASP', 'PRU', 'WMBH') then 'nursing facility'
            when f.facility ~* 'HOSPITAL|MEDICAL CENTER|TMH|HCA FLORIDA' and f.facility !~* 'REHAB' then 'hospital'
            when f.facility ~* 'ALF|ASSISTED|SENIOR LIVING|MEMORY CARE' then 'assisted living'
            when f.facility ~* 'HOME|RESIDENCE' then 'home'
            when f.facility ~* 'OFFICE|CLINIC|EFFINGER|TELE' then 'office'
            else 'other' end as setting
from (select facility_code, max(facility) as facility, count(*) as charge_lines, min(dos) as first_dos, max(dos) as last_dos
      from amd.charges group by 1) f;

-- D2. charge_outcomes: re-created so that it reads the NEW charges, payment_reasons and facility_settings. Same text, same output columns.
create or replace view amd.charge_outcomes as
select c.chart_id, c.charge_id, c.visit_id, c.dos, date_trunc('month', c.dos)::date as dos_month, c.cpt, c.modifiers, c.provider, c.facility_code, s.setting,
       c.carrier as current_carrier, c.fee, c.balance, c.insurance_balance, c.patient_balance, c.bill_date, c.bill_status,
       coalesce(p.insurance_paid, 0) as insurance_paid, coalesce(p.patient_paid, 0) as patient_paid, p.first_insurance_payment, p.paying_carriers, p.payment_lines,
       coalesce(w.written_off, 0) as written_off, w.writeoff_codes,
       r.contractual as contractual_adjustment, r.patient_responsibility, r.sequestration, r.denial_codes
from amd.charges c
left join amd.facility_settings s using (facility_code)
left join (select charge_id,
                  sum(paid) filter (where not void and source = '2') as insurance_paid,
                  sum(paid) filter (where not void and source is distinct from '2') as patient_paid,
                  min(payment_date) filter (where not void and source = '2' and paid > 0) as first_insurance_payment,
                  string_agg(distinct carrier, ' ' order by carrier) filter (where not void and paid > 0) as paying_carriers,
                  count(*) filter (where not void) as payment_lines
           from amd.payments group by 1) p using (charge_id)
left join (select charge_id, sum(written_off) filter (where not void) as written_off,
                  string_agg(distinct writeoff_code, ' ' order by writeoff_code) filter (where not void) as writeoff_codes
           from amd.writeoffs group by 1) w using (charge_id)
left join (select charge_id,
                  sum(amount) filter (where not void and reason_code = 'CO45') as contractual,
                  sum(amount) filter (where not void and reason_group = 'PR') as patient_responsibility,
                  sum(amount) filter (where not void and reason_code = 'CO253') as sequestration,
                  string_agg(distinct reason_code, ' ' order by reason_code) filter (where not void and reason_code not in ('CO45', 'CO253') and reason_group <> 'PR') as denial_codes
           from amd.payment_reasons group by 1) r using (charge_id)
where c.live;

-- D3. paid_lines_monthly: re-created on the new charge_outcomes. Same text, same output columns.
create or replace view amd.paid_lines_monthly as
select dos_month, cpt, setting, coalesce(nullif(paying_carriers, ''), 'not paid') as paid_by,
       count(*) as lines,
       count(*) filter (where insurance_paid > 0) as lines_paid,
       round(sum(fee), 2) as charged, round(sum(insurance_paid), 2) as insurance_paid, round(sum(patient_paid), 2) as patient_paid,
       round(sum(written_off), 2) as written_off, round(sum(balance), 2) as still_open,
       round(avg(insurance_paid) filter (where insurance_paid > 0), 2) as average_insurance_payment
from amd.charge_outcomes
group by 1, 2, 3, 4;

-- E1. the old facility_settings, kept for comparison: the old definition word for word, reading the old charges table.
create or replace view amd.facility_settings_before_1110 as
select f.facility_code, f.facility, f.charge_lines, f.first_dos, f.last_dos,
       case when f.facility ~* 'HOSPITAL|MEDICAL CENTER|TMH|HCA FLORIDA' and f.facility !~* 'REHAB' then 'hospital'
            when f.facility ~* 'ALF|ASSISTED|SENIOR LIVING|MEMORY CARE' then 'assisted living'
            when f.facility ~* 'BRYNWOOD|ASPIRE|CENTRE POINTE|WESTMINSTER|PRUITT|SOUTHWOOD|HEALTH AND REHAB|NURSING|SKILLED|REHAB' then 'nursing facility'
            when f.facility ~* 'HOME|RESIDENCE' then 'home'
            when f.facility ~* 'OFFICE|CLINIC|EFFINGER|TELE' then 'office'
            else 'other' end as setting
from (select facility_code, max(facility) as facility, count(*) as charge_lines, min(dos) as first_dos, max(dos) as last_dos
      from amd.charges_before_1110 group by 1) f;

-- E2. the old charge_outcomes, kept for comparison: the old definition, reading the old tables (payments and write-offs did not change).
create or replace view amd.charge_outcomes_before_1110 as
select c.chart_id, c.charge_id, c.visit_id, c.dos, date_trunc('month', c.dos)::date as dos_month, c.cpt, c.modifiers, c.provider, c.facility_code, s.setting,
       c.carrier as current_carrier, c.fee, c.balance, c.insurance_balance, c.patient_balance, c.bill_date, c.bill_status,
       coalesce(p.insurance_paid, 0) as insurance_paid, coalesce(p.patient_paid, 0) as patient_paid, p.first_insurance_payment, p.paying_carriers, p.payment_lines,
       coalesce(w.written_off, 0) as written_off, w.writeoff_codes,
       r.contractual as contractual_adjustment, r.patient_responsibility, r.sequestration, r.denial_codes
from amd.charges_before_1110 c
left join amd.facility_settings_before_1110 s using (facility_code)
left join (select charge_id,
                  sum(paid) filter (where not void and source = '2') as insurance_paid,
                  sum(paid) filter (where not void and source is distinct from '2') as patient_paid,
                  min(payment_date) filter (where not void and source = '2' and paid > 0) as first_insurance_payment,
                  string_agg(distinct carrier, ' ' order by carrier) filter (where not void and paid > 0) as paying_carriers,
                  count(*) filter (where not void) as payment_lines
           from amd.payments group by 1) p using (charge_id)
left join (select charge_id, sum(written_off) filter (where not void) as written_off,
                  string_agg(distinct writeoff_code, ' ' order by writeoff_code) filter (where not void) as writeoff_codes
           from amd.writeoffs group by 1) w using (charge_id)
left join (select charge_id,
                  sum(amount) filter (where not void and reason_code = 'CO45') as contractual,
                  sum(amount) filter (where not void and reason_group = 'PR') as patient_responsibility,
                  sum(amount) filter (where not void and reason_code = 'CO253') as sequestration,
                  string_agg(distinct reason_code, ' ' order by reason_code) filter (where not void and reason_code not in ('CO45', 'CO253') and reason_group <> 'PR') as denial_codes
           from amd.payment_reasons_before_1110 group by 1) r using (charge_id)
where c.live;

-- E3. the old paid_lines_monthly, kept for comparison.
create or replace view amd.paid_lines_monthly_before_1110 as
select dos_month, cpt, setting, coalesce(nullif(paying_carriers, ''), 'not paid') as paid_by,
       count(*) as lines,
       count(*) filter (where insurance_paid > 0) as lines_paid,
       round(sum(fee), 2) as charged, round(sum(insurance_paid), 2) as insurance_paid, round(sum(patient_paid), 2) as patient_paid,
       round(sum(written_off), 2) as written_off, round(sum(balance), 2) as still_open,
       round(avg(insurance_paid) filter (where insurance_paid > 0), 2) as average_insurance_payment
from amd.charge_outcomes_before_1110
group by 1, 2, 3, 4;

-- F1. schema comment: pseudonymous, not anonymous. What is and is not in these tables.
comment on schema amd is 'AdvancedMD billing history of the practice, pulled 11/10/2026 at the owner''s request. One raw document per chart in raw.documents (source amd_history, collections txhistory, chartfacts and chargedetail). The v_* views read the documents live. The tables of the same name without v_ are indexed copies, refreshed after each load. PSEUDONYMOUS, NOT ANONYMOUS: a chart number (chart_id) can be tied to a name through other data the practice holds. Nothing in these tables is a patient''s name, birth date, address, phone number or member number. amd.chart_facts holds sex, birth year (1936 stands for 1936 or earlier) and state for each chart. Read money by year of service: payment and write-off dates are the day of entry in the billing system, not the day money arrived.';

-- F2. comment, first layer: amd.charts
comment on materialized view amd.charts is 'One row per chart pulled from AdvancedMD. The money columns are AdvancedMD''s own chart totals. A chart with no charge has no dates. Filled from amd.v_charts, refreshed after each load.';

-- F3. comment, first layer: amd.v_charts
comment on view amd.v_charts is 'Live view behind amd.charts: the same columns, read from the documents at query time. Column notes are on amd.charts.';

-- F4. comment, first layer: amd.charts.oldest_charge
comment on column amd.charts.oldest_charge is 'AdvancedMD''s own value: date of the oldest charge on the chart. Empty when the chart has no charge. AdvancedMD sends 1900-01-01 there, which is turned into no value.';

-- F5. comment, first layer: amd.charts.newest_charge
comment on column amd.charts.newest_charge is 'AdvancedMD''s own value, kept as sent and not computed from the lines here. It is not always the newest date of service in amd.charges: on some charts it is earlier (later lines are void) or later (an unapplied payment). Empty when the chart has no charge.';

-- F6. comment, first layer: amd.charts.insurance_payments
comment on column amd.charts.insurance_payments is 'AdvancedMD''s own total of insurance payments on the chart. It counts unapplied payments too, which sit on no charge (see amd.unapplied_payments).';

-- F7. comment, first layer: amd.charts.patient_payments
comment on column amd.charts.patient_payments is 'AdvancedMD''s own total of patient payments on the chart. It counts unapplied payments too (see amd.unapplied_payments).';

-- F8. comment, first layer: amd.charts.unapplied_payments
comment on column amd.charts.unapplied_payments is 'Number of unapplied payment lines on the chart. The lines themselves are in amd.unapplied_payments.';

-- F9. comment, first layer: amd.charges
comment on materialized view amd.charges is 'One row per charge line AdvancedMD holds. Void lines and their negative reversals are included: keep only rows where live is true when adding money. Filled from amd.v_charges, refreshed after each load.';

-- F10. comment, first layer: amd.v_charges
comment on view amd.v_charges is 'Live view behind amd.charges: the same columns, read from the documents at query time. Column notes are on amd.charges.';

-- F11. comment, first layer: amd.charges.settled
comment on column amd.charges.settled is 'Fee minus balance: payments plus write-offs. AdvancedMD sends it under the name paid, and this column was named paid until 11/10/2026. It is NOT money paid. Money paid is in amd.payments (rows that are not void).';

-- F12. comment, first layer: amd.v_charges.settled
comment on column amd.v_charges.settled is 'Fee minus balance: payments plus write-offs. AdvancedMD sends it under the name paid, and this column was named paid until 11/10/2026. It is NOT money paid. Money paid is in amd.payments (rows that are not void).';

-- F13. comment, first layer: amd.charges.live
comment on column amd.charges.live is 'True for a real charge: not void and not a negative reversal. Add money on live rows only.';

-- F14. comment, first layer: amd.charges.void
comment on column amd.charges.void is 'True on a voided charge and on the negative line that reverses it. The pair nets to zero.';

-- F15. comment, first layer: amd.charges.carrier
comment on column amd.charges.carrier is 'The payer the charge sits with today. Not the payer billed first and not the payer that paid: paying payers are in amd.payments.';

-- F16. comment, first layer: amd.charges.npi
comment on column amd.charges.npi is 'Billing number on the charge. It follows the payer the charge sits with, not the clinician. Empty text on about half the lines. Not a clinician key: use provider.';

-- F17. comment, first layer: amd.charges.bill_status
comment on column amd.charges.bill_status is 'Filled only when AdvancedMD sends words in place of a bill date. Empty on every line of the 11/10/2026 pull.';

-- F18. comment, first layer: amd.payments
comment on materialized view amd.payments is 'One row per payment line posted on a charge. paid is minus the amount AdvancedMD stores. Add rows that are not void. Posted money only: unapplied payments are in amd.unapplied_payments. Filled from amd.v_payments, refreshed after each load.';

-- F19. comment, first layer: amd.v_payments
comment on view amd.v_payments is 'Live view behind amd.payments: the same columns, read from the documents at query time. Column notes are on amd.payments.';

-- F20. comment, first layer: amd.payments.payment_date
comment on column amd.payments.payment_date is 'Day the line was entered in the billing system (the same day as posted_at). NOT the day the money arrived. Entry came in bursts: almost nothing from October 2024 to April 2026, then the backlog. Read money by year of service (dos), never by this date.';

-- F21. comment, first layer: amd.v_payments.payment_date
comment on column amd.v_payments.payment_date is 'Day the line was entered in the billing system (the same day as posted_at). NOT the day the money arrived. Entry came in bursts: almost nothing from October 2024 to April 2026, then the backlog. Read money by year of service (dos), never by this date.';

-- F22. comment, first layer: amd.payments.posted_at
comment on column amd.payments.posted_at is 'Time the line was entered in the billing system.';

-- F23. comment, first layer: amd.payments.paid
comment on column amd.payments.paid is 'Money on the line: minus the amount AdvancedMD stores. A negative value is a take-back.';

-- F24. comment, first layer: amd.payments.source
comment on column amd.payments.source is '2 = paid by a payer (carrier is filled). 1 = paid by the patient (no carrier).';

-- F25. comment, first layer: amd.payments.void
comment on column amd.payments.void is 'True on a voided line and on the line that offsets it. The pair nets to zero. Use not void.';

-- F26. comment, first layer: amd.payments.void_offset
comment on column amd.payments.void_offset is 'True only on the offsetting line of a voided pair. Do not use it alone as the filter: the voided line itself would stay in.';

-- F27. comment, first layer: amd.payment_reasons
comment on materialized view amd.payment_reasons is 'One row per adjustment reason code on a payment line, for example CO45, PR2 or COB9. reason_group is the first two characters, carc is the rest. Add rows that are not void. Filled from amd.v_payment_reasons, refreshed after each load.';

-- F28. comment, first layer: amd.v_payment_reasons
comment on view amd.v_payment_reasons is 'Live view behind amd.payment_reasons: the same columns, read from the documents at query time. Column notes are on amd.payment_reasons.';

-- F29. comment, first layer: amd.payment_reasons.reason_group
comment on column amd.payment_reasons.reason_group is 'First two characters of the reason code: CO, PR, OA, PI or CR.';

-- F30. comment, first layer: amd.payment_reasons.carc
comment on column amd.payment_reasons.carc is 'The reason code after the group. It can start with a letter: COB9 is group CO and code B9, COA1 is group CO and code A1.';

-- F31. comment, first layer: amd.payment_reasons.payment_date
comment on column amd.payment_reasons.payment_date is 'Day the payment line was entered in the billing system. NOT the day the money arrived. Read money by year of service (dos), never by this date.';

-- F32. comment, first layer: amd.v_payment_reasons.payment_date
comment on column amd.v_payment_reasons.payment_date is 'Day the payment line was entered in the billing system. NOT the day the money arrived. Read money by year of service (dos), never by this date.';

-- F33. comment, first layer: amd.writeoffs
comment on materialized view amd.writeoffs is 'One row per write-off line on a charge. written_off is minus the amount AdvancedMD stores. Add rows that are not void. Filled from amd.v_writeoffs, refreshed after each load.';

-- F34. comment, first layer: amd.v_writeoffs
comment on view amd.v_writeoffs is 'Live view behind amd.writeoffs: the same columns, read from the documents at query time. Column notes are on amd.writeoffs.';

-- F35. comment, first layer: amd.writeoffs.writeoff_date
comment on column amd.writeoffs.writeoff_date is 'Day the line was entered in the billing system (the same day as posted_at). NOT the day of a payer decision. Entry came in bursts, with a large batch in May 2026. Read money by year of service (dos), never by this date.';

-- F36. comment, first layer: amd.v_writeoffs.writeoff_date
comment on column amd.v_writeoffs.writeoff_date is 'Day the line was entered in the billing system (the same day as posted_at). NOT the day of a payer decision. Entry came in bursts, with a large batch in May 2026. Read money by year of service (dos), never by this date.';

-- F37. comment, first layer: amd.writeoffs.posted_at
comment on column amd.writeoffs.posted_at is 'Time the line was entered in the billing system.';

-- F38. comment, first layer: amd.writeoffs.writeoff_code
comment on column amd.writeoffs.writeoff_code is 'The practice''s write-off code. WOINSBANK is its code for a balance the payer reports paid but that was never posted: such a charge can show no payment in amd.payments although money came in. The text None is AdvancedMD''s own value on a line without a code.';

-- F39. comment, first layer: amd.writeoffs.void
comment on column amd.writeoffs.void is 'True on a voided line and on the line that offsets it. The pair nets to zero. Use not void.';

-- F40. comment, first layer: amd.writeoffs.void_offset
comment on column amd.writeoffs.void_offset is 'True only on the offsetting line of a voided pair. Do not use it alone as the filter.';

-- F41. comment, first layer: amd.unapplied_payments
comment on materialized view amd.unapplied_payments is 'One row per unapplied payment line: money entered on a chart but applied to no charge. These lines are not in amd.payments and have no date of service. Money still unapplied = rows that are not void with paid other than zero. Filled from amd.v_unapplied_payments, refreshed after each load.';

-- F42. comment, first layer: amd.v_unapplied_payments
comment on view amd.v_unapplied_payments is 'Live view behind amd.unapplied_payments: the same columns, read from the documents at query time. Column notes are on amd.unapplied_payments.';

-- F43. comment, first layer: amd.unapplied_payments.payment_date
comment on column amd.unapplied_payments.payment_date is 'Day the line was entered in the billing system (the same day as posted_at). NOT the day the money arrived. These lines have no date of service.';

-- F44. comment, first layer: amd.v_unapplied_payments.payment_date
comment on column amd.v_unapplied_payments.payment_date is 'Day the line was entered in the billing system (the same day as posted_at). NOT the day the money arrived. These lines have no date of service.';

-- F45. comment, first layer: amd.unapplied_payments.paid
comment on column amd.unapplied_payments.paid is 'Money on the line: minus the amount AdvancedMD stores. Many lines are zero or void.';

-- F46. comment, first layer: amd.unapplied_payments.source
comment on column amd.unapplied_payments.source is '2 = from a payer (carrier is filled). 1 = from the patient (no carrier).';

-- F47. comment, first layer: amd.unapplied_payments.provider
comment on column amd.unapplied_payments.provider is 'Clinician code AdvancedMD holds on the unapplied line.';

-- F48. comment, first layer: amd.unapplied_payments.void
comment on column amd.unapplied_payments.void is 'True on a voided line and on the line that offsets it. The pair nets to zero. Use not void.';

-- F49. comment, second layer (chart facts): amd.chart_facts
comment on materialized view amd.chart_facts is 'One row per chart: patient-level facts from AdvancedMD (sex, birth year, state, flags, number of plans). No name, no full birth date, no ZIP code, no city, no marital status. This is pseudonymous patient data, not anonymous data. Filled from amd.v_chart_facts, refreshed after each load.';

-- F50. comment, second layer (chart facts): amd.v_chart_facts
comment on view amd.v_chart_facts is 'Live view behind amd.chart_facts: the same columns, read from the documents at query time. Column notes are on amd.chart_facts.';

-- F51. comment, second layer (chart facts): amd.chart_facts.birth_year
comment on column amd.chart_facts.birth_year is 'Year of birth. 1936 stands for 1936 or earlier: an age of 90 or more is not shown.';

-- F52. comment, second layer (chart facts): amd.chart_facts.state
comment on column amd.chart_facts.state is 'State of the patient''s address. The ZIP code and the city are not stored.';

-- F53. comment, second layer (chart facts): amd.chart_facts.deceased
comment on column amd.chart_facts.deceased is 'True where AdvancedMD carries a deceased mark. Few charts carry one: false does not prove the patient is alive.';

-- F54. comment, second layer (chart facts): amd.chart_facts.inactive
comment on column amd.chart_facts.inactive is 'AdvancedMD''s inactive value. AdvancedMD sent none on any chart in the 11/10/2026 pull: empty on every row.';

-- F55. comment, analysis views: amd.facility_settings
comment on view amd.facility_settings is 'One row per AdvancedMD building code with the kind of building. nursing facility means one of the five nursing buildings the practice serves, set by building code: BRYNW, C, ASP, PRU, WMBH. Every other kind is read from the building name. A new nursing building has to be added to the list by its code.';

-- F56. comment, analysis views: amd.facility_settings.setting
comment on column amd.facility_settings.setting is 'hospital, nursing facility, assisted living, home, office or other. nursing facility = the five nursing buildings only (codes BRYNW, C, ASP, PRU, WMBH). Other nursing homes, the hospital rehab unit and independent living fall under other.';

-- F57. comment, analysis views: amd.charge_outcomes
comment on view amd.charge_outcomes is 'One row per live charge line with what happened to it: payments by insurance and by the patient, write-offs, what is still open, and the adjustment codes posted. Payments are posted money only, taken from amd.payments. Read money by year of service (dos).';

-- F58. comment, analysis views: amd.charge_outcomes.setting
comment on column amd.charge_outcomes.setting is 'Kind of building, from amd.facility_settings. nursing facility = the five nursing buildings only.';

-- F59. comment, analysis views: amd.charge_outcomes.current_carrier
comment on column amd.charge_outcomes.current_carrier is 'The payer the charge sits with today, not the payer that paid. Paying payers are in paying_carriers.';

-- F60. comment, analysis views: amd.charge_outcomes.insurance_paid
comment on column amd.charge_outcomes.insurance_paid is 'Payer payments posted on the line (not void). Posted money only: a line closed with write-off code WOINSBANK can show nothing here although the payer paid.';

-- F61. comment, analysis views: amd.charge_outcomes.first_insurance_payment
comment on column amd.charge_outcomes.first_insurance_payment is 'Day the first payer payment was entered in the billing system. NOT the day the payer paid: do not use it for days-to-pay.';

-- F62. comment, analysis views: amd.charge_outcomes.patient_responsibility
comment on column amd.charge_outcomes.patient_responsibility is 'Sum of the reason lines of group PR (not void). Codes that start with a letter, such as PRA1, are counted.';

-- F63. comment, analysis views: amd.charge_outcomes.denial_codes
comment on column amd.charge_outcomes.denial_codes is 'Every other reason code posted on the line: not CO45, not CO253, not group PR. The name says denial, but the list holds every such code.';

-- F64. comment, analysis views: amd.paid_lines_monthly
comment on view amd.paid_lines_monthly is 'Live charge lines by month of service, procedure code, kind of building and paying carrier. Many rows hold a single line, so a row can be one patient: do not send it outside the practice as it is.';

-- F65. comment, analysis views: amd.paid_lines_monthly.paid_by
comment on column amd.paid_lines_monthly.paid_by is 'All carriers that paid the line, joined in one label. A line paid by two carriers sits under the combined label, so adding one carrier''s rows leaves such lines out: total by carrier from amd.payments. not paid means no carrier paid, and a few of those lines were paid by the patient.';

-- F66. comment, the old objects kept as _before_1110: amd.charts_before_1110
comment on materialized view amd.charts_before_1110 is 'State before the correction of 11/10/2026, kept for comparison. Charts with no charge show 1900-01-01 as oldest and newest charge date. The refresh scripts leave it alone. Use amd.charts.';

-- F67. comment, the old objects kept as _before_1110: amd.v_charts_before_1110
comment on view amd.v_charts_before_1110 is 'Old live view behind amd.charts_before_1110, kept for comparison. Use amd.v_charts.';

-- F68. comment, the old objects kept as _before_1110: amd.charges_before_1110
comment on materialized view amd.charges_before_1110 is 'State before the correction of 11/10/2026, kept for comparison. Its column paid is fee minus balance (payments plus write-offs), NOT money paid. The refresh scripts leave it alone. Use amd.charges.';

-- F69. comment, the old objects kept as _before_1110: amd.v_charges_before_1110
comment on view amd.v_charges_before_1110 is 'Old live view behind amd.charges_before_1110, kept for comparison. Its column paid is fee minus balance, NOT money paid. Use amd.v_charges.';

-- F70. comment, the old objects kept as _before_1110: amd.payment_reasons_before_1110
comment on materialized view amd.payment_reasons_before_1110 is 'State before the correction of 11/10/2026, kept for comparison. Reason codes that start with a letter are split wrongly here (COB9 as group COB and code 9). The refresh scripts leave it alone. Use amd.payment_reasons.';

-- F71. comment, the old objects kept as _before_1110: amd.v_payment_reasons_before_1110
comment on view amd.v_payment_reasons_before_1110 is 'Old live view behind amd.payment_reasons_before_1110, kept for comparison. Use amd.v_payment_reasons.';

-- F72. comment, the old objects kept as _before_1110: amd.chart_facts_before_1110
comment on materialized view amd.chart_facts_before_1110 is 'State before the correction of 11/10/2026, kept for comparison. Old layout with the columns zip5 and city. The refresh scripts leave it alone. Use amd.chart_facts.';

-- F73. comment, the old objects kept as _before_1110: amd.v_chart_facts_before_1110
comment on view amd.v_chart_facts_before_1110 is 'Old live view behind amd.chart_facts_before_1110, kept for comparison. Old layout with the columns zip5 and city. Use amd.v_chart_facts.';

-- F74. comment, the old objects kept as _before_1110: amd.facility_settings_before_1110
comment on view amd.facility_settings_before_1110 is 'Definition before the correction of 11/10/2026, reading amd.charges_before_1110. Old rule by building name: more buildings than the five nursing buildings fall under nursing facility here. For comparison only. Use amd.facility_settings.';

-- F75. comment, the old objects kept as _before_1110: amd.charge_outcomes_before_1110
comment on view amd.charge_outcomes_before_1110 is 'Definition before the correction of 11/10/2026, reading the tables kept as _before_1110. For comparison only. Use amd.charge_outcomes.';

-- F76. comment, the old objects kept as _before_1110: amd.paid_lines_monthly_before_1110
comment on view amd.paid_lines_monthly_before_1110 is 'Definition before the correction of 11/10/2026, reading amd.charge_outcomes_before_1110. For comparison only. Use amd.paid_lines_monthly.';

-- G1. statistics for the planner on the new table amd.charts (reads the table, changes no data).
analyze amd.charts;

-- G2. statistics for the planner on the new table amd.charges (reads the table, changes no data).
analyze amd.charges;

-- G3. statistics for the planner on the new table amd.payment_reasons (reads the table, changes no data).
analyze amd.payment_reasons;

-- G4. statistics for the planner on the new table amd.unapplied_payments (reads the table, changes no data).
analyze amd.unapplied_payments;

-- G5. statistics for the planner on the new table amd.chart_facts (reads the table, changes no data).
analyze amd.chart_facts;

-- H1. last check (looks only, changes nothing). Stops with an error if the end state is not the expected one. No error = the migration is complete.
do $mig$
 begin
  if exists (select 1 from pg_class c join pg_namespace n on n.oid = c.relnamespace where n.nspname = 'amd' and c.relname ~ '_new_1110') then
    raise exception 'migrate_1110 check: an object named _new_1110 is still there, so a swap did not run';
  end if;
  if not exists (select 1 from pg_attribute where attrelid = 'amd.charges'::regclass and attname = 'settled' and not attisdropped)
     or exists (select 1 from pg_attribute where attrelid = 'amd.charges'::regclass and attname = 'paid' and not attisdropped) then
    raise exception 'migrate_1110 check: amd.charges does not have the column settled in place of paid';
  end if;
  if exists (select 1 from pg_attribute where attrelid in ('amd.chart_facts'::regclass, 'amd.v_chart_facts'::regclass) and attname in ('zip5', 'city') and not attisdropped) then
    raise exception 'migrate_1110 check: amd.chart_facts still has the column zip5 or city';
  end if;
  if to_regclass('amd.unapplied_payments') is null or to_regclass('amd.charts_before_1110') is null or to_regclass('amd.charges_before_1110') is null
     or to_regclass('amd.payment_reasons_before_1110') is null or to_regclass('amd.chart_facts_before_1110') is null then
    raise exception 'migrate_1110 check: a new table or an old table kept as _before_1110 is missing';
  end if;
  if exists (select 1 from pg_rewrite rw join pg_class dep on dep.oid = rw.ev_class join pg_namespace dn on dn.oid = dep.relnamespace
             join pg_depend d on d.classid = 'pg_rewrite'::regclass and d.objid = rw.oid and d.refclassid = 'pg_class'::regclass
             join pg_class ref on ref.oid = d.refobjid
             where dn.nspname = 'amd' and dep.relname !~ '_before_1110$' and ref.relname ~ '_before_1110$') then
    raise exception 'migrate_1110 check: a live view still reads an object kept as _before_1110';
  end if;
 end $mig$;
