-- =========================================
-- 001_init_schema.sql
-- Khởi tạo schema cho portfolio_oltp
-- =========================================

CREATE SCHEMA IF NOT EXISTS portfolio_oltp;

-- Set context cho các file migration sau
SET search_path TO portfolio_oltp;
