create schema if not exists amd;

comment on schema amd is 'AdvancedMD billing history of the practice, pulled 11/10/2026 at the owner''s request. One raw document per chart in raw.documents (source amd_history, collections txhistory, chartfacts and chargedetail). The v_* views read the documents live. The tables of the same name without v_ are indexed copies, refreshed after each load. PSEUDONYMOUS, NOT ANONYMOUS: a chart number (chart_id) can be tied to a name through other data the practice holds. Nothing in these tables is a patient''s name, birth date, address, phone number or member number. amd.chart_facts holds sex, birth year (1936 stands for 1936 or earlier) and state for each chart. Read money by year of service: payment and write-off dates are the day of entry in the billing system, not the day money arrived.';

create or replace view amd.v_charts as
-- AdvancedMD history (source amd_history, one document per chart from gettxhistory; William 11/10/2026): one row per chart pulled.
-- AdvancedMD sends 1900-01-01 as oldest and newest charge date on a chart that has no charge: turned into no value (corrected 11/10/2026).
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

create or replace view amd.v_charges as
-- one row per charge line AdvancedMD holds (void lines and their negative reversals included: filter on live)
-- settled = AdvancedMD's own 'paid' attribute on the charge: fee minus balance, that is payments PLUS write-offs. It is not money paid
-- (money paid is in amd.v_payments). The column was named paid until 11/10/2026.
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

create or replace view amd.v_payments as
-- one row per payment line posted on a charge (AdvancedMD stores a payment as a negative amount: paid = -amount)
-- payment_date is the day of entry in the billing system, not the day the money arrived: read money by year of service (dos).
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
-- reason_group = the first two characters (CO, PR, OA, PI, CR), carc = the rest. The code can start with a letter: COB9 is CO + B9
-- (corrected 11/10/2026: the old rule took every leading letter as the group).
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

create or replace view amd.v_writeoffs as
-- one row per write-off line on a charge (stored negative by AdvancedMD: written_off = -amount)
-- writeoff_date is the day of entry in the billing system: read money by year of service (dos).
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

create or replace view amd.v_unapplied_payments as
-- one row per unapplied payment line: money entered on a chart but applied to no charge (added 11/10/2026). These lines sit in the
-- document beside the charges (unapplied_payments) and are in no other view. paid = -amount, as for payments. No date of service.
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

create materialized view if not exists amd.charts as select * from amd.v_charts with no data;

create materialized view if not exists amd.charges as select * from amd.v_charges with no data;

create materialized view if not exists amd.payments as select * from amd.v_payments with no data;

create materialized view if not exists amd.payment_reasons as select * from amd.v_payment_reasons with no data;

create materialized view if not exists amd.writeoffs as select * from amd.v_writeoffs with no data;

create materialized view if not exists amd.unapplied_payments as select * from amd.v_unapplied_payments with no data;

create index if not exists amd_charges_chart_idx on amd.charges (chart_id);

create index if not exists amd_charges_dos_idx on amd.charges (dos);

create index if not exists amd_charges_cpt_idx on amd.charges (cpt, dos);

create index if not exists amd_charges_id_idx on amd.charges (charge_id);

create index if not exists amd_payments_charge_idx on amd.payments (charge_id);

create index if not exists amd_payments_date_idx on amd.payments (payment_date);

create index if not exists amd_payment_reasons_charge_idx on amd.payment_reasons (charge_id);

create index if not exists amd_writeoffs_charge_idx on amd.writeoffs (charge_id);

create index if not exists amd_unapplied_payments_chart_idx on amd.unapplied_payments (chart_id);

comment on materialized view amd.charts is 'One row per chart pulled from AdvancedMD. The money columns are AdvancedMD''s own chart totals. A chart with no charge has no dates. Filled from amd.v_charts, refreshed after each load.';

comment on view amd.v_charts is 'Live view behind amd.charts: the same columns, read from the documents at query time. Column notes are on amd.charts.';

