import { Router } from 'express'
import { DividendController } from '../controllers/dividendController'

const router = Router()

router.get('/dividend-calendar', DividendController.getDividendCalendar)
router.get('/ex-dividend-calendar', DividendController.getExDividendCalendar)

export default router
