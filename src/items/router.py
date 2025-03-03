from src.logging.service import logger
from settings.settings import Settings
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from typing import Optional, List
from pydantic import BaseModel

settings = Settings()
router = APIRouter()

class Item(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    available: bool = True

async def get_api_key(x_api_key: str = Depends(lambda x: x)):
    if x_api_key != settings.secret_key:
        raise HTTPException(status_code=403, detail="Invalid API Key")
    return x_api_key


@router.post("/items/", dependencies=[Depends(get_api_key)])
async def create_item(item: Item):
    logger.info(f"Creating new item: {item.name}")
    return {"item": item, "created_at": datetime.now().isoformat()}

@router.get("/items/{item_id}")
async def read_item(item_id: int, q: Optional[str] = None):
    return {"item_id": item_id, "q": q}