comment on column amd.charts.oldest_charge is 'AdvancedMD''s own value: date of the oldest charge on the chart. Empty when the chart has no charge. AdvancedMD sends 1900-01-01 there, which is turned into no value.';

comment on column amd.charts.newest_charge is 'AdvancedMD''s own value, kept as sent and not computed from the lines here. It is not always the newest date of service in amd.charges: on some charts it is earlier (later lines are void) or later (an unapplied payment). Empty when the chart has no charge.';

comment on column amd.charts.insurance_payments is 'AdvancedMD''s own total of insurance payments on the chart. It counts unapplied payments too, which sit on no charge (see amd.unapplied_payments).';

comment on column amd.charts.patient_payments is 'AdvancedMD''s own total of patient payments on the chart. It counts unapplied payments too (see amd.unapplied_payments).';

comment on column amd.charts.unapplied_payments is 'Number of unapplied payment lines on the chart. The lines themselves are in amd.unapplied_payments.';

comment on materialized view amd.charges is 'One row per charge line AdvancedMD holds. Void lines and their negative reversals are included: keep only rows where live is true when adding money. Filled from amd.v_charges, refreshed after each load.';

comment on view amd.v_charges is 'Live view behind amd.charges: the same columns, read from the documents at query time. Column notes are on amd.charges.';

comment on column amd.charges.settled is 'Fee minus balance: payments plus write-offs. AdvancedMD sends it under the name paid, and this column was named paid until 11/10/2026. It is NOT money paid. Money paid is in amd.payments (rows that are not void).';

comment on column amd.v_charges.settled is 'Fee minus balance: payments plus write-offs. AdvancedMD sends it under the name paid, and this column was named paid until 11/10/2026. It is NOT money paid. Money paid is in amd.payments (rows that are not void).';

comment on column amd.charges.live is 'True for a real charge: not void and not a negative reversal. Add money on live rows only.';

comment on column amd.charges.void is 'True on a voided charge and on the negative line that reverses it. The pair nets to zero.';

comment on column amd.charges.carrier is 'The payer the charge sits with today. Not the payer billed first and not the payer that paid: paying payers are in amd.payments.';

comment on column amd.charges.npi is 'Billing number on the charge. It follows the payer the charge sits with, not the clinician. Empty text on about half the lines. Not a clinician key: use provider.';

comment on column amd.charges.bill_status is 'Filled only when AdvancedMD sends words in place of a bill date. Empty on every line of the 11/10/2026 pull.';

comment on materialized view amd.payments is 'One row per payment line posted on a charge. paid is minus the amount AdvancedMD stores. Add rows that are not void. Posted money only: unapplied payments are in amd.unapplied_payments. Filled from amd.v_payments, refreshed after each load.';

comment on view amd.v_payments is 'Live view behind amd.payments: the same columns, read from the documents at query time. Column notes are on amd.payments.';

comment on column amd.payments.payment_date is 'Day the line was entered in the billing system (the same day as posted_at). NOT the day the money arrived. Entry came in bursts: almost nothing from October 2024 to April 2026, then the backlog. Read money by year of service (dos), never by this date.';

comment on column amd.v_payments.payment_date is 'Day the line was entered in the billing system (the same day as posted_at). NOT the day the money arrived. Entry came in bursts: almost nothing from October 2024 to April 2026, then the backlog. Read money by year of service (dos), never by this date.';

comment on column amd.payments.posted_at is 'Time the line was entered in the billing system.';

comment on column amd.payments.paid is 'Money on the line: minus the amount AdvancedMD stores. A negative value is a take-back.';

comment on column amd.payments.source is '2 = paid by a payer (carrier is filled). 1 = paid by the patient (no carrier).';

comment on column amd.payments.void is 'True on a voided line and on the line that offsets it. The pair nets to zero. Use not void.';

