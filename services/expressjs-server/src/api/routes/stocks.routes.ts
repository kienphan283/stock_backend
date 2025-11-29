/**
 * Stock Routes
 * Defines routes for stock endpoints
 */

import { Router } from "express";
import { StockController } from "../controllers";
import {
  validateParams,
  validateQuery,
  tickerParamSchema,
  periodQuerySchema,
  limitQuerySchema,
} from "../validators";

export const createStockRouter = (stockController: StockController): Router => {
  const router = Router();

  // GET /api/stocks - Get all stocks
  router.get("/", stockController.getAllStocks);

  // GET /api/stocks/:ticker - Get stock by ticker
  router.get(
    "/:ticker",
    validateParams(tickerParamSchema),
    stockController.getStockByTicker
  );

  // GET /api/stocks/:ticker/quote - Get real-time quote
  router.get(
    "/:ticker/quote",
    validateParams(tickerParamSchema),
    stockController.getStockQuote
  );

  // GET /api/stocks/:ticker/price-history - Get price history
  router.get(
    "/:ticker/price-history",
    validateParams(tickerParamSchema),
    validateQuery(periodQuerySchema),
    stockController.getPriceHistory
  );

  // GET /api/stocks/:ticker/news - Get company news
  router.get(
    "/:ticker/news",
    validateParams(tickerParamSchema),
    validateQuery(limitQuerySchema),
    stockController.getCompanyNews
  );

  // GET /api/stocks/:ticker/financials - Get financials
  router.get(
    "/:ticker/financials",
    validateParams(tickerParamSchema),
    stockController.getFinancials
  );

  // GET /api/stocks/:ticker/earnings - Get earnings
  router.get(
    "/:ticker/earnings",
    validateParams(tickerParamSchema),
    stockController.getEarnings
  );

  // POST /api/stocks/refresh - Refresh data
  router.post("/refresh", stockController.refreshData);

  return router;
};
