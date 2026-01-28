"""
Main window with sidebar navigation (Spotify-style).
"""
from typing import Optional

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QStackedWidget, QPushButton, QLabel, QProgressBar,
    QStatusBar, QMessageBox, QFrame, QSizePolicy
)
from PySide6.QtCore import Qt, Slot, QSize
from PySide6.QtGui import QFont, QCloseEvent

from src.core.services.tts_service import TTSService, get_tts_service
from src.core.models.settings import AppSettings
from ui.pages.synthesis_page import SynthesisPage
from ui.workers.model_loader_worker import ModelLoaderWorker


class SidebarButton(QPushButton):
    """Custom button for sidebar navigation."""

    def __init__(self, text: str, icon: str = "", parent=None):
        super().__init__(parent)
        self.setText(f"  {icon}  {text}" if icon else f"  {text}")
        self.setCheckable(True)
        self.setFlat(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(48)
        self.setStyleSheet("""
            QPushButton {
                text-align: left;
                padding: 10px 16px;
                border: none;
                border-radius: 10px;
                font-size: 14px;
                color: rgba(255, 255, 255, 0.8);
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
                color: #ffffff;
            }
            QPushButton:checked {
                background-color: rgba(74, 144, 217, 0.3);
                color: #ffffff;
                font-weight: bold;
            }
            QPushButton:disabled {
                color: rgba(255, 255, 255, 0.3);
            }
        """)


class Sidebar(QWidget):
    """Sidebar widget with navigation buttons."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._buttons = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Setup the sidebar UI."""
        self.setFixedWidth(240)
        self.setStyleSheet("""
            QWidget {
                background-color: #1a1a2e;
                color: #ffffff;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 24, 16, 24)
        layout.setSpacing(6)

        # App title
        title = QLabel("XTTS Desktop")
        title.setFont(QFont("", 20, QFont.Bold))
        title.setStyleSheet("color: #ffffff; padding: 10px 0 24px 0;")
        layout.addWidget(title)

        # Section label
        section_label = QLabel("MENU PRINCIPAL")
        section_label.setStyleSheet("color: rgba(255, 255, 255, 0.4); font-size: 11px; font-weight: bold; padding: 8px 0 4px 8px;")
        layout.addWidget(section_label)

        # Navigation buttons
        self._synthesis_btn = SidebarButton("Síntese de Voz", "🔊")
        self._synthesis_btn.setChecked(True)
        layout.addWidget(self._synthesis_btn)
        self._buttons.append(self._synthesis_btn)

        # Future pages (disabled for now)
        self._conversion_btn = SidebarButton("Conversão de Voz", "🎭")
        self._conversion_btn.setEnabled(False)
        self._conversion_btn.setToolTip("Em breve")
        layout.addWidget(self._conversion_btn)
        self._buttons.append(self._conversion_btn)

        self._translation_btn = SidebarButton("Tradução", "🌐")
        self._translation_btn.setEnabled(False)
        self._translation_btn.setToolTip("Em breve")
        layout.addWidget(self._translation_btn)
        self._buttons.append(self._translation_btn)

        self._batch_btn = SidebarButton("Processamento em Lote", "📁")
        self._batch_btn.setEnabled(False)
        self._batch_btn.setToolTip("Em breve")
        layout.addWidget(self._batch_btn)
        self._buttons.append(self._batch_btn)

        layout.addStretch()

        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet("background-color: rgba(255,255,255,0.1);")
        layout.addWidget(separator)

        # Bottom section label
        bottom_label = QLabel("CONFIGURAÇÕES")
        bottom_label.setStyleSheet("color: rgba(255, 255, 255, 0.4); font-size: 11px; font-weight: bold; padding: 12px 0 4px 8px;")
        layout.addWidget(bottom_label)

        # Settings button
        self._settings_btn = SidebarButton("Configurações", "⚙️")
        self._settings_btn.setEnabled(False)
        self._settings_btn.setToolTip("Em breve")
        layout.addWidget(self._settings_btn)
        self._buttons.append(self._settings_btn)

        # About button
        self._about_btn = SidebarButton("Sobre", "ℹ️")
        layout.addWidget(self._about_btn)
        self._buttons.append(self._about_btn)

    def get_button(self, index: int) -> Optional[QPushButton]:
        """Get button by index."""
        if 0 <= index < len(self._buttons):
            return self._buttons[index]
        return None

    def set_active(self, button: QPushButton) -> None:
        """Set the active button."""
        for btn in self._buttons:
            btn.setChecked(btn == button)


class MainWindow(QMainWindow):
    """
    Main application window with sidebar navigation.
    """

    def __init__(self):
        super().__init__()

        self._settings = AppSettings.load()
        self._tts_service = get_tts_service()
        self._model_loader: Optional[ModelLoaderWorker] = None
        self._is_model_loaded = False

        self._setup_ui()
        self._connect_signals()
        self._restore_window_state()

        # Start loading the model
        self._load_model()

    def _setup_ui(self) -> None:
        """Setup the main window UI."""
        self.setWindowTitle("XTTS Desktop")
        self.setMinimumSize(1100, 750)

        # Central widget
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Sidebar
        self._sidebar = Sidebar()
        main_layout.addWidget(self._sidebar)

        # Content area
        content_widget = QWidget()
        content_widget.setStyleSheet("""
            QWidget {
                background-color: #16213e;
                color: #ffffff;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid rgba(255,255,255,0.1);
                border-radius: 10px;
                margin-top: 14px;
                padding-top: 12px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 6px;
            }
            QTextEdit, QLineEdit, QSpinBox, QComboBox {
                background-color: rgba(255,255,255,0.05);
                border: 1px solid rgba(255,255,255,0.1);
                border-radius: 6px;
                padding: 10px;
                color: #ffffff;
                selection-background-color: #4a90d9;
            }
            QTextEdit:focus, QLineEdit:focus, QSpinBox:focus, QComboBox:focus {
                border: 1px solid #4a90d9;
            }
            QPushButton {
                background-color: #4a90d9;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 18px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5da0e9;
            }
            QPushButton:pressed {
                background-color: #3a80c9;
            }
            QPushButton:disabled {
                background-color: rgba(255,255,255,0.1);
                color: rgba(255,255,255,0.4);
            }
            QProgressBar {
                border: none;
                border-radius: 6px;
                background-color: rgba(255,255,255,0.1);
                text-align: center;
                color: white;
            }
            QProgressBar::chunk {
                background-color: #4a90d9;
                border-radius: 6px;
            }
            QSlider::groove:horizontal {
                height: 8px;
                background: rgba(255,255,255,0.1);
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                width: 18px;
                height: 18px;
                margin: -5px 0;
                background: #4a90d9;
                border-radius: 9px;
            }
            QSlider::sub-page:horizontal {
                background: #4a90d9;
                border-radius: 4px;
            }
            QComboBox::drop-down {
                border: none;
                padding-right: 8px;
            }
            QComboBox::down-arrow {
                width: 12px;
                height: 12px;
            }
        """)

        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(24, 24, 24, 24)

        # Page stack
        self._page_stack = QStackedWidget()
        content_layout.addWidget(self._page_stack)

        # Add pages
        self._synthesis_page = SynthesisPage(self._tts_service)
        self._page_stack.addWidget(self._synthesis_page)

        # Placeholder pages for future features
        self._placeholder_pages = {}
        placeholder_texts = {
            "conversion": "Conversão de Voz",
            "translation": "Tradução",
            "batch": "Processamento em Lote",
            "settings": "Configurações",
            "about": "Sobre"
        }
        for name, display_name in placeholder_texts.items():
            page = QWidget()
            page_layout = QVBoxLayout(page)
            label = QLabel(f"{display_name}\n\nEm breve...")
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet("font-size: 24px; color: rgba(255,255,255,0.5);")
            page_layout.addWidget(label)
            self._page_stack.addWidget(page)
            self._placeholder_pages[name] = page

        main_layout.addWidget(content_widget, 1)

        # Status bar
        self._status_bar = QStatusBar()
        self._status_bar.setStyleSheet("""
            QStatusBar {
                background-color: #1a1a2e;
                color: rgba(255,255,255,0.7);
                border-top: 1px solid rgba(255,255,255,0.1);
                padding: 4px 12px;
            }
        """)
        self.setStatusBar(self._status_bar)

        # Model status label
        self._model_status = QLabel("Carregando modelo...")
        self._status_bar.addPermanentWidget(self._model_status)

        # Loading progress
        self._loading_progress = QProgressBar()
        self._loading_progress.setFixedWidth(220)
        self._loading_progress.setFixedHeight(20)
        self._loading_progress.setTextVisible(True)
        self._status_bar.addPermanentWidget(self._loading_progress)

    def _connect_signals(self) -> None:
        """Connect signals to slots."""
        # Sidebar navigation
        self._sidebar._synthesis_btn.clicked.connect(
            lambda: self._navigate_to(0)
        )
        self._sidebar._about_btn.clicked.connect(self._show_about)

    def _navigate_to(self, index: int) -> None:
        """Navigate to a page by index."""
        self._page_stack.setCurrentIndex(index)

        # Update sidebar
        btn = self._sidebar.get_button(index)
        if btn:
            self._sidebar.set_active(btn)

    def _load_model(self) -> None:
        """Start loading the TTS model."""
        self._model_loader = ModelLoaderWorker(self._tts_service)
        self._model_loader.progress.connect(self._on_model_loading_progress)
        self._model_loader.finished.connect(self._on_model_loaded)
        self._model_loader.error.connect(self._on_model_load_error)
        self._model_loader.start()

    @Slot(int, str)
    def _on_model_loading_progress(self, percent: int, message: str) -> None:
        """Handle model loading progress."""
        self._loading_progress.setValue(percent)
        self._loading_progress.setFormat(f"{message}")
        self._model_status.setText(message)

    @Slot(bool)
    def _on_model_loaded(self, success: bool) -> None:
        """Handle model loading completion."""
        self._loading_progress.setVisible(False)

        if success:
            self._is_model_loaded = True
            self._model_status.setText("✓ Modelo carregado")
            self._status_bar.showMessage("Modelo carregado com sucesso", 3000)

            # Initialize pages
            self._synthesis_page.initialize()
        else:
            self._model_status.setText("✗ Falha ao carregar modelo")
            QMessageBox.critical(
                self,
                "Erro",
                "Falha ao carregar o modelo TTS.\n"
                "Verifique se os arquivos do modelo estão presentes."
            )

    @Slot(str)
    def _on_model_load_error(self, error: str) -> None:
        """Handle model loading error."""
        self._loading_progress.setVisible(False)
        self._model_status.setText("✗ Erro")
        QMessageBox.critical(self, "Erro", f"Erro ao carregar modelo:\n{error}")

    def _show_about(self) -> None:
        """Show about dialog."""
        QMessageBox.about(
            self,
            "Sobre o XTTS Desktop",
            "<h2>XTTS Desktop</h2>"
            "<p>Aplicativo de Text-to-Speech para desktop</p>"
            "<p>Baseado no XTTS v2 da Coqui TTS</p>"
            "<hr>"
            "<p><b>Versão:</b> 1.0.0</p>"
            "<p><b>Licença:</b> GPL-3.0</p>"
        )

    def _restore_window_state(self) -> None:
        """Restore window geometry from settings."""
        ui = self._settings.ui
        self.resize(ui.window_width, ui.window_height)

        if ui.window_x is not None and ui.window_y is not None:
            self.move(ui.window_x, ui.window_y)

    def _save_window_state(self) -> None:
        """Save window geometry to settings."""
        self._settings.ui.window_width = self.width()
        self._settings.ui.window_height = self.height()
        self._settings.ui.window_x = self.x()
        self._settings.ui.window_y = self.y()
        self._settings.save()

    def closeEvent(self, event: QCloseEvent) -> None:
        """Handle window close event."""
        # Save window state
        self._save_window_state()

        # Cleanup
        self._synthesis_page.cleanup()

        if self._model_loader and self._model_loader.isRunning():
            self._model_loader.cancel()
            self._model_loader.wait()

        event.accept()
