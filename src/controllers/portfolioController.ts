import { Request, Response } from 'express'
import { DataService } from '../services/dataService'
import { ApiResponse } from '../types/shared'

export class PortfolioController {
  static async getPortfolio(req: Request, res: Response) {
    try {
      const portfolio = DataService.getPortfolio()
      const stocks = await DataService.getAllStocks() // Added await here
      const portfolioWithValues = DataService.calculatePortfolioValue(portfolio, stocks)

      const response: ApiResponse<typeof portfolioWithValues> = {
        data: portfolioWithValues,
        success: true
      }
      res.json(response)
    } catch (error) {
      const response: ApiResponse<null> = {
        error: 'Failed to fetch portfolio',
        success: false
      }
      res.status(500).json(response)
    }
  }
}
