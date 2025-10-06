import { Stock, PortfolioItem } from '@stock-portfolio/shared'
import stocksData from '../data/stocks.json'
import portfolioData from '../data/portfolio.json'

export class DataService {
  static getAllStocks(): Stock[] {
    return stocksData as Stock[]
  }
    
  static getStockByTicker(ticker: string): Stock | null {
    const stock = stocksData.find(s => s.ticker.toUpperCase() === ticker.toUpperCase())
    return stock as Stock || null
  }

  static getPortfolio(): PortfolioItem[] {
    return portfolioData as PortfolioItem[]
  }

  static calculatePortfolioValue(portfolio: PortfolioItem[], stocks: Stock[]) {
    return portfolio.map(item => {
      const stock = stocks.find(s => s.ticker === item.ticker)
      if (!stock) return null

      const currentValue = stock.price * item.quantity
      const totalCost = item.cost * item.quantity
      const gainLoss = currentValue - totalCost
      const gainLossPercent = (gainLoss / totalCost) * 100

      return {
        ...item,
        currentValue,
        gainLoss,
        gainLossPercent
      }
    }).filter(Boolean)
  }
}
