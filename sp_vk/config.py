"""
Определение параметров для работы бота.

Author: Milinuri Nirvalen
"""

import os

from dotenv import load_dotenv

load_dotenv()


VK_TOKEN = os.getenv("VK_TOKEN")

ENABLE_GOTIFY = os.getenv("ENABLE_GOTIFY", False)
GOTIFY_BASE_URL = os.getenv("GOTIFY_BASE_URL")
GOTIFY_APP_TOKEN = os.getenv("GOTIFY_APP_TOKEN")
