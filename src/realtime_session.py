"""Persistent Realtime session support for the Streamlit app."""

from __future__ import annotations

import asyncio
import base64
import concurrent.futures
import threading
from dataclasses import dataclass

from openai import AsyncOpenAI
from openai.resources.realtime.realtime import AsyncRealtimeConnection

from src.audio_util import SAMPLE_RATE
from src.laoshi_prompt import LAOSHI_INSTRUCTIONS, MODEL_NAME

MIN_INPUT_AUDIO_BYTES = int(SAMPLE_RATE * 0.1) * 2


@dataclass(frozen=True)
class RealtimeTurnResult:
    user_text: str
    assistant_text: str
    assistant_audio: bytes | None
    error: str | None = None


class StreamlitRealtimeSession:
    """Owns one Realtime websocket across Streamlit reruns."""

    def __init__(self) -> None:
        self._loop = asyncio.new_event_loop()
        self._loop_started = threading.Event()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        self._loop_started.wait(timeout=5)
        self._client: AsyncOpenAI | None = None
        self._connection: AsyncRealtimeConnection | None = None
        self._closed = False
        self._stream_audio_queue: list[bytes] = []
        self._stream_results: list[RealtimeTurnResult] = []
        self._stream_lock = threading.Lock()
        self._stream_pending_audio = b""
        self._streaming = False
        self._stream_task: concurrent.futures.Future[None] | None = None

    def submit_audio(self, pcm_bytes: bytes) -> RealtimeTurnResult:
        if self._closed:
            return RealtimeTurnResult("", "", None, "Realtime session is closed.")
        self.stop_streaming()
        stream_task = getattr(self, "_stream_task", None)
        if stream_task is not None and not stream_task.done():
            return RealtimeTurnResult("", "", None, "Streaming session is still stopping.")
        if len(pcm_bytes) < MIN_INPUT_AUDIO_BYTES:
            return RealtimeTurnResult(
                "",
                "",
                None,
                "Recorded audio is empty or shorter than the Realtime API minimum of 100ms.",
            )

        future = asyncio.run_coroutine_threadsafe(self._submit_audio(pcm_bytes), self._loop)
        try:
            return future.result()
        except Exception as exc:
            self.close()
            return RealtimeTurnResult("", "", None, str(exc))

    def start_streaming(self) -> None:
        stream_task = getattr(self, "_stream_task", None)
        if self._closed or self._streaming or (stream_task is not None and not stream_task.done()):
            return
        self._streaming = True
        self._stream_task = asyncio.run_coroutine_threadsafe(self._run_streaming(), self._loop)

    def append_stream_audio(self, pcm_bytes: bytes) -> None:
        if not pcm_bytes or self._closed:
            return
        with self._get_stream_lock():
            self._stream_audio_queue.append(pcm_bytes)

    def poll_stream_result(self) -> RealtimeTurnResult | None:
        with self._get_stream_lock():
            if not self._stream_results:
                return None
            return self._stream_results.pop(0)

    def stop_streaming(self) -> None:
        self._streaming = False
        with self._get_stream_lock():
            self._stream_audio_queue = []
            self._stream_pending_audio = b""

        stream_task = getattr(self, "_stream_task", None)
        if stream_task is None or stream_task.done():
            self._stream_task = None
            return

        if threading.current_thread() is not getattr(self, "_thread", None):
            try:
                stream_task.result(timeout=5)
            except TimeoutError:
                return
            except concurrent.futures.CancelledError:
                pass
        if stream_task.done():
            self._stream_task = None

    def _queue_stream_result(self, result: RealtimeTurnResult) -> None:
        with self._get_stream_lock():
            self._stream_results.append(result)

    def _get_stream_lock(self) -> threading.Lock:
        lock = getattr(self, "_stream_lock", None)
        if lock is None:
            lock = threading.Lock()
            self._stream_lock = lock
        return lock

    def close(self) -> None:
        if self._closed:
            return
        self.stop_streaming()
        self._closed = True

        if self._connection is not None or self._client is not None:
            future = asyncio.run_coroutine_threadsafe(self._close_async(), self._loop)
            try:
                future.result(timeout=5)
            except Exception:
                pass

        self._loop.call_soon_threadsafe(self._loop.stop)
        self._thread.join(timeout=5)

    def _run_loop(self) -> None:
        asyncio.set_event_loop(self._loop)
        self._loop_started.set()
        self._loop.run_forever()

    async def _submit_audio(self, pcm_bytes: bytes) -> RealtimeTurnResult:
        connection = await self._ensure_connection()
        audio_b64 = base64.b64encode(pcm_bytes).decode("utf-8")

        await connection.input_audio_buffer.clear()
        await connection.input_audio_buffer.append(audio=audio_b64)

        return await self._collect_turn(connection)

    async def _run_streaming(self) -> None:
        user_text_parts: list[str] = []
        assistant_text_parts: list[str] = []
        assistant_audio_parts: list[bytes] = []
        saw_audio_transcript_delta = False
        try:
            connection = await self._ensure_connection()
            await connection.input_audio_buffer.clear()
            response_requested = False

            while self._streaming and not self._closed:
                await self._flush_stream_audio(connection)

                try:
                    event = await asyncio.wait_for(connection.recv(), timeout=0.2)
                except TimeoutError:
                    continue

                event_type = getattr(event, "type", "")

                if event_type == "conversation.item.input_audio_transcription.delta":
                    self._append_text(user_text_parts, getattr(event, "delta", None))
                elif event_type == "conversation.item.input_audio_transcription.completed":
                    transcript = getattr(event, "transcript", None)
                    if isinstance(transcript, str) and transcript.strip():
                        user_text_parts = [transcript]
                    if not response_requested:
                        await connection.response.create(response={"output_modalities": ["audio"]})
                        response_requested = True
                elif event_type == "response.created":
                    response_requested = True
                elif event_type == "response.output_audio_transcript.delta":
                    saw_audio_transcript_delta = True
                    self._append_text(assistant_text_parts, getattr(event, "delta", None))
                elif event_type == "response.output_text.delta" and not saw_audio_transcript_delta:
                    self._append_text(assistant_text_parts, getattr(event, "delta", None))
                elif event_type == "response.output_audio.delta":
                    delta = getattr(event, "delta", None)
                    if isinstance(delta, str):
                        try:
                            assistant_audio_parts.append(base64.b64decode(delta))
                        except Exception:
                            pass
                elif event_type == "response.done":
                    self._extract_from_response_done(event, assistant_text_parts, assistant_audio_parts)
                    user_text = "".join(user_text_parts).strip()
                    assistant_text = "".join(assistant_text_parts).strip() or "(No transcript returned)"
                    assistant_audio = b"".join(assistant_audio_parts) if assistant_audio_parts else None
                    self._queue_stream_result(RealtimeTurnResult(user_text, assistant_text, assistant_audio))
                    response_requested = False
                    user_text_parts = []
                    assistant_text_parts = []
                    assistant_audio_parts = []
                    saw_audio_transcript_delta = False
                elif event_type == "error":
                    raise RuntimeError(self._format_error(event))
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            self._queue_stream_result(RealtimeTurnResult("".join(user_text_parts).strip(), "", None, str(exc)))
            try:
                await self._close_async()
            except Exception:
                pass
        finally:
            self._streaming = False
            with self._get_stream_lock():
                self._stream_audio_queue = []
                self._stream_pending_audio = b""
            self._stream_task = None

    async def _flush_stream_audio(self, connection: AsyncRealtimeConnection) -> None:
        with self._get_stream_lock():
            chunks = self._stream_audio_queue
            self._stream_audio_queue = []

            if not chunks:
                return

            pending_audio = getattr(self, "_stream_pending_audio", b"") + b"".join(chunks)
            if len(pending_audio) < MIN_INPUT_AUDIO_BYTES:
                self._stream_pending_audio = pending_audio
                return

            self._stream_pending_audio = b""
        audio_b64 = base64.b64encode(pending_audio).decode("utf-8")
        await connection.input_audio_buffer.append(audio=audio_b64)

    async def _ensure_connection(self) -> AsyncRealtimeConnection:
        if self._connection is not None:
            return self._connection

        self._client = AsyncOpenAI()
        self._connection = await self._client.realtime.connect(model=MODEL_NAME).enter()
        await self._connection.session.update(
            session={
                "audio": {
                    "input": {
                        "format": {"type": "audio/pcm", "rate": SAMPLE_RATE},
                        "transcription": {"model": "gpt-4o-mini-transcribe"},
                        "turn_detection": {"type": "server_vad"},
                    }
                },
                "instructions": LAOSHI_INSTRUCTIONS,
                "model": MODEL_NAME,
                "output_modalities": ["audio"],
                "type": "realtime",
            }
        )
        return self._connection

    async def _collect_turn(self, connection: AsyncRealtimeConnection) -> RealtimeTurnResult:
        user_text_parts: list[str] = []
        assistant_text_parts: list[str] = []
        assistant_audio_parts: list[bytes] = []
        saw_audio_transcript_delta = False
        saw_response_done = False
        response_requested = False

        while True:
            try:
                event = await asyncio.wait_for(connection.recv(), timeout=1.5 if saw_response_done else 45)
            except TimeoutError:
                break

            event_type = getattr(event, "type", "")

            if event_type == "conversation.item.input_audio_transcription.delta":
                self._append_text(user_text_parts, getattr(event, "delta", None))
            elif event_type == "conversation.item.input_audio_transcription.completed":
                transcript = getattr(event, "transcript", None)
                if isinstance(transcript, str) and transcript.strip():
                    user_text_parts = [transcript]
                if not response_requested:
                    await connection.response.create(response={"output_modalities": ["audio"]})
                    response_requested = True
            elif event_type == "response.created":
                response_requested = True
            elif event_type == "response.output_audio_transcript.delta":
                saw_audio_transcript_delta = True
                self._append_text(assistant_text_parts, getattr(event, "delta", None))
            elif event_type == "response.output_text.delta" and not saw_audio_transcript_delta:
                self._append_text(assistant_text_parts, getattr(event, "delta", None))
            elif event_type == "response.output_audio.delta":
                delta = getattr(event, "delta", None)
                if isinstance(delta, str):
                    try:
                        assistant_audio_parts.append(base64.b64decode(delta))
                    except Exception:
                        pass
            elif event_type == "response.done":
                self._extract_from_response_done(event, assistant_text_parts, assistant_audio_parts)
                saw_response_done = True
                if user_text_parts:
                    break
            elif event_type == "error":
                return RealtimeTurnResult(
                    "".join(user_text_parts).strip(),
                    "",
                    None,
                    self._format_error(event),
                )

        user_text = "".join(user_text_parts).strip()
        assistant_text = "".join(assistant_text_parts).strip() or "(No transcript returned)"
        assistant_audio = b"".join(assistant_audio_parts) if assistant_audio_parts else None
        return RealtimeTurnResult(user_text, assistant_text, assistant_audio)

    async def _close_async(self) -> None:
        connection = self._connection
        client = self._client
        self._connection = None
        self._client = None

        try:
            if connection is not None:
                await connection.close()
        finally:
            if client is not None:
                await client.close()

    @staticmethod
    def _append_text(parts: list[str], value: object) -> None:
        if isinstance(value, str) and value.strip():
            parts.append(value)

    @staticmethod
    def _extract_from_response_done(event: object, text_parts: list[str], audio_parts: list[bytes]) -> None:
        if text_parts or audio_parts:
            return

        response = getattr(event, "response", None)
        outputs = getattr(response, "output", None)
        if not outputs:
            return

        for output_item in outputs:
            content = getattr(output_item, "content", None) or []
            for part in content:
                StreamlitRealtimeSession._append_text(text_parts, getattr(part, "text", None))
                StreamlitRealtimeSession._append_text(text_parts, getattr(part, "transcript", None))
                StreamlitRealtimeSession._append_text(text_parts, getattr(part, "audio_transcript", None))

                for audio_attr in ("audio", "data", "delta"):
                    audio_payload = getattr(part, audio_attr, None)
                    if isinstance(audio_payload, str):
                        try:
                            audio_parts.append(base64.b64decode(audio_payload))
                        except Exception:
                            pass

    @staticmethod
    def _format_error(event: object) -> str:
        error_obj = getattr(event, "error", None)
        if isinstance(error_obj, dict):
            return error_obj.get("message") or str(error_obj)
        return str(error_obj or event)
