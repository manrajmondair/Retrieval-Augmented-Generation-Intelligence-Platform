from loguru import logger
import sys


def setup_logging() -> None:
    logger.remove()
    logger.add(sys.stdout, level="INFO", enqueue=True, backtrace=False, diagnose=False)

