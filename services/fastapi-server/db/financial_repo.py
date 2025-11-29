from .base_repo import BaseRepository
import logging

logger = logging.getLogger(__name__)

class FinancialRepository(BaseRepository):
    """
    Repository for financial statement data.
    
    Schema mapping:
    - symbol (e.g., "IBM") → company.company_id (ticker = company_id for US stocks)
    - company.company_id is used directly (no need to join with stocks table)
    """
    
    def get_financials(self, company_id: str, view_name: str):
        """
        Get financials from a view.
        
        Args:
            company_id: Company ID (ticker symbol, e.g., "IBM")
            view_name: View name (e.g., "financial_oltp.vw_income_statement_recent")
        """
        query = f"SELECT * FROM {view_name} WHERE company_id = %s"
        logger.info(f"[FinancialRepository] Executing query: {query} with params: ({company_id},)")
        rows = self.execute_query(query, (company_id.upper(),), fetch_all=True)
        logger.info(f"[FinancialRepository] Query returned {len(rows) if rows else 0} rows")
        return rows
    
    def get_financials_from_tables(self, company_id: str, statement_code: str):
        """
        Fallback: Query raw tables directly if view returns empty.
        
        Uses company_id directly (ticker = company_id for US stocks).
        No need to join with stocks table - financial_oltp.company is independent.
        """
        query = """
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
            FROM financial_oltp.financial_statement fs
            JOIN financial_oltp.company c ON fs.company_id = c.company_id
            JOIN financial_oltp.statement_type st ON fs.statement_type_id = st.statement_type_id
            JOIN financial_oltp.financial_line_item li ON fs.statement_id = li.statement_id
            WHERE c.company_id = %s 
              AND st.statement_code = %s
            ORDER BY fs.fiscal_year DESC, fs.fiscal_quarter DESC, li.display_order
            LIMIT 1000
        """
        logger.info(f"[FinancialRepository] Fallback query for company_id={company_id}, statement_code={statement_code}")
        rows = self.execute_query(query, (company_id.upper(), statement_code), fetch_all=True)
        logger.info(f"[FinancialRepository] Fallback query returned {len(rows) if rows else 0} rows")
        return rows
