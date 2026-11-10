-- V01 objects in schema amd after the migration: 25 live views and tables, 11 kept as _before_1110, nothing left as _new_1110, every table filled, 14 live indexes and 5 old ones
select count(*) filter (where c.relkind in ('v', 'm') and c.relname !~ '_(before|new)_1110$') as live_views_and_tables,
       count(*) filter (where c.relkind in ('v', 'm') and c.relname ~ '_before_1110$') as kept_as_before_1110,
       count(*) filter (where c.relname ~ '_new_1110') as left_as_new_1110,
       count(*) filter (where c.relkind = 'm' and not c.relispopulated) as tables_not_filled,
       count(*) filter (where c.relkind = 'i' and c.relname !~ '_(before|new)_1110$') as live_indexes,
       count(*) filter (where c.relkind = 'i' and c.relname ~ '_before_1110$') as indexes_kept_as_before_1110,
       count(*) filter (where c.relkind not in ('v', 'm', 'i')) as other_kinds,
       (count(*) filter (where c.relkind in ('v', 'm') and c.relname !~ '_(before|new)_1110$') = 25
        and count(*) filter (where c.relkind in ('v', 'm') and c.relname ~ '_before_1110$') = 11
        and count(*) filter (where c.relname ~ '_new_1110') = 0
        and count(*) filter (where c.relkind = 'm' and not c.relispopulated) = 0
        and count(*) filter (where c.relkind = 'i' and c.relname !~ '_(before|new)_1110$') = 14
        and count(*) filter (where c.relkind = 'i' and c.relname ~ '_before_1110$') = 5
        and count(*) filter (where c.relkind not in ('v', 'm', 'i')) = 0) as ok
from pg_class c join pg_namespace n on n.oid = c.relnamespace
where n.nspname = 'amd';

-- V02 every expected object, by name and kind (m = table, v = view, i = index). A row here is an object that is missing, of the wrong kind, or not expected. No row = good
with expected(name, kind) as (values
  ('charts', 'm'), ('charges', 'm'), ('payments', 'm'), ('payment_reasons', 'm'), ('writeoffs', 'm'), ('unapplied_payments', 'm'),
  ('chart_facts', 'm'), ('chart_plans', 'm'), ('chart_ageing', 'm'), ('charge_details', 'm'), ('charge_bills', 'm'),
  ('v_charts', 'v'), ('v_charges', 'v'), ('v_payments', 'v'), ('v_payment_reasons', 'v'), ('v_writeoffs', 'v'), ('v_unapplied_payments', 'v'),
  ('v_chart_facts', 'v'), ('v_chart_plans', 'v'), ('v_chart_ageing', 'v'), ('v_charge_details', 'v'), ('v_charge_bills', 'v'),
  ('facility_settings', 'v'), ('charge_outcomes', 'v'), ('paid_lines_monthly', 'v'),
  ('charts_before_1110', 'm'), ('charges_before_1110', 'm'), ('payment_reasons_before_1110', 'm'), ('chart_facts_before_1110', 'm'),
  ('v_charts_before_1110', 'v'), ('v_charges_before_1110', 'v'), ('v_payment_reasons_before_1110', 'v'), ('v_chart_facts_before_1110', 'v'),
  ('facility_settings_before_1110', 'v'), ('charge_outcomes_before_1110', 'v'), ('paid_lines_monthly_before_1110', 'v'),
  ('amd_charges_chart_idx', 'i'), ('amd_charges_dos_idx', 'i'), ('amd_charges_cpt_idx', 'i'), ('amd_charges_id_idx', 'i'),
  ('amd_payments_charge_idx', 'i'), ('amd_payments_date_idx', 'i'), ('amd_payment_reasons_charge_idx', 'i'), ('amd_writeoffs_charge_idx', 'i'),
  ('amd_unapplied_payments_chart_idx', 'i'), ('amd_chart_plans_chart_idx', 'i'), ('amd_charge_details_charge_idx', 'i'), ('amd_charge_details_dos_idx', 'i'),
  ('amd_charge_details_cpt_idx', 'i'), ('amd_charge_bills_charge_idx', 'i'),
  ('amd_charges_chart_idx_before_1110', 'i'), ('amd_charges_dos_idx_before_1110', 'i'), ('amd_charges_cpt_idx_before_1110', 'i'), ('amd_charges_id_idx_before_1110', 'i'),
  ('amd_payment_reasons_charge_idx_before_1110', 'i')),
found as (select c.relname as name, c.relkind::text as kind from pg_class c join pg_namespace n on n.oid = c.relnamespace where n.nspname = 'amd')
select coalesce(e.name, f.name) as object_name, e.kind as expected_kind, f.kind as found_kind, false as ok
from expected e full join found f using (name)
where e.name is null or f.name is null or e.kind <> f.kind
order by 1;

-- V03 the indexes sit on the right tables with the right columns. A row here is an index that differs. No row = good
with expected(indexname, tablename, cols) as (values
  ('amd_charges_chart_idx', 'charges', '(chart_id)'), ('amd_charges_dos_idx', 'charges', '(dos)'), ('amd_charges_cpt_idx', 'charges', '(cpt, dos)'), ('amd_charges_id_idx', 'charges', '(charge_id)'),
  ('amd_payments_charge_idx', 'payments', '(charge_id)'), ('amd_payments_date_idx', 'payments', '(payment_date)'),
  ('amd_payment_reasons_charge_idx', 'payment_reasons', '(charge_id)'), ('amd_writeoffs_charge_idx', 'writeoffs', '(charge_id)'),
  ('amd_unapplied_payments_chart_idx', 'unapplied_payments', '(chart_id)'), ('amd_chart_plans_chart_idx', 'chart_plans', '(chart_id)'),
  ('amd_charge_details_charge_idx', 'charge_details', '(charge_id)'), ('amd_charge_details_dos_idx', 'charge_details', '(dos)'),
  ('amd_charge_details_cpt_idx', 'charge_details', '(cpt, place_of_service)'), ('amd_charge_bills_charge_idx', 'charge_bills', '(charge_id)'),
  ('amd_charges_chart_idx_before_1110', 'charges_before_1110', '(chart_id)'), ('amd_charges_dos_idx_before_1110', 'charges_before_1110', '(dos)'),
  ('amd_charges_cpt_idx_before_1110', 'charges_before_1110', '(cpt, dos)'), ('amd_charges_id_idx_before_1110', 'charges_before_1110', '(charge_id)'),
  ('amd_payment_reasons_charge_idx_before_1110', 'payment_reasons_before_1110', '(charge_id)'))
select e.indexname, e.tablename as expected_table, i.tablename as found_table, e.cols as expected_columns, i.indexdef as found_definition, false as ok
from expected e left join pg_indexes i on i.schemaname = 'amd' and i.indexname = e.indexname
where i.indexname is null or i.tablename <> e.tablename
   or i.indexdef not like '% INDEX ' || e.indexname || ' ON amd.' || e.tablename || ' USING btree ' || e.cols;

-- V04 who reads what. No live view or table may read an object kept as _before_1110, and each live table must read its own live view
with reads as (select distinct dep.relname as reader, ref.relname as source, rn.nspname as source_schema
               from pg_rewrite rw join pg_class dep on dep.oid = rw.ev_class join pg_namespace dn on dn.oid = dep.relnamespace
               join pg_depend d on d.classid = 'pg_rewrite'::regclass and d.objid = rw.oid and d.refclassid = 'pg_class'::regclass
               join pg_class ref on ref.oid = d.refobjid join pg_namespace rn on rn.oid = ref.relnamespace
               where dn.nspname = 'amd' and ref.oid <> dep.oid)
