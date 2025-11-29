/**
 * Stock Service
 * Business logic for stock operations
 */

import { IFinancialClient } from "../interfaces";
import { Stock } from "../../types";
import { logger, NotFoundError } from "../../utils";

export class StockService {
  constructor(private readonly financialClient: IFinancialClient) {}

  /**
   * Get all available stocks/companies
   */
  async getAllStocks(): Promise<Stock[]> {
    try {
      const companies = await this.financialClient.getCompanies();

      if (!companies) {
        logger.warn("No companies data available from external API");
        return [];
      }

      const stocks: Stock[] = companies.map((company: any) => ({
        ticker: company.ticker,
        name: company.name || company.ticker,
        price: 0,
        sector: company.sector || "Unknown",
      }));

      return stocks;
    } catch (error) {
      logger.error("Error getting all stocks", error);
      return [];
    }
  }

  /**
   * Get detailed stock information by ticker
   */
  async getStockByTicker(ticker: string): Promise<Stock | null> {
    try {
      const [quote, profile] = await Promise.all([
        this.financialClient.getQuote(ticker),
        this.financialClient.getProfile(ticker),
      ]);

      if (!quote || !profile) {
        logger.warn(`Stock data not available for ticker: ${ticker}`);
        return null;
      }

      const stock: Stock = {
        ticker: profile.ticker || ticker.toUpperCase(),
        name: profile.name || "Unknown Company",
        price: quote.currentPrice || 0,
        change: quote.change || 0,
        changePercent: quote.percentChange || 0,
        volume: 1000000, // Mock - not in current data
        marketCap: profile.marketCap || 0,
        pe: 0, // Will be filled from ratios
        eps: 0, // Will be filled from earnings
        high52: quote.high || 0,
        low52: quote.low || 0,
        sector: profile.industry || "Technology",
        industry: profile.industry || "Technology",
        description: `${profile.name} is a leading company in the ${profile.industry} sector.`,
        website: profile.website || "",
        logo: profile.logo || "",
      };

      return stock;
    } catch (error) {
      logger.error(`Error getting stock data for ${ticker}`, error);
      throw new NotFoundError(`Stock ${ticker}`);
    }
  }

  /**
   * Get real-time quote for a stock
   */
  async getQuote(ticker: string) {
    const quote = await this.financialClient.getQuote(ticker);
    if (!quote) {
      throw new NotFoundError(`Quote for ${ticker}`);
    }
    return quote;
  }

  /**
   * Get price history
   */
  async getPriceHistory(ticker: string, period: string) {
    const history = await this.financialClient.getPriceHistory(ticker, period);
    if (!history) {
      throw new NotFoundError("Price history");
    }
    return history;
  }

  /**
   * Get company news
   */
  async getNews(limit: number) {
    const news = await this.financialClient.getNews(limit);
    if (!news) {
      throw new NotFoundError("News");
    }
    return news;
  }

  /**
   * Get financial statements
   */
  async getFinancials() {
    const financials = await this.financialClient.getFinancials();
    if (!financials) {
      throw new NotFoundError("Financials");
    }
    return financials;
  }

  /**
   * Get earnings data
   */
  async getEarnings() {
    const earnings = await this.financialClient.getEarnings();
    if (!earnings) {
      throw new NotFoundError("Earnings");
    }
    return earnings;
  }

  /**
   * Refresh stock data
   */
  async refreshData(): Promise<boolean> {
    return this.financialClient.refreshData();
  }

  /**
   * Get data summary
   */
  async getDataSummary() {
    return this.financialClient.getSummary();
  }
}
