from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

_ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(_ENV_PATH)

TWELVE_DATA_API_KEY: str = os.getenv("TWELVE_DATA_API_KEY", "")
