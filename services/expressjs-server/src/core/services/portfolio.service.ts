/**
 * Portfolio Service
 * Business logic for portfolio operations
 */

import { IPortfolioRepository } from "../interfaces";
import { PortfolioItem, PortfolioPosition, Stock } from "../../types";
import { logger } from "../../utils";

export class PortfolioService {
  constructor(private readonly portfolioRepository: IPortfolioRepository) {}

  /**
   * Get all portfolio items
   */
  async getPortfolio(): Promise<PortfolioItem[]> {
    const result = this.portfolioRepository.getAll();
    return result instanceof Promise ? await result : result;
  }

  /**
   * Get portfolio with calculated values
   */
  calculatePortfolioValue(
    portfolio: PortfolioItem[],
    stocks: Stock[]
  ): (PortfolioPosition | null)[] {
    return portfolio
      .map((item) => {
        const stock = stocks.find((s) => s.ticker === item.ticker);
        if (!stock) {
          logger.warn(`Stock not found for portfolio item: ${item.ticker}`);
          return null;
        }

        const currentValue = stock.price * item.quantity;
        const totalCost = item.cost * item.quantity;
        const gainLoss = currentValue - totalCost;
        const gainLossPercent = (gainLoss / totalCost) * 100;

        const position: PortfolioPosition = {
          ...item,
          shares: item.quantity,
          averagePrice: item.cost,
          currentPrice: stock.price,
          currentValue,
          totalValue: currentValue,
          gainLoss,
          gainLossPercent,
        };

        return position;
      })
      .filter((item): item is PortfolioPosition => item !== null);
  }

  /**
   * Add item to portfolio
   */
  async addToPortfolio(item: PortfolioItem): Promise<PortfolioItem> {
    const result = this.portfolioRepository.add(item);
    return result instanceof Promise ? await result : result;
  }

  /**
   * Update portfolio item
   */
  async updatePortfolioItem(
    ticker: string,
    updates: Partial<PortfolioItem>
  ): Promise<PortfolioItem | null> {
    const result = this.portfolioRepository.update(ticker, updates);
    return result instanceof Promise ? await result : result;
  }

  /**
   * Remove item from portfolio
   */
  async removeFromPortfolio(ticker: string): Promise<boolean> {
    const result = this.portfolioRepository.delete(ticker);
    return result instanceof Promise ? await result : result;
  }
}
