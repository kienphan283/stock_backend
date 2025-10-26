/**
 * Portfolio Controller
 * Handles HTTP requests for portfolio endpoints
 */

import { Request, Response } from "express";
import { PortfolioService, StockService } from "../../core/services";
import { ApiResponse } from "../../types";
import { asyncHandler } from "../middlewares";

export class PortfolioController {
  constructor(
    private readonly portfolioService: PortfolioService,
    private readonly stockService: StockService
  ) {}

  getPortfolio = asyncHandler(async (req: Request, res: Response) => {
    const portfolio = await this.portfolioService.getPortfolio();
    const stocks = await this.stockService.getAllStocks();
    const portfolioWithValues = this.portfolioService.calculatePortfolioValue(
      portfolio,
      stocks
    );

    const response: ApiResponse = {
      success: true,
      data: portfolioWithValues,
    };
    res.json(response);
  });

  addToPortfolio = asyncHandler(async (req: Request, res: Response) => {
    const item = this.portfolioService.addToPortfolio(req.body);

    const response: ApiResponse = {
      success: true,
      data: item,
      message: "Item added to portfolio",
    };
    res.status(201).json(response);
  });

  updatePortfolioItem = asyncHandler(async (req: Request, res: Response) => {
    const { ticker } = req.params;
    const item = this.portfolioService.updatePortfolioItem(ticker, req.body);

    const response: ApiResponse = {
      success: true,
      data: item,
      message: "Portfolio item updated",
    };
    res.json(response);
  });

  removeFromPortfolio = asyncHandler(async (req: Request, res: Response) => {
    const { ticker } = req.params;
    const success = await this.portfolioService.removeFromPortfolio(ticker);

    const response: ApiResponse = {
      success,
      message: success ? "Item removed from portfolio" : "Item not found",
    };
    res.json(response);
  });
}
