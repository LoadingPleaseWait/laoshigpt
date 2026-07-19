import av
import numpy as np

from src.audio_util import SAMPLE_RATE
from src.hands_free_audio import HandsFreeAudioBridge, audio_frame_to_pcm16, pcm16_duration_seconds


def test_pcm16_duration_seconds_for_one_second_mono_audio():
    pcm_bytes = b"\x00\x00" * SAMPLE_RATE

    assert pcm16_duration_seconds(pcm_bytes) == 1.0


def test_bridge_drops_audio_while_paused():
    bridge = HandsFreeAudioBridge()
    bridge.set_paused(True)

    bridge.push_pcm16(b"\x01\x00" * 2400)

    assert bridge.pop_pcm16_chunks() == []


def test_bridge_pausing_clears_queued_audio():
    bridge = HandsFreeAudioBridge()
    bridge.push_pcm16(b"\x01\x00" * 2400)

    bridge.set_paused(True)

    assert bridge.pop_pcm16_chunks() == []


def test_bridge_returns_chunks_and_clears_queue():
    bridge = HandsFreeAudioBridge()
    first = b"\x01\x00" * 1200
    second = b"\x02\x00" * 1200

    bridge.push_pcm16(first)
    bridge.push_pcm16(second)

    assert bridge.pop_pcm16_chunks() == [first, second]
    assert bridge.pop_pcm16_chunks() == []


def test_audio_frame_conversion_uses_only_valid_mono_samples():
    samples = np.array([[1, -2, 300]], dtype=np.int16)
    frame = av.AudioFrame.from_ndarray(samples, format="s16", layout="mono")
    frame.sample_rate = SAMPLE_RATE

    assert audio_frame_to_pcm16(frame) == samples.tobytes()


def test_bridge_reuses_its_resampler_for_frames():
    samples = np.array([[1, 2]], dtype=np.int16)
    frame = av.AudioFrame.from_ndarray(samples, format="s16", layout="mono")
    frame.sample_rate = SAMPLE_RATE
    bridge = HandsFreeAudioBridge()
    resampler = bridge._resampler

    bridge.push_frame(frame)
    bridge.push_frame(frame)

    assert bridge._resampler is resampler
    assert bridge.pop_pcm16_chunks() == [samples.tobytes(), samples.tobytes()]
