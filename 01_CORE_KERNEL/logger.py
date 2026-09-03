import logging
import os

LOG_FOLDER = "01_CORE_KERNEL/logs"

os.makedirs(LOG_FOLDER, exist_ok=True)

logging.basicConfig(
    filename=f"{LOG_FOLDER}/jarvis.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

def log(message):
    logging.info(message)

