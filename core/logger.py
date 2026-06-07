# ⚡ APEX ORACLE — Logging Setup
# Beautiful, colored, structured logs
# ─────────────────────────────────────────────────

import sys
import os
from loguru import logger


def setup_logger(log_level: str = "INFO"):
    """
    Configure APEX ORACLE's logging system.
    Logs to both console (colored) and file.
    """
    # Remove default logger
    logger.remove()

    # ─── CONSOLE LOGGING (colored) ───────────────
    logger.add(
        sys.stdout,
        level=log_level,
        colorize=True,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        ),
    )

    # ─── FILE LOGGING ─────────────────────────────
    os.makedirs("logs", exist_ok=True)
    logger.add(
        "logs/apex_oracle.log",
        level=log_level,
        rotation="1 day",
        retention="7 days",
        compression="zip",
        format=(
            "{time:YYYY-MM-DD HH:mm:ss} | "
            "{level: <8} | "
            "{name}:{line} | "
            "{message}"
        ),
    )

    logger.info("⚡ APEX ORACLE Logger initialized")
    return logger


# Initialize on import
setup_logger(os.getenv("LOG_LEVEL", "INFO"))
