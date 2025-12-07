-- Clean patch script using corrected individual files
SET search_path TO financial_oltp;

\i '/docker-entrypoint-initdb.d/financial_oltp/views/201_income_statement_recent_10.sql'
\i '/docker-entrypoint-initdb.d/financial_oltp/views/202_balance_sheet_recent_10.sql'
\i '/docker-entrypoint-initdb.d/financial_oltp/views/203_cashflow_statement_recent_10.sql'
