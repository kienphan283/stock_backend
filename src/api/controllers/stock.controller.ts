/**
 * Stock Controller
 * Handles HTTP requests for stock endpoints
 */

import { Request, Response, NextFunction } from "express";
import { StockService } from "../../core/services";
import { ApiResponse } from "../../types";
import { asyncHandler } from "../middlewares";

export class StockController {
  constructor(private readonly stockService: StockService) {}

  getAllStocks = asyncHandler(async (req: Request, res: Response) => {
    const stocks = await this.stockService.getAllStocks();
    const response: ApiResponse = {
      success: true,
      data: stocks,
    };
    res.json(response);
  });

  getStockByTicker = asyncHandler(async (req: Request, res: Response) => {
    const { ticker } = req.params;
    const stock = await this.stockService.getStockByTicker(ticker);

    const response: ApiResponse = {
      success: true,
      data: stock,
    };
    res.json(response);
  });

  getStockQuote = asyncHandler(async (req: Request, res: Response) => {
    const { ticker } = req.params;
    const quote = await this.stockService.getQuote(ticker);

    const response: ApiResponse = {
      success: true,
      data: quote,
    };
    res.json(response);
  });

  getPriceHistory = asyncHandler(async (req: Request, res: Response) => {
    const { period } = req.query;
    const history = await this.stockService.getPriceHistory(
      (period as string) || "3m"
    );

    const response: ApiResponse = {
      success: true,
      data: history,
    };
    res.json(response);
  });

  getCompanyNews = asyncHandler(async (req: Request, res: Response) => {
    const { limit } = req.query;
    const news = await this.stockService.getNews(Number(limit) || 16);

    const response: ApiResponse = {
      success: true,
      data: news,
    };
    res.json(response);
  });

  getFinancials = asyncHandler(async (req: Request, res: Response) => {
    const financials = await this.stockService.getFinancials();

    const response: ApiResponse = {
      success: true,
      data: financials,
    };
    res.json(response);
  });

  getEarnings = asyncHandler(async (req: Request, res: Response) => {
    const earnings = await this.stockService.getEarnings();

    const response: ApiResponse = {
      success: true,
      data: earnings,
    };
    res.json(response);
  });

  refreshData = asyncHandler(async (req: Request, res: Response) => {
    const success = await this.stockService.refreshData();

    const response: ApiResponse = {
      success,
      data: { refreshed: success },
      ...(!success && { error: "Failed to refresh data" }),
    };

    res.status(success ? 200 : 500).json(response);
  });
}
