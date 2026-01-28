from fastapi import FastAPI
import uvicorn
from settings.settings import Settings
from src.middleware.app_middlewares import AppMiddlewares
from src.tts.xtts.manager.tts_manager import TtsManager

from src.routers.tts_router import router as tts_router
from src.routers.health_router import router as health_router
from src.routers.queue_router import router as queue_router
from src.queue import start_consumer, stop_consumer
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting app")
    print("Loading model...")
    tts_manager = TtsManager()
    tts_manager.model.load_model()
    print(f"lifespan instance id: {id(tts_manager)}")
    print("Model loaded")

    print("Starting queue consumer...")
    start_consumer()
    print("Queue consumer started")

    yield

    print("Stopping queue consumer...")
    stop_consumer()
    print("Stopping app")
    print("App finished")


app_middlewares = AppMiddlewares()
settings = Settings()

app = FastAPI(
    title="Advanced FastAPI Application",
    description="A sophisticated FastAPI application with advanced configurations",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    debug=True,
    lifespan=lifespan
)

app_middlewares.apply_cors_middlewares(app)

app_middlewares.apply_exception_handlers(app)

app.include_router(tts_router)
app.include_router(health_router)
app.include_router(queue_router)


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8880, reload=True)