from fastapi import FastAPI
import uvicorn
from datetime import datetime
from settings.settings import Settings
from src.middleware.app_middlewares import AppMiddlewares
from src.logging.service import logger
from src.model.instance.service import Model

from src.items.router import router as items_router
from src.tts.router import router as tts_router
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QLabel, QPushButton, QWidget
import sys
import threading
import requests


app_middlewares = AppMiddlewares()
settings = Settings()

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
    model = Model()
    model.load_model()

    logger.info("Model loaded successfully")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Application shutdown...")

app.include_router(items_router, prefix="/api")
app.include_router(tts_router, prefix="/api")


def run_api():
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=False)

# Interface Gráfica com PySide6
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FastAPI + PySide6")
        self.setGeometry(100, 100, 400, 300)
        
        layout = QVBoxLayout()
        
        self.label = QLabel("Status: Desconhecido", self)
        layout.addWidget(self.label)
        
        self.ping_button = QPushButton("Ping API", self)
        self.ping_button.clicked.connect(self.ping_api)
        layout.addWidget(self.ping_button)
        
        self.status_button = QPushButton("Obter Status", self)
        self.status_button.clicked.connect(self.get_status)
        layout.addWidget(self.status_button)
        
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def ping_api(self):
        try:
            response = requests.get("http://127.0.0.1:8000/ping")
            if response.status_code == 200:
                self.label.setText(f"Ping: {response.json()['message']}")
        except requests.exceptions.ConnectionError:
            self.label.setText("Erro: API não encontrada!")

    def get_status(self):
        try:
            response = requests.get("http://127.0.0.1:8000/status")
            if response.status_code == 200:
                status = response.json()
                self.label.setText(f"Status: {status['status']}, Debug: {status['debug_mode']}")
        except requests.exceptions.ConnectionError:
            self.label.setText("Erro: API não encontrada!")

# Inicialização da Aplicação
if __name__ == "__main__":
    # Inicia a API em um thread separado
    api_thread = threading.Thread(target=run_api, daemon=True)
    api_thread.start()

    # Inicia a Interface Gráfica no thread principal
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
