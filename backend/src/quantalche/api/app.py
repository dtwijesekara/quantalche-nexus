from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import router

_DEFAULT_ORIGINS = "http://localhost:3000,http://127.0.0.1:3000"

app = FastAPI(
    title="Quantalche Nexus API",
    description=(
        "REST + WebSocket signal API for the Quantalche Nexus engine "
        "(architecture.md Layer 8)."
    ),
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("QUANTALCHE_CORS_ORIGINS", _DEFAULT_ORIGINS).split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
