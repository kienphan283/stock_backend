/**
 * Bars Routes
 * Proxies FastAPI bar endpoints for charting data
 */

import { Router, Request, Response } from "express";
import { PythonFinancialClient } from "../../infrastructure/external";
import { asyncHandler } from "../middlewares";

export const createBarsRouter = (pythonClient: PythonFinancialClient): Router => {
  const router = Router();

  // GET /api/bars/:symbol - Get bars for symbol
  router.get(
    "/:symbol",
    asyncHandler(async (req: Request, res: Response) => {
      const { symbol } = req.params;
      const limit = parseInt(req.query.limit as string) || 100;

      const data = await pythonClient.get(`/bars/${symbol}?limit=${limit}`);
      res.json(data);
    })
  );

  // GET /api/bars/:symbol/range - Get bars for symbol in date range
  router.get(
    "/:symbol/range",
    asyncHandler(async (req: Request, res: Response) => {
      const { symbol } = req.params;
      const { start, end, limit } = req.query;

      if (!start || !end) {
        return res.status(400).json({
          success: false,
          error: "start and end query parameters are required",
        });
      }

      const queryParams = new URLSearchParams({
        start: start as string,
        end: end as string,
        ...(limit && { limit: limit as string }),
      });

      const data = await pythonClient.get(`/bars/${symbol}/range?${queryParams}`);
      res.json(data);
    })
  );

  // GET /api/bars/latest - Get latest bars for all symbols
  router.get(
    "/latest",
    asyncHandler(async (req: Request, res: Response) => {
      const limit = parseInt(req.query.limit as string) || 10;

      const data = await pythonClient.get(`/bars/latest?limit=${limit}`);
      res.json(data);
    })
  );

  return router;
};

