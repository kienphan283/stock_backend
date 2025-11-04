/**
 * Python Financial API Client
 * Implements IFinancialClient interface to communicate with Python FastAPI
 */

import { IFinancialClient } from "../../core/interfaces";
import {
  QuoteData,
  ProfileData,
  PriceHistoryData,
  NewsData,
  FinancialsData,
  EarningsData,
  DividendsData,
  FastAPIResponse,
} from "../../types";
import { logger, ExternalApiError } from "../../utils";
import { config } from "../config";

export class PythonFinancialClient implements IFinancialClient {
  private readonly baseUrl: string;
  private readonly timeout: number;

  constructor(baseUrl?: string, timeout?: number) {
    this.baseUrl = baseUrl || config.pythonApiUrl;
    this.timeout = timeout || config.pythonApiTimeout;
  }

  /**
   * Generic API call method with error handling
   */
  private async call<T>(endpoint: string): Promise<T | null> {
    const url = `${this.baseUrl}${endpoint}`;
    logger.apiCall(endpoint, "GET");

    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), this.timeout);

      const response = await fetch(url, {
        signal: controller.signal,
        headers: {
          "Content-Type": "application/json",
        },
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        throw new ExternalApiError(
          "Python API",
          `${response.status} ${response.statusText}`
        );
      }

      const result = (await response.json()) as FastAPIResponse<T>;

      if (result.success) {
        logger.apiSuccess(endpoint);
        return result.data;
      } else {
        throw new ExternalApiError("Python API", "Response success: false");
      }
    } catch (error) {
      if (error instanceof ExternalApiError) {
        logger.apiError(endpoint, error);
        throw error;
      }

      logger.apiError(endpoint, error);
      return null;
    }
  }

  async getQuote(ticker: string = "APP"): Promise<QuoteData | null> {
    return this.call<QuoteData>(`/quote?ticker=${ticker}`);
  }

  async getProfile(ticker: string = "APP"): Promise<ProfileData | null> {
    return this.call<ProfileData>(`/profile?ticker=${ticker}`);
  }

  async getPriceHistory(
    ticker: string,
    period: string = "3m"
  ): Promise<PriceHistoryData | null> {
    return this.call<PriceHistoryData>(`/price-history?ticker=${ticker}&period=${period}`);
  }

  async getNews(limit: number = 16): Promise<NewsData | null> {
    return this.call<NewsData>(`/news?limit=${limit}`);
  }

  async getFinancials(): Promise<FinancialsData | null> {
    return this.call<FinancialsData>("/financials");
  }

  async getEarnings(): Promise<EarningsData[] | null> {
    return this.call<EarningsData[]>("/earnings");
  }

  async getDividends(): Promise<DividendsData[] | null> {
    return this.call<DividendsData[]>("/dividends");
  }

  async getCompanies(): Promise<any[] | null> {
    const result = await this.call<{ companies: any[] }>("/api/companies");
    return result?.companies || null;
  }

  async refreshData(): Promise<boolean> {
    try {
      const url = `${this.baseUrl}/refresh`;
      logger.apiCall("/refresh", "POST");

      const response = await fetch(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
      });

      const result = (await response.json()) as FastAPIResponse<{
        refreshed: boolean;
      }>;
      logger.apiSuccess("/refresh");
      return result.success;
    } catch (error) {
      logger.apiError("/refresh", error);
      return false;
    }
  }

  async getSummary(): Promise<any> {
    return this.call("/summary");
  }
}