select count(*) as read_links,
       count(*) filter (where reader !~ '_before_1110$' and source ~ '_before_1110$') as live_reading_an_old_object,
       count(*) filter (where source_schema not in ('amd', 'raw')) as reads_outside_amd_and_raw,
       count(*) filter (where reader !~ '^v_' and reader !~ '_before_1110$' and reader not in ('facility_settings', 'charge_outcomes', 'paid_lines_monthly') and source <> 'v_' || reader) as live_table_not_on_its_own_view,
       (select string_agg(source, ', ' order by source) from reads where reader = 'facility_settings') as facility_settings_reads,
       (select string_agg(source, ', ' order by source) from reads where reader = 'charge_outcomes') as charge_outcomes_reads,
       (select string_agg(source, ', ' order by source) from reads where reader = 'paid_lines_monthly') as paid_lines_monthly_reads,
       (select string_agg(source, ', ' order by source) from reads where reader = 'charge_outcomes_before_1110') as charge_outcomes_before_1110_reads,
       (count(*) filter (where reader !~ '_before_1110$' and source ~ '_before_1110$') = 0
        and count(*) filter (where source_schema not in ('amd', 'raw')) = 0
        and count(*) filter (where reader !~ '^v_' and reader !~ '_before_1110$' and reader not in ('facility_settings', 'charge_outcomes', 'paid_lines_monthly') and source <> 'v_' || reader) = 0
        and (select string_agg(source, ', ' order by source) from reads where reader = 'facility_settings') = 'charges'
        and (select string_agg(source, ', ' order by source) from reads where reader = 'charge_outcomes') = 'charges, facility_settings, payment_reasons, payments, writeoffs'
        and (select string_agg(source, ', ' order by source) from reads where reader = 'paid_lines_monthly') = 'charge_outcomes') as ok
from reads;

