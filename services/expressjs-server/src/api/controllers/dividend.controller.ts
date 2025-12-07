/**
 * Dividend Controller
 * Handles HTTP requests for dividend endpoints
 */

import { Request, Response } from "express";
import { DividendService } from "../../core/services";
import { ApiResponse } from "../../types";
import { asyncHandler } from "../middlewares";

export class DividendController {
  constructor(private readonly dividendService: DividendService) {}

  getDividends = asyncHandler(async (req: Request, res: Response) => {
    const dividends = await this.dividendService.getDividends();

    const response: ApiResponse = {
      success: true,
      data: dividends,
    };
    res.json(response);
  });

  getDividendsByTicker = asyncHandler(async (req: Request, res: Response) => {
    const { ticker } = req.params;
    const allDividends = await this.dividendService.getDividends();
    const dividends = this.dividendService.getDividendsByTicker(
      allDividends,
      ticker
    );

    const response: ApiResponse = {
      success: true,
      data: dividends,
    };
    res.json(response);
  });
}
