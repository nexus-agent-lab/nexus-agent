"""
Centralized logging configuration for Nexus Agent.

Import this module EARLY to ensure all loggers use the same format.
All other modules should use: `logger = logging.getLogger(__name__)` only.
Do NOT call logging.basicConfig() in any other file.

Global log buffer exported here: `log_buffer`
"""

import logging
import os
import sys
from collections import deque

# Global buffer to store recent logs for admin API
log_buffer = deque(maxlen=2000)


class MemoryLogHandler(logging.Handler):
    """Custom handler to store logs in memory deque."""
    def emit(self, record):
        try:
            msg = self.format(record)
            log_buffer.append(msg)
        except Exception:
            self.handleError(record)


LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FORMAT = "%(asctime)s [%(name)s] %(levelname)s: %(message)s"
LOG_DATEFMT = "%H:%M:%S"


def setup_logging():
    """Configure root logger once. Idempotent — safe to call multiple times."""
    root = logging.getLogger()

    # Only configure if no handlers exist (prevent duplicate setup)
    if root.handlers:
        return

    formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATEFMT)

    # 1. Console Handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    root.addHandler(handler)
    
    # 2. Memory Handler (for Dashboard API)
    mem_handler = MemoryLogHandler()
    mem_handler.setFormatter(formatter)
    root.addHandler(mem_handler)

    root.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))

    # Silence noisy libraries
    for lib in ["httpx", "httpcore", "aiosqlite", "sqlalchemy.engine", "websockets"]:
        logging.getLogger(lib).setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.INFO)


# Auto-setup on import
setup_logging()
