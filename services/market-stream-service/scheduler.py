"""
ETL Job Scheduler
Schedules batch ETL jobs (BCTC, EOD)
"""

import schedule
import time
import threading
import sys
from pathlib import Path

# Ensure project root (/app in Docker) is on sys.path
ROOT_PATH = Path(__file__).resolve().parent
if str(ROOT_PATH) not in sys.path:
    sys.path.insert(0, str(ROOT_PATH))
from shared.python.utils.logging_config import get_logger

logger = get_logger(__name__)

class ETLJobScheduler:
    def __init__(self):
        self.running = False
        self.thread = None
    
    def start(self):
        """Start the scheduler"""
        logger.info("Starting ETL Job Scheduler...")
        
        # Schedule BCTC pipeline (daily at 2 AM)
        schedule.every().day.at("02:00").do(self._run_bctc)
        
        # Schedule EOD pipeline (daily at 3 AM)
        schedule.every().day.at("03:00").do(self._run_eod)
        
        # Run immediately on startup (optional)
        # self._run_bctc()
        # self._run_eod()
        
        self.running = True
        self.thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.thread.start()
        
        logger.info("ETL Job Scheduler started")
    
    def _run_scheduler(self):
        """Run the scheduler loop"""
        while self.running:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    
    def _run_bctc(self):
        """Run BCTC pipeline"""
        logger.info("Running BCTC pipeline...")
        try:
            # Import and run BCTC pipeline directly
            from etl.bctc.pipeline import run as run_bctc_pipeline
            run_bctc_pipeline()
            logger.info("BCTC pipeline completed")
        except Exception as e:
            logger.error(f"Error running BCTC pipeline: {e}")
    
    def _run_eod(self):
        """Run EOD pipeline"""
        logger.info("Running EOD pipeline...")
        try:
            # Import and run EOD pipeline directly
            from etl.eod.pipeline import run as run_eod_pipeline
            run_eod_pipeline()
            logger.info("EOD pipeline completed")
        except Exception as e:
            logger.error(f"Error running EOD pipeline: {e}")
    
    def stop(self):
        """Stop the scheduler"""
        logger.info("Stopping ETL Job Scheduler...")
        self.running = False
        schedule.clear()
        logger.info("ETL Job Scheduler stopped")

