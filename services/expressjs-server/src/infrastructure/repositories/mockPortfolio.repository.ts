/**
 * Mock Portfolio Repository
 * Implements IPortfolioRepository using local JSON data
 */

import { IPortfolioRepository } from "../../core/interfaces";
import { PortfolioItem } from "../../types";
import portfolioData from "../../data/portfolio.json";

export class MockPortfolioRepository implements IPortfolioRepository {
  private portfolio: PortfolioItem[];

  constructor() {
    this.portfolio = portfolioData as PortfolioItem[];
  }

  getAll(): PortfolioItem[] {
    return this.portfolio;
  }

  getByTicker(ticker: string): PortfolioItem | null {
    const item = this.portfolio.find((p) => p.ticker === ticker);
    return item || null;
  }

  add(item: PortfolioItem): PortfolioItem {
    this.portfolio.push(item);
    return item;
  }

  update(
    ticker: string,
    updates: Partial<PortfolioItem>
  ): PortfolioItem | null {
    const index = this.portfolio.findIndex((p) => p.ticker === ticker);
    if (index === -1) return null;

    this.portfolio[index] = {
      ...this.portfolio[index],
      ...updates,
    };

    return this.portfolio[index];
  }

  delete(ticker: string): boolean {
    const index = this.portfolio.findIndex((p) => p.ticker === ticker);
    if (index === -1) return false;

    this.portfolio.splice(index, 1);
    return true;
  }
}
