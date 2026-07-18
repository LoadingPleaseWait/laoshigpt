from src.audio_util import SAMPLE_RATE
from src.hands_free_audio import HandsFreeAudioBridge, pcm16_duration_seconds


def test_pcm16_duration_seconds_for_one_second_mono_audio():
    pcm_bytes = b"\x00\x00" * SAMPLE_RATE

    assert pcm16_duration_seconds(pcm_bytes) == 1.0


def test_bridge_drops_audio_while_paused():
    bridge = HandsFreeAudioBridge()
    bridge.set_paused(True)

    bridge.push_pcm16(b"\x01\x00" * 2400)

    assert bridge.pop_pcm16_chunks() == []


def test_bridge_returns_chunks_and_clears_queue():
    bridge = HandsFreeAudioBridge()
    first = b"\x01\x00" * 1200
    second = b"\x02\x00" * 1200

    bridge.push_pcm16(first)
    bridge.push_pcm16(second)

    assert bridge.pop_pcm16_chunks() == [first, second]
    assert bridge.pop_pcm16_chunks() == []
