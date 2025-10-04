# withdrawal_advisor/router.py
import logging
from fastapi import APIRouter

router = APIRouter()

@router.get("/hello", response_model=str)
def api_router(

):
    return "Hello World"