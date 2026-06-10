import sys
import os
from loguru import logger


def setup_logger(log_level: str = "INFO"):
    logger.remove()
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
    return logger