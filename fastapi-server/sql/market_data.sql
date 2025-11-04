-- =======================
-- Schema cho dữ liệu realtime & bar
-- =======================

DROP SCHEMA IF EXISTS market_data_oltp CASCADE;
CREATE SCHEMA market_data_oltp;
SET search_path TO market_data_oltp;

-- Danh mục mã cổ phiếu
CREATE TABLE stocks (
    stock_id SERIAL PRIMARY KEY,
    company_id VARCHAR(20) REFERENCES financial_oltp.company(company_id),
    stock_ticker VARCHAR(10) UNIQUE NOT NULL,
    stock_name VARCHAR(255),
    exchange VARCHAR(20),
    delisted BOOLEAN DEFAULT FALSE
);

-- =====================================
-- (1) Bảng lưu tick / trade (giá realtime)
-- =====================================
CREATE TABLE stock_trades_realtime (
    trade_id BIGSERIAL PRIMARY KEY,
    stock_id INT REFERENCES stocks(stock_id),
    ts TIMESTAMPTZ NOT NULL,      -- thời điểm giao dịch
    price NUMERIC(12,6) NOT NULL, -- giá khớp
    size NUMERIC(12,6),           -- khối lượng
    inserted_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Index để truy vấn giá gần nhất hoặc theo thời gian
CREATE INDEX idx_trade_stock_time ON stock_trades_realtime (stock_id, ts DESC);

-- =====================================
-- (2) Bảng lưu bar (nến)
-- =====================================
CREATE TABLE stock_bars (
    bar_id BIGSERIAL PRIMARY KEY,
    stock_id INT REFERENCES stocks(stock_id),
    timeframe VARCHAR(10) NOT NULL DEFAULT '1m',
    ts TIMESTAMPTZ NOT NULL,          -- timestamp của khung thời gian
    open_price NUMERIC(12,6),
    high_price NUMERIC(12,6),
    low_price NUMERIC(12,6),
    close_price NUMERIC(12,6),
    volume BIGINT,
    trade_count INT,                  -- số lệnh trong bar
    vwap NUMERIC(14,8),               -- Volume Weighted Average Price
    inserted_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(stock_id, ts, timeframe)
);

CREATE INDEX idx_bar_stock_time ON stock_bars (stock_id, ts DESC);
CREATE INDEX idx_bar_timeframe ON stock_bars (timeframe);

-- =====================================
-- (3) Staging table cho bar (để batch insert)
-- =====================================
CREATE TABLE stock_bars_staging (
    id BIGSERIAL PRIMARY KEY,
    stock_id INT REFERENCES stocks(stock_id),
    timeframe VARCHAR(10) DEFAULT '1m',
    ts TIMESTAMPTZ NOT NULL,
    open_price NUMERIC(12,6),
    high_price NUMERIC(12,6),
    low_price NUMERIC(12,6),
    close_price NUMERIC(12,6),
    volume BIGINT,
    trade_count INT,
    vwap NUMERIC(14,8),
    inserted_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(stock_id, ts, timeframe)
);

CREATE INDEX idx_staging_stock_time ON stock_bars_staging (stock_id, ts DESC);
-- =====================================
-- (4) Bảng lưu giá cuối ngày (EOD)
-- =====================================

CREATE TABLE stock_eod_prices (
    eod_id BIGSERIAL PRIMARY KEY,
    stock_id INT REFERENCES stocks(stock_id),
    trading_date DATE NOT NULL,               -- ngày giao dịch
    open_price NUMERIC(12,6),
    high_price NUMERIC(12,6),
    low_price NUMERIC(12,6),
    close_price NUMERIC(12,6),                -- giá đóng cửa cuối ngày
    volume BIGINT,
    pct_change NUMERIC(6,2),                  -- phần trăm thay đổi so với hôm trước
    inserted_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(stock_id, trading_date)
);

CREATE INDEX idx_eod_stock_date ON stock_eod_prices (stock_id, trading_date DESC);

-- Insert IBM into company table first (to satisfy foreign key constraint)
INSERT INTO financial_oltp.company (company_id, company_name, sector, exchange)
VALUES ('IBM', 'IBM Corporation', 'Technology', 'NYSE')
ON CONFLICT (company_id) DO NOTHING;

INSERT INTO market_data_oltp.stocks (
    company_id,
    stock_ticker,
    stock_name,
    exchange,
    delisted
)
VALUES (
    'IBM',                          -- company_id trùng với bảng financial_oltp.company
    'IBM',                          -- mã chứng khoán
    'International Business Machines Corporation',  -- tên đầy đủ công ty
    'NYSE',                         -- sàn giao dịch
    FALSE                           -- chưa hủy niêm yết
);
