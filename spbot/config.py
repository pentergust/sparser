"""
Определение настроек для работы бота.

Author: Milinuri Nirvalen
"""

import os

from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

ENABLE_GOTIFY = os.getenv("ENABLE_GOTIFY", False)
GOTIFY_BASE_URL = os.getenv("GOTIFY_BASE_URL")
GOTIFY_APP_TOKEN = os.getenv("GOTIFY_APP_TOKEN")
