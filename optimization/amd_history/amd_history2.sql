-- AdvancedMD history, layers 2 and 3 (11/10/2026): chart facts (getdemographic) and charge detail (getchargedetaildataicd10).
-- Reads raw.documents (source amd_history, collections chartfacts / chargedetail). No name, full birth date, address, phone, member id or note is in those documents.
-- Since the privacy review of 11/10/2026 the documents also carry no ZIP code, no city and no marital status, and a birth year of 1936 or earlier is
-- stored as 1936. The chart facts are still patient-level data: pseudonymous, not anonymous.
-- Every date and number is cast only when it has the expected shape, so one odd value never breaks a view.

create or replace view amd.v_chart_facts as
-- one row per chart: patient-level facts (sex, birth YEAR with 1936 standing for 1936 or earlier, state, flags). No ZIP code, no city, no marital status:
-- the pulled documents no longer carry them and the columns zip5 and city were taken out on 11/10/2026.
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

create or replace view amd.v_chart_plans as
-- one row per insurance plan on a chart (payer and dates; never a member id or group number)
select d.doc_id as chart_id,
       p->>'id' as plan_id,
       p->>'carrier' as carrier_id,
       d.body->'carriers'->(p->>'carrier')->>'code' as carrier,
       d.body->'carriers'->(p->>'carrier')->>'name' as carrier_name,
       case when p->>'begindate' ~ '^\d{2}/\d{2}/\d{4}' then to_date(left(p->>'begindate', 10), 'MM/DD/YYYY') end as begin_date,
       case when p->>'enddate' ~ '^\d{2}/\d{2}/\d{4}' then to_date(left(p->>'enddate', 10), 'MM/DD/YYYY') end as end_date,
       nullif(p->>'sequence', '') as sequence,
       nullif(p->>'coverage', '') as coverage,
       nullif(p->>'mspcode', '') as msp_code,
       nullif(p->>'finclasscode', '') as financial_class,
       case when p->>'claimcount' ~ '^\d+$' then (p->>'claimcount')::int end as claim_count
  from raw.documents d
 cross join lateral jsonb_array_elements(coalesce(d.body->'plans', '[]'::jsonb)) p
 where d.source = 'amd_history' and d.collection = 'chartfacts';

create or replace view amd.v_chart_ageing as
-- AdvancedMD's own ageing buckets per chart (insurance and patient side) on the day of the pull
select d.doc_id as chart_id,
       b->>'buckettype' as bucket_type,
       case when b->>'current' ~ '^-?\d+(\.\d+)?$' then (b->>'current')::numeric end as current_amount,
       case when b->>'past30' ~ '^-?\d+(\.\d+)?$' then (b->>'past30')::numeric end as past_30,
       case when b->>'past60' ~ '^-?\d+(\.\d+)?$' then (b->>'past60')::numeric end as past_60,
       case when b->>'past90' ~ '^-?\d+(\.\d+)?$' then (b->>'past90')::numeric end as past_90,
       case when b->>'past120' ~ '^-?\d+(\.\d+)?$' then (b->>'past120')::numeric end as past_120,
       case when b->>'unapplied' ~ '^-?\d+(\.\d+)?$' then (b->>'unapplied')::numeric end as unapplied,
       case when b->>'total' ~ '^-?\d+(\.\d+)?$' then (b->>'total')::numeric end as total
  from raw.documents d
 cross join lateral jsonb_array_elements(coalesce(d.body->'ageing', '[]'::jsonb)) b
 where d.source = 'amd_history' and d.collection = 'chartfacts';

