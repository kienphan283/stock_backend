-- =========================================
-- 003_add_portfolio_details.sql
-- Thêm các trường chi tiết cho Portfolio
-- =========================================

SET search_path TO portfolio_oltp;

ALTER TABLE portfolios 
ADD COLUMN goal_type VARCHAR(20) DEFAULT 'VALUE' CHECK (goal_type IN ('VALUE', 'PASSIVE_INCOME')),
ADD COLUMN target_amount NUMERIC(18, 6),
ADD COLUMN note TEXT;

COMMENT ON COLUMN portfolios.goal_type IS 'Mục tiêu danh mục: Tăng trưởng giá trị (VALUE) hoặc Thu nhập thụ động (PASSIVE_INCOME)';
COMMENT ON COLUMN portfolios.target_amount IS 'Số tiền mục tiêu (VD: 1,000,000 USD)';
