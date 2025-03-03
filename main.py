from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, BaseSettings
from typing import Optional, List
import uvicorn
import logging
from datetime import datetime
import os
from settings.settings import Settings

settings = Settings()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI with custom configurations
app = FastAPI(
    title=settings.app_name,
    description="A sophisticated FastAPI application with advanced configurations",
    version=settings.api_version,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_hosts,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request Models
class Item(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    available: bool = True

# Custom dependency
async def get_api_key(x_api_key: str = Depends(lambda x: x)):
    if x_api_key != settings.secret_key:
        raise HTTPException(status_code=403, detail="Invalid API Key")
    return x_api_key

# Error handler
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.detail},
    )

# Routes
@app.get("/")
async def read_root():
    return {"message": "Welcome to the API", "version": settings.api_version}

@app.get("/status")
async def get_status():
    return {
        "status": "operational",
        "timestamp": datetime.now().isoformat(),
        "debug_mode": settings.debug_mode
    }

@app.post("/items/", dependencies=[Depends(get_api_key)])
async def create_item(item: Item):
    logger.info(f"Creating new item: {item.name}")
    return {"item": item, "created_at": datetime.now().isoformat()}

@app.get("/items/{item_id}")
async def read_item(item_id: int, q: Optional[str] = None):
    return {"item_id": item_id, "q": q}

# Application startup event
@app.on_event("startup")
async def startup_event():
    logger.info("Application startup...")
    # You could initialize database connections here
    
# Application shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Application shutdown...")
    # You could close database connections here

# Run the application
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug_mode,
        workers=4
    )