comment on column amd.payments.void_offset is 'True only on the offsetting line of a voided pair. Do not use it alone as the filter: the voided line itself would stay in.';

comment on materialized view amd.payment_reasons is 'One row per adjustment reason code on a payment line, for example CO45, PR2 or COB9. reason_group is the first two characters, carc is the rest. Add rows that are not void. Filled from amd.v_payment_reasons, refreshed after each load.';

comment on view amd.v_payment_reasons is 'Live view behind amd.payment_reasons: the same columns, read from the documents at query time. Column notes are on amd.payment_reasons.';

comment on column amd.payment_reasons.reason_group is 'First two characters of the reason code: CO, PR, OA, PI or CR.';

comment on column amd.payment_reasons.carc is 'The reason code after the group. It can start with a letter: COB9 is group CO and code B9, COA1 is group CO and code A1.';

comment on column amd.payment_reasons.payment_date is 'Day the payment line was entered in the billing system. NOT the day the money arrived. Read money by year of service (dos), never by this date.';

comment on column amd.v_payment_reasons.payment_date is 'Day the payment line was entered in the billing system. NOT the day the money arrived. Read money by year of service (dos), never by this date.';

comment on materialized view amd.writeoffs is 'One row per write-off line on a charge. written_off is minus the amount AdvancedMD stores. Add rows that are not void. Filled from amd.v_writeoffs, refreshed after each load.';

comment on view amd.v_writeoffs is 'Live view behind amd.writeoffs: the same columns, read from the documents at query time. Column notes are on amd.writeoffs.';

comment on column amd.writeoffs.writeoff_date is 'Day the line was entered in the billing system (the same day as posted_at). NOT the day of a payer decision. Entry came in bursts, with a large batch in May 2026. Read money by year of service (dos), never by this date.';

comment on column amd.v_writeoffs.writeoff_date is 'Day the line was entered in the billing system (the same day as posted_at). NOT the day of a payer decision. Entry came in bursts, with a large batch in May 2026. Read money by year of service (dos), never by this date.';

comment on column amd.writeoffs.posted_at is 'Time the line was entered in the billing system.';

comment on column amd.writeoffs.writeoff_code is 'The practice''s write-off code. WOINSBANK is its code for a balance the payer reports paid but that was never posted: such a charge can show no payment in amd.payments although money came in. The text None is AdvancedMD''s own value on a line without a code.';

comment on column amd.writeoffs.void is 'True on a voided line and on the line that offsets it. The pair nets to zero. Use not void.';

comment on column amd.writeoffs.void_offset is 'True only on the offsetting line of a voided pair. Do not use it alone as the filter.';

comment on materialized view amd.unapplied_payments is 'One row per unapplied payment line: money entered on a chart but applied to no charge. These lines are not in amd.payments and have no date of service. Money still unapplied = rows that are not void with paid other than zero. Filled from amd.v_unapplied_payments, refreshed after each load.';

comment on view amd.v_unapplied_payments is 'Live view behind amd.unapplied_payments: the same columns, read from the documents at query time. Column notes are on amd.unapplied_payments.';

comment on column amd.unapplied_payments.payment_date is 'Day the line was entered in the billing system (the same day as posted_at). NOT the day the money arrived. These lines have no date of service.';

comment on column amd.v_unapplied_payments.payment_date is 'Day the line was entered in the billing system (the same day as posted_at). NOT the day the money arrived. These lines have no date of service.';

comment on column amd.unapplied_payments.paid is 'Money on the line: minus the amount AdvancedMD stores. Many lines are zero or void.';

comment on column amd.unapplied_payments.source is '2 = from a payer (carrier is filled). 1 = from the patient (no carrier).';

comment on column amd.unapplied_payments.provider is 'Clinician code AdvancedMD holds on the unapplied line.';

comment on column amd.unapplied_payments.void is 'True on a voided line and on the line that offsets it. The pair nets to zero. Use not void.';
