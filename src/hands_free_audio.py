"""Hands-free audio helpers for Streamlit WebRTC capture."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field

import av
from av.audio.resampler import AudioResampler

from src.audio_util import CHANNELS, SAMPLE_RATE


BYTES_PER_PCM16_SAMPLE = 2


def pcm16_duration_seconds(pcm_bytes: bytes) -> float:
    if not pcm_bytes:
        return 0.0
    return len(pcm_bytes) / (SAMPLE_RATE * CHANNELS * BYTES_PER_PCM16_SAMPLE)


def audio_frame_to_pcm16(frame: av.AudioFrame, resampler: AudioResampler | None = None) -> bytes:
    resampler = resampler or AudioResampler(format="s16", layout="mono", rate=SAMPLE_RATE)
    resampled_frames = resampler.resample(frame)
    return b"".join(resampled.to_ndarray().tobytes() for resampled in resampled_frames)


@dataclass
class HandsFreeAudioBridge:
    _lock: threading.Lock = field(default_factory=threading.Lock)
    _chunks: list[bytes] = field(default_factory=list)
    _paused: bool = False
    _stopped: bool = False
    _resampler: AudioResampler = field(
        default_factory=lambda: AudioResampler(format="s16", layout="mono", rate=SAMPLE_RATE)
    )

    def set_paused(self, paused: bool) -> None:
        with self._lock:
            self._paused = paused
            if paused:
                self._chunks = []

    def set_stopped(self, stopped: bool) -> None:
        with self._lock:
            self._stopped = stopped
            if stopped:
                self._chunks = []

    def push_frame(self, frame: av.AudioFrame) -> None:
        pcm_bytes = audio_frame_to_pcm16(frame, self._resampler)
        self.push_pcm16(pcm_bytes)

    def push_pcm16(self, pcm_bytes: bytes) -> None:
        if not pcm_bytes:
            return
        with self._lock:
            if self._paused or self._stopped:
                return
            self._chunks.append(pcm_bytes)

    def pop_pcm16_chunks(self) -> list[bytes]:
        with self._lock:
            chunks = self._chunks
            self._chunks = []
            return chunks
