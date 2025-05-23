# test_datetime.py
import logging
from datetime import datetime, UTC

logging.basicConfig(level=logging.INFO)
lg = logging.getLogger(__name__)

lg.info("Testing datetime import")
t = datetime.now(UTC).strftime('%b %d, %Y')
lg.info(f"Current date: {t}")