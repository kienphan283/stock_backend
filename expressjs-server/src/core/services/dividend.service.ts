/**
 * Dividend Service
 * Business logic for dividend operations
 */

import { IFinancialClient } from "../interfaces";
import { DividendsData } from "../../types";
import { logger, NotFoundError } from "../../utils";

export class DividendService {
  constructor(private readonly financialClient: IFinancialClient) {}

  /**
   * Get dividends data
   */
  async getDividends(): Promise<DividendsData[]> {
    const dividends = await this.financialClient.getDividends();

    if (!dividends) {
      logger.warn("No dividends data available");
      throw new NotFoundError("Dividends");
    }

    return dividends;
  }

  /**
   * Calculate total dividends for a period
   */
  calculateTotalDividends(dividends: DividendsData[]): number {
    return dividends.reduce((total, div) => total + div.amount, 0);
  }

  /**
   * Get dividends by ticker
   */
  getDividendsByTicker(
    dividends: DividendsData[],
    ticker: string
  ): DividendsData[] {
    return dividends.filter(
      (div) => div.ticker.toLowerCase() === ticker.toLowerCase()
    );
  }
}
