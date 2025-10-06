import { Router } from 'express'
import { StockController } from '../controllers/stockController'

const router = Router()

router.get('/', StockController.getAllStocks)
router.get('/:ticker', StockController.getStockByTicker)

export default router
