import asyncio
from concurrent.futures import Future
import threading
from types import SimpleNamespace
from unittest.mock import patch

from src.realtime_session import RealtimeTurnResult, StreamlitRealtimeSession, format_realtime_exception


def test_realtime_websocket_400_error_mentions_model_override():
    message = format_realtime_exception(Exception("server rejected WebSocket connection: HTTP 400"))

    assert "OPENAI_REALTIME_MODEL" in message
    assert "visible Realtime model" in message


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


def test_stop_streaming_waits_for_task_before_restart():
    class WaitingFuture(Future[None]):
        def __init__(self) -> None:
            super().__init__()
            self.waiting = threading.Event()

        def result(self, timeout=None):
            self.waiting.set()
            return super().result(timeout)

    session = StreamlitRealtimeSession.__new__(StreamlitRealtimeSession)
    session._stream_lock = None
    session._stream_audio_queue = []
    session._stream_pending_audio = b""
    session._closed = False
    session._streaming = True
    session._loop = object()
    session._thread = object()
    submitted_tasks: list[Future[None]] = []
    running_task = WaitingFuture()
    session._stream_task = running_task

    def start_task(coroutine, loop):
        coroutine.close()
        task: Future[None] = Future()
        submitted_tasks.append(task)
        return task

    with patch("src.realtime_session.asyncio.run_coroutine_threadsafe", side_effect=start_task):
        stopper = threading.Thread(target=session.stop_streaming)
        stopper.start()
        assert running_task.waiting.wait(timeout=1)

        session.start_streaming()
        assert submitted_tasks == []

        running_task.set_result(None)
        stopper.join(timeout=1)
        session.start_streaming()

    assert not stopper.is_alive()
    assert len(submitted_tasks) == 1
    assert session._stream_task is submitted_tasks[0]


def test_stop_streaming_timeout_keeps_task_and_blocks_restart():
    class TimeoutFuture(Future[None]):
        def result(self, timeout=None):
            raise TimeoutError

    session = StreamlitRealtimeSession.__new__(StreamlitRealtimeSession)
    session._stream_lock = None
    session._stream_audio_queue = []
    session._stream_pending_audio = b""
    session._closed = False
    session._streaming = True
    session._thread = object()
    running_task = TimeoutFuture()
    session._stream_task = running_task

    session.stop_streaming()

    with patch("src.realtime_session.asyncio.run_coroutine_threadsafe") as start_task:
        session.start_streaming()

    assert session._stream_task is running_task
    start_task.assert_not_called()


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


def test_stop_streaming_clears_queued_results_and_connection():
    class FakeCloser:
        def __init__(self) -> None:
            self.closed = False

        async def close(self) -> None:
            self.closed = True

    def close_task(coroutine, loop):
        asyncio.run(coroutine)
        task: Future[None] = Future()
        task.set_result(None)
        return task

    session = StreamlitRealtimeSession.__new__(StreamlitRealtimeSession)
    session._stream_lock = None
    session._stream_audio_queue = [b"audio"]
    session._stream_pending_audio = b"pending"
    session._stream_results = [RealtimeTurnResult("old", "result", None)]
    session._streaming = True
    session._stream_task = None
    session._loop = object()
    connection = FakeCloser()
    client = FakeCloser()
    session._connection = connection
    session._client = client

    with patch("src.realtime_session.asyncio.run_coroutine_threadsafe", side_effect=close_task):
        session.stop_streaming()

    assert session._stream_results == []
    assert session._connection is None
    assert session._client is None
    assert connection.closed
    assert client.closed


def test_late_transcript_after_response_done_emits_one_result_without_new_response():
    class FakeInputAudioBuffer:
        async def clear(self) -> None:
            pass

        async def append(self, *, audio: str) -> None:
            pass

    class FakeConnection:
        def __init__(self, session) -> None:
            self.input_audio_buffer = FakeInputAudioBuffer()
            self.response = SimpleNamespace(create=self.create_response)
            self._session = session
            self._events = iter(
                [
                    SimpleNamespace(type="response.created"),
                    SimpleNamespace(type="response.done", response=None),
                    SimpleNamespace(
                        type="conversation.item.input_audio_transcription.completed",
                        transcript="late transcript",
                    ),
                ]
            )
            self.create_calls = 0

        async def create_response(self, *, response) -> None:
            self.create_calls += 1

        async def recv(self):
            event = next(self._events)
            if event.type == "conversation.item.input_audio_transcription.completed":
                self._session._streaming = False
            return event

    session = StreamlitRealtimeSession.__new__(StreamlitRealtimeSession)
    session._stream_results = []
    session._stream_lock = None
    session._stream_audio_queue = []
    session._stream_pending_audio = b""
    session._streaming = True
    session._stream_task = Future()
    session._closed = False
    connection = FakeConnection(session)
    session._ensure_connection = lambda: None

    async def ensure_connection():
        return connection

    session._ensure_connection = ensure_connection

    asyncio.run(session._run_streaming())

    assert session.poll_stream_result() == RealtimeTurnResult("late transcript", "(No transcript returned)", None)
    assert session.poll_stream_result() is None
    assert connection.create_calls == 0


def test_failed_stream_queues_error_and_clears_stream_state():
    class FakeCloser:
        def __init__(self) -> None:
            self.closed = False

        async def close(self) -> None:
            self.closed = True

    session = StreamlitRealtimeSession.__new__(StreamlitRealtimeSession)
    session._stream_results = []
    session._stream_lock = None
    session._stream_audio_queue = [b"audio"]
    session._stream_pending_audio = b"pending"
    session._streaming = True
    session._stream_task = Future()
    session._closed = False
    connection = FakeCloser()
    client = FakeCloser()
    session._connection = connection
    session._client = client

    async def fail_to_connect():
        raise RuntimeError("connection failed")

    session._ensure_connection = fail_to_connect

    asyncio.run(session._run_streaming())

    result = session.poll_stream_result()
    assert result is not None
    assert result.error == "connection failed"
    assert not session._streaming
    assert session._stream_task is None
    assert session._stream_audio_queue == []
    assert session._stream_pending_audio == b""
    assert session._connection is None
    assert session._client is None
    assert connection.closed
    assert client.closed
