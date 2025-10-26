/**
 * Financials Routes
 * Proxy requests to Python ETL API for financial data
 */

import { Router, Request, Response } from "express";
import { config } from "../../infrastructure/config";
import { logger } from "../../utils";
import { validateQuery } from "../validators/validate.middleware";
import { getFinancialsQuerySchema } from "../validators/financials.validator";

export const createFinancialsRouter = (): Router => {
  const router = Router();

  /**
   * GET /api/financials
   * Proxy financial data requests to Python API
   */
  router.get(
    "/",
    validateQuery(getFinancialsQuerySchema),
    async (req: Request, res: Response) => {
      try {
        const { company, type, period } = req.query;

        // Call Python API
        const pythonApiUrl = config.pythonApiUrl;
        const params = new URLSearchParams({
          company: company as string,
          type: type as string,
          period: period as string,
        });

        logger.info(
          `Fetching financials: ${pythonApiUrl}/api/financials?${params}`
        );

        const response = await fetch(`${pythonApiUrl}/api/financials?${params}`);

        if (!response.ok) {
          const errorText = await response.text();
          logger.error(`Python API error: ${response.status} - ${errorText}`);

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

        const data = await response.json();

        return res.json(data);
      } catch (error) {
        logger.error("Error fetching financials:", error);
        return res.status(500).json({
          success: false,
          error: error instanceof Error ? error.message : "Internal server error",
        });
      }
    });

  return router;
};
