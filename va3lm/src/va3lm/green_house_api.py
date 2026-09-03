from __future__ import annotations

from fastapi import APIRouter

from va3lm.green_house import green_house_status

router = APIRouter()


@router.get("/api/black-house/green-house")
def black_house_green_house() -> dict:
    return green_house_status()
