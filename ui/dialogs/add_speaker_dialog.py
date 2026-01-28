"""
Dialog for adding a new speaker/voice with modern styling.
"""
from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QFileDialog, QProgressBar,
    QGroupBox, QMessageBox, QFrame
)
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QFont

from src.core.services.tts_service import TTSService
from ui.workers.add_speaker_worker import AddSpeakerWorker


class AddSpeakerDialog(QDialog):
    """
    Dialog for adding a new speaker/voice to the system.
    Provides file selection, naming, and progress feedback.
    """

    # Signal emitted when a speaker is added successfully
    speaker_added = Signal(str)  # speaker_name

    def __init__(self, tts_service: TTSService, parent=None):
        super().__init__(parent)
        self._tts_service = tts_service
        self._worker: Optional[AddSpeakerWorker] = None
        self._selected_file: str = ""

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        """Setup the dialog UI."""
        self.setWindowTitle("Cadastrar Nova Voz")
        self.setMinimumWidth(550)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(24, 24, 24, 24)

        # Header
        header = QLabel("Cadastrar Nova Voz")
        header.setFont(QFont("", 18, QFont.Bold))
        layout.addWidget(header)

        description = QLabel(
            "Selecione um arquivo de áudio WAV (recomendado 10-30 segundos) "
            "com fala clara para criar uma nova voz."
        )
        description.setWordWrap(True)
        description.setStyleSheet("color: rgba(255, 255, 255, 0.7); font-size: 13px; line-height: 1.4;")
        layout.addWidget(description)

        # File selection group
        file_group = QGroupBox("Arquivo de Áudio")
        file_group.setFont(QFont("", 11, QFont.Bold))
        file_layout = QHBoxLayout(file_group)
        file_layout.setSpacing(12)

        self._file_path_edit = QLineEdit()
        self._file_path_edit.setPlaceholderText("Selecione um arquivo WAV...")
        self._file_path_edit.setReadOnly(True)
        self._file_path_edit.setMinimumHeight(40)
        file_layout.addWidget(self._file_path_edit, 1)

        self._browse_btn = QPushButton("Procurar...")
        self._browse_btn.setMinimumWidth(120)
        self._browse_btn.setMinimumHeight(40)
        self._browse_btn.setCursor(Qt.PointingHandCursor)
        self._browse_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.1);
                color: white;
                font-size: 13px;
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 6px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.15);
                border-color: rgba(255, 255, 255, 0.3);
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 0.2);
            }
        """)
        file_layout.addWidget(self._browse_btn)

        layout.addWidget(file_group)

        # Name group
        name_group = QGroupBox("Nome da Voz")
        name_group.setFont(QFont("", 11, QFont.Bold))
        name_layout = QVBoxLayout(name_group)
        name_layout.setSpacing(8)

        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("Digite um nome para esta voz...")
        self._name_edit.setMaxLength(50)
        self._name_edit.setMinimumHeight(40)
        name_layout.addWidget(self._name_edit)

        name_hint = QLabel("Use apenas letras, números, espaços, underlines e hífens.")
        name_hint.setStyleSheet("color: rgba(255, 255, 255, 0.5); font-size: 11px;")
        name_layout.addWidget(name_hint)

        layout.addWidget(name_group)

        # Progress section (initially hidden)
        self._progress_group = QGroupBox("Progresso")
        self._progress_group.setFont(QFont("", 11, QFont.Bold))
        progress_layout = QVBoxLayout(self._progress_group)
        progress_layout.setSpacing(12)

        self._progress_bar = QProgressBar()
        self._progress_bar.setTextVisible(True)
        self._progress_bar.setFormat("%p%")
        self._progress_bar.setMinimumHeight(32)
        progress_layout.addWidget(self._progress_bar)

        self._status_label = QLabel("Pronto")
        self._status_label.setStyleSheet("color: rgba(255, 255, 255, 0.7); font-size: 12px;")
        progress_layout.addWidget(self._status_label)

        self._progress_group.setVisible(False)
        layout.addWidget(self._progress_group)

        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet("background-color: rgba(255, 255, 255, 0.1);")
        layout.addWidget(separator)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)
        button_layout.addStretch()

        self._cancel_btn = QPushButton("Cancelar")
        self._cancel_btn.setMinimumWidth(120)
        self._cancel_btn.setMinimumHeight(42)
        self._cancel_btn.setCursor(Qt.PointingHandCursor)
        self._cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.1);
                color: white;
                font-size: 13px;
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 8px;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.15);
                border-color: rgba(255, 255, 255, 0.3);
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 0.2);
            }
        """)
        button_layout.addWidget(self._cancel_btn)

        self._add_btn = QPushButton("Cadastrar Voz")
        self._add_btn.setMinimumWidth(140)
        self._add_btn.setMinimumHeight(42)
        self._add_btn.setEnabled(False)
        self._add_btn.setCursor(Qt.PointingHandCursor)
        self._add_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                font-size: 14px;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #5CBF60;
            }
            QPushButton:pressed {
                background-color: #3C9F40;
            }
            QPushButton:disabled {
                background-color: rgba(76, 175, 80, 0.3);
                color: rgba(255, 255, 255, 0.5);
            }
        """)
        button_layout.addWidget(self._add_btn)

        layout.addLayout(button_layout)

    def _connect_signals(self) -> None:
        """Connect UI signals."""
        self._browse_btn.clicked.connect(self._on_browse)
        self._name_edit.textChanged.connect(self._validate_inputs)
        self._cancel_btn.clicked.connect(self._on_cancel)
        self._add_btn.clicked.connect(self._on_add)

    def _validate_inputs(self) -> None:
        """Validate inputs and enable/disable the Add button."""
        has_file = bool(self._selected_file and Path(self._selected_file).exists())
        has_name = bool(self._name_edit.text().strip())
        self._add_btn.setEnabled(has_file and has_name)

    @Slot()
    def _on_browse(self) -> None:
        """Handle browse button click."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Selecionar Arquivo de Áudio",
            "",
            "Arquivos WAV (*.wav);;Todos os Arquivos (*)"
        )

        if file_path:
            self._selected_file = file_path
            self._file_path_edit.setText(file_path)

            # Auto-fill name from filename if empty
            if not self._name_edit.text().strip():
                name = Path(file_path).stem
                # Clean up the name
                name = name.replace("_", " ").replace("-", " ").title()
                self._name_edit.setText(name)

            self._validate_inputs()

    @Slot()
    def _on_cancel(self) -> None:
        """Handle cancel button click."""
        if self._worker and self._worker.isRunning():
            self._worker.cancel()
            self._worker.wait()
        self.reject()

    @Slot()
    def _on_add(self) -> None:
        """Handle add button click."""
        name = self._name_edit.text().strip()
        file_path = self._selected_file

        if not name or not file_path:
            return

        # Check if speaker already exists
        existing_speakers = self._tts_service.list_speakers()
        if name.lower() in [s.lower() for s in existing_speakers]:
            result = QMessageBox.question(
                self,
                "Voz Existente",
                f"Uma voz chamada '{name}' já existe. Deseja substituí-la?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if result != QMessageBox.Yes:
                return

        # Show progress
        self._set_processing_state(True)

        # Start worker
        self._worker = AddSpeakerWorker(self._tts_service)
        self._worker.set_speaker_data(name, file_path)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.start()

    def _set_processing_state(self, processing: bool) -> None:
        """Update UI for processing/idle state."""
        self._progress_group.setVisible(processing)
        self._browse_btn.setEnabled(not processing)
        self._name_edit.setEnabled(not processing)
        self._add_btn.setEnabled(not processing)
        self._cancel_btn.setText("Cancelar" if processing else "Fechar")

        if processing:
            self._progress_bar.setValue(0)
            self._status_label.setText("Iniciando...")
            self._status_label.setStyleSheet("color: rgba(255, 255, 255, 0.7); font-size: 12px;")

    @Slot(int, str)
    def _on_progress(self, percent: int, message: str) -> None:
        """Handle progress updates."""
        self._progress_bar.setValue(percent)
        self._status_label.setText(message)

    @Slot(bool, str)
    def _on_finished(self, success: bool, result: str) -> None:
        """Handle worker completion."""
        self._set_processing_state(False)

        if success:
            self._progress_bar.setValue(100)
            self._status_label.setText(f"Voz '{result}' cadastrada com sucesso!")
            self._status_label.setStyleSheet("color: #4CAF50; font-size: 12px;")

            # Emit signal and close
            self.speaker_added.emit(result)

            QMessageBox.information(
                self,
                "Sucesso",
                f"A voz '{result}' foi cadastrada com sucesso!\n\n"
                "Você já pode usar esta voz para síntese."
            )
            self.accept()
        else:
            self._progress_bar.setValue(0)
            self._status_label.setText(f"Erro: {result}")
            self._status_label.setStyleSheet("color: #f44336; font-size: 12px;")

            QMessageBox.critical(
                self,
                "Erro",
                f"Falha ao cadastrar voz:\n{result}"
            )

    def closeEvent(self, event) -> None:
        """Handle dialog close."""
        if self._worker and self._worker.isRunning():
            self._worker.cancel()
            self._worker.wait()
        event.accept()
