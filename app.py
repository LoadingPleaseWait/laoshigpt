"""Browser-friendly Streamlit app for Laoshi."""

from __future__ import annotations

import asyncio
import base64
import os
import wave
from io import BytesIO

import streamlit as st
from openai import AsyncOpenAI
from src.audio_util import CHANNELS, SAMPLE_RATE, audio_to_pcm16_base64

MODEL_NAME = "gpt-realtime-mini"

LAOSHI_INSTRUCTIONS = """You are an interactive Chinese language tutor.
Start by asking in English about level, goals, target Sinitic language,
and preferred explanation language.
When speaking Chinese, speak slowly and use only HSK-3 vocabulary.
Keep responses concise.
For Mandarin transcriptions use Traditional Chinese + Hanyu Pinyin unless asked otherwise.
For Cantonese transcriptions use Traditional Chinese + Jyutping unless asked otherwise.
"""


def init_state() -> None:
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "Hi! I’m Laoshi 👋 Tell me your level, goals, target language, and explanation preference.",
            }
        ]


def render_messages() -> None:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message["role"] == "assistant" and message.get("audio_b64"):
                st.audio(base64.b64decode(message["audio_b64"]), format="audio/wav", autoplay=True)


def _build_history_prompt() -> str:
    lines: list[str] = []
    for message in st.session_state.messages:
        role = message["role"].capitalize()
        lines.append(f"{role}: {message['content']}")
    return "\n".join(lines)


def pcm16_to_wav_bytes(pcm_data: bytes) -> bytes:
    buffer = BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(CHANNELS)
        wav_file.setsampwidth(2)
        wav_file.setframerate(SAMPLE_RATE)
        wav_file.writeframes(pcm_data)
    return buffer.getvalue()


async def _respond_realtime_audio(rt_client: AsyncOpenAI, recorded_audio_bytes: bytes) -> tuple[str, bytes | None]:
    history = _build_history_prompt()
    pcm_bytes = audio_to_pcm16_base64(recorded_audio_bytes)
    history_context = f"\n\nConversation so far:\n{history}" if history else ""

    async with rt_client.realtime.connect(model=MODEL_NAME) as connection:
        await connection.session.update(
            session={
                "instructions": f"{LAOSHI_INSTRUCTIONS}{history_context}",
                "model": MODEL_NAME,
                "type": "realtime",
                "output_modalities": ["audio"],
                "audio": {"input": {"turn_detection": None}},
            }
        )

        # Submit audio via input buffer (most reliable for recorded blobs).
        await connection.input_audio_buffer.append(audio=base64.b64encode(pcm_bytes).decode("utf-8"))
        await connection.input_audio_buffer.commit()
        await connection.response.create()

        text_parts: list[str] = []
        audio_parts: list[bytes] = []
        saw_audio_transcript_delta = False

        def _append_if_text(value: object) -> None:
            if isinstance(value, str) and value.strip():
                text_parts.append(value)

        def _extract_from_response_done(event: object) -> None:
            """Best-effort fallback extraction for SDK event-shape differences."""
            # If we already captured streaming deltas, don't append done-level content,
            # which can duplicate the same assistant text.
            if text_parts or audio_parts:
                return

            response = getattr(event, "response", None)
            outputs = getattr(response, "output", None)
            if not outputs:
                return

            for output_item in outputs:
                content = getattr(output_item, "content", None) or []
                for part in content:
                    # Text fields across SDK versions
                    _append_if_text(getattr(part, "text", None))
                    _append_if_text(getattr(part, "transcript", None))
                    _append_if_text(getattr(part, "audio_transcript", None))

                    # Audio payload fields across SDK versions
                    for audio_attr in ("audio", "data", "delta"):
                        audio_payload = getattr(part, audio_attr, None)
                        if isinstance(audio_payload, str):
                            try:
                                audio_parts.append(base64.b64decode(audio_payload))
                            except Exception:
                                pass
        realtime_error: str | None = None

        async for event in connection:
            event_type = getattr(event, "type", "")

            if event_type.endswith("output_audio_transcript.delta"):
                saw_audio_transcript_delta = True
                _append_if_text(getattr(event, "delta", None))
            elif event_type.endswith("output_text.delta"):
                # Some models emit both transcript and text deltas with duplicated content.
                # Prefer transcript deltas when present to avoid doubled output.
                if not saw_audio_transcript_delta:
                    _append_if_text(getattr(event, "delta", None))
            elif event_type.endswith("output_audio.delta"):
                delta = getattr(event, "delta", None)
                if isinstance(delta, str):
                    try:
                        audio_parts.append(base64.b64decode(delta))
                    except Exception:
                        pass
            elif event_type == "response.done":
                _extract_from_response_done(event)
                break
            elif event_type == "error":
                error_obj = getattr(event, "error", None)
                if isinstance(error_obj, dict):
                    realtime_error = error_obj.get("message") or str(error_obj)
                else:
                    realtime_error = str(error_obj or event)
                break

    assistant_text = "".join(text_parts).strip()
    if realtime_error:
        assistant_text = f"(Realtime API error: {realtime_error})"
    if not assistant_text:
        assistant_text = "(No transcript returned)"

    if audio_parts:
        return assistant_text, pcm16_to_wav_bytes(b"".join(audio_parts))
    return assistant_text, None


def respond_with_audio(rt_client: AsyncOpenAI, recorded_audio_bytes: bytes) -> tuple[str, bytes | None]:
    return asyncio.run(_respond_realtime_audio(rt_client, recorded_audio_bytes))


def main() -> None:
    st.set_page_config(page_title="Laoshi Web", page_icon="🧑‍🏫")
    st.title("🧑‍🏫 Laoshi (Streamlit)")
    st.caption("Web version of your prototype")

    if not os.getenv("OPENAI_API_KEY"):
        st.error("Please set OPENAI_API_KEY before running this app.")
        st.stop()

    rt_client = AsyncOpenAI()
    init_state()

    if st.button("Reset chat"):
        st.session_state.messages = []
        init_state()
        st.rerun()

    render_messages()

    audio_input = st.audio_input("Record your message")
    if audio_input is not None:
        audio_bytes = audio_input.read()
        # user_text = "(Voice message)"
        # st.session_state.messages.append({"role": "user", "content": user_text})
        # with st.chat_message("user"):
        #     st.markdown(user_text)

        with st.spinner("Laoshi is responding..."):
            assistant_text, speech_bytes = respond_with_audio(rt_client, audio_bytes)
        assistant_message = {"role": "assistant", "content": assistant_text}
        if speech_bytes is not None:
            assistant_message["audio_b64"] = base64.b64encode(speech_bytes).decode("utf-8")

        st.session_state.messages.append(assistant_message)
        with st.chat_message("assistant"):
            st.markdown(assistant_text)
            if speech_bytes is not None:
                st.audio(speech_bytes, format="audio/wav", autoplay=True)
            else:
                st.caption("(Audio playback unavailable for this response)")


if __name__ == "__main__":
    main()