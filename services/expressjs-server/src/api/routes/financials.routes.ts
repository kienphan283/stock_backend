/**
 * Financials Routes
 * Proxy requests to Python ETL API for financial data
 */

import { Router, Request, Response } from "express";
import { config } from "../../infrastructure/config";
import { logger } from "../../utils";
import { validateQuery } from "../validators/validate.middleware";
import { getFinancialsQuerySchema } from "../validators/financials.validator";
import { FinancialDataResponse } from "../../types/api.types";

export const createFinancialsRouter = (): Router => {
  const router = Router();

  /**
   * GET /api/financials
   * Proxy financial data requests to Python API
   */
  /**
   * @swagger
   * /financials:
   *   get:
   *     summary: Get financial data
   *     tags: [Financials]
   *     parameters:
   *       - in: query
   *         name: company
   *         schema:
   *           type: string
   *         required: true
   *         description: Company ticker symbol
   *       - in: query
   *         name: type
   *         schema:
   *           type: string
   *           enum: [IS, BS, CF]
   *         required: true
   *         description: Type of financial statement (IS=Income Statement, BS=Balance Sheet, CF=Cash Flow)
   *       - in: query
   *         name: period
   *         schema:
   *           type: string
   *           enum: [annual, quarterly]
   *         required: true
   *         description: Reporting period
   *     responses:
   *       200:
   *         description: Financial data
   */
  router.get(
    "/",
    validateQuery(getFinancialsQuerySchema),
    async (req: Request, res: Response) => {
      try {
        const { company, type, period } = req.query;

        console.log("[Express FinancialsRoute] Incoming request params:", { company, type, period });

        // Call Python API
        const pythonApiUrl = config.pythonApiUrl;
        const params = new URLSearchParams({
          company: company as string,
          type: type as string,
          period: period as string,
        });

        const fullUrl = `${pythonApiUrl}/api/financials?${params}`;
        logger.info(`[Express FinancialsRoute] Fetching financials: ${fullUrl}`);
        console.log("[Express FinancialsRoute] Calling FastAPI:", fullUrl);

        const response = await fetch(fullUrl);

        if (!response.ok) {
          const errorText = await response.text();
          logger.error(`[Express FinancialsRoute] Python API error: ${response.status} - ${errorText}`);
          console.error("[Express FinancialsRoute] FastAPI error:", response.status, errorText);

          let errorDetail = "Failed to fetch financial data from Python API";
          try {
            const errorJson = JSON.parse(errorText);
            errorDetail = errorJson.detail || errorDetail;
          } catch (e) {
            errorDetail = errorText || errorDetail;
          }

          return res.status(response.status).json({
            success: false,
            error: errorDetail,
          });
        }

        const data = await response.json() as FinancialDataResponse;
        console.log("[Express FinancialsRoute] FastAPI response received, periods:", data?.periods?.length || 0);
        logger.info(`[Express FinancialsRoute] Successfully fetched financials for ${company}, periods: ${data?.periods?.length || 0}`);

        return res.json(data);
      } catch (error) {
        logger.error("[Express FinancialsRoute] Error fetching financials:", error);
        console.error("[Express FinancialsRoute] Exception:", error);
        return res.status(500).json({
          success: false,
          error: error instanceof Error ? error.message : "Internal server error",
        });
      }
    });

  return router;
};
