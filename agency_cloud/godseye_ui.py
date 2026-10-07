from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse


router = APIRouter()
STATIC_DIR = Path(__file__).resolve().parent / "static"


@router.get("/godseye")
def godseye_dashboard():
    return FileResponse(STATIC_DIR / "godseye.html")
