create or replace view amd.facility_settings as
-- which kind of building each AdvancedMD facility code is, and the place of service the practice has billed there.
-- Built from the facility names in the history; the five nursing buildings are the ones the charge feed sends as place of service 31.
select f.facility_code, f.facility, f.charge_lines, f.first_dos, f.last_dos,
       case when f.facility ~* 'HOSPITAL|MEDICAL CENTER|TMH|HCA FLORIDA' and f.facility !~* 'REHAB' then 'hospital'
            when f.facility ~* 'ALF|ASSISTED|SENIOR LIVING|MEMORY CARE' then 'assisted living'
            when f.facility ~* 'BRYNWOOD|ASPIRE|CENTRE POINTE|WESTMINSTER|PRUITT|SOUTHWOOD|HEALTH AND REHAB|NURSING|SKILLED|REHAB' then 'nursing facility'
            when f.facility ~* 'HOME|RESIDENCE' then 'home'
            when f.facility ~* 'OFFICE|CLINIC|EFFINGER|TELE' then 'office'
            else 'other' end as setting
from (select facility_code, max(facility) as facility, count(*) as charge_lines, min(dos) as first_dos, max(dos) as last_dos
      from amd.charges group by 1) f;

create or replace view amd.charge_outcomes as
-- one row per live charge line with what happened to it: insurance and patient payments, write-offs, what is still open,
-- the first payer payment date, and the adjustment codes posted (CO45 contractual, PR patient share, CO253 sequestration ...)
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

create or replace view amd.paid_lines_monthly as
-- the report the place-of-service question needs: charge lines by month of service, code, kind of building and paying carrier
select dos_month, cpt, setting, coalesce(nullif(paying_carriers, ''), 'not paid') as paid_by,
       count(*) as lines,
       count(*) filter (where insurance_paid > 0) as lines_paid,
       round(sum(fee), 2) as charged, round(sum(insurance_paid), 2) as insurance_paid, round(sum(patient_paid), 2) as patient_paid,
       round(sum(written_off), 2) as written_off, round(sum(balance), 2) as still_open,
       round(avg(insurance_paid) filter (where insurance_paid > 0), 2) as average_insurance_payment
from amd.charge_outcomes
group by 1, 2, 3, 4;
