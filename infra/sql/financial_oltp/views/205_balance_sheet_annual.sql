CREATE OR REPLACE VIEW financial_oltp.vw_balance_sheet_annual AS
SELECT
    c.company_id,
    c.company_name,
    fs.fiscal_year,
    li.item_name,
    li.item_value,
    li.unit,
    li.display_order,
    fs.report_date
FROM financial_oltp.financial_statement fs
JOIN financial_oltp.company c ON fs.company_id = c.company_id
JOIN financial_oltp.statement_type st ON fs.statement_type_id = st.statement_type_id
JOIN financial_oltp.financial_line_item li ON fs.statement_id = li.statement_id
WHERE st.statement_code = 'BS'
  AND fs.report_date = (
      SELECT MAX(fs2.report_date)
      FROM financial_oltp.financial_statement fs2
      WHERE fs2.company_id = fs.company_id
        AND fs2.statement_type_id = fs.statement_type_id
        AND fs2.fiscal_year = fs.fiscal_year
  )
ORDER BY 
    c.company_id,
    fs.fiscal_year DESC,
    li.display_order;

COMMENT ON VIEW financial_oltp.vw_balance_sheet_annual IS 
'Bảng cân đối kế toán cuối năm của mỗi công ty.';