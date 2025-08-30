from typing import Any, List
from pydub.silence import detect_nonsilent  # type: ignore
from src.core.application import Application
from pydub import AudioSegment  # type: ignore
import numpy as np
import librosa  # type: ignore
import torchaudio  # type: ignore
import torch  # type: ignore
import io



from dataclasses import dataclass
from typing import Any, List
import numpy as np

@dataclass
class GenerateOutputAudioDto:
    audio: np.ndarray
    max_silence_samples: int
    non_silent_intervals: list
    output_audio: list
    i: int
    end: int

@dataclass
class GetAudioBatchDto:
    audio: np.ndarray
    max_silence_samples: int
    non_silent_intervals: list
    output_audio: list
    i: int
    start: int
    end: int

app = Application()


class AudioProcessor():
    """Backward-compatible refactor of the original AudioProcessor.

    Public method signatures are preserved. Internals were cleaned up,
    edge-cases handled, and logs improved.
    """

    def apply_silences(self, output: Any, start_end_silence: int) -> bytes:
        """Add leading/trailing silence to an audio buffer.

        Accepts torch.Tensor, numpy.ndarray or raw WAV bytes (as previously supported).
        Returns WAV bytes with desired padding.
        """
        if output is None:
            app.logger.error(
                "Cannot apply silences to None audio object. Synthesis likely failed."
            )
            raise ValueError("Input audio to apply_silences cannot be None.")

        app.logger.info("Applying audio silence: %s ms", start_end_silence)

        audio_np = self._to_numpy_audio(output, sample_rate=24000)

        if audio_np is None or len(audio_np) == 0:
            app.logger.error("Converted audio is empty after loading")
            raise ValueError("Audio data is empty or None")

        # Remove long internal silences first
        audio_processed = self.remove_excessive_silence(audio_np)

        # Trim extremes and then add requested silences
        audio_trim = librosa.effects.trim(audio_processed, top_db=60)[0]

        padding = 0.95
        silence_duration_samples = int(start_end_silence * 24000 / 1000 * padding)
        silence = np.zeros(silence_duration_samples, dtype=audio_trim.dtype)

        audio = np.concatenate((silence, audio_trim, silence), axis=None)

        # Save to WAV in-memory
        buffer = io.BytesIO()
        audio_tensor = torch.tensor(audio).unsqueeze(0)
        torchaudio.save(buffer, audio_tensor, 24000, format="wav")

        # Ensure buffer is rewound before reading with pydub
        buffer.seek(0)
        audio_segment = AudioSegment.from_wav(buffer)

        # Remove leading/trailing noise around actual non-silent regions
        non_silent_ranges = detect_nonsilent(
            audio_segment, min_silence_len=100, silence_thresh=-50
        )

        if non_silent_ranges:
            start_trim = non_silent_ranges[0][0]
            end_trim = non_silent_ranges[-1][1]
            audio_segment = audio_segment[start_trim:end_trim]

        # Add exact silence requested at beginning and end (ms)
        silence_segment = AudioSegment.silent(duration=start_end_silence)
        padded_audio = silence_segment + audio_segment + silence_segment

        out_buffer = io.BytesIO()
        padded_audio.export(out_buffer, format="wav")
        out_buffer.seek(0)
        return out_buffer.read()

    def _to_numpy_audio(self, output: Any, sample_rate: int = 24000) -> np.ndarray:
        """Normalize different audio input types to a 1D numpy array.

        Supports: torch.Tensor, bytes (wav), numpy.ndarray.
        """
        # torch Tensor
        if isinstance(output, torch.Tensor):
            return output.squeeze().cpu().numpy()

        # raw bytes (wav) or file-like
        if isinstance(output, (bytes, bytearray)):
            try:
                return librosa.load(io.BytesIO(bytes(output)), sr=sample_rate)[0]
            except Exception:
                app.logger.exception("Failed to load WAV bytes into numpy array")
                raise

        # numpy array
        if isinstance(output, np.ndarray):
            return output

        raise TypeError("Unsupported audio type for output: %s" % type(output))

    def remove_excessive_silence(
        self,
        audio: np.ndarray,
        max_silence_duration: int = 30,
        sample_rate: int = 24000,
        silence_db_threshold: int = 55,
    ) -> np.ndarray:
        """Split audio into non-silent intervals and cap long silent gaps.

        Returns a concatenated numpy array containing the cleaned audio.
        """
        max_silence_samples = int((max_silence_duration / 1000) * sample_rate)

        non_silent_intervals = librosa.effects.split(
            audio, top_db=silence_db_threshold
        )

        if len(non_silent_intervals) == 0:
            # Nothing detected as non-silent — return original
            app.logger.debug("No non-silent intervals detected; returning original audio")
            return audio

        output_audio: List[np.ndarray] = []
        for i, (start, end) in enumerate(non_silent_intervals):
            self.get_audio_batches(
                audio, max_silence_samples, non_silent_intervals, output_audio, i, start, end
            )

        if not output_audio:
            return audio

        return np.concatenate(output_audio)

    def get_audio_batches(self, audio, max_silence_samples, non_silent_intervals, output_audio, i, start, end):
        # Keep signature and behavior for backward compatibility
        dto = GetAudioBatchDto(
            audio=audio,
            max_silence_samples=max_silence_samples,
            non_silent_intervals=non_silent_intervals,
            output_audio=output_audio,
            i=i,
            start=start,
            end=end,
        )
        dto.output_audio.append(dto.audio[dto.start:dto.end])

        if dto.i < len(dto.non_silent_intervals) - 1:
            generate_dto = GenerateOutputAudioDto(
                audio=dto.audio,
                max_silence_samples=dto.max_silence_samples,
                non_silent_intervals=dto.non_silent_intervals,
                output_audio=dto.output_audio,
                i=dto.i,
                end=dto.end,
            )
            self._generate_output_audio_with_silence(generate_dto)

    def _generate_output_audio_with_silence(self, dto: GenerateOutputAudioDto):
        # Keep signature and behavior for backward compatibility
        next_start = dto.non_silent_intervals[dto.i + 1][0]
        silence_duration = next_start - dto.end
        if silence_duration > dto.max_silence_samples:
            silence_duration = dto.max_silence_samples

        silence = np.zeros(silence_duration, dtype=dto.audio.dtype)
        dto.output_audio.append(silence)
