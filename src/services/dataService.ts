import { Stock, PortfolioItem } from "../types/shared";
import stocksData from "../data/stocks.json";
import portfolioData from "../data/portfolio.json";

// Python FastAPI server configuration
const PYTHON_API_URL = "http://localhost:8000";
const REQUEST_TIMEOUT = 10000; // 10 seconds

interface FastAPIResponse<T> {
  success: boolean;
  data: T;
}

// Define interfaces for FastAPI response data
interface QuoteData {
  currentPrice: number;
  change: number;
  percentChange: number;
  high: number;
  low: number;
  open: number;
  previousClose: number;
}

interface ProfileData {
  name: string;
  ticker: string;
  exchange: string;
  country: string;
  currency: string;
  industry: string;
  marketCap: number;
  ipoDate: string;
  logo: string;
  sharesOutstanding: number;
  website: string;
  phone: string;
}

interface PriceHistoryData {
  dates: string[];
  series: Array<{
    name: string;
    data: number[];
  }>;
}

interface NewsData {
  newsTotalCount: number;
  news: Array<{
    id: string;
    headline: string;
    summary: string;
    source: string;
    url: string;
    datetime: string;
    category: string;
    image: string;
    assetInfoIds: string[];
  }>;
}

interface FinancialsData {
  incomeStatement: any[];
  balanceSheet: any[];
  cashFlow: any[];
  supplemental: any[];
  ratios: any[];
}

interface EarningsData {
  period: string;
  actualEps: number;
  estimateEps: number;
  surprise: number;
  surprisePercent: number;
  actualRevenue: number;
  estimateRevenue: number;
  revenueSurprise: number;
}

export class DataService {
  // Get all stocks from database via Python API
  static async getAllStocks(): Promise<Stock[]> {
    try {
      const companiesResponse = await fetch(`${PYTHON_API_URL}/api/companies`);

      if (!companiesResponse.ok) {
        console.error("Failed to fetch companies from Python API");
        return [];
      }

      const data: any = await companiesResponse.json();

      if (!data.success || !data.companies) {
        return [];
      }

      // Map companies to Stock format
      const stocks: Stock[] = data.companies.map((company: any) => ({
        ticker: company.ticker,
        name: company.name || company.ticker,
        price: 0, // We'll fetch real price separately if needed
        sector: company.sector || "Unknown",
      }));

      return stocks;
    } catch (error) {
      console.error("Error getting all stocks:", error);
      return [];
    }
  }

  static async getStockByTicker(ticker: string): Promise<Stock | null> {
    // Always use real data, no fallback to mock JSON
    return await this.getStockByTickerWithRealData(ticker);
  }

  static getPortfolio(): PortfolioItem[] {
    return portfolioData as PortfolioItem[];
  }

  static calculatePortfolioValue(portfolio: PortfolioItem[], stocks: Stock[]) {
    return portfolio
      .map((item) => {
        const stock = stocks.find((s) => s.ticker === item.ticker);
        if (!stock) return null;

        const currentValue = stock.price * item.quantity;
        const totalCost = item.cost * item.quantity;
        const gainLoss = currentValue - totalCost;
        const gainLossPercent = (gainLoss / totalCost) * 100;

        return {
          ...item,
          currentValue,
          gainLoss,
          gainLossPercent,
        };
      })
      .filter(Boolean);
  }

  // New method to call Python FastAPI
  static async callPythonAPI<T>(endpoint: string): Promise<T | null> {
    try {
      console.log(`🐍 Calling Python API: ${PYTHON_API_URL}${endpoint}`);

      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT);

      const response = await fetch(`${PYTHON_API_URL}${endpoint}`, {
        signal: controller.signal,
        headers: {
          "Content-Type": "application/json",
        },
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        throw new Error(
          `Python API error: ${response.status} ${response.statusText}`
        );
      }

      const result = (await response.json()) as FastAPIResponse<T>;

      if (result.success) {
        console.log(`✅ Python API success: ${endpoint}`);
        return result.data;
      } else {
        throw new Error("Python API returned success: false");
      }
    } catch (error) {
      console.error(`❌ Python API error for ${endpoint}:`, error);
      return null;
    }
  }

  // New methods for real stock data with proper typing
  static async getRealStockQuote(
    ticker: string = "APP"
  ): Promise<QuoteData | null> {
    return await this.callPythonAPI<QuoteData>(`/quote?ticker=${ticker}`);
  }

  static async getRealCompanyProfile(
    ticker: string = "APP"
  ): Promise<ProfileData | null> {
    return await this.callPythonAPI<ProfileData>(`/profile?ticker=${ticker}`);
  }

  static async getRealPriceHistory(
    period: string = "3m"
  ): Promise<PriceHistoryData | null> {
    return await this.callPythonAPI<PriceHistoryData>(
      `/price-history?period=${period}`
    );
  }

  static async getRealDividends(): Promise<any[] | null> {
    return await this.callPythonAPI<any[]>("/dividends");
  }

  static async getRealNews(limit: number = 16): Promise<NewsData | null> {
    return await this.callPythonAPI<NewsData>(`/news?limit=${limit}`);
  }

  static async getRealFinancials(): Promise<FinancialsData | null> {
    return await this.callPythonAPI<FinancialsData>("/financials");
  }

  static async getRealEarnings(): Promise<EarningsData[] | null> {
    return await this.callPythonAPI<EarningsData[]>("/earnings");
  }

  static async refreshStockData(): Promise<boolean> {
    try {
      const response = await fetch(`${PYTHON_API_URL}/refresh`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
      });

      const result = (await response.json()) as FastAPIResponse<{
        refreshed: boolean;
      }>;
      return result.success;
    } catch (error) {
      console.error("❌ Error refreshing stock data:", error);
      return false;
    }
  }

  static async getDataSummary() {
    return await this.callPythonAPI("/summary");
  }

  // Enhanced stock method with real data integration
  static async getStockByTickerWithRealData(
    ticker: string
  ): Promise<Stock | null> {
    try {
      // Get real-time data from Python API
      const [quote, profile] = await Promise.all([
        this.getRealStockQuote(ticker),
        this.getRealCompanyProfile(ticker),
      ]);

      if (quote && profile) {
        // Combine real data with Stock interface structure
        return {
          ticker: profile.ticker || ticker.toUpperCase(),
          name: profile.name || "Unknown Company",
          price: quote.currentPrice || 0,
          change: quote.change || 0,
          changePercent: quote.percentChange || 0,
          volume: 1000000, // Mock volume since not in our real data
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
        } as Stock;
      }

      // Return null if real data fails - no more mock fallback
      return null;
    } catch (error) {
      console.error(`Error getting real stock data for ${ticker}:`, error);
      return null;
    }
  }
}
