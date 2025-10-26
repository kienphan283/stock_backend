/**
 * Repository Interface for Portfolio Data
 * Defines contract for portfolio data access
 */

import { PortfolioItem } from "../../types";

export interface IPortfolioRepository {
  /**
   * Get all portfolio items
   */
  getAll(): Promise<PortfolioItem[]> | PortfolioItem[];

  /**
   * Get portfolio item by ticker
   */
  getByTicker(
    ticker: string
  ): Promise<PortfolioItem | null> | PortfolioItem | null;

  /**
   * Add new portfolio item
   */
  add(item: PortfolioItem): Promise<PortfolioItem> | PortfolioItem;

  /**
   * Update existing portfolio item
   */
  update(
    ticker: string,
    item: Partial<PortfolioItem>
  ): Promise<PortfolioItem | null> | PortfolioItem | null;

  /**
   * Delete portfolio item
   */
  delete(ticker: string): Promise<boolean> | boolean;
}
