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

MODEL_NAME = "gpt-realtime-1.5"

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
                st.audio(base64.b64decode(message["audio_b64"]), format="audio/wav")


def _build_history_prompt() -> str:
    lines: list[str] = []
    for message in st.session_state.messages:
        role = message["role"].capitalize()
        lines.append(f"{role}: {message['content']}")
    return "\n".join(lines)


async def _respond_realtime(rt_client: AsyncOpenAI) -> str:
    history = _build_history_prompt()
    prompt = (
        "Continue this tutoring conversation naturally and respond as the assistant.\n\n"
        f"Conversation so far:\n{history}"
    )

    async with rt_client.realtime.connect(model=MODEL_NAME) as connection:
        await connection.session.update(
            session={
                "output_modalities": ["text"],
                "instructions": LAOSHI_INSTRUCTIONS,
                "model": MODEL_NAME,
                "type": "realtime",
            }
        )
        await connection.conversation.item.create(
            item={
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": prompt}],
            }
        )
        await connection.response.create()

        parts: list[str] = []
        async for event in connection:
            if event.type == "response.output_text.delta":
                parts.append(event.delta)
            elif event.type == "response.done":
                break

    return "".join(parts).strip()


def respond(rt_client: AsyncOpenAI) -> str:
    return asyncio.run(_respond_realtime(rt_client))


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
                "output_modalities": ["audio", "text"],
                "audio": {"input": {"turn_detection": None}},
            }
        )

        await connection.input_audio_buffer.append(audio=base64.b64encode(pcm_bytes).decode("utf-8"))
        await connection.input_audio_buffer.commit()
        await connection.response.create()

        text_parts: list[str] = []
        audio_parts: list[bytes] = []
        async for event in connection:
            if event.type == "response.output_audio_transcript.delta":
                text_parts.append(event.delta)
            elif event.type == "response.output_text.delta":
                text_parts.append(event.delta)
            elif event.type == "response.output_audio.delta":
                audio_parts.append(base64.b64decode(event.delta))
            elif event.type == "response.done":
                break

    assistant_text = "".join(text_parts).strip()
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

    audio_input = st.audio_input("Optional: record a message")
    if audio_input is not None:
        audio_bytes = audio_input.read()
        user_text = "(Voice message)"
        st.session_state.messages.append({"role": "user", "content": user_text})
        with st.chat_message("user"):
            st.markdown(user_text)

        with st.spinner("Laoshi is responding..."):
            assistant_text, speech_bytes = respond_with_audio(rt_client, audio_bytes)
        assistant_message = {"role": "assistant", "content": assistant_text}
        if speech_bytes is not None:
            assistant_message["audio_b64"] = base64.b64encode(speech_bytes).decode("utf-8")

        st.session_state.messages.append(assistant_message)
        with st.chat_message("assistant"):
            st.markdown(assistant_text)
            if speech_bytes is not None:
                st.audio(speech_bytes, format="audio/wav")
            else:
                st.caption("(Audio playback unavailable for this response)")

    prompt = st.chat_input("Type your message")
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.spinner("Laoshi is responding..."):
            assistant_text = respond(rt_client)
        assistant_message = {"role": "assistant", "content": assistant_text}

        st.session_state.messages.append(assistant_message)
        with st.chat_message("assistant"):
            st.markdown(assistant_text)


if __name__ == "__main__":
    main()