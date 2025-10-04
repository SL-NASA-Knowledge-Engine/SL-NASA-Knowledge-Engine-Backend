# main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
import sys

from core.logging_config import LogLevels, configure_logging
from api.router import router


configure_logging(LogLevels.info)

app = FastAPI(
    title="Withdrawal Advisor API",
    description="API para asesorar sobre retiros de inversión.",
    version="2.1.0"
)

app.include_router(router, prefix="/api/v1")