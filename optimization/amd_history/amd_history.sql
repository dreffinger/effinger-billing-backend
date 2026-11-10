create schema if not exists amd;

comment on schema amd is 'AdvancedMD transaction history pulled 11/10/2026 at the owner''s request: one raw document per chart in raw.documents (source amd_history, collection txhistory); v_* views read the documents live, the tables of the same name without v_ are indexed copies refreshed after each load. Chart ids, dates of service, codes, payers and dollars only - no names, birth dates or member ids.';

create or replace view amd.v_charts as
-- AdvancedMD history (source amd_history, one document per chart from gettxhistory; William 11/10/2026): one row per chart pulled.
select d.doc_id as chart_id,
       (d.body->>'_written')::timestamptz as pulled_at,
       (d.body->>'pages')::int as pages,
       jsonb_array_length(d.body->'charges') as charge_lines,
       nullif(d.body->'summary'->>'oldestcharge', '')::timestamp::date as oldest_charge,
       nullif(d.body->'summary'->>'newestcharge', '')::timestamp::date as newest_charge,
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

create or replace view amd.v_charges as
-- one row per charge line AdvancedMD holds (void lines and their negative reversals included: filter on live)
select d.doc_id as chart_id,
       c->>'id' as charge_id,
       c->>'visit' as visit_id,
       case when c->>'dos' ~ '^\d{2}/\d{2}/\d{4}$' then to_date(c->>'dos', 'MM/DD/YYYY') end as dos,
       c->>'proccode' as cpt,
       nullif(c->>'modifiers', '') as modifiers,
       case when c->>'fee' ~ '^-?\d+(\.\d+)?$' then (c->>'fee')::numeric end as fee,
       case when c->>'paid' ~ '^-?\d+(\.\d+)?$' then (c->>'paid')::numeric end as paid,
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

create or replace view amd.v_payments as
-- one row per payment line posted on a charge (AdvancedMD stores a payment as a negative amount: paid = -amount)
select d.doc_id as chart_id,
       c->>'id' as charge_id,
       c->>'visit' as visit_id,
       case when c->>'dos' ~ '^\d{2}/\d{2}/\d{4}$' then to_date(c->>'dos', 'MM/DD/YYYY') end as dos,
       c->>'proccode' as cpt,
       c->>'faccode' as facility_code,
       p->>'id' as payment_id,
       case when p->>'date' ~ '^\d{2}/\d{2}/\d{4}$' then to_date(p->>'date', 'MM/DD/YYYY') end as payment_date,
       nullif(p->>'createtime', '')::timestamp as posted_at,
       case when p->>'amount' ~ '^-?\d+(\.\d+)?$' then (p->>'amount')::numeric end as amount_raw,
       -case when p->>'amount' ~ '^-?\d+(\.\d+)?$' then (p->>'amount')::numeric end as paid,
       nullif(p->>'carrier', '') as carrier,
       nullif(p->>'paycode', '') as pay_code,
       nullif(p->>'source', '') as source,
       nullif(p->>'checknumber', '') as check_number,
       (p->>'void') = '1' as void,
       (p->>'voidoffset') = '1' as void_offset,
       jsonb_array_length(coalesce(p->'reasons', '[]'::jsonb)) as reason_lines
from raw.documents d
cross join lateral jsonb_array_elements(d.body->'charges') c
cross join lateral jsonb_array_elements(coalesce(c->'payments', '[]'::jsonb)) p
where d.source = 'amd_history' and d.collection = 'txhistory';

create or replace view amd.v_payment_reasons as
-- one row per adjustment reason code (CARC with its group, e.g. CO45, PR2) on a payment line
select d.doc_id as chart_id,
       c->>'id' as charge_id,
       case when c->>'dos' ~ '^\d{2}/\d{2}/\d{4}$' then to_date(c->>'dos', 'MM/DD/YYYY') end as dos,
       c->>'proccode' as cpt,
       p->>'id' as payment_id,
       case when p->>'date' ~ '^\d{2}/\d{2}/\d{4}$' then to_date(p->>'date', 'MM/DD/YYYY') end as payment_date,
       nullif(p->>'carrier', '') as carrier,
       (p->>'void') = '1' as void,
       r->>'code' as reason_code,
       substring(r->>'code' from '^[A-Za-z]+') as reason_group,
       substring(r->>'code' from '[0-9].*$') as carc,
       case when r->>'amount' ~ '^-?\d+(\.\d+)?$' then (r->>'amount')::numeric end as amount
from raw.documents d
cross join lateral jsonb_array_elements(d.body->'charges') c
cross join lateral jsonb_array_elements(coalesce(c->'payments', '[]'::jsonb)) p
cross join lateral jsonb_array_elements(coalesce(p->'reasons', '[]'::jsonb)) r
where d.source = 'amd_history' and d.collection = 'txhistory';

create or replace view amd.v_writeoffs as
-- one row per write-off line on a charge (stored negative by AdvancedMD: written_off = -amount)
select d.doc_id as chart_id,
       c->>'id' as charge_id,
       case when c->>'dos' ~ '^\d{2}/\d{2}/\d{4}$' then to_date(c->>'dos', 'MM/DD/YYYY') end as dos,
       c->>'proccode' as cpt,
       w->>'id' as writeoff_id,
       case when w->>'date' ~ '^\d{2}/\d{2}/\d{4}$' then to_date(w->>'date', 'MM/DD/YYYY') end as writeoff_date,
       nullif(w->>'createtime', '')::timestamp as posted_at,
       w->>'wocode' as writeoff_code,
       case when w->>'amount' ~ '^-?\d+(\.\d+)?$' then (w->>'amount')::numeric end as amount_raw,
       -case when w->>'amount' ~ '^-?\d+(\.\d+)?$' then (w->>'amount')::numeric end as written_off,
       nullif(w->>'source', '') as source,
       (w->>'void') = '1' as void,
       (w->>'voidoffset') = '1' as void_offset
from raw.documents d
cross join lateral jsonb_array_elements(d.body->'charges') c
cross join lateral jsonb_array_elements(coalesce(c->'writeoffs', '[]'::jsonb)) w
where d.source = 'amd_history' and d.collection = 'txhistory';

create materialized view if not exists amd.charts as select * from amd.v_charts with no data;

create materialized view if not exists amd.charges as select * from amd.v_charges with no data;

create materialized view if not exists amd.payments as select * from amd.v_payments with no data;

create materialized view if not exists amd.payment_reasons as select * from amd.v_payment_reasons with no data;

create materialized view if not exists amd.writeoffs as select * from amd.v_writeoffs with no data;

create index if not exists amd_charges_chart_idx on amd.charges (chart_id);

create index if not exists amd_charges_dos_idx on amd.charges (dos);

create index if not exists amd_charges_cpt_idx on amd.charges (cpt, dos);

create index if not exists amd_charges_id_idx on amd.charges (charge_id);

create index if not exists amd_payments_charge_idx on amd.payments (charge_id);

create index if not exists amd_payments_date_idx on amd.payments (payment_date);

create index if not exists amd_payment_reasons_charge_idx on amd.payment_reasons (charge_id);

create index if not exists amd_writeoffs_charge_idx on amd.writeoffs (charge_id);