-- V05 nothing outside schema amd depends on these objects, and owner and grants are as before (all owned by the tool's role, no grants)
select (select count(*) from pg_depend d join pg_rewrite rw on d.classid = 'pg_rewrite'::regclass and rw.oid = d.objid join pg_class dep on dep.oid = rw.ev_class join pg_namespace dn on dn.oid = dep.relnamespace
        join pg_class ref on d.refclassid = 'pg_class'::regclass and ref.oid = d.refobjid join pg_namespace rn on rn.oid = ref.relnamespace
        where rn.nspname = 'amd' and dn.nspname <> 'amd') as views_outside_amd_reading_amd,
       (select count(*) from pg_class c join pg_namespace n on n.oid = c.relnamespace where n.nspname = 'amd' and c.relacl is not null) as objects_with_grants,
       (select count(*) from pg_class c join pg_namespace n on n.oid = c.relnamespace where n.nspname = 'amd' and pg_get_userbyid(c.relowner) <> current_user) as objects_not_owned_by_the_tool_role,
       ((select count(*) from pg_depend d join pg_rewrite rw on d.classid = 'pg_rewrite'::regclass and rw.oid = d.objid join pg_class dep on dep.oid = rw.ev_class join pg_namespace dn on dn.oid = dep.relnamespace
         join pg_class ref on d.refclassid = 'pg_class'::regclass and ref.oid = d.refobjid join pg_namespace rn on rn.oid = ref.relnamespace
         where rn.nspname = 'amd' and dn.nspname <> 'amd') = 0
        and (select count(*) from pg_class c join pg_namespace n on n.oid = c.relnamespace where n.nspname = 'amd' and c.relacl is not null) = 0
        and (select count(*) from pg_class c join pg_namespace n on n.oid = c.relnamespace where n.nspname = 'amd' and pg_get_userbyid(c.relowner) <> current_user) = 0) as ok;

-- V06 CF-01 the column: amd.charges and amd.v_charges have settled (8th column, a number) and no column named paid. The comment says it is not money paid
select (select count(*) from pg_attribute where attrelid in ('amd.charges'::regclass, 'amd.v_charges'::regclass) and attname = 'paid' and not attisdropped) as columns_named_paid,
       (select count(*) from pg_attribute where attrelid in ('amd.charges'::regclass, 'amd.v_charges'::regclass) and attname = 'settled' and attnum = 8 and format_type(atttypid, atttypmod) = 'numeric' and not attisdropped) as settled_columns_in_place,
       (select col_description('amd.charges'::regclass, 8) ~ 'NOT money paid') as table_comment_says_not_money_paid,
       (select col_description('amd.v_charges'::regclass, 8) ~ 'NOT money paid') as view_comment_says_not_money_paid,
       (select count(*) from pg_attribute where attrelid = 'amd.charges_before_1110'::regclass and attname = 'paid' and attnum = 8) as old_table_still_has_paid,
       ((select count(*) from pg_attribute where attrelid in ('amd.charges'::regclass, 'amd.v_charges'::regclass) and attname = 'paid' and not attisdropped) = 0
        and (select count(*) from pg_attribute where attrelid in ('amd.charges'::regclass, 'amd.v_charges'::regclass) and attname = 'settled' and attnum = 8 and format_type(atttypid, atttypmod) = 'numeric' and not attisdropped) = 2
        and (select col_description('amd.charges'::regclass, 8) ~ 'NOT money paid')
        and (select col_description('amd.v_charges'::regclass, 8) ~ 'NOT money paid')
        and (select count(*) from pg_attribute where attrelid = 'amd.charges_before_1110'::regclass and attname = 'paid' and attnum = 8) = 1) as ok;

-- V07 CF-01 the money: settled on live lines = fee minus balance = payments plus write-offs (not void) on those lines. On PROD expect settled 10,042,860.47, payments 3,757,541.84, write-offs 6,285,318.63
select count(*) as charge_rows, count(*) filter (where c.live) as live_rows,
       sum(c.fee) filter (where c.live) as live_fee, sum(c.settled) filter (where c.live) as live_settled, sum(c.balance) filter (where c.live) as live_balance,
       sum(p.paid) filter (where c.live) as payments_on_live_lines, sum(w.written_off) filter (where c.live) as writeoffs_on_live_lines,
       (select sum(paid) from amd.payments where not void) as all_payments_not_void, (select sum(written_off) from amd.writeoffs where not void) as all_writeoffs_not_void,
       count(*) filter (where c.live and c.settled is distinct from c.fee - c.balance) as live_lines_where_settled_is_not_fee_minus_balance,
       count(*) filter (where c.live and c.settled is distinct from coalesce(p.paid, 0) + coalesce(w.written_off, 0)) as live_lines_where_settled_is_not_payments_plus_writeoffs,
       count(*) filter (where c.live and c.settled is distinct from coalesce(p.paid, 0)) as live_lines_where_settled_is_not_the_payments,
       (count(*) filter (where c.live and c.settled is distinct from c.fee - c.balance) = 0
        and count(*) filter (where c.live and c.settled is distinct from coalesce(p.paid, 0) + coalesce(w.written_off, 0)) = 0) as ok
from amd.charges c
left join (select charge_id, sum(paid) filter (where not void) as paid from amd.payments group by 1) p using (charge_id)
left join (select charge_id, sum(written_off) filter (where not void) as written_off from amd.writeoffs group by 1) w using (charge_id);

-- V08 CF-01 nothing else changed in charges: the new table against the old one, column by column in order (settled against the old paid). Both counts must be 0
select (select count(*) from amd.charges) as rows_now, (select count(*) from amd.charges_before_1110) as rows_before,
       (select count(*) from (select * from amd.charges except all select * from amd.charges_before_1110) x) as rows_in_new_not_in_old,
       (select count(*) from (select * from amd.charges_before_1110 except all select * from amd.charges) x) as rows_in_old_not_in_new,
       ((select count(*) from (select * from amd.charges except all select * from amd.charges_before_1110) x) = 0
        and (select count(*) from (select * from amd.charges_before_1110 except all select * from amd.charges) x) = 0) as ok;

-- V09 CF-02 the split: every group is two capital letters, group + code gives back the reason code, and the rows whose split changed are exactly the rows the old table had wrong. On PROD expect 1,415 rows, $195,032.78
select count(*) as reason_rows,
       count(*) filter (where reason_group !~ '^[A-Z]{2}$') as groups_that_are_not_two_letters,
       count(distinct reason_group) as groups, string_agg(distinct reason_group, ' ' order by reason_group) as group_list,
       count(*) filter (where reason_group || coalesce(carc, '') is distinct from reason_code) as rows_where_group_plus_code_is_not_the_reason_code,
       count(*) filter (where carc is null) as rows_with_no_code,
       count(*) filter (where reason_group is distinct from substring(reason_code from '^[A-Za-z]+') or carc is distinct from substring(reason_code from '[0-9].*$')) as rows_whose_split_changed,
       sum(amount) filter (where reason_group is distinct from substring(reason_code from '^[A-Za-z]+') or carc is distinct from substring(reason_code from '[0-9].*$')) as amount_on_those_rows,
       count(*) filter (where carc ~ '^[A-Za-z]') as rows_whose_code_starts_with_a_letter,
       (select count(*) from amd.payment_reasons_before_1110 where reason_group !~ '^[A-Z]{2}$') as rows_the_old_table_had_wrong,
       (count(*) filter (where reason_group !~ '^[A-Z]{2}$') = 0
        and count(*) filter (where reason_group || coalesce(carc, '') is distinct from reason_code) = 0
        and count(*) filter (where reason_group is distinct from substring(reason_code from '^[A-Za-z]+') or carc is distinct from substring(reason_code from '[0-9].*$'))
            = (select count(*) from amd.payment_reasons_before_1110 where reason_group !~ '^[A-Z]{2}$')
        and count(*) filter (where carc ~ '^[A-Za-z]') = (select count(*) from amd.payment_reasons_before_1110 where reason_group !~ '^[A-Z]{2}$')) as ok
from amd.payment_reasons;

-- V10 CF-02 nothing else changed in the reason lines: apart from reason_group and carc the new table equals the old one (both counts 0). Whole rows that differ = the rows whose split changed
select (select count(*) from amd.payment_reasons) as rows_now, (select count(*) from amd.payment_reasons_before_1110) as rows_before,
       (select count(*) from (select chart_id, charge_id, dos, cpt, payment_id, payment_date, carrier, void, reason_code, amount from amd.payment_reasons
                              except all select chart_id, charge_id, dos, cpt, payment_id, payment_date, carrier, void, reason_code, amount from amd.payment_reasons_before_1110) x) as other_columns_in_new_not_in_old,
       (select count(*) from (select chart_id, charge_id, dos, cpt, payment_id, payment_date, carrier, void, reason_code, amount from amd.payment_reasons_before_1110
                              except all select chart_id, charge_id, dos, cpt, payment_id, payment_date, carrier, void, reason_code, amount from amd.payment_reasons) x) as other_columns_in_old_not_in_new,
       (select count(*) from (select * from amd.payment_reasons except all select * from amd.payment_reasons_before_1110) x) as whole_rows_that_differ,
       (select sum(amount) from amd.payment_reasons) as amount_now, (select sum(amount) from amd.payment_reasons_before_1110) as amount_before,
       ((select count(*) from (select chart_id, charge_id, dos, cpt, payment_id, payment_date, carrier, void, reason_code, amount from amd.payment_reasons
                               except all select chart_id, charge_id, dos, cpt, payment_id, payment_date, carrier, void, reason_code, amount from amd.payment_reasons_before_1110) x) = 0
        and (select count(*) from (select chart_id, charge_id, dos, cpt, payment_id, payment_date, carrier, void, reason_code, amount from amd.payment_reasons_before_1110
                                   except all select chart_id, charge_id, dos, cpt, payment_id, payment_date, carrier, void, reason_code, amount from amd.payment_reasons) x) = 0
        and (select count(*) from (select * from amd.payment_reasons except all select * from amd.payment_reasons_before_1110) x)
            = (select count(*) from amd.payment_reasons_before_1110 where reason_group !~ '^[A-Z]{2}$')) as ok;

-- V11 CF-02 the letter codes, old split against new split (codes and counts only). On PROD expect 14 codes, 1,415 rows
select n.reason_code, o.reason_group as group_before, o.carc as code_before, n.reason_group as group_now, n.carc as code_now, n.lines
from (select reason_code, reason_group, carc, count(*) as lines from amd.payment_reasons where carc ~ '^[A-Za-z]' group by 1, 2, 3) n
left join (select distinct reason_code, reason_group, carc from amd.payment_reasons_before_1110) o using (reason_code)
order by n.lines desc, n.reason_code;

-- V12 CF-03 no 1900-01-01: charts with no charge have no date, charts with charges have both dates. On PROD expect 5,534 charts with no date
select count(*) as chart_rows,
       count(*) filter (where oldest_charge = date '1900-01-01' or newest_charge = date '1900-01-01') as rows_with_1900_01_01,
       count(*) filter (where oldest_charge is null) as rows_with_no_oldest_date, count(*) filter (where newest_charge is null) as rows_with_no_newest_date,
       count(*) filter (where (oldest_charge is null) <> (newest_charge is null)) as rows_with_only_one_date,
       count(*) filter (where charge_lines = 0) as charts_with_no_charge_line,
       count(*) filter (where oldest_charge is null and charge_lines > 0) as no_date_but_has_charge_lines,
       count(*) filter (where oldest_charge is not null and charge_lines = 0) as date_but_no_charge_line,
       min(oldest_charge) as earliest_oldest_charge, max(newest_charge) as latest_newest_charge,
       (select count(*) from amd.charts_before_1110 where oldest_charge = date '1900-01-01' or newest_charge = date '1900-01-01') as rows_with_1900_in_the_old_table,
       (count(*) filter (where oldest_charge = date '1900-01-01' or newest_charge = date '1900-01-01') = 0
        and count(*) filter (where oldest_charge < date '1990-01-01' or newest_charge < date '1990-01-01') = 0
        and count(*) filter (where oldest_charge is null) = (select count(*) from amd.charts_before_1110 where oldest_charge = date '1900-01-01')
        and count(*) filter (where newest_charge is null) = (select count(*) from amd.charts_before_1110 where newest_charge = date '1900-01-01')
        and count(*) filter (where oldest_charge is null and charge_lines > 0) = 0
        and count(*) filter (where oldest_charge is not null and charge_lines = 0) = 0) as ok
from amd.charts;

-- V13 CF-03 nothing else changed in charts: apart from the two dates the new table equals the old one (both counts 0). Whole rows that differ = the rows that showed 1900-01-01
select (select count(*) from amd.charts) as rows_now, (select count(*) from amd.charts_before_1110) as rows_before,
       (select count(*) from (select chart_id, pulled_at, pages, charge_lines, insurance_charges, patient_charges, insurance_payments, patient_payments, insurance_writeoffs, patient_writeoffs, insurance_balance, patient_balance, unapplied_payments from amd.charts
                              except all select chart_id, pulled_at, pages, charge_lines, insurance_charges, patient_charges, insurance_payments, patient_payments, insurance_writeoffs, patient_writeoffs, insurance_balance, patient_balance, unapplied_payments from amd.charts_before_1110) x) as other_columns_in_new_not_in_old,
       (select count(*) from (select chart_id, pulled_at, pages, charge_lines, insurance_charges, patient_charges, insurance_payments, patient_payments, insurance_writeoffs, patient_writeoffs, insurance_balance, patient_balance, unapplied_payments from amd.charts_before_1110
                              except all select chart_id, pulled_at, pages, charge_lines, insurance_charges, patient_charges, insurance_payments, patient_payments, insurance_writeoffs, patient_writeoffs, insurance_balance, patient_balance, unapplied_payments from amd.charts) x) as other_columns_in_old_not_in_new,
       (select count(*) from (select * from amd.charts except all select * from amd.charts_before_1110) x) as whole_rows_that_differ,
       (select count(*) from amd.charts n join amd.charts_before_1110 o using (chart_id)
        where (n.oldest_charge is distinct from o.oldest_charge and not (o.oldest_charge = date '1900-01-01' and n.oldest_charge is null))
           or (n.newest_charge is distinct from o.newest_charge and not (o.newest_charge = date '1900-01-01' and n.newest_charge is null))) as dates_changed_other_than_1900_to_none,
       ((select count(*) from (select chart_id, pulled_at, pages, charge_lines, insurance_charges, patient_charges, insurance_payments, patient_payments, insurance_writeoffs, patient_writeoffs, insurance_balance, patient_balance, unapplied_payments from amd.charts
                               except all select chart_id, pulled_at, pages, charge_lines, insurance_charges, patient_charges, insurance_payments, patient_payments, insurance_writeoffs, patient_writeoffs, insurance_balance, patient_balance, unapplied_payments from amd.charts_before_1110) x) = 0
        and (select count(*) from (select chart_id, pulled_at, pages, charge_lines, insurance_charges, patient_charges, insurance_payments, patient_payments, insurance_writeoffs, patient_writeoffs, insurance_balance, patient_balance, unapplied_payments from amd.charts_before_1110
                                   except all select chart_id, pulled_at, pages, charge_lines, insurance_charges, patient_charges, insurance_payments, patient_payments, insurance_writeoffs, patient_writeoffs, insurance_balance, patient_balance, unapplied_payments from amd.charts) x) = 0
        and (select count(*) from (select * from amd.charts except all select * from amd.charts_before_1110) x)
            = (select count(*) from amd.charts_before_1110 where oldest_charge = date '1900-01-01' or newest_charge = date '1900-01-01')
        and (select count(*) from amd.charts n join amd.charts_before_1110 o using (chart_id)
             where (n.oldest_charge is distinct from o.oldest_charge and not (o.oldest_charge = date '1900-01-01' and n.oldest_charge is null))
                or (n.newest_charge is distinct from o.newest_charge and not (o.newest_charge = date '1900-01-01' and n.newest_charge is null))) = 0) as ok;

-- V14 CF-04 unapplied payments are in a table now. On PROD expect 310 lines on 133 charts, 42 void, 119 zero, 149 with money, $9,266.19
select count(*) as lines, count(distinct chart_id) as charts,
       count(*) filter (where void) as void_lines, count(*) filter (where not void and paid = 0) as zero_lines_not_void,
       count(*) filter (where not void and paid <> 0) as lines_with_money, sum(paid) filter (where not void) as money_not_void, coalesce(sum(paid) filter (where void), 0) as money_on_void_lines,
       sum(paid) filter (where not void and source = '2') as from_payers, count(distinct chart_id) filter (where not void and paid <> 0 and source = '2') as charts_with_payer_money,
       sum(paid) filter (where not void and source is distinct from '2') as from_patients, count(distinct chart_id) filter (where not void and paid <> 0 and source is distinct from '2') as charts_with_patient_money,
       count(distinct payment_id) as distinct_payment_ids,
       count(*) filter (where payment_date is null or posted_at is null or paid is null) as lines_with_a_missing_date_or_amount,
       (select sum(unapplied_payments) from amd.charts) as lines_counted_in_amd_charts, (select count(*) from amd.charts where unapplied_payments > 0) as charts_counted_in_amd_charts,
       (select count(*) from amd.unapplied_payments u join amd.payments p using (payment_id)) as ids_also_in_amd_payments,
       (count(*) = (select sum(unapplied_payments) from amd.charts) and count(distinct chart_id) = (select count(*) from amd.charts where unapplied_payments > 0)
        and count(distinct payment_id) = count(*) and coalesce(sum(paid) filter (where void), 0) = 0
        and count(*) filter (where payment_date is null or posted_at is null or paid is null) = 0
        and (select count(*) from amd.unapplied_payments u join amd.payments p using (payment_id)) = 0) as ok
from amd.unapplied_payments;

-- V15 CF-04 with the unapplied lines the payments tie to AdvancedMD's own chart totals, in total and on every chart. On PROD expect 3,756,842.04 + 9,036.54 = 3,765,878.58 and 699.80 + 229.65 = 929.45
with pay as (select chart_id, sum(paid) filter (where not void and source = '2') as ins, sum(paid) filter (where not void and source is distinct from '2') as pat from amd.payments group by 1),
     un as (select chart_id, sum(paid) filter (where not void and source = '2') as ins, sum(paid) filter (where not void and source is distinct from '2') as pat from amd.unapplied_payments group by 1)
select sum(coalesce(pay.ins, 0)) as insurance_paid_on_charges, sum(coalesce(un.ins, 0)) as insurance_unapplied, sum(c.insurance_payments) as advancedmd_insurance_total,
       sum(coalesce(pay.pat, 0)) as patient_paid_on_charges, sum(coalesce(un.pat, 0)) as patient_unapplied, sum(c.patient_payments) as advancedmd_patient_total,
       count(*) filter (where c.insurance_payments is distinct from coalesce(pay.ins, 0) + coalesce(un.ins, 0)) as charts_where_insurance_does_not_tie,
       count(*) filter (where c.patient_payments is distinct from coalesce(pay.pat, 0) + coalesce(un.pat, 0)) as charts_where_patient_does_not_tie,
       count(*) filter (where c.insurance_payments is distinct from coalesce(pay.ins, 0)) as charts_that_did_not_tie_without_unapplied,
       (count(*) filter (where c.insurance_payments is distinct from coalesce(pay.ins, 0) + coalesce(un.ins, 0)) = 0
        and count(*) filter (where c.patient_payments is distinct from coalesce(pay.pat, 0) + coalesce(un.pat, 0)) = 0) as ok
from amd.charts c left join pay using (chart_id) left join un using (chart_id);

-- V16 CF-05 the date columns keep their names and carry a comment that says: day of entry, read money by year of service. One row per column
select c.relname as object_name, a.attname as column_name, format_type(a.atttypid, a.atttypmod) as type,
       col_description(c.oid, a.attnum) is not null as has_comment,
       coalesce(col_description(c.oid, a.attnum) ~ 'entered in the billing system', false) as says_day_of_entry,
       coalesce(col_description(c.oid, a.attnum) ~ 'NOT the day', false) as says_not_the_day_money_arrived,
       (col_description(c.oid, a.attnum) is not null and coalesce(col_description(c.oid, a.attnum) ~ 'entered in the billing system', false) and coalesce(col_description(c.oid, a.attnum) ~ 'NOT the day', false)) as ok
from pg_class c join pg_namespace n on n.oid = c.relnamespace join pg_attribute a on a.attrelid = c.oid and a.attnum > 0 and not a.attisdropped
where n.nspname = 'amd' and (c.relname, a.attname) in (('payments', 'payment_date'), ('v_payments', 'payment_date'), ('writeoffs', 'writeoff_date'), ('v_writeoffs', 'writeoff_date'),
      ('payment_reasons', 'payment_date'), ('v_payment_reasons', 'payment_date'), ('unapplied_payments', 'payment_date'), ('v_unapplied_payments', 'payment_date'), ('charge_outcomes', 'first_insurance_payment'))
order by 1, 2;

-- V17 CF-05 the facts behind the comment: the date equals the day of entry on every payment and write-off line, and money by year of payment date is not money by year of service. On PROD expect 2025: 2,812.68 by payment date against 770,108.06 by year of service
select (select count(*) from amd.payments) as payment_lines, (select count(*) from amd.payments where payment_date = posted_at::date) as payment_lines_dated_on_the_day_of_entry,
       (select count(*) from amd.writeoffs) as writeoff_lines, (select count(*) from amd.writeoffs where writeoff_date = posted_at::date) as writeoff_lines_dated_on_the_day_of_entry,
       (select sum(paid) from amd.payments where not void and extract(year from payment_date) = 2025) as paid_2025_by_payment_date,
       (select sum(paid) from amd.payments where not void and extract(year from dos) = 2025) as paid_2025_by_year_of_service,
       ((select count(*) from amd.payments) = (select count(*) from amd.payments where payment_date = posted_at::date)
        and (select count(*) from amd.writeoffs) = (select count(*) from amd.writeoffs where writeoff_date = posted_at::date)) as ok;

-- V18 comments: the schema comment says pseudonymous and what is not held. 64 comments on live objects and columns, 11 on the old objects
select (select obj_description(n.oid, 'pg_namespace') ~ 'PSEUDONYMOUS, NOT ANONYMOUS' from pg_namespace n where n.nspname = 'amd') as schema_says_pseudonymous_not_anonymous,
       (select obj_description(n.oid, 'pg_namespace') ~ 'can be tied to a name through other data the practice holds' from pg_namespace n where n.nspname = 'amd') as schema_says_chart_numbers_can_be_tied_to_a_name,
       (select obj_description(n.oid, 'pg_namespace') ~ 'Nothing in these tables is a patient''s name, birth date, address, phone number or member number' from pg_namespace n where n.nspname = 'amd') as schema_says_what_is_not_held,
       (select count(*) from pg_description d join pg_class c on d.classoid = 'pg_class'::regclass and c.oid = d.objoid join pg_namespace n on n.oid = c.relnamespace where n.nspname = 'amd' and c.relname !~ '_before_1110$') as comments_on_live_objects_and_columns,
       (select count(*) from pg_description d join pg_class c on d.classoid = 'pg_class'::regclass and c.oid = d.objoid join pg_namespace n on n.oid = c.relnamespace where n.nspname = 'amd' and c.relname ~ '_before_1110$') as comments_on_old_objects,
       (select count(*) from pg_description d join pg_class c on d.classoid = 'pg_class'::regclass and c.oid = d.objoid join pg_namespace n on n.oid = c.relnamespace where n.nspname = 'amd' and d.description ~* '(anonymous|non-identifying|de-identified)' and d.description !~* 'not anonymous') as comments_that_claim_anonymous,
       ((select obj_description(n.oid, 'pg_namespace') ~ 'PSEUDONYMOUS, NOT ANONYMOUS' from pg_namespace n where n.nspname = 'amd')
        and (select obj_description(n.oid, 'pg_namespace') ~ 'can be tied to a name through other data the practice holds' from pg_namespace n where n.nspname = 'amd')
        and (select obj_description(n.oid, 'pg_namespace') ~ 'Nothing in these tables is a patient''s name, birth date, address, phone number or member number' from pg_namespace n where n.nspname = 'amd')
        and (select count(*) from pg_description d join pg_class c on d.classoid = 'pg_class'::regclass and c.oid = d.objoid join pg_namespace n on n.oid = c.relnamespace where n.nspname = 'amd' and c.relname !~ '_before_1110$') = 64
        and (select count(*) from pg_description d join pg_class c on d.classoid = 'pg_class'::regclass and c.oid = d.objoid join pg_namespace n on n.oid = c.relnamespace where n.nspname = 'amd' and c.relname ~ '_before_1110$') = 11
        and (select count(*) from pg_description d join pg_class c on d.classoid = 'pg_class'::regclass and c.oid = d.objoid join pg_namespace n on n.oid = c.relnamespace where n.nspname = 'amd' and d.description ~* '(anonymous|non-identifying|de-identified)' and d.description !~* 'not anonymous') = 0) as ok;

-- V19 chart_facts: no zip5, no city, no marital-status column, in the table or in its view. 12 columns. No live amd object has a column named like a direct identifier
select (select count(*) from pg_attribute where attrelid in ('amd.chart_facts'::regclass, 'amd.v_chart_facts'::regclass) and attnum > 0 and not attisdropped and attname ~* '(zip|city|marital)') as zip_city_marital_columns,
       (select string_agg(attname, ', ' order by attnum) from pg_attribute where attrelid = 'amd.chart_facts'::regclass and attnum > 0 and not attisdropped) as chart_facts_columns,
       (select string_agg(attname, ', ' order by attnum) from pg_attribute where attrelid = 'amd.chart_facts'::regclass and attnum > 0 and not attisdropped)
         = (select string_agg(attname, ', ' order by attnum) from pg_attribute where attrelid = 'amd.v_chart_facts'::regclass and attnum > 0 and not attisdropped) as view_has_the_same_columns,
       (select count(*) from pg_attribute a join pg_class c on c.oid = a.attrelid join pg_namespace n on n.oid = c.relnamespace
        where n.nspname = 'amd' and c.relkind in ('v', 'm') and c.relname !~ '_before_1110$' and a.attnum > 0 and not a.attisdropped
          and a.attname ~* '(zip|city|marital|ssn|dob|birth_date|birthdate|address|street|phone|email|member|subscriber|first_name|last_name|patient_name)') as identifier_like_column_names_in_live_objects,
       (select count(*) from amd.chart_facts) as rows_in_table, (select count(*) from amd.v_chart_facts) as rows_in_view,
       (select count(*) from amd.chart_facts where birth_year < 1936) as birth_years_before_1936,
       ((select count(*) from pg_attribute where attrelid in ('amd.chart_facts'::regclass, 'amd.v_chart_facts'::regclass) and attnum > 0 and not attisdropped and attname ~* '(zip|city|marital)') = 0
        and (select string_agg(attname, ', ' order by attnum) from pg_attribute where attrelid = 'amd.chart_facts'::regclass and attnum > 0 and not attisdropped)
            = 'chart_id, pulled_at, sex, birth_year, deceased, inactive, state, profile, financial_class, insurance_order, plans, last_statement_date'
        and (select string_agg(attname, ', ' order by attnum) from pg_attribute where attrelid = 'amd.v_chart_facts'::regclass and attnum > 0 and not attisdropped)
            = 'chart_id, pulled_at, sex, birth_year, deceased, inactive, state, profile, financial_class, insurance_order, plans, last_statement_date'
        and (select count(*) from pg_attribute a join pg_class c on c.oid = a.attrelid join pg_namespace n on n.oid = c.relnamespace
             where n.nspname = 'amd' and c.relkind in ('v', 'm') and c.relname !~ '_before_1110$' and a.attnum > 0 and not a.attisdropped
               and a.attname ~* '(zip|city|marital|ssn|dob|birth_date|birthdate|address|street|phone|email|member|subscriber|first_name|last_name|patient_name)') = 0
        and (select count(*) from amd.chart_facts) = (select count(*) from amd.v_chart_facts)) as ok;

-- V20 chart_facts: on the 12 columns that stay, the new table equals the old one (both counts 0). The old table still holds zip5 and city (filled or empty)
select (select count(*) from amd.chart_facts) as rows_now, (select count(*) from amd.chart_facts_before_1110) as rows_before,
       (select count(*) from (select chart_id, pulled_at, sex, birth_year, deceased, inactive, state, profile, financial_class, insurance_order, plans, last_statement_date from amd.chart_facts
                              except all select chart_id, pulled_at, sex, birth_year, deceased, inactive, state, profile, financial_class, insurance_order, plans, last_statement_date from amd.chart_facts_before_1110) x) as in_new_not_in_old,
       (select count(*) from (select chart_id, pulled_at, sex, birth_year, deceased, inactive, state, profile, financial_class, insurance_order, plans, last_statement_date from amd.chart_facts_before_1110
                              except all select chart_id, pulled_at, sex, birth_year, deceased, inactive, state, profile, financial_class, insurance_order, plans, last_statement_date from amd.chart_facts) x) as in_old_not_in_new,
       (select count(zip5) from amd.chart_facts_before_1110) as old_rows_with_a_zip5, (select count(city) from amd.chart_facts_before_1110) as old_rows_with_a_city,
       ((select count(*) from (select chart_id, pulled_at, sex, birth_year, deceased, inactive, state, profile, financial_class, insurance_order, plans, last_statement_date from amd.chart_facts
                               except all select chart_id, pulled_at, sex, birth_year, deceased, inactive, state, profile, financial_class, insurance_order, plans, last_statement_date from amd.chart_facts_before_1110) x) = 0
        and (select count(*) from (select chart_id, pulled_at, sex, birth_year, deceased, inactive, state, profile, financial_class, insurance_order, plans, last_statement_date from amd.chart_facts_before_1110
                                   except all select chart_id, pulled_at, sex, birth_year, deceased, inactive, state, profile, financial_class, insurance_order, plans, last_statement_date from amd.chart_facts) x) = 0) as ok;

-- V21 facility_settings, before and now, by setting. MEANT TO CHANGE: nursing facility is now the five nursing buildings only. On PROD expect nursing facility 10 codes / 33,465 live lines before, 5 codes / 31,883 live lines now. other: 5 / 291 before, 10 / 1,873 now
select coalesce(n.setting, o.setting) as setting, o.codes as codes_before, n.codes as codes_now, o.charge_lines as lines_before, n.charge_lines as lines_now,
       o.live_lines as live_lines_before, n.live_lines as live_lines_now, o.live_fee as live_fee_before, n.live_fee as live_fee_now
from (select s.setting, count(*) as codes, sum(s.charge_lines) as charge_lines, sum(l.live_lines) as live_lines, sum(l.live_fee) as live_fee
      from amd.facility_settings s join (select facility_code, count(*) filter (where live) as live_lines, sum(fee) filter (where live) as live_fee from amd.charges group by 1) l using (facility_code) group by 1) n
full join (select s.setting, count(*) as codes, sum(s.charge_lines) as charge_lines, sum(l.live_lines) as live_lines, sum(l.live_fee) as live_fee
      from amd.facility_settings_before_1110 s join (select facility_code, count(*) filter (where live) as live_lines, sum(fee) filter (where live) as live_fee from amd.charges_before_1110 group by 1) l using (facility_code) group by 1) o using (setting)
order by coalesce(n.charge_lines, 0) desc;

-- V22 facility_settings, the checks: same codes and same line counts as before, nursing facility = codes among the five, and a setting changed only for SEVEN, STJAM, EDEN, WMIL, HCAR (nursing facility -> other)
select (select count(*) from amd.facility_settings) as codes_now, (select count(*) from amd.facility_settings_before_1110) as codes_before,
       (select sum(charge_lines) from amd.facility_settings) as lines_now, (select count(*) from amd.charges) as charge_rows,
       (select count(*) from amd.facility_settings where setting = 'nursing facility') as nursing_facility_codes,
       (select count(*) from amd.facility_settings where setting = 'nursing facility' and facility_code not in ('BRYNW', 'C', 'ASP', 'PRU', 'WMBH')) as nursing_facility_codes_outside_the_five,
       (select count(*) from amd.facility_settings where facility_code in ('BRYNW', 'C', 'ASP', 'PRU', 'WMBH') and setting <> 'nursing facility') as codes_of_the_five_not_nursing_facility,
       (select count(*) from amd.facility_settings n join amd.facility_settings_before_1110 o using (facility_code) where n.setting is distinct from o.setting) as codes_whose_setting_changed,
       (select string_agg(n.facility_code, ', ' order by n.facility_code) from amd.facility_settings n join amd.facility_settings_before_1110 o using (facility_code) where n.setting is distinct from o.setting) as changed_codes,
       (select count(*) from amd.facility_settings n join amd.facility_settings_before_1110 o using (facility_code)
        where n.setting is distinct from o.setting and not (n.facility_code in ('SEVEN', 'STJAM', 'EDEN', 'WMIL', 'HCAR') and o.setting = 'nursing facility' and n.setting = 'other')) as unexpected_changes,
       (select count(*) from (select facility_code, facility, charge_lines, first_dos, last_dos from amd.facility_settings except all select facility_code, facility, charge_lines, first_dos, last_dos from amd.facility_settings_before_1110) x) as other_columns_that_differ,
       (select string_agg(distinct setting, ', ' order by setting) from amd.facility_settings) as settings_now,
       ((select count(*) from amd.facility_settings) = (select count(*) from amd.facility_settings_before_1110)
        and (select sum(charge_lines) from amd.facility_settings) = (select count(*) from amd.charges)
        and (select count(*) from amd.facility_settings where setting = 'nursing facility' and facility_code not in ('BRYNW', 'C', 'ASP', 'PRU', 'WMBH')) = 0
        and (select count(*) from amd.facility_settings where facility_code in ('BRYNW', 'C', 'ASP', 'PRU', 'WMBH') and setting <> 'nursing facility') = 0
        and (select count(*) from amd.facility_settings n join amd.facility_settings_before_1110 o using (facility_code)
             where n.setting is distinct from o.setting and not (n.facility_code in ('SEVEN', 'STJAM', 'EDEN', 'WMIL', 'HCAR') and o.setting = 'nursing facility' and n.setting = 'other')) = 0
        and (select count(*) from (select facility_code, facility, charge_lines, first_dos, last_dos from amd.facility_settings except all select facility_code, facility, charge_lines, first_dos, last_dos from amd.facility_settings_before_1110) x) = 0) as ok;

-- V23 charge_outcomes, before and now, measure by measure. Same rows and same money. MEANT TO CHANGE: patient_responsibility (group PR now counts codes that start with a letter: on PROD + 966.00) and rows_with_denial_codes
with n as (select count(*) as c, sum(fee) as fee, sum(balance) as balance, sum(insurance_balance) as ins_bal, sum(patient_balance) as pat_bal, sum(insurance_paid) as ins_paid, sum(patient_paid) as pat_paid,
                  sum(written_off) as wo, sum(payment_lines) as pay_lines, sum(contractual_adjustment) as co45, sum(sequestration) as co253, sum(patient_responsibility) as pr, count(denial_codes) as den,
                  count(first_insurance_payment) as first_pay, sum(fee - insurance_paid - patient_paid - written_off - balance) as residual from amd.charge_outcomes),
     o as (select count(*) as c, sum(fee) as fee, sum(balance) as balance, sum(insurance_balance) as ins_bal, sum(patient_balance) as pat_bal, sum(insurance_paid) as ins_paid, sum(patient_paid) as pat_paid,
                  sum(written_off) as wo, sum(payment_lines) as pay_lines, sum(contractual_adjustment) as co45, sum(sequestration) as co253, sum(patient_responsibility) as pr, count(denial_codes) as den,
                  count(first_insurance_payment) as first_pay, sum(fee - insurance_paid - patient_paid - written_off - balance) as residual from amd.charge_outcomes_before_1110)
select m.measure, m.before, m.now, m.before is not distinct from m.now as same, m.meant_to_change, (m.before is not distinct from m.now or m.meant_to_change) as ok
from n, o, lateral (values
  ('01 rows', o.c::numeric, n.c::numeric, false), ('02 fee', o.fee, n.fee, false), ('03 balance', o.balance, n.balance, false), ('04 insurance_balance', o.ins_bal, n.ins_bal, false),
  ('05 patient_balance', o.pat_bal, n.pat_bal, false), ('06 insurance_paid', o.ins_paid, n.ins_paid, false), ('07 patient_paid', o.pat_paid, n.pat_paid, false), ('08 written_off', o.wo, n.wo, false),
  ('09 payment_lines', o.pay_lines::numeric, n.pay_lines::numeric, false), ('10 contractual_adjustment (CO45)', o.co45, n.co45, false), ('11 sequestration (CO253)', o.co253, n.co253, false),
  ('12 rows_with_first_insurance_payment', o.first_pay::numeric, n.first_pay::numeric, false), ('13 fee - paid - written off - balance (must be 0)', o.residual, n.residual, false),
  ('14 patient_responsibility (group PR)', o.pr, n.pr, true), ('15 rows_with_denial_codes', o.den::numeric, n.den::numeric, true)) as m(measure, before, now, meant_to_change)
order by m.measure;

-- V24 charge_outcomes, line by line against the old view: 24 columns must be the same on every line. Only setting, patient_responsibility and denial_codes may differ. On PROD expect 1,582 lines with a new setting and + 966.00 patient responsibility
select count(*) as lines_compared,
       count(*) filter (where n.charge_id is null or o.charge_id is null) as lines_in_only_one_of_the_two,
       count(*) filter (where (n.chart_id, n.visit_id, n.dos, n.dos_month, n.cpt, n.modifiers, n.provider, n.facility_code, n.current_carrier, n.fee, n.balance, n.insurance_balance, n.patient_balance, n.bill_date, n.bill_status,
                               n.insurance_paid, n.patient_paid, n.first_insurance_payment, n.paying_carriers, n.payment_lines, n.written_off, n.writeoff_codes, n.contractual_adjustment, n.sequestration)
                          is distinct from
                              (o.chart_id, o.visit_id, o.dos, o.dos_month, o.cpt, o.modifiers, o.provider, o.facility_code, o.current_carrier, o.fee, o.balance, o.insurance_balance, o.patient_balance, o.bill_date, o.bill_status,
                               o.insurance_paid, o.patient_paid, o.first_insurance_payment, o.paying_carriers, o.payment_lines, o.written_off, o.writeoff_codes, o.contractual_adjustment, o.sequestration)) as lines_where_another_column_differs,
       count(*) filter (where n.setting is distinct from o.setting) as lines_with_a_new_setting,
       count(*) filter (where n.setting is distinct from o.setting and not (o.setting = 'nursing facility' and n.setting = 'other' and n.facility_code in ('SEVEN', 'STJAM', 'EDEN', 'WMIL', 'HCAR'))) as setting_changes_not_expected,
       count(*) filter (where n.patient_responsibility is distinct from o.patient_responsibility) as lines_with_new_patient_responsibility,
       sum(coalesce(n.patient_responsibility, 0) - coalesce(o.patient_responsibility, 0)) as patient_responsibility_added,
       count(*) filter (where n.denial_codes is distinct from o.denial_codes) as lines_with_new_denial_codes,
       count(*) filter (where n.patient_responsibility is distinct from o.patient_responsibility or n.denial_codes is distinct from o.denial_codes) as lines_touched_by_the_reason_code_correction,
       (count(*) filter (where n.charge_id is null or o.charge_id is null) = 0
        and count(*) filter (where (n.chart_id, n.visit_id, n.dos, n.dos_month, n.cpt, n.modifiers, n.provider, n.facility_code, n.current_carrier, n.fee, n.balance, n.insurance_balance, n.patient_balance, n.bill_date, n.bill_status,
                               n.insurance_paid, n.patient_paid, n.first_insurance_payment, n.paying_carriers, n.payment_lines, n.written_off, n.writeoff_codes, n.contractual_adjustment, n.sequestration)
                          is distinct from
                              (o.chart_id, o.visit_id, o.dos, o.dos_month, o.cpt, o.modifiers, o.provider, o.facility_code, o.current_carrier, o.fee, o.balance, o.insurance_balance, o.patient_balance, o.bill_date, o.bill_status,
                               o.insurance_paid, o.patient_paid, o.first_insurance_payment, o.paying_carriers, o.payment_lines, o.written_off, o.writeoff_codes, o.contractual_adjustment, o.sequestration)) = 0
        and count(*) filter (where n.setting is distinct from o.setting and not (o.setting = 'nursing facility' and n.setting = 'other' and n.facility_code in ('SEVEN', 'STJAM', 'EDEN', 'WMIL', 'HCAR'))) = 0) as ok
from amd.charge_outcomes n full join amd.charge_outcomes_before_1110 o using (charge_id);

-- V25 charge_outcomes by setting, before and now. MEANT TO CHANGE: lines of the five moved codes go from nursing facility to other. The totals over all settings are the same (V23)
select coalesce(n.setting, o.setting) as setting, o.lines as lines_before, n.lines as lines_now, o.fee as fee_before, n.fee as fee_now, o.insurance_paid as insurance_paid_before, n.insurance_paid as insurance_paid_now,
       o.written_off as written_off_before, n.written_off as written_off_now, o.balance as balance_before, n.balance as balance_now
from (select setting, count(*) as lines, sum(fee) as fee, sum(insurance_paid) as insurance_paid, sum(written_off) as written_off, sum(balance) as balance from amd.charge_outcomes group by 1) n
full join (select setting, count(*) as lines, sum(fee) as fee, sum(insurance_paid) as insurance_paid, sum(written_off) as written_off, sum(balance) as balance from amd.charge_outcomes_before_1110 group by 1) o using (setting)
order by coalesce(n.lines, 0) desc;

-- V26 paid_lines_monthly, before and now. Same lines and same money. MEANT TO CHANGE: the number of rows (groups), because lines of the five moved codes now sit under other
with n as (select count(*) as c, sum(lines) as lines, sum(lines_paid) as lines_paid, sum(charged) as charged, sum(insurance_paid) as ins_paid, sum(patient_paid) as pat_paid, sum(written_off) as wo, sum(still_open) as still_open,
                  sum(lines) filter (where paid_by = 'not paid') as not_paid_lines from amd.paid_lines_monthly),
     o as (select count(*) as c, sum(lines) as lines, sum(lines_paid) as lines_paid, sum(charged) as charged, sum(insurance_paid) as ins_paid, sum(patient_paid) as pat_paid, sum(written_off) as wo, sum(still_open) as still_open,
                  sum(lines) filter (where paid_by = 'not paid') as not_paid_lines from amd.paid_lines_monthly_before_1110)
select m.measure, m.before, m.now, m.before is not distinct from m.now as same, m.meant_to_change, (m.before is not distinct from m.now or m.meant_to_change) as ok
from n, o, lateral (values
  ('01 lines', o.lines, n.lines, false), ('02 lines_paid', o.lines_paid, n.lines_paid, false), ('03 charged', o.charged, n.charged, false), ('04 insurance_paid', o.ins_paid, n.ins_paid, false),
  ('05 patient_paid', o.pat_paid, n.pat_paid, false), ('06 written_off', o.wo, n.wo, false), ('07 still_open', o.still_open, n.still_open, false), ('08 lines labelled not paid', o.not_paid_lines, n.not_paid_lines, false),
  ('09 rows (groups)', o.c::numeric, n.c::numeric, true)) as m(measure, before, now, meant_to_change)
order by m.measure;

-- V27 paid_lines_monthly: outside the two settings that exchange lines (nursing facility, other) every row is the same as before (both counts 0)
select (select count(*) from (select * from amd.paid_lines_monthly where setting not in ('nursing facility', 'other') except all select * from amd.paid_lines_monthly_before_1110 where setting not in ('nursing facility', 'other')) x) as rows_in_new_not_in_old,
       (select count(*) from (select * from amd.paid_lines_monthly_before_1110 where setting not in ('nursing facility', 'other') except all select * from amd.paid_lines_monthly where setting not in ('nursing facility', 'other')) x) as rows_in_old_not_in_new,
       (select sum(lines) from amd.paid_lines_monthly where setting in ('nursing facility', 'other')) as lines_in_the_two_settings_now,
       (select sum(lines) from amd.paid_lines_monthly_before_1110 where setting in ('nursing facility', 'other')) as lines_in_the_two_settings_before,
       ((select count(*) from (select * from amd.paid_lines_monthly where setting not in ('nursing facility', 'other') except all select * from amd.paid_lines_monthly_before_1110 where setting not in ('nursing facility', 'other')) x) = 0
        and (select count(*) from (select * from amd.paid_lines_monthly_before_1110 where setting not in ('nursing facility', 'other') except all select * from amd.paid_lines_monthly where setting not in ('nursing facility', 'other')) x) = 0
        and (select sum(lines) from amd.paid_lines_monthly where setting in ('nursing facility', 'other')) = (select sum(lines) from amd.paid_lines_monthly_before_1110 where setting in ('nursing facility', 'other'))) as ok;

-- V28 every live table equals its live view today (rows in one and not in the other, both ways: all 0)
select t.table_name, t.in_table_not_in_view, t.in_view_not_in_table, (t.in_table_not_in_view = 0 and t.in_view_not_in_table = 0) as ok
from (select 'charts' as table_name, (select count(*) from (select * from amd.charts except all select * from amd.v_charts) a) as in_table_not_in_view, (select count(*) from (select * from amd.v_charts except all select * from amd.charts) a) as in_view_not_in_table
      union all select 'charges', (select count(*) from (select * from amd.charges except all select * from amd.v_charges) a), (select count(*) from (select * from amd.v_charges except all select * from amd.charges) a)
      union all select 'payments', (select count(*) from (select * from amd.payments except all select * from amd.v_payments) a), (select count(*) from (select * from amd.v_payments except all select * from amd.payments) a)
      union all select 'payment_reasons', (select count(*) from (select * from amd.payment_reasons except all select * from amd.v_payment_reasons) a), (select count(*) from (select * from amd.v_payment_reasons except all select * from amd.payment_reasons) a)
      union all select 'writeoffs', (select count(*) from (select * from amd.writeoffs except all select * from amd.v_writeoffs) a), (select count(*) from (select * from amd.v_writeoffs except all select * from amd.writeoffs) a)
      union all select 'unapplied_payments', (select count(*) from (select * from amd.unapplied_payments except all select * from amd.v_unapplied_payments) a), (select count(*) from (select * from amd.v_unapplied_payments except all select * from amd.unapplied_payments) a)
      union all select 'chart_facts', (select count(*) from (select * from amd.chart_facts except all select * from amd.v_chart_facts) a), (select count(*) from (select * from amd.v_chart_facts except all select * from amd.chart_facts) a)) t;

-- V29 fingerprints after the migration: one hash per table or view over every row and column. Compare with the fingerprints taken BEFORE the migration:
-- the old objects (charts_before_1110, charges_before_1110, payment_reasons_before_1110) and the old analysis views (..._before_1110) must show the hash their live name showed before,
-- payments and writeoffs must show the same hash as before (not touched).
-- expected_on_prod = the hash recorded on PROD on 11/10/2026 before the migration: for the old objects the hash their live name showed, for the corrected ones the hash of the
-- corrected body run read-only (prod_expected.sql). as_expected_on_prod is filled on PROD only (11,050 charts) and must be true on every row there
select object_name, f.row_count, f.fingerprint, e.fingerprint as expected_on_prod,
       case when (select count(*) from amd.charts) = 11050 then f.fingerprint is not distinct from e.fingerprint end as as_expected_on_prod
from (values ('charts', '8ea9905565d1d0217779212ee1d45e2f'), ('charges', 'b101703dea9606dbcf654c82da13c871'), ('payment_reasons', '21c8b5c1d9d5e3e52866688226685234'),
             ('unapplied_payments', '394d45217fb2c6d30c87d085cce5ae84'), ('chart_facts', 'bdceb76b23aa4bea13cb3f5b0dfde0ab'),
             ('facility_settings (view)', '2fc7e13f5d8b60398f3cadb5d495e460'), ('charge_outcomes (view)', 'bada263b78d4ac6a739e5d32d61132b5'), ('paid_lines_monthly (view)', '24f95c03a1e4db5fb0f154cdc411095d'),
             ('charts_before_1110', '1feb977c1b3763cd95a4da7e0bd597c3'), ('charges_before_1110', 'b101703dea9606dbcf654c82da13c871'), ('payment_reasons_before_1110', 'ec30305d9cd7b0dbdb6d97e9e9754c14'),
             ('payments', 'ef6ecf40b1bf4176bb2c9b789b267c9a'), ('writeoffs', '53a4fac1141ff083cbf2bb8c4d93e339'),
             ('facility_settings_before_1110 (view)', '2bdefae336ac0f032baaec0d106f91ed'), ('charge_outcomes_before_1110 (view)', '6d42132a7c8026c1c188cfd79229ec99'),
             ('paid_lines_monthly_before_1110 (view)', '410112bdc44628a7f30d336068751eed')) as e(object_name, fingerprint)
full join (
select 'charts_before_1110' as object_name, count(*) as row_count, md5(string_agg(h, '' order by h)) as fingerprint from (select md5(t::text) as h from amd.charts_before_1110 t) x
union all select 'charges_before_1110', count(*), md5(string_agg(h, '' order by h)) from (select md5(t::text) as h from amd.charges_before_1110 t) x
union all select 'payment_reasons_before_1110', count(*), md5(string_agg(h, '' order by h)) from (select md5(t::text) as h from amd.payment_reasons_before_1110 t) x
union all select 'payments', count(*), md5(string_agg(h, '' order by h)) from (select md5(t::text) as h from amd.payments t) x
union all select 'writeoffs', count(*), md5(string_agg(h, '' order by h)) from (select md5(t::text) as h from amd.writeoffs t) x
union all select 'facility_settings_before_1110 (view)', count(*), md5(string_agg(h, '' order by h)) from (select md5(t::text) as h from amd.facility_settings_before_1110 t) x
union all select 'charge_outcomes_before_1110 (view)', count(*), md5(string_agg(h, '' order by h)) from (select md5(t::text) as h from amd.charge_outcomes_before_1110 t) x
union all select 'paid_lines_monthly_before_1110 (view)', count(*), md5(string_agg(h, '' order by h)) from (select md5(t::text) as h from amd.paid_lines_monthly_before_1110 t) x
union all select 'charts', count(*), md5(string_agg(h, '' order by h)) from (select md5(t::text) as h from amd.charts t) x
union all select 'charges', count(*), md5(string_agg(h, '' order by h)) from (select md5(t::text) as h from amd.charges t) x
union all select 'payment_reasons', count(*), md5(string_agg(h, '' order by h)) from (select md5(t::text) as h from amd.payment_reasons t) x
union all select 'unapplied_payments', count(*), md5(string_agg(h, '' order by h)) from (select md5(t::text) as h from amd.unapplied_payments t) x
union all select 'chart_facts', count(*), md5(string_agg(h, '' order by h)) from (select md5(t::text) as h from amd.chart_facts t) x
union all select 'facility_settings (view)', count(*), md5(string_agg(h, '' order by h)) from (select md5(t::text) as h from amd.facility_settings t) x
union all select 'charge_outcomes (view)', count(*), md5(string_agg(h, '' order by h)) from (select md5(t::text) as h from amd.charge_outcomes t) x
union all select 'paid_lines_monthly (view)', count(*), md5(string_agg(h, '' order by h)) from (select md5(t::text) as h from amd.paid_lines_monthly t) x
) f using (object_name) order by object_name;

-- V30 the totals in one place (the figures the lead compares with the expected PROD totals)
select (select count(*) from amd.charts) as charts, (select count(*) from amd.charts where oldest_charge is null) as charts_with_no_date,
       (select count(*) from amd.charges) as charge_rows, (select count(*) from amd.charges where live) as live_charge_rows,
       (select sum(fee) from amd.charges where live) as live_fee, (select sum(settled) from amd.charges where live) as live_settled, (select sum(balance) from amd.charges where live) as live_balance,
       (select count(*) from amd.payments) as payment_rows, (select count(*) from amd.payments where not void) as payment_rows_not_void, (select sum(paid) from amd.payments where not void) as paid_not_void,
       (select count(*) from amd.writeoffs) as writeoff_rows, (select count(*) from amd.writeoffs where not void) as writeoff_rows_not_void, (select sum(written_off) from amd.writeoffs where not void) as written_off_not_void,
       (select count(*) from amd.payment_reasons) as reason_rows,
       (select count(*) from amd.payment_reasons where reason_group is distinct from substring(reason_code from '^[A-Za-z]+') or carc is distinct from substring(reason_code from '[0-9].*$')) as reason_rows_whose_split_changed,
       (select count(*) from amd.unapplied_payments) as unapplied_lines, (select count(*) from amd.unapplied_payments where not void and paid <> 0) as unapplied_lines_with_money,
       (select sum(paid) from amd.unapplied_payments where not void) as unapplied_money, (select count(distinct chart_id) from amd.unapplied_payments) as charts_with_unapplied_lines,
       (select count(*) from amd.chart_facts) as chart_facts_rows,
       (select count(*) from amd.charge_outcomes) as charge_outcomes_rows, (select count(*) from amd.paid_lines_monthly) as paid_lines_monthly_rows,
       (select count(*) from amd.charge_outcomes where setting = 'nursing facility') as live_lines_in_nursing_facility;

-- V31 on PROD only (11,050 charts): do the totals equal the figures recorded before the migration? Every other database shows "not PROD". The figures hold as long as no document was loaded again since 11/10/2026 11:52 UTC
select case when t.charts <> 11050 then 'not PROD: no fixed figures to compare with'
            when t.charts_with_no_date = 5534 and t.charge_rows = 84617 and t.live_charge_rows = 68727 and t.live_fee = 10521029.45 and t.live_settled = 10042860.47 and t.live_balance = 478168.98
             and t.payment_rows = 91094 and t.payment_rows_not_void = 89190 and t.paid_not_void = 3757541.84 and t.writeoff_rows = 108768 and t.writeoff_rows_not_void = 84014 and t.written_off_not_void = 6285318.63
             and t.reason_rows = 154197 and t.reason_rows_whose_split_changed = 1415 and t.reason_groups = 5 and t.unapplied_lines = 310 and t.unapplied_lines_with_money = 149 and t.unapplied_money = 9266.19
             and t.charts_with_unapplied_lines = 133 and t.chart_facts_rows = 11050 and t.charge_outcomes_rows = 68727 and t.paid_lines_monthly_rows = 6167
             and t.nursing_facility_codes = 5 and t.live_lines_in_nursing_facility = 31883 and t.live_lines_in_other = 1873 and t.patient_responsibility = 1254499.51
            then 'yes: every total equals the figure expected on PROD'
            else 'NO: at least one total differs from the figure expected on PROD' end as prod_totals_as_expected,
       t.*
from (select (select count(*) from amd.charts) as charts, (select count(*) from amd.charts where oldest_charge is null) as charts_with_no_date,
             (select count(*) from amd.charges) as charge_rows, (select count(*) from amd.charges where live) as live_charge_rows,
             (select sum(fee) from amd.charges where live) as live_fee, (select sum(settled) from amd.charges where live) as live_settled, (select sum(balance) from amd.charges where live) as live_balance,
             (select count(*) from amd.payments) as payment_rows, (select count(*) from amd.payments where not void) as payment_rows_not_void, (select sum(paid) from amd.payments where not void) as paid_not_void,
             (select count(*) from amd.writeoffs) as writeoff_rows, (select count(*) from amd.writeoffs where not void) as writeoff_rows_not_void, (select sum(written_off) from amd.writeoffs where not void) as written_off_not_void,
             (select count(*) from amd.payment_reasons) as reason_rows,
             (select count(*) from amd.payment_reasons where reason_group is distinct from substring(reason_code from '^[A-Za-z]+') or carc is distinct from substring(reason_code from '[0-9].*$')) as reason_rows_whose_split_changed,
             (select count(distinct reason_group) from amd.payment_reasons) as reason_groups,
             (select count(*) from amd.unapplied_payments) as unapplied_lines, (select count(*) from amd.unapplied_payments where not void and paid <> 0) as unapplied_lines_with_money,
             (select sum(paid) from amd.unapplied_payments where not void) as unapplied_money, (select count(distinct chart_id) from amd.unapplied_payments) as charts_with_unapplied_lines,
             (select count(*) from amd.chart_facts) as chart_facts_rows,
             (select count(*) from amd.charge_outcomes) as charge_outcomes_rows, (select count(*) from amd.paid_lines_monthly) as paid_lines_monthly_rows,
             (select count(*) from amd.facility_settings where setting = 'nursing facility') as nursing_facility_codes,
             (select count(*) from amd.charge_outcomes where setting = 'nursing facility') as live_lines_in_nursing_facility,
             (select count(*) from amd.charge_outcomes where setting = 'other') as live_lines_in_other,
             (select sum(patient_responsibility) from amd.charge_outcomes) as patient_responsibility) t;
