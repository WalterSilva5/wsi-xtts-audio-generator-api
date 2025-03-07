from fastapi import FastAPI
import uvicorn
from datetime import datetime
from settings.settings import Settings
from src.middleware.app_middlewares import AppMiddlewares
from src.logging.service import logger
from src.model.instance.service import Model

from src.items.router import router as items_router
from src.tts.router import router as tts_router
from PySide6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QLabel, 
                             QPushButton, QWidget, QComboBox, QHBoxLayout,
                             QTextEdit, QMessageBox, QFileDialog)
from PySide6.QtCore import QThread, Signal
import sys
import threading
import requests
import os

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
    uvicorn.run("main:app", host="127.0.0.1", port=8000)

# Interface Gráfica com PySide6

class TtsRequestThread(QThread):
    finished = Signal(str)
    error = Signal(str)
    
    def __init__(self, text, speaker, rvc_speaker):
        super().__init__()
        self.text = text
        self.speaker = speaker
        self.rvc_speaker = rvc_speaker
        
    def run(self):
        try:
            payload = {
                "text": self.text,
                "speaker": self.speaker,
                "rvc_speaker": self.rvc_speaker if self.rvc_speaker else None
            }
            response = requests.post("http://127.0.0.1:8000/api/tts", json=payload)
            
            if response.status_code == 200:
                # Save the audio file
                save_path, _ = QFileDialog.getSaveFileName(None, "Save Audio File", 
                                                        os.path.expanduser("~"), "Audio Files (*.wav)")
                if save_path:
                    with open(save_path, 'wb') as f:
                        f.write(response.content)
                    self.finished.emit(f"Audio saved to {save_path}")
                else:
                    self.finished.emit("Operation cancelled")
            else:
                self.error.emit(f"Error: {response.status_code} - {response.text}")
        except Exception as e:
            self.error.emit(f"Error: {str(e)}")



class TtsRequestThread(QThread):
    request_save = Signal(bytes)
    error = Signal(str)
    
    def __init__(self, text, speaker, rvc_speaker):
        super().__init__()
        self.text = text
        self.speaker = speaker
        self.rvc_speaker = rvc_speaker
        
    def run(self):
        try:
            payload = {
                "text": self.text,
                "speaker": self.speaker,
                "rvc_speaker": self.rvc_speaker if self.rvc_speaker else None
            }
            response = requests.post("http://127.0.0.1:8000/api/tts", json=payload)
            
            if response.status_code == 200:
                self.request_save.emit(response.content)
            else:
                self.error.emit(f"Error: {response.status_code} - {response.text}")
        except Exception as e:
            self.error.emit(f"Error: {str(e)}")

# Interface gráfica
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("XTTS Audio Generator")
        self.setGeometry(100, 100, 600, 400)
        
        layout = QVBoxLayout()
        
        self.label = QLabel("Status: Waiting for input", self)
        layout.addWidget(self.label)
        
        text_label = QLabel("Text to convert to speech:")
        layout.addWidget(text_label)
        
        self.text_input = QTextEdit()
        self.text_input.setPlaceholderText("Enter text to convert to speech...")
        layout.addWidget(self.text_input)
        
        # XTTS Speaker selection
        speaker_layout = QHBoxLayout()
        speaker_layout.addWidget(QLabel("XTTS Voice:"))
        
        self.speaker_dropdown = QComboBox()
        self.speaker_dropdown.addItem("masculina", "masculina")
        self.speaker_dropdown.addItem("feminina", "feminina")
        self.speaker_dropdown.addItem("feminina_calma", "feminina_calma")
        self.speaker_dropdown.addItem("ozymandias", "ozymandias")
        speaker_layout.addWidget(self.speaker_dropdown)
        
        speaker_container = QWidget()
        speaker_container.setLayout(speaker_layout)
        layout.addWidget(speaker_container)
        
        # RVC Speaker selection
        rvc_layout = QHBoxLayout()
        rvc_layout.addWidget(QLabel("RVC Voice:"))
        
        self.rvc_dropdown = QComboBox()
        self.rvc_dropdown.addItem("None", "")  # Default empty option
        self.rvc_dropdown.addItem("Kratos", "kratos")
        self.rvc_dropdown.addItem("Zelda", "zelda")
        self.rvc_dropdown.addItem("Walt", "walt")
        rvc_layout.addWidget(self.rvc_dropdown)
        
        rvc_container = QWidget()
        rvc_container.setLayout(rvc_layout)
        layout.addWidget(rvc_container)
        
        self.generate_button = QPushButton("Generate Audio", self)
        self.generate_button.clicked.connect(self.generate_audio)
        layout.addWidget(self.generate_button)
        
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)
    
    def generate_audio(self):
        text = self.text_input.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "Input Error", "Please enter text to convert to speech.")
            return
        
        speaker = self.speaker_dropdown.currentData()
        rvc_speaker = self.rvc_dropdown.currentData()
        
        self.label.setText("Generating audio... Please wait.")
        self.generate_button.setEnabled(False)
        
        self.tts_thread = TtsRequestThread(text, speaker, rvc_speaker)
        self.tts_thread.request_save.connect(self.save_audio_file)
        self.tts_thread.error.connect(self.on_generation_error)
        self.tts_thread.start()
    
    def save_audio_file(self, audio_data):
        save_path, _ = QFileDialog.getSaveFileName(self, "Save Audio File", 
                                                   os.path.expanduser("~"), "Audio Files (*.wav)")
        if save_path:
            with open(save_path, 'wb') as f:
                f.write(audio_data)
            self.label.setText(f"Audio saved to {save_path}")
        else:
            self.label.setText("Operation cancelled")
        
        self.generate_button.setEnabled(True)
    
    def on_generation_error(self, error_message):
        self.label.setText(error_message)
        self.generate_button.setEnabled(True)



if __name__ == "__main__":
    # Inicia a API em um thread separado
    api_thread = threading.Thread(target=run_api, daemon=True)
    api_thread.start()

    # Inicia a Interface Gráfica no thread principal
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())