/**
 * Portfolio related types
 */

export interface PortfolioItem {
  ticker: string;
  quantity: number;
  cost: number;
}

export interface PortfolioPosition extends PortfolioItem {
  shares: number;
  averagePrice: number;
  currentPrice: number;
  totalValue: number;
  gainLoss: number;
  gainLossPercent: number;
  currentValue?: number;
}
