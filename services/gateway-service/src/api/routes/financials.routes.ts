/**
 * Financials Routes
 * Pure proxy routes to market-api-service
 */

import { Router, Request, Response } from "express";
import { config } from "../../config";
import { logger } from "../../utils";
import { wrapHttpCall } from "../../utils/errorHandler";
import { validateQuery } from "../validators/validate.middleware";
import { getFinancialsQuerySchema } from "../validators/financials.validator";
import { FinancialDataResponse } from "../../types/api.types";
import { asyncHandler } from "../middlewares";

export const createFinancialsRouter = (): Router => {
  const router = Router();
  const baseUrl = config.marketApiUrl;

  /**
   * GET /api/financials
   * Proxy financial data requests to market-api-service
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
    asyncHandler(async (req: Request, res: Response) => {
      try {
        const { company, type, period } = req.query;


        logger.info(`[Gateway] Proxying financials request: company=${company}, type=${type}, period=${period}`);

        const params = new URLSearchParams({
          company: company as string,
          type: type as string,
          period: period as string,
        });

        const fullUrl = `${baseUrl}/api/financials?${params}`;
        const response = await wrapHttpCall(
          () => fetch(fullUrl),
          `fetch:${fullUrl}`
        );
        if (!response) {
          return res.status(502).json({
            success: false,
            error: "Upstream request failed",
          });
        }

        if (!response.ok) {
          const errorText = await response.text();
          logger.error(`[Gateway] Market API error: ${response.status} - ${errorText}`);

          let errorDetail = "Failed to fetch financial data from market-api-service";
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

        const data = (await response.json()) as FinancialDataResponse;
        logger.info(`[Gateway] Successfully proxied financials for ${company}, periods: ${data?.periods?.length || 0}`);

        return res.json(data);
      } catch (error) {
        logger.error("[Gateway] Error proxying financials:", error);
        return res.status(500).json({
          success: false,
          error: error instanceof Error ? error.message : "Internal server error",
        });
      }
    })
  );

  return router;
};
