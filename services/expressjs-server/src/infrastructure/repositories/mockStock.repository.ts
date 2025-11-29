/**
 * Mock Stock Repository
 * Implements IStockRepository using local JSON data (fallback)
 */

import { IStockRepository } from "../../core/interfaces";
import { Stock } from "../../types";
import stocksData from "../../data/stocks.json";

export class MockStockRepository implements IStockRepository {
  private stocks: Stock[];

  constructor() {
    this.stocks = stocksData as Stock[];
  }

  getAll(): Stock[] {
    return this.stocks;
  }

  getByTicker(ticker: string): Stock | null {
    const stock = this.stocks.find(
      (s) => s.ticker.toLowerCase() === ticker.toLowerCase()
    );
    return stock || null;
  }

  search(query: string): Stock[] {
    const lowerQuery = query.toLowerCase();
    return this.stocks.filter(
      (stock) =>
        stock.ticker.toLowerCase().includes(lowerQuery) ||
        stock.name.toLowerCase().includes(lowerQuery)
    );
  }
}
