/**
 * Financial Data Client Interface
 * Defines contract for external financial data API
 */

import {
  QuoteData,
  ProfileData,
  PriceHistoryData,
  NewsData,
  FinancialsData,
  EarningsData,
  DividendsData,
} from "../../types";

export interface IFinancialClient {
  /**
   * Get real-time stock quote
   */
  getQuote(ticker: string): Promise<QuoteData | null>;

  /**
   * Get company profile
   */
  getProfile(ticker: string): Promise<ProfileData | null>;

  /**
   * Get price history for a given period
   */
  getPriceHistory(ticker: string, period: string): Promise<PriceHistoryData | null>;

  /**
   * Get company news
   */
  getNews(limit: number): Promise<NewsData | null>;

  /**
   * Get financial statements
   */
  getFinancials(): Promise<FinancialsData | null>;

  /**
   * Get earnings data
   */
  getEarnings(): Promise<EarningsData[] | null>;

  /**
   * Get dividends data
   */
  getDividends(): Promise<DividendsData[] | null>;

  /**
   * Get list of all companies
   */
  getCompanies(): Promise<any[] | null>;

  /**
   * Refresh/reload data from source
   */
  refreshData(): Promise<boolean>;

  /**
   * Get data summary
   */
  getSummary(): Promise<any>;
}
