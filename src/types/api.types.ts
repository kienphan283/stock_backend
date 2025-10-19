/**
 * API related types
 * Types for external API responses and requests
 */

// FastAPI Response wrapper
export interface FastAPIResponse<T> {
  success: boolean;
  data: T;
}

// Quote Data from Financial API
export interface QuoteData {
  currentPrice: number;
  change: number;
  percentChange: number;
  high: number;
  low: number;
  open: number;
  previousClose: number;
}

// Company Profile Data
export interface ProfileData {
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

// Price History Data
export interface PriceHistoryData {
  dates: string[];
  series: Array<{
    name: string;
    data: number[];
  }>;
}

// News Article
export interface NewsArticle {
  id: string;
  headline: string;
  summary: string;
  source: string;
  url: string;
  datetime: string;
  category: string;
  image: string;
  assetInfoIds: string[];
}

// News Data
export interface NewsData {
  newsTotalCount: number;
  news: NewsArticle[];
}

// Financials Data
export interface FinancialsData {
  incomeStatement: any[];
  balanceSheet: any[];
  cashFlow: any[];
  supplemental: any[];
  ratios: any[];
}

// Earnings Data
export interface EarningsData {
  period: string;
  actualEps: number;
  estimateEps: number;
  surprise: number;
  surprisePercent: number;
  actualRevenue: number;
  estimateRevenue: number;
  revenueSurprise: number;
}

// Dividends Data
export interface DividendsData {
  ticker: string;
  exDate: string;
  payDate: string;
  amount: number;
  currency?: string;
}

// Generic API Response
export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}
