-- =========================================
-- 001_init_schema.sql
-- Khởi tạo schema cho financial_oltp
-- =========================================


CREATE SCHEMA IF NOT EXISTS financial_oltp;

-- Set context cho các file migration sau
SET search_path TO financial_oltp;
