-- Migration: Add volume column to stock_trades_realtime table
-- Purpose: Store accumulated volume (cộng dồn) for each trade

-- Add volume column (tích lũy volume)
ALTER TABLE market_data_oltp.stock_trades_realtime 
ADD COLUMN IF NOT EXISTS volume NUMERIC(12,6) DEFAULT 0;

-- Add comment
COMMENT ON COLUMN market_data_oltp.stock_trades_realtime.volume IS 
'Volume tích lũy: cộng dồn từ các trade trước đó. Ví dụ: trade 1 size=5 → volume=5, trade 2 size=3 → volume=8';

-- Create index for faster lookups of latest volume
CREATE INDEX IF NOT EXISTS idx_trade_stock_volume ON market_data_oltp.stock_trades_realtime (stock_id, ts DESC, volume);

