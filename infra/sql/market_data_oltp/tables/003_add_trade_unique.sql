-- Ensure idempotency for realtime trades by enforcing uniqueness on (stock_id, ts)
ALTER TABLE market_data_oltp.stock_trades_realtime
    ADD CONSTRAINT stock_trades_realtime_stock_id_ts_uniq
    UNIQUE (stock_id, ts);

