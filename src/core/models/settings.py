"""
Application settings models.
"""
from dataclasses import dataclass, field
from typing import Optional, List
from pathlib import Path
import json
import os


@dataclass
class AudioSettings:
    """Audio processing settings."""
    sample_rate: int = 24000
    default_format: str = "wav"
    silence_padding_ms: int = 150
    audio_factor: float = 0.6


@dataclass
class ModelSettings:
    """TTS model settings."""
    model_version: str = "v2.0.3"
    model_dir: str = "models"
    speakers_dir: str = "speakers"
    use_gpu: bool = True
    low_vram_mode: bool = False


@dataclass
class UISettings:
    """UI settings."""
    theme: str = "dark"
    language: str = "pt_BR"
    window_width: int = 1200
    window_height: int = 800
    window_x: Optional[int] = None
    window_y: Optional[int] = None
    sidebar_width: int = 200
    recent_files: List[str] = field(default_factory=list)
    max_recent_files: int = 10


@dataclass
class AppSettings:
    """Application settings container."""
    audio: AudioSettings = field(default_factory=AudioSettings)
    model: ModelSettings = field(default_factory=ModelSettings)
    ui: UISettings = field(default_factory=UISettings)

    @classmethod
    def get_config_path(cls) -> Path:
        """Get platform-appropriate config path."""
        if os.name == 'nt':  # Windows
            base = Path(os.environ.get('LOCALAPPDATA', Path.home()))
            return base / "XTTSDesktop" / "config.json"
        else:  # Linux/macOS
            base = Path.home() / ".config"
            return base / "xtts-desktop" / "config.json"

    @classmethod
    def load(cls, config_path: Optional[Path] = None) -> "AppSettings":
        """Load settings from file."""
        if config_path is None:
            config_path = cls.get_config_path()

        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                settings = cls()
                if 'audio' in data:
                    settings.audio = AudioSettings(**data['audio'])
                if 'model' in data:
                    settings.model = ModelSettings(**data['model'])
                if 'ui' in data:
                    settings.ui = UISettings(**data['ui'])
                return settings
            except (json.JSONDecodeError, TypeError, KeyError):
                pass

        return cls()

    def save(self, config_path: Optional[Path] = None) -> None:
        """Save settings to file."""
        if config_path is None:
            config_path = self.get_config_path()

        config_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            'audio': {
                'sample_rate': self.audio.sample_rate,
                'default_format': self.audio.default_format,
                'silence_padding_ms': self.audio.silence_padding_ms,
                'audio_factor': self.audio.audio_factor,
            },
            'model': {
                'model_version': self.model.model_version,
                'model_dir': self.model.model_dir,
                'speakers_dir': self.model.speakers_dir,
                'use_gpu': self.model.use_gpu,
                'low_vram_mode': self.model.low_vram_mode,
            },
            'ui': {
                'theme': self.ui.theme,
                'language': self.ui.language,
                'window_width': self.ui.window_width,
                'window_height': self.ui.window_height,
                'window_x': self.ui.window_x,
                'window_y': self.ui.window_y,
                'sidebar_width': self.ui.sidebar_width,
                'recent_files': self.ui.recent_files[:self.ui.max_recent_files],
                'max_recent_files': self.ui.max_recent_files,
            }
        }

        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
