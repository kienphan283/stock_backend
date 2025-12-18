-- =========================================
-- 002_create_portfolio_tables.sql
-- Tạo bảng cho Portfolio và Transactions
-- =========================================

SET search_path TO portfolio_oltp;

-- 1. Bảng Portfolios
CREATE TABLE portfolios (
    portfolio_id VARCHAR(50) PRIMARY KEY, -- ID duy nhất (UUID)
    user_id VARCHAR(50) NOT NULL,         -- ID người dùng (Owner) - giả định string
    name VARCHAR(100) NOT NULL,           -- Tên danh mục (VD: "Main Portfolio")
    currency VARCHAR(10) DEFAULT 'USD',   -- Tiền tệ gốc (USD)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE portfolios IS 'Danh mục đầu tư của người dùng';

-- 2. Bảng Portfolio Transactions
-- Lưu lịch sử giao dịch (Source of truth)
CREATE TABLE portfolio_transactions (
    transaction_id VARCHAR(50) PRIMARY KEY,
    portfolio_id VARCHAR(50) NOT NULL REFERENCES portfolios(portfolio_id) ON DELETE CASCADE,
    stock_ticker VARCHAR(20) NOT NULL,    -- Mã cổ phiếu (VD: AAPL)
    transaction_type VARCHAR(20) NOT NULL CHECK (transaction_type IN ('BUY', 'SELL')), -- Loại giao dịch (đã bỏ DIVIDEND)
    quantity NUMERIC(18, 6) NOT NULL,     -- Số lượng cổ phiếu (Dương)
    price NUMERIC(18, 6) NOT NULL,        -- Giá tại thời điểm giao dịch
    fee NUMERIC(18, 6) DEFAULT 0,         -- Phí giao dịch
    tax NUMERIC(18, 6) DEFAULT 0,         -- Thuế
    transaction_date TIMESTAMP NOT NULL,  -- Ngày giao dịch
    note TEXT,                            -- Ghi chú của người dùng
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE portfolio_transactions IS 'Lịch sử giao dịch mua bán cổ phiếu';
COMMENT ON COLUMN portfolio_transactions.quantity IS 'Số lượng cổ phiếu (luôn dương)';

-- Index cho tìm kiếm nhanh theo portfolio
CREATE INDEX idx_transactions_portfolio ON portfolio_transactions(portfolio_id, transaction_date DESC);
CREATE INDEX idx_transactions_ticker ON portfolio_transactions(stock_ticker);


-- 3. Bảng Portfolio Holdings
-- Cache vị thế hiện tại (được tính toán từ transactions)
CREATE TABLE portfolio_holdings (
    holding_id VARCHAR(50) PRIMARY KEY,
    portfolio_id VARCHAR(50) NOT NULL REFERENCES portfolios(portfolio_id) ON DELETE CASCADE,
    stock_ticker VARCHAR(20) NOT NULL,
    total_shares NUMERIC(18, 6) NOT NULL DEFAULT 0,   -- Tổng số lượng đang giữ
    avg_cost_basis NUMERIC(18, 6) NOT NULL DEFAULT 0, -- Giá vốn trung bình
    first_buy_date TIMESTAMP,                         -- Ngày mua đầu tiên (cho mục đích thống kê agings)
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(portfolio_id, stock_ticker)
);

COMMENT ON TABLE portfolio_holdings IS 'Vị thế hiện tại của các mã trong danh mục (Cache)';

-- Index cho Holdings
CREATE INDEX idx_holdings_portfolio ON portfolio_holdings(portfolio_id);
