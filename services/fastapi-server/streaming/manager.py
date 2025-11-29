import threading
import time
from .alpaca import AlpacaKafkaProducer
import logging

logger = logging.getLogger(__name__)

class StreamingManager:
    def __init__(self):
        self.producer = None
        self.thread = None
        self.running = False

    def start(self):
        if self.running:
            return
        
        self.running = True
        self.producer = AlpacaKafkaProducer()
        
        self.thread = threading.Thread(target=self._run_producer, daemon=True)
        self.thread.start()
        logger.info("Streaming manager started")

    def _run_producer(self):
        while self.running:
            try:
                self.producer.start()
            except Exception as e:
                logger.error(f"Producer crashed: {e}")
                time.sleep(5) # Wait before restart

    def stop(self):
        self.running = False
        if self.producer:
            self.producer.stop()
        if self.thread:
            self.thread.join(timeout=2)
        logger.info("Streaming manager stopped")

manager = StreamingManager()
