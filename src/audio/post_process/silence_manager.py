import io
from dataclasses import dataclass
from typing import Tuple, List

import torch
import numpy as np
import librosa
import torchaudio#type: ignore
import soundfile as sf#type: ignore
from pydub import AudioSegment#type: ignore
from pydub.silence import detect_nonsilent#type: ignore

@dataclass
class AudioConfig:
    sample_rate: int = 24000
    edge_padding: int = 150
    scale_factor: float = 0.95
    silence_max_len: int = 30
    db_threshold: int = 55
    min_silence_len: int = 100
    silence_thresh: int = -50
    top_db: int = 60

class AudioPadding:
    @staticmethod
    def create_padding(config: AudioConfig) -> np.ndarray:
        pad_samples = int(config.edge_padding * config.sample_rate / 1000 * config.scale_factor)
        return np.zeros(pad_samples)

class SilenceDetector:
    @staticmethod
    def detect_voice_sections(audio: AudioSegment, config: AudioConfig) -> List[Tuple[int, int]]:
        return detect_nonsilent(
            audio,
            min_silence_len=config.min_silence_len,
            silence_thresh=config.silence_thresh
        )

class AudioProcessor:
    def __init__(self, config: AudioConfig = AudioConfig()):
        self.config = config

    def _process_internal_silences(self, audio_input: np.ndarray) -> np.ndarray:
        silence_samples = int((self.config.silence_max_len / 1000) * self.config.sample_rate)
        voice_segments = librosa.effects.split(audio_input, top_db=self.config.db_threshold)
        
        return self._combine_segments(audio_input, voice_segments, silence_samples)

    def _combine_segments(self, audio_input: np.ndarray, voice_segments: np.ndarray, silence_samples: int) -> np.ndarray:
        processed = []
        for idx, (curr_start, curr_end) in enumerate(voice_segments):
            processed.append(audio_input[curr_start:curr_end])
            
            if idx < len(voice_segments) - 1:
                gap_size = min(voice_segments[idx + 1][0] - curr_end, silence_samples)
                gap = np.zeros(gap_size, dtype=audio_input.dtype)
                processed.append(gap)
                
        return np.concatenate(processed)

    def _convert_to_audio_segment(self, audio_data: np.ndarray) -> AudioSegment:
        io_buffer = io.BytesIO()
        audio_as_tensor = torch.tensor(audio_data).unsqueeze(0)
        torchaudio.save(io_buffer, audio_as_tensor, self.config.sample_rate, format="wav")
        return AudioSegment.from_wav(io_buffer)

    def _add_silence_padding(self, audio: AudioSegment) -> AudioSegment:
        silence = AudioSegment.silent(duration=self.config.edge_padding)
        return silence + audio + silence

    def _process_voice_sections(self, audio: AudioSegment) -> AudioSegment:
        voice_sections = SilenceDetector.detect_voice_sections(audio, self.config)
        if voice_sections:
            begin, end = voice_sections[0][0], voice_sections[-1][1]
            return audio[begin:end]
        return audio

    def _export_to_bytes(self, audio: AudioSegment) -> bytes:
        output_buffer = io.BytesIO()
        audio.export(output_buffer, format="wav")
        output_buffer.seek(0)
        return output_buffer.read()

    def process_audio_with_silence(self, audio_data: np.ndarray) -> bytes:
        cleaned_audio = self._process_internal_silences(audio_data)
        trimmed_audio = librosa.effects.trim(cleaned_audio, top_db=self.config.top_db)[0]
        
        padding = AudioPadding.create_padding(self.config)
        final_audio = np.concatenate((padding, trimmed_audio, padding))
        
        audio = self._convert_to_audio_segment(final_audio)
        audio = self._process_voice_sections(audio)
        audio = self._add_silence_padding(audio)
        
        return self._export_to_bytes(audio)
