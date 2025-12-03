# MODULE: Alpaca streaming manager.
# PURPOSE: Supervise the Alpaca WebSocket client and restart on failure.

import threading
import time
from .websocket_client import AlpacaWebSocketClient
import logging

logger = logging.getLogger(__name__)

class AlpacaStreamingManager:
    def __init__(self):
        self.client = None
        self.thread = None
        self.running = False

    def start(self):
        if self.running:
            return
        
        self.running = True
        self.client = AlpacaWebSocketClient()
        
        self.thread = threading.Thread(target=self._run_client, daemon=True)
        self.thread.start()
        logger.info("Alpaca streaming manager started")

    def _run_client(self):
        while self.running:
            try:
                self.client.start()
            except Exception as e:
                logger.error(f"WebSocket client crashed: {e}")
                time.sleep(5)  # Wait before restart

    def stop(self):
        self.running = False
        if self.client:
            self.client.stop()
        if self.thread:
            self.thread.join(timeout=2)
        logger.info("Alpaca streaming manager stopped")

