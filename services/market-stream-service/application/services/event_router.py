"""
Event router for Kafka messages.

This class wraps the existing MessageProcessor to keep all behavior
identical while placing the routing concern under the application layer.
"""

from application.processors.message_processor import MessageProcessor


class EventRouter(MessageProcessor):
    """
    Thin subclass of MessageProcessor.

    All processing logic (process_trade, process_bar, process_message)
    remains in the base class. This router is introduced only to provide
    an application-layer abstraction without changing behavior.
    """

    pass



