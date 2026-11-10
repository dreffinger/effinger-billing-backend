refresh materialized view amd.charts;

refresh materialized view amd.charges;

refresh materialized view amd.payments;

refresh materialized view amd.payment_reasons;

refresh materialized view amd.writeoffs;

refresh materialized view amd.unapplied_payments;

analyze amd.charges;

analyze amd.payments;

analyze amd.payment_reasons;

analyze amd.writeoffs;

analyze amd.unapplied_payments;
