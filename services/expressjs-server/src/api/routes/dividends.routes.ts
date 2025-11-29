/**
 * Dividend Routes
 * Defines routes for dividend endpoints
 */

import { Router } from "express";
import { DividendController } from "../controllers";
import { validateParams, tickerParamSchema } from "../validators";

export const createDividendRouter = (
  dividendController: DividendController
): Router => {
  const router = Router();

  // GET /api/dividends - Get all dividends
  router.get("/", dividendController.getDividends);

  // GET /api/dividends/:ticker - Get dividends by ticker
  router.get(
    "/:ticker",
    validateParams(tickerParamSchema),
    dividendController.getDividendsByTicker
  );

  return router;
};
