CREATE OR REPLACE VIEW vw_income_statement_recent AS
SELECT
    fs.statement_id,
    c.company_id,
    c.company_name,
    fs.fiscal_year,
    fs.fiscal_quarter,
    (fs.fiscal_year || '-' || fs.fiscal_quarter) AS fiscal_period,
    li.item_name,
    li.item_value,
    li.unit,
    li.display_order,
    fs.report_date
FROM financial_statement fs
JOIN company c ON fs.company_id = c.company_id
JOIN statement_type st ON fs.statement_type_id = st.statement_type_id
JOIN financial_line_item li ON fs.statement_id = li.statement_id
WHERE st.statement_code = 'IS'
  AND (fs.fiscal_year, fs.fiscal_quarter) IN (
      SELECT fiscal_year, fiscal_quarter
      FROM financial_statement fs2
      WHERE fs2.company_id = fs.company_id
        AND fs2.statement_type_id = fs.statement_type_id
      ORDER BY fs2.fiscal_year DESC, fs2.fiscal_quarter DESC
      LIMIT 10
  )
ORDER BY c.company_id, fs.fiscal_year DESC, fs.fiscal_quarter DESC, li.display_order;

COMMENT ON VIEW vw_income_statement_recent IS 'Báo cáo kết quả kinh doanh 10 kỳ gần nhất của mỗi công ty.';
