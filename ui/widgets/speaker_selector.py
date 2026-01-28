"""
Speaker selector widget with modern styling.
"""
from typing import List, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QComboBox,
    QPushButton, QLabel, QFrame
)
from PySide6.QtCore import Signal, Slot, Qt
from PySide6.QtGui import QFont


class SpeakerSelectorWidget(QWidget):
    """
    Widget for selecting a speaker/voice with modern styling.
    """

    # Signals
    speaker_changed = Signal(str)  # speaker name
    refresh_requested = Signal()
    add_speaker_requested = Signal()  # request to add new speaker

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        """Setup the UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Header with label
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)

        self._label = QLabel("Voz")
        self._label.setFont(QFont("", 11, QFont.Bold))
        header_layout.addWidget(self._label)
        header_layout.addStretch()

        layout.addLayout(header_layout)

        # Combo box
        self._combo = QComboBox()
        self._combo.setMinimumWidth(200)
        self._combo.setMinimumHeight(40)
        self._combo.setPlaceholderText("Selecione uma voz...")
        self._combo.setStyleSheet("""
            QComboBox {
                padding: 8px 12px;
                font-size: 13px;
            }
            QComboBox::drop-down {
                width: 30px;
            }
        """)
        layout.addWidget(self._combo)

        # Buttons row
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        self._add_btn = QPushButton("+ Cadastrar Voz")
        self._add_btn.setMinimumHeight(36)
        self._add_btn.setCursor(Qt.PointingHandCursor)
        self._add_btn.setToolTip("Adicionar uma nova voz a partir de um arquivo de áudio")
        self._add_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                font-size: 12px;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
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
        btn_layout.addWidget(self._add_btn)

        self._refresh_btn = QPushButton("Atualizar")
        self._refresh_btn.setMinimumHeight(36)
        self._refresh_btn.setCursor(Qt.PointingHandCursor)
        self._refresh_btn.setToolTip("Recarregar lista de vozes")
        self._refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.1);
                color: white;
                font-size: 12px;
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
            QPushButton:disabled {
                color: rgba(255, 255, 255, 0.3);
                border-color: rgba(255, 255, 255, 0.1);
            }
        """)
        btn_layout.addWidget(self._refresh_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def _connect_signals(self) -> None:
        """Connect signals to slots."""
        self._combo.currentTextChanged.connect(self._on_selection_changed)
        self._refresh_btn.clicked.connect(self.refresh_requested.emit)
        self._add_btn.clicked.connect(self.add_speaker_requested.emit)

    @Slot(str)
    def _on_selection_changed(self, text: str) -> None:
        """Handle selection change."""
        if text:
            self.speaker_changed.emit(text)

    def set_speakers(self, speakers: List[str]) -> None:
        """
        Set the list of available speakers.

        Args:
            speakers: List of speaker names
        """
        current = self._combo.currentText()

        self._combo.blockSignals(True)
        self._combo.clear()
        self._combo.addItems(sorted(speakers))

        # Restore selection if possible
        if current and current in speakers:
            self._combo.setCurrentText(current)
        elif speakers:
            self._combo.setCurrentIndex(0)

        self._combo.blockSignals(False)

        # Emit signal for initial selection
        if self._combo.currentText():
            self.speaker_changed.emit(self._combo.currentText())

    def get_selected_speaker(self) -> Optional[str]:
        """Get the currently selected speaker."""
        text = self._combo.currentText()
        return text if text else None

    def set_selected_speaker(self, speaker: str) -> None:
        """Set the selected speaker."""
        index = self._combo.findText(speaker)
        if index >= 0:
            self._combo.setCurrentIndex(index)

    def set_label(self, text: str) -> None:
        """Set the label text."""
        self._label.setText(text)

    def set_enabled(self, enabled: bool) -> None:
        """Enable/disable the widget."""
        self._combo.setEnabled(enabled)
        self._refresh_btn.setEnabled(enabled)
        self._add_btn.setEnabled(enabled)


class LanguageSelectorWidget(QWidget):
    """
    Widget for selecting a language with modern styling.
    """

    # Signals
    language_changed = Signal(str)  # language code

    def __init__(self, parent=None):
        super().__init__(parent)
        self._languages = {}
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        """Setup the UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Label
        self._label = QLabel("Idioma")
        self._label.setFont(QFont("", 11, QFont.Bold))
        layout.addWidget(self._label)

        # Combo
        self._combo = QComboBox()
        self._combo.setMinimumWidth(180)
        self._combo.setMinimumHeight(40)
        self._combo.setStyleSheet("""
            QComboBox {
                padding: 8px 12px;
                font-size: 13px;
            }
            QComboBox::drop-down {
                width: 30px;
            }
        """)
        layout.addWidget(self._combo)

    def _connect_signals(self) -> None:
        """Connect signals to slots."""
        self._combo.currentIndexChanged.connect(self._on_selection_changed)

    @Slot(int)
    def _on_selection_changed(self, index: int) -> None:
        """Handle selection change."""
        code = self._combo.currentData()
        if code:
            self.language_changed.emit(code)

    def set_languages(self, languages: dict) -> None:
        """
        Set the list of available languages.

        Args:
            languages: Dict of {code: name}
        """
        self._languages = languages
        current_code = self._combo.currentData()

        self._combo.blockSignals(True)
        self._combo.clear()

        for code, name in sorted(languages.items(), key=lambda x: x[1]):
            self._combo.addItem(name, code)

        # Restore selection or default to Portuguese
        if current_code and current_code in languages:
            self.set_selected_language(current_code)
        elif "pt" in languages:
            self.set_selected_language("pt")
        elif self._combo.count() > 0:
            self._combo.setCurrentIndex(0)

        self._combo.blockSignals(False)

        # Emit signal for initial selection
        if self._combo.currentData():
            self.language_changed.emit(self._combo.currentData())

    def get_selected_language(self) -> Optional[str]:
        """Get the currently selected language code."""
        return self._combo.currentData()

    def set_selected_language(self, code: str) -> None:
        """Set the selected language by code."""
        for i in range(self._combo.count()):
            if self._combo.itemData(i) == code:
                self._combo.setCurrentIndex(i)
                break

    def set_label(self, text: str) -> None:
        """Set the label text."""
        self._label.setText(text)

    def set_enabled(self, enabled: bool) -> None:
        """Enable/disable the widget."""
        self._combo.setEnabled(enabled)
