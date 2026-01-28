"""
Audio player widget for playback controls.
"""
from pathlib import Path
from typing import Optional
import tempfile
import io

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QPushButton, QSlider, QLabel, QStyle
)
from PySide6.QtCore import Qt, Signal, Slot, QUrl
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput

import numpy as np
import soundfile as sf


class AudioPlayerWidget(QWidget):
    """
    Widget for audio playback with play/pause/stop controls.
    """

    # Signals
    playback_started = Signal()
    playback_paused = Signal()
    playback_stopped = Signal()
    playback_finished = Signal()
    position_changed = Signal(int)  # position in ms

    def __init__(self, parent=None):
        super().__init__(parent)

        self._player = QMediaPlayer()
        self._audio_output = QAudioOutput()
        self._player.setAudioOutput(self._audio_output)

        self._temp_file: Optional[Path] = None
        self._duration_ms: int = 0

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        """Setup the UI components."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Play button
        self._play_btn = QPushButton()
        self._play_btn.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self._play_btn.setToolTip("Play")
        self._play_btn.setFixedSize(32, 32)
        layout.addWidget(self._play_btn)

        # Stop button
        self._stop_btn = QPushButton()
        self._stop_btn.setIcon(self.style().standardIcon(QStyle.SP_MediaStop))
        self._stop_btn.setToolTip("Stop")
        self._stop_btn.setFixedSize(32, 32)
        layout.addWidget(self._stop_btn)

        # Position slider
        self._position_slider = QSlider(Qt.Horizontal)
        self._position_slider.setRange(0, 0)
        layout.addWidget(self._position_slider, 1)

        # Time label
        self._time_label = QLabel("00:00 / 00:00")
        self._time_label.setMinimumWidth(100)
        layout.addWidget(self._time_label)

        # Volume slider
        self._volume_slider = QSlider(Qt.Horizontal)
        self._volume_slider.setRange(0, 100)
        self._volume_slider.setValue(80)
        self._volume_slider.setFixedWidth(80)
        self._volume_slider.setToolTip("Volume")
        layout.addWidget(self._volume_slider)

        # Set initial state
        self._set_playing_state(False)

    def _connect_signals(self) -> None:
        """Connect signals to slots."""
        self._play_btn.clicked.connect(self._on_play_clicked)
        self._stop_btn.clicked.connect(self._on_stop_clicked)
        self._position_slider.sliderMoved.connect(self._on_position_changed)
        self._volume_slider.valueChanged.connect(self._on_volume_changed)

        self._player.positionChanged.connect(self._on_player_position_changed)
        self._player.durationChanged.connect(self._on_duration_changed)
        self._player.playbackStateChanged.connect(self._on_playback_state_changed)

        # Set initial volume
        self._audio_output.setVolume(0.8)

    def _set_playing_state(self, playing: bool) -> None:
        """Update UI for playing/paused state."""
        if playing:
            self._play_btn.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))
            self._play_btn.setToolTip("Pause")
        else:
            self._play_btn.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
            self._play_btn.setToolTip("Play")

    def _format_time(self, ms: int) -> str:
        """Format milliseconds as MM:SS."""
        seconds = ms // 1000
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes:02d}:{seconds:02d}"

    @Slot()
    def _on_play_clicked(self) -> None:
        """Handle play button click."""
        if self._player.playbackState() == QMediaPlayer.PlayingState:
            self._player.pause()
            self.playback_paused.emit()
        else:
            self._player.play()
            self.playback_started.emit()

    @Slot()
    def _on_stop_clicked(self) -> None:
        """Handle stop button click."""
        self._player.stop()
        self.playback_stopped.emit()

    @Slot(int)
    def _on_position_changed(self, position: int) -> None:
        """Handle slider position change."""
        self._player.setPosition(position)

    @Slot(int)
    def _on_volume_changed(self, value: int) -> None:
        """Handle volume slider change."""
        self._audio_output.setVolume(value / 100.0)

    @Slot(int)
    def _on_player_position_changed(self, position: int) -> None:
        """Handle player position update."""
        self._position_slider.setValue(position)
        self._update_time_label(position)
        self.position_changed.emit(position)

    @Slot(int)
    def _on_duration_changed(self, duration: int) -> None:
        """Handle duration change."""
        self._duration_ms = duration
        self._position_slider.setRange(0, duration)
        self._update_time_label(self._player.position())

    @Slot(QMediaPlayer.PlaybackState)
    def _on_playback_state_changed(self, state: QMediaPlayer.PlaybackState) -> None:
        """Handle playback state change."""
        self._set_playing_state(state == QMediaPlayer.PlayingState)

        if state == QMediaPlayer.StoppedState:
            # Check if playback finished naturally
            if self._player.position() >= self._duration_ms - 100:
                self.playback_finished.emit()

    def _update_time_label(self, position: int) -> None:
        """Update the time label."""
        current = self._format_time(position)
        total = self._format_time(self._duration_ms)
        self._time_label.setText(f"{current} / {total}")

    def load_audio(self, audio_data: np.ndarray, sample_rate: int = 24000) -> bool:
        """
        Load audio data for playback.

        Args:
            audio_data: Audio samples as numpy array
            sample_rate: Sample rate in Hz

        Returns:
            True if loaded successfully
        """
        try:
            # Stop any current playback
            self._player.stop()

            # Clean up previous temp file
            if self._temp_file and self._temp_file.exists():
                try:
                    self._temp_file.unlink()
                except OSError:
                    pass

            # Create temp file
            fd, temp_path = tempfile.mkstemp(suffix='.wav')
            self._temp_file = Path(temp_path)

            # Write audio to temp file
            sf.write(str(self._temp_file), audio_data, sample_rate)

            # Load into player
            self._player.setSource(QUrl.fromLocalFile(str(self._temp_file)))

            return True

        except Exception as e:
            print(f"Error loading audio: {e}")
            return False

    def load_file(self, file_path: str) -> bool:
        """
        Load audio from file.

        Args:
            file_path: Path to audio file

        Returns:
            True if loaded successfully
        """
        try:
            self._player.stop()
            self._player.setSource(QUrl.fromLocalFile(file_path))
            return True
        except Exception as e:
            print(f"Error loading file: {e}")
            return False

    def play(self) -> None:
        """Start playback."""
        self._player.play()

    def pause(self) -> None:
        """Pause playback."""
        self._player.pause()

    def stop(self) -> None:
        """Stop playback."""
        self._player.stop()

    def is_playing(self) -> bool:
        """Check if audio is playing."""
        return self._player.playbackState() == QMediaPlayer.PlayingState

    def set_enabled(self, enabled: bool) -> None:
        """Enable/disable the widget."""
        self._play_btn.setEnabled(enabled)
        self._stop_btn.setEnabled(enabled)
        self._position_slider.setEnabled(enabled)

    def cleanup(self) -> None:
        """Clean up resources."""
        self._player.stop()
        if self._temp_file and self._temp_file.exists():
            try:
                self._temp_file.unlink()
            except OSError:
                pass
