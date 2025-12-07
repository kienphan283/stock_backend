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
  /**
   * @swagger
   * /dividends:
   *   get:
   *     summary: Get all dividends
   *     tags: [Dividends]
   *     responses:
   *       200:
   *         description: List of all dividends
   */
  router.get("/", dividendController.getDividends);

  // GET /api/dividends/:ticker - Get dividends by ticker
  /**
   * @swagger
   * /dividends/{ticker}:
   *   get:
   *     summary: Get dividends by ticker
   *     tags: [Dividends]
   *     parameters:
   *       - in: path
   *         name: ticker
   *         schema:
   *           type: string
   *         required: true
   *         description: Stock ticker symbol
   *     responses:
   *       200:
   *         description: Dividend history for the stock
   */
  router.get(
    "/:ticker",
    validateParams(tickerParamSchema),
    dividendController.getDividendsByTicker
  );

  return router;
};
