"""
Synthesis page - Main TTS synthesis interface with modern styling.
"""
from pathlib import Path
from typing import Optional
import io

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
    QPushButton, QLabel, QGroupBox, QProgressBar,
    QFileDialog, QSlider, QSpinBox, QMessageBox,
    QSplitter, QFrame
)
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QFont

import numpy as np
import soundfile as sf

from src.core.services.tts_service import TTSService
from src.core.models.tts_request import (
    SynthesisRequest, SynthesisResult, SynthesisStatus, SUPPORTED_LANGUAGES
)
from ui.widgets.audio_player import AudioPlayerWidget
from ui.widgets.speaker_selector import SpeakerSelectorWidget, LanguageSelectorWidget
from ui.workers.synthesis_worker import SynthesisWorker
from ui.dialogs.add_speaker_dialog import AddSpeakerDialog


class SynthesisPage(QWidget):
    """
    Main TTS synthesis page.
    Allows users to input text and generate speech.
    """

    # Signals
    synthesis_started = Signal()
    synthesis_finished = Signal(bool)  # success

    def __init__(self, tts_service: TTSService, parent=None):
        super().__init__(parent)

        self._tts_service = tts_service
        self._synthesis_worker: Optional[SynthesisWorker] = None
        self._current_audio: Optional[np.ndarray] = None
        self._current_sample_rate: int = 24000

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        """Setup the UI components."""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # Create splitter for text input and controls
        splitter = QSplitter(Qt.Vertical)

        # === Text Input Section ===
        input_widget = QWidget()
        input_layout = QVBoxLayout(input_widget)
        input_layout.setContentsMargins(0, 0, 0, 0)

        input_group = QGroupBox("Texto para Conversão")
        input_group.setFont(QFont("", 11, QFont.Bold))
        input_group_layout = QVBoxLayout(input_group)

        self._text_edit = QTextEdit()
        self._text_edit.setPlaceholderText(
            "Digite o texto que você deseja converter em fala...\n\n"
            "Dica: Use pontuação para pausas naturais."
        )
        self._text_edit.setMinimumHeight(150)
        self._text_edit.setStyleSheet("""
            QTextEdit {
                font-size: 14px;
                line-height: 1.5;
            }
        """)
        input_group_layout.addWidget(self._text_edit)

        # Character count
        char_layout = QHBoxLayout()
        self._char_count_label = QLabel("0 caracteres")
        self._char_count_label.setStyleSheet("color: rgba(255, 255, 255, 0.5); font-size: 11px;")
        char_layout.addStretch()
        char_layout.addWidget(self._char_count_label)
        input_group_layout.addLayout(char_layout)

        input_layout.addWidget(input_group)
        splitter.addWidget(input_widget)

        # === Controls Section ===
        controls_widget = QWidget()
        controls_layout = QVBoxLayout(controls_widget)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(16)

        # Voice settings row
        voice_group = QGroupBox("Configurações de Voz")
        voice_group.setFont(QFont("", 11, QFont.Bold))
        voice_layout = QHBoxLayout(voice_group)
        voice_layout.setSpacing(24)

        # Speaker selector
        self._speaker_selector = SpeakerSelectorWidget()
        voice_layout.addWidget(self._speaker_selector)

        # Language selector
        self._language_selector = LanguageSelectorWidget()
        voice_layout.addWidget(self._language_selector)

        # Speed control
        speed_widget = QWidget()
        speed_layout = QVBoxLayout(speed_widget)
        speed_layout.setContentsMargins(0, 0, 0, 0)
        speed_layout.setSpacing(8)

        speed_label = QLabel("Velocidade")
        speed_label.setFont(QFont("", 11, QFont.Bold))
        speed_layout.addWidget(speed_label)

        speed_row = QHBoxLayout()
        speed_row.setSpacing(12)

        self._speed_slider = QSlider(Qt.Horizontal)
        self._speed_slider.setRange(50, 150)  # 0.5x to 1.5x
        self._speed_slider.setValue(100)
        self._speed_slider.setTickPosition(QSlider.TicksBelow)
        self._speed_slider.setTickInterval(25)
        self._speed_slider.setMinimumWidth(150)
        speed_row.addWidget(self._speed_slider)

        self._speed_label = QLabel("1.0x")
        self._speed_label.setMinimumWidth(45)
        self._speed_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        speed_row.addWidget(self._speed_label)
        speed_layout.addLayout(speed_row)

        voice_layout.addWidget(speed_widget)
        voice_layout.addStretch()

        controls_layout.addWidget(voice_group)

        # Advanced settings (collapsible)
        self._advanced_group = QGroupBox("Configurações Avançadas")
        self._advanced_group.setFont(QFont("", 11, QFont.Bold))
        self._advanced_group.setCheckable(True)
        self._advanced_group.setChecked(False)
        advanced_layout = QHBoxLayout(self._advanced_group)
        advanced_layout.setSpacing(20)

        # Temperature
        temp_widget = QWidget()
        temp_layout = QVBoxLayout(temp_widget)
        temp_layout.setContentsMargins(0, 0, 0, 0)
        temp_layout.setSpacing(4)
        temp_layout.addWidget(QLabel("Temperatura:"))
        self._temperature_spin = QSpinBox()
        self._temperature_spin.setRange(0, 100)
        self._temperature_spin.setValue(65)
        self._temperature_spin.setSuffix("%")
        self._temperature_spin.setMinimumHeight(32)
        self._temperature_spin.setToolTip("Controla a aleatoriedade da geração.\nValores mais altos = mais variação.")
        temp_layout.addWidget(self._temperature_spin)
        advanced_layout.addWidget(temp_widget)

        # Top-K
        topk_widget = QWidget()
        topk_layout = QVBoxLayout(topk_widget)
        topk_layout.setContentsMargins(0, 0, 0, 0)
        topk_layout.setSpacing(4)
        topk_layout.addWidget(QLabel("Top-K:"))
        self._top_k_spin = QSpinBox()
        self._top_k_spin.setRange(1, 100)
        self._top_k_spin.setValue(35)
        self._top_k_spin.setMinimumHeight(32)
        self._top_k_spin.setToolTip("Número de tokens mais prováveis a considerar.")
        topk_layout.addWidget(self._top_k_spin)
        advanced_layout.addWidget(topk_widget)

        # Top-P
        topp_widget = QWidget()
        topp_layout = QVBoxLayout(topp_widget)
        topp_layout.setContentsMargins(0, 0, 0, 0)
        topp_layout.setSpacing(4)
        topp_layout.addWidget(QLabel("Top-P:"))
        self._top_p_spin = QSpinBox()
        self._top_p_spin.setRange(0, 100)
        self._top_p_spin.setValue(75)
        self._top_p_spin.setSuffix("%")
        self._top_p_spin.setMinimumHeight(32)
        self._top_p_spin.setToolTip("Probabilidade cumulativa para amostragem de núcleo.")
        topp_layout.addWidget(self._top_p_spin)
        advanced_layout.addWidget(topp_widget)

        # Repetition penalty
        rep_widget = QWidget()
        rep_layout = QVBoxLayout(rep_widget)
        rep_layout.setContentsMargins(0, 0, 0, 0)
        rep_layout.setSpacing(4)
        rep_layout.addWidget(QLabel("Penalidade de Repetição:"))
        self._rep_penalty_spin = QSpinBox()
        self._rep_penalty_spin.setRange(1, 20)
        self._rep_penalty_spin.setValue(12)
        self._rep_penalty_spin.setMinimumHeight(32)
        self._rep_penalty_spin.setToolTip("Penaliza tokens repetidos.\nValores mais altos = menos repetição.")
        rep_layout.addWidget(self._rep_penalty_spin)
        advanced_layout.addWidget(rep_widget)

        advanced_layout.addStretch()
        controls_layout.addWidget(self._advanced_group)

        # Progress and action buttons
        action_layout = QHBoxLayout()
        action_layout.setSpacing(12)

        self._progress_bar = QProgressBar()
        self._progress_bar.setVisible(False)
        self._progress_bar.setTextVisible(True)
        self._progress_bar.setMinimumHeight(36)
        action_layout.addWidget(self._progress_bar, 1)

        self._synthesize_btn = QPushButton("Gerar Áudio")
        self._synthesize_btn.setMinimumWidth(140)
        self._synthesize_btn.setMinimumHeight(42)
        self._synthesize_btn.setCursor(Qt.PointingHandCursor)
        self._synthesize_btn.setStyleSheet("""
            QPushButton {
                background-color: #4a90d9;
                color: white;
                font-weight: bold;
                font-size: 14px;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #5da0e9;
            }
            QPushButton:pressed {
                background-color: #3a80c9;
            }
            QPushButton:disabled {
                background-color: rgba(74, 144, 217, 0.3);
                color: rgba(255, 255, 255, 0.5);
            }
        """)
        action_layout.addWidget(self._synthesize_btn)

        self._cancel_btn = QPushButton("Cancelar")
        self._cancel_btn.setEnabled(False)
        self._cancel_btn.setMinimumHeight(42)
        self._cancel_btn.setCursor(Qt.PointingHandCursor)
        self._cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.1);
                color: white;
                font-size: 13px;
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 8px;
                padding: 10px 16px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.15);
                border-color: rgba(255, 255, 255, 0.3);
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 0.2);
            }
            QPushButton:disabled {
                color: rgba(255, 255, 255, 0.3);
                border-color: rgba(255, 255, 255, 0.1);
            }
        """)
        action_layout.addWidget(self._cancel_btn)

        controls_layout.addLayout(action_layout)

        # Audio player section
        player_group = QGroupBox("Reprodutor de Áudio")
        player_group.setFont(QFont("", 11, QFont.Bold))
        player_layout = QVBoxLayout(player_group)

        self._audio_player = AudioPlayerWidget()
        self._audio_player.set_enabled(False)
        player_layout.addWidget(self._audio_player)

        # Export buttons
        export_layout = QHBoxLayout()
        export_layout.addStretch()

        self._save_btn = QPushButton("Salvar Áudio")
        self._save_btn.setEnabled(False)
        self._save_btn.setMinimumHeight(36)
        self._save_btn.setCursor(Qt.PointingHandCursor)
        self._save_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                font-size: 12px;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
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
        export_layout.addWidget(self._save_btn)

        player_layout.addLayout(export_layout)
        controls_layout.addWidget(player_group)

        splitter.addWidget(controls_widget)

        # Set splitter sizes
        splitter.setSizes([200, 400])

        layout.addWidget(splitter)

    def _connect_signals(self) -> None:
        """Connect signals to slots."""
        self._text_edit.textChanged.connect(self._on_text_changed)
        self._speed_slider.valueChanged.connect(self._on_speed_changed)
        self._synthesize_btn.clicked.connect(self._on_synthesize)
        self._cancel_btn.clicked.connect(self._on_cancel)
        self._save_btn.clicked.connect(self._on_save)
        self._speaker_selector.refresh_requested.connect(self._refresh_speakers)
        self._speaker_selector.add_speaker_requested.connect(self._on_add_speaker)

    def initialize(self) -> None:
        """Initialize the page with data from the service."""
        # Load speakers
        self._refresh_speakers()

        # Load languages
        self._language_selector.set_languages(SUPPORTED_LANGUAGES)

    def _refresh_speakers(self) -> None:
        """Refresh the speaker list."""
        speakers = self._tts_service.list_speakers()
        self._speaker_selector.set_speakers(speakers)

    @Slot()
    def _on_add_speaker(self) -> None:
        """Handle add speaker button click."""
        dialog = AddSpeakerDialog(self._tts_service, self)
        dialog.speaker_added.connect(self._on_speaker_added)
        dialog.exec()

    @Slot(str)
    def _on_speaker_added(self, speaker_name: str) -> None:
        """Handle speaker added event."""
        # Refresh the speaker list
        self._refresh_speakers()
        # Select the newly added speaker
        self._speaker_selector.set_selected_speaker(speaker_name)

    @Slot()
    def _on_text_changed(self) -> None:
        """Handle text input change."""
        text = self._text_edit.toPlainText()
        self._char_count_label.setText(f"{len(text)} caracteres")

    @Slot(int)
    def _on_speed_changed(self, value: int) -> None:
        """Handle speed slider change."""
        speed = value / 100.0
        self._speed_label.setText(f"{speed:.1f}x")

    @Slot()
    def _on_synthesize(self) -> None:
        """Start synthesis."""
        text = self._text_edit.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "Aviso", "Por favor, insira um texto para converter.")
            return

        speaker = self._speaker_selector.get_selected_speaker()
        if not speaker:
            QMessageBox.warning(self, "Aviso", "Por favor, selecione uma voz.")
            return

        language = self._language_selector.get_selected_language()
        if not language:
            language = "en"

        # Create request
        request = SynthesisRequest(
            text=text,
            voice=speaker,
            language=language,
            speed=self._speed_slider.value() / 100.0,
            temperature=self._temperature_spin.value() / 100.0,
            top_k=self._top_k_spin.value(),
            top_p=self._top_p_spin.value() / 100.0,
            repetition_penalty=float(self._rep_penalty_spin.value())
        )

        # Update UI state
        self._set_synthesizing_state(True)

        # Create and start worker
        self._synthesis_worker = SynthesisWorker(self._tts_service)
        self._synthesis_worker.set_request(request)
        self._synthesis_worker.started_signal.connect(self._on_synthesis_started)
        self._synthesis_worker.progress.connect(self._on_synthesis_progress)
        self._synthesis_worker.finished.connect(self._on_synthesis_finished)
        self._synthesis_worker.error.connect(self._on_synthesis_error)
        self._synthesis_worker.start()

    @Slot()
    def _on_cancel(self) -> None:
        """Cancel ongoing synthesis."""
        if self._synthesis_worker and self._synthesis_worker.isRunning():
            self._synthesis_worker.cancel()
            self._progress_bar.setFormat("Cancelando...")

    @Slot()
    def _on_save(self) -> None:
        """Save the generated audio."""
        if self._current_audio is None:
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Salvar Áudio",
            "audio_gerado.wav",
            "Arquivos WAV (*.wav);;Arquivos MP3 (*.mp3);;Todos os Arquivos (*)"
        )

        if file_path:
            try:
                sf.write(file_path, self._current_audio, self._current_sample_rate)
                QMessageBox.information(
                    self, "Sucesso", f"Áudio salvo em:\n{file_path}"
                )
            except Exception as e:
                QMessageBox.critical(
                    self, "Erro", f"Falha ao salvar áudio:\n{e}"
                )

    @Slot()
    def _on_synthesis_started(self) -> None:
        """Handle synthesis start."""
        self.synthesis_started.emit()

    @Slot(int, str)
    def _on_synthesis_progress(self, percent: int, message: str) -> None:
        """Handle synthesis progress update."""
        self._progress_bar.setValue(percent)
        self._progress_bar.setFormat(f"{message} ({percent}%)")

    @Slot(object)
    def _on_synthesis_finished(self, result: SynthesisResult) -> None:
        """Handle synthesis completion."""
        self._set_synthesizing_state(False)

        if result.status == SynthesisStatus.COMPLETED and result.is_success:
            # Store audio data
            self._current_audio = result.audio_data
            self._current_sample_rate = result.sample_rate

            # Load into player
            self._audio_player.load_audio(result.audio_data, result.sample_rate)
            self._audio_player.set_enabled(True)
            self._audio_player.play()

            self._save_btn.setEnabled(True)
            self.synthesis_finished.emit(True)

        elif result.status == SynthesisStatus.CANCELLED:
            self._progress_bar.setFormat("Cancelado")
            self.synthesis_finished.emit(False)

        else:
            error_msg = result.error_message or "Erro desconhecido"
            QMessageBox.critical(self, "Erro", f"Falha na síntese:\n{error_msg}")
            self.synthesis_finished.emit(False)

    @Slot(str)
    def _on_synthesis_error(self, error: str) -> None:
        """Handle synthesis error."""
        self._set_synthesizing_state(False)
        QMessageBox.critical(self, "Erro", f"Erro na síntese:\n{error}")
        self.synthesis_finished.emit(False)

    def _set_synthesizing_state(self, synthesizing: bool) -> None:
        """Update UI for synthesizing/idle state."""
        self._text_edit.setEnabled(not synthesizing)
        self._speaker_selector.set_enabled(not synthesizing)
        self._language_selector.set_enabled(not synthesizing)
        self._speed_slider.setEnabled(not synthesizing)
        self._advanced_group.setEnabled(not synthesizing)
        self._synthesize_btn.setEnabled(not synthesizing)
        self._cancel_btn.setEnabled(synthesizing)
        self._progress_bar.setVisible(synthesizing)

        if synthesizing:
            self._progress_bar.setValue(0)
            self._progress_bar.setFormat("Iniciando...")

    def cleanup(self) -> None:
        """Clean up resources."""
        if self._synthesis_worker and self._synthesis_worker.isRunning():
            self._synthesis_worker.cancel()
            self._synthesis_worker.wait()

        self._audio_player.cleanup()
