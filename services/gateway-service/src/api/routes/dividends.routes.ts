/**
 * Dividend Routes
 * Pure proxy routes to market-api-service
 */

import { Router, Request, Response } from "express";
import { validateParams, tickerParamSchema } from "../validators";
import { config } from "../../config";
import { asyncHandler } from "../middlewares";
import { wrapHttpCall } from "../../utils/errorHandler";

export const createDividendRouter = (): Router => {
  const router = Router();
  const baseUrl = config.marketApiUrl;
  const callUpstream = async (url: string) => {
    const response = await wrapHttpCall(() => fetch(url), `fetch:${url}`);
    if (!response) {
      return null;
    }
    const data = await response.json();
    return { status: response.status, data };
  };

  // GET /api/dividends - Get all dividends
  router.get(
    "/",
    asyncHandler(async (_req: Request, res: Response) => {
      const upstream = await callUpstream(`${baseUrl}/api/dividends`);
      if (!upstream) {
        return res.status(502).json({ success: false, error: "Upstream request failed" });
      }
      res.status(upstream.status).json(upstream.data);
    })
  );

  // GET /api/dividends/:ticker - Get dividends by ticker
  router.get(
    "/:ticker",
    validateParams(tickerParamSchema),
    asyncHandler(async (req: Request, res: Response) => {
      const { ticker } = req.params;
      const upstream = await callUpstream(`${baseUrl}/api/dividends?symbol=${ticker}`);
      if (!upstream) {
        return res.status(502).json({ success: false, error: "Upstream request failed" });
      }
      res.status(upstream.status).json(upstream.data);
    })
  );

  return router;
};
