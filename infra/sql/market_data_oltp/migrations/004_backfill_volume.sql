-- Migration: Backfill accumulated volume for existing records
-- Purpose: Tính lại volume tích lũy cho các records cũ (records được insert trước khi có cột volume)

-- Update volume tích lũy cho mỗi stock theo thứ tự thời gian
-- Volume của record đầu tiên = size của nó
-- Volume của record tiếp theo = volume của record trước + size của nó

WITH ranked_trades AS (
    SELECT 
        trade_id,
        stock_id,
        ts,
        size,
        ROW_NUMBER() OVER (PARTITION BY stock_id ORDER BY ts ASC, trade_id ASC) as rn
    FROM market_data_oltp.stock_trades_realtime
    WHERE size IS NOT NULL AND size > 0
),
cumulative_volumes AS (
    SELECT 
        rt.trade_id,
        rt.stock_id,
        rt.size,
        rt.rn,
        COALESCE(SUM(rt.size) OVER (
            PARTITION BY rt.stock_id 
            ORDER BY rt.ts ASC, rt.trade_id ASC 
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ), 0) as accumulated_volume
    FROM ranked_trades rt
)
UPDATE market_data_oltp.stock_trades_realtime t
SET volume = cv.accumulated_volume
FROM cumulative_volumes cv
WHERE t.trade_id = cv.trade_id
  AND t.volume = 0;  -- Chỉ update các records có volume = 0

-- Log summary
DO $$
DECLARE
    updated_count INTEGER;
    total_count INTEGER;
    with_volume_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO total_count FROM market_data_oltp.stock_trades_realtime;
    SELECT COUNT(*) INTO with_volume_count FROM market_data_oltp.stock_trades_realtime WHERE volume > 0;
    
    RAISE NOTICE 'Backfill completed: % records with volume > 0 out of % total records', with_volume_count, total_count;
END $$;