create or replace view amd.v_charge_details as
-- one row per charge: what the claim line itself carried (place of service, units, diagnoses, modifiers, allowed and expected amounts)
select d.doc_id as chart_id,
       c->>'id' as charge_id,
       c->>'visit_id' as visit_id,
       nullif(c->>'cpt', '') as cpt,
       case when c->>'begindate' ~ '^\d{2}/\d{2}/\d{4}' then to_date(left(c->>'begindate', 10), 'MM/DD/YYYY') end as dos,
       nullif(c->>'pos', '') as place_of_service,
       nullif(c->>'tos', '') as type_of_service,
       case when c->>'units' ~ '^-?\d+(\.\d+)?$' then (c->>'units')::numeric end as units,
       case when c->>'fee' ~ '^-?\d+(\.\d+)?$' then (c->>'fee')::numeric end as fee,
       case when c->>'allowed' ~ '^-?\d+(\.\d+)?$' then (c->>'allowed')::numeric end as allowed,
       case when c->>'expected' ~ '^-?\d+(\.\d+)?$' then (c->>'expected')::numeric end as expected,
       case when c->>'insbalance' ~ '^-?\d+(\.\d+)?$' then (c->>'insbalance')::numeric end as insurance_balance,
       case when c->>'patbalance' ~ '^-?\d+(\.\d+)?$' then (c->>'patbalance')::numeric end as patient_balance,
       (select string_agg(x, ' ') from jsonb_array_elements_text(coalesce(c->'dx', '[]'::jsonb)) x) as diagnoses,
       (select string_agg(x, ' ') from jsonb_array_elements_text(coalesce(c->'mods', '[]'::jsonb)) x) as modifiers,
       nullif(c->>'lastbilledcarrier_code', '') as last_billed_carrier,
       case when c->>'datebilled' ~ '^\d{2}/\d{2}/\d{4}' then to_date(left(c->>'datebilled', 10), 'MM/DD/YYYY') end as date_billed,
       case when c->>'entered' ~ '^\d{2}/\d{2}/\d{4}' then to_date(left(c->>'entered', 10), 'MM/DD/YYYY') end as entered_date,
       (c->>'void') = '1' as void,
       nullif(c->>'batchnumber', '') as batch_number,
       nullif(c->>'finclasscode', '') as financial_class,
       d.body->'visits'->(c->>'visit_id')->>'facility_code' as facility_code,
       d.body->'visits'->(c->>'visit_id')->>'profile_code' as profile_code,
       nullif(d.body->'visits'->(c->>'visit_id')->>'insorder', '') as visit_insurance_order,
       jsonb_array_length(coalesce(c->'insbills', '[]'::jsonb)) as times_billed
  from raw.documents d
 cross join lateral jsonb_array_elements(coalesce(d.body->'charges', '[]'::jsonb)) c
 where d.source = 'amd_history' and d.collection = 'chargedetail';

create or replace view amd.v_charge_bills as
-- one row per time a charge went out on a claim (payer, date, paper or electronic, claim number)
select d.doc_id as chart_id,
       c->>'id' as charge_id,
       nullif(c->>'cpt', '') as cpt,
       case when c->>'begindate' ~ '^\d{2}/\d{2}/\d{4}' then to_date(left(c->>'begindate', 10), 'MM/DD/YYYY') end as dos,
       b->>'carriername' as carrier_name,
       case when b->>'billeddate' ~ '^\d{2}/\d{2}/\d{4}' then to_date(left(b->>'billeddate', 10), 'MM/DD/YYYY') end as billed_date,
       nullif(b->>'paperedi', '') as paper_or_electronic,
       nullif(b->>'claimid', '') as claim_id,
       nullif(b->>'claimrun', '') as claim_run,
       nullif(b->>'demand', '') as demand
  from raw.documents d
 cross join lateral jsonb_array_elements(coalesce(d.body->'charges', '[]'::jsonb)) c
 cross join lateral jsonb_array_elements(coalesce(c->'insbills', '[]'::jsonb)) b
 where d.source = 'amd_history' and d.collection = 'chargedetail';

create materialized view if not exists amd.chart_facts as select * from amd.v_chart_facts with no data;
create materialized view if not exists amd.chart_plans as select * from amd.v_chart_plans with no data;
create materialized view if not exists amd.chart_ageing as select * from amd.v_chart_ageing with no data;
create materialized view if not exists amd.charge_details as select * from amd.v_charge_details with no data;
create materialized view if not exists amd.charge_bills as select * from amd.v_charge_bills with no data;
create index if not exists amd_chart_plans_chart_idx on amd.chart_plans (chart_id);
create index if not exists amd_charge_details_charge_idx on amd.charge_details (charge_id);
create index if not exists amd_charge_details_dos_idx on amd.charge_details (dos);
create index if not exists amd_charge_details_cpt_idx on amd.charge_details (cpt, place_of_service);
create index if not exists amd_charge_bills_charge_idx on amd.charge_bills (charge_id);
comment on materialized view amd.chart_facts is 'One row per chart: patient-level facts from AdvancedMD (sex, birth year, state, flags, number of plans). No name, no full birth date, no ZIP code, no city, no marital status. This is pseudonymous patient data, not anonymous data. Filled from amd.v_chart_facts, refreshed after each load.';
comment on view amd.v_chart_facts is 'Live view behind amd.chart_facts: the same columns, read from the documents at query time. Column notes are on amd.chart_facts.';
comment on column amd.chart_facts.birth_year is 'Year of birth. 1936 stands for 1936 or earlier: an age of 90 or more is not shown.';
comment on column amd.chart_facts.state is 'State of the patient''s address. The ZIP code and the city are not stored.';
comment on column amd.chart_facts.deceased is 'True where AdvancedMD carries a deceased mark. Few charts carry one: false does not prove the patient is alive.';
comment on column amd.chart_facts.inactive is 'AdvancedMD''s inactive value. AdvancedMD sent none on any chart in the 11/10/2026 pull: empty on every row.';
