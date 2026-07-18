from src.realtime_session import RealtimeTurnResult, StreamlitRealtimeSession


def test_poll_stream_result_returns_queued_result_without_network():
    session = StreamlitRealtimeSession.__new__(StreamlitRealtimeSession)
    session._stream_results = []
    session._stream_lock = None

    result = RealtimeTurnResult("你好", "很好", b"audio")
    session._queue_stream_result(result)

    assert session.poll_stream_result() == result
    assert session.poll_stream_result() is None


def test_append_stream_audio_ignores_empty_audio():
    session = StreamlitRealtimeSession.__new__(StreamlitRealtimeSession)
    session._stream_audio_queue = []
    session._closed = False
    session._stream_lock = None

    session.append_stream_audio(b"")

    assert session._stream_audio_queue == []
