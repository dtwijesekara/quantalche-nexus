from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

_ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(_ENV_PATH)

TWELVE_DATA_API_KEY: str = os.getenv("TWELVE_DATA_API_KEY", "")

# Alerting (architecture.md Layer 9) -- all optional, a channel is only
# enabled if its variable(s) are set. See alerting/senders.py.
ALERT_WEBHOOK_URL: str = os.getenv("ALERT_WEBHOOK_URL", "")
DISCORD_WEBHOOK_URL: str = os.getenv("DISCORD_WEBHOOK_URL", "")
TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")
