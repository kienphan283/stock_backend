// Temporary types to replace @stock-portfolio/shared
export interface Stock {
  ticker: string;
  name: string;
  price: number;
  sector: string;
}

export interface PortfolioPosition {
  ticker: string;
  shares: number;
  averagePrice: number;
  currentPrice: number;
  totalValue: number;
  gainLoss: number;
  gainLossPercent: number;
}

export interface PortfolioItem {
  ticker: string;
  quantity: number;
  cost: number;
}

export interface DividendEvent {
  id?: string;
  ticker: string;
  companyName: string;
  exDate: string;
  payDate: string;
  amount: number;
  frequency?: string;
  sector?: string;
  yield?: number;
}

export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}
