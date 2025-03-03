from fastapi import FastAPI
import uvicorn
from datetime import datetime
from settings.settings import Settings
from src.middleware.app_middlewares import AppMiddlewares
from src.logging.service import logger

settings = Settings()
app_middlewares = AppMiddlewares()
from src.items.router import router as items_router


app = FastAPI(
    title="Advanced FastAPI Application",
    description="A sophisticated FastAPI application with advanced configurations",
    version="0.1.0",    docs_url="/docs",
    redoc_url="/redoc"
)

app_middlewares.apply_cors_middlewares(app)

app_middlewares.apply_exception_handlers(app)

# Routes
@app.get("/")
async def read_root():
    return {"message": "Welcome to the API", "version": "0.1.0",}

@app.get("/ping")
async def ping():
    return {"message": "pong"}

@app.get("/status")
async def get_status():
    return {
        "status": "operational",
        "timestamp": datetime.now().isoformat(),
        "debug_mode": True
    }

@app.on_event("startup")
async def startup_event():
    logger.info("Application startup...")
    
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Application shutdown...")

app.include_router(items_router, prefix="/api")

# Run the application
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        workers=1
    )