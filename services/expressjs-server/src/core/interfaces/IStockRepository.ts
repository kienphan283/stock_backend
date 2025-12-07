/**
 * Stock Repository Interface
 * Defines contract for stock data access
 */

import { Stock } from "../../types";

export interface IStockRepository {
  /**
   * Get all stocks
   */
  getAll(): Promise<Stock[]> | Stock[];

  /**
   * Get stock by ticker
   */
  getByTicker(ticker: string): Promise<Stock | null> | Stock | null;

  /**
   * Search stocks by criteria
   */
  search(query: string): Promise<Stock[]> | Stock[];
}
