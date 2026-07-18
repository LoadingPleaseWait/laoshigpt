import asyncio
from concurrent.futures import Future
from unittest.mock import patch

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


def test_stop_streaming_cancels_task_before_restart():
    session = StreamlitRealtimeSession.__new__(StreamlitRealtimeSession)
    session._closed = False
    session._streaming = False
    session._stream_task = None
    session._stream_lock = None
    session._stream_audio_queue = []
    session._stream_pending_audio = b""
    session._loop = object()
    session._thread = object()
    submitted_tasks: list[Future[None]] = []

    def start_task(coroutine, loop):
        coroutine.close()
        task: Future[None] = Future()
        submitted_tasks.append(task)
        return task

    with patch("src.realtime_session.asyncio.run_coroutine_threadsafe", side_effect=start_task):
        session.start_streaming()
        first_task = session._stream_task
        session.stop_streaming()
        session.start_streaming()

    assert first_task is not None
    assert first_task.cancelled()
    assert len(submitted_tasks) == 2
    assert session._stream_task is submitted_tasks[1]


def test_stop_streaming_clears_buffered_pending_audio():
    session = StreamlitRealtimeSession.__new__(StreamlitRealtimeSession)
    session._stream_lock = None
    session._stream_audio_queue = [b"a"]
    session._stream_pending_audio = b"b"
    session._streaming = True
    session._stream_task = None

    asyncio.run(session._flush_stream_audio(object()))

    assert session._stream_pending_audio == b"ba"

    session.stop_streaming()

    assert session._stream_pending_audio == b""
    assert session._stream_audio_queue == []
