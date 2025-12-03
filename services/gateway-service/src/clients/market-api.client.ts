/**
 * Market API Client
 * HTTP client for communicating with market-api-service
 */

import {
  QuoteData,
  ProfileData,
  PriceHistoryData,
  NewsData,
  FinancialsData,
  EarningsData,
  DividendsData,
  FastAPIResponse,
} from "../types";
import { logger, ExternalApiError } from "../utils";
import { wrapHttpCall } from "../utils/errorHandler";
import { config } from "../config";

export class MarketApiClient {
  private readonly baseUrl: string;
  private readonly timeout: number;

  constructor(baseUrl?: string, timeout?: number) {
    this.baseUrl = baseUrl || config.pythonApiUrl;
    this.timeout = timeout || config.pythonApiTimeout;
  }

  /**
   * Generic API call method with error handling
   */
  private async call<T>(endpoint: string, options?: RequestInit): Promise<T | null> {
    const url = `${this.baseUrl}${endpoint}`;
    logger.apiCall(url, options?.method || "GET");

    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), this.timeout);

      const response = await wrapHttpCall(
        () =>
          fetch(url, {
            ...options,
            signal: controller.signal,
            headers: {
              "Content-Type": "application/json",
              ...options?.headers,
            },
          }),
        `fetch:${url}`
      );

      clearTimeout(timeoutId);

      if (!response) {
        throw new ExternalApiError("Market API request failed", endpoint);
      }

      if (!response.ok) {
        logger.apiError(
          url,
          new Error(`HTTP ${response.status} ${response.statusText}`)
        );
        throw new ExternalApiError(
          "Market API",
          `${response.status} ${response.statusText}`
        );
      }

      const result = (await response.json()) as FastAPIResponse<T>;

      if (result.success) {
        logger.apiSuccess(url);
        return result.data;
      } else {
        throw new ExternalApiError("Market API", "Response success: false");
      }
    } catch (error) {
      if (error instanceof ExternalApiError) {
        logger.apiError(url, error);
        throw error;
      }

      logger.apiError(url, error);
      return null;
    }
  }

  async getQuote(ticker: string = "APP"): Promise<QuoteData | null> {
    return this.call<QuoteData>(`/api/quote?symbol=${ticker}`);
  }

  async getProfile(ticker: string = "APP"): Promise<ProfileData | null> {
    return this.call<ProfileData>(`/api/profile?symbol=${ticker}`);
  }

  async getPriceHistory(
    ticker: string,
    period: string = "3m"
  ): Promise<PriceHistoryData | null> {
    return this.call<PriceHistoryData>(
      `/api/price-history/eod?symbol=${ticker}&period=${period}`
    );
  }

  async getEODPriceHistory(
    ticker: string,
    period: string = "3mo"
  ): Promise<PriceHistoryData | null> {
    return this.call<PriceHistoryData>(
      `/api/price-history/eod?symbol=${ticker}&period=${period}`
    );
  }

  async getCandles(
    ticker: string,
    timeframe: string = "5m",
    limit: number = 300
  ): Promise<any[] | null> {
    return this.call<any[]>(
      `/api/candles?symbol=${ticker}&tf=${timeframe}&limit=${limit}`
    );
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

  /**
   * Generic proxy method for forwarding requests
   */
  async proxyRequest(endpoint: string, options?: RequestInit): Promise<Response> {
    const url = `${this.baseUrl}${endpoint}`;
    return fetch(url, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...options?.headers,
      },
    });
  }
}
