import { Router } from 'express'
import { StockController } from '../controllers/stockController'

const router = Router()

// Existing routes
router.get('/', StockController.getAllStocks)
router.get('/:ticker', StockController.getStockByTicker)

// New routes for real-time data
router.get('/:ticker/quote', StockController.getStockQuote)
router.get('/:ticker/price-history', StockController.getPriceHistory)
router.get('/:ticker/news', StockController.getCompanyNews)
router.get('/:ticker/financials', StockController.getFinancials)
router.get('/:ticker/earnings', StockController.getEarnings)

// Data management routes
router.post('/refresh', StockController.refreshData)

export default router
