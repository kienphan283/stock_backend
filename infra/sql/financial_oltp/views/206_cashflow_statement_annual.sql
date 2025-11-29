CREATE OR REPLACE VIEW financial_oltp.vw_cashflow_statement_annual AS
SELECT
    c.company_id,
    c.company_name,
    fs.fiscal_year,
    li.item_name,
    SUM(li.item_value) AS total_value,
    li.unit,
    li.display_order,
    MAX(fs.report_date) AS latest_report_date
FROM financial_oltp.financial_statement fs
JOIN financial_oltp.company c ON fs.company_id = c.company_id
JOIN financial_oltp.statement_type st ON fs.statement_type_id = st.statement_type_id
JOIN financial_oltp.financial_line_item li ON fs.statement_id = li.statement_id
WHERE st.statement_code = 'CF'
GROUP BY 
    c.company_id,
    c.company_name,
    fs.fiscal_year,
    li.item_name,
    li.unit,
    li.display_order
ORDER BY 
    c.company_id,
    fs.fiscal_year DESC,
    li.display_order;
