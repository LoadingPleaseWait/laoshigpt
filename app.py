"""Browser-friendly Streamlit app for Laoshi."""

from __future__ import annotations

import asyncio
import base64
import os

import streamlit as st
from openai import AsyncOpenAI, OpenAI

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
                st.audio(base64.b64decode(message["audio_b64"]), format="audio/mp3")


def transcribe_audio(client: OpenAI, audio_bytes: bytes) -> str:
    result = client.audio.transcriptions.create(
        model="gpt-4o-mini-transcribe",
        file=("input.wav", audio_bytes, "audio/wav"),
    )
    return result.text


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


def text_to_speech(client: OpenAI, text: str) -> bytes | None:
    try:
        speech = client.audio.speech.create(
            model="gpt-4o-mini-tts",
            voice="alloy",
            input=text,
            response_format="mp3",
        )
        return speech.read()
    except Exception:
        return None


def main() -> None:
    st.set_page_config(page_title="Laoshi Web", page_icon="🧑‍🏫")
    st.title("🧑‍🏫 Laoshi (Streamlit)")
    st.caption("Web version of your prototype")

    if not os.getenv("OPENAI_API_KEY"):
        st.error("Please set OPENAI_API_KEY before running this app.")
        st.stop()

    client = OpenAI()
    rt_client = AsyncOpenAI()
    init_state()

    if st.button("Reset chat"):
        st.session_state.messages = []
        init_state()
        st.rerun()

    render_messages()

    audio_input = st.audio_input("Optional: record a message")
    if audio_input is not None:
        with st.spinner("Transcribing..."):
            user_text = transcribe_audio(client, audio_input.read())
        st.session_state.messages.append({"role": "user", "content": user_text})
        with st.chat_message("user"):
            st.markdown(user_text)

        with st.spinner("Laoshi is responding..."):
            assistant_text = respond(rt_client)
        speech_bytes = text_to_speech(client, assistant_text)
        assistant_message = {"role": "assistant", "content": assistant_text}
        if speech_bytes is not None:
            assistant_message["audio_b64"] = base64.b64encode(speech_bytes).decode("utf-8")

        st.session_state.messages.append(assistant_message)
        with st.chat_message("assistant"):
            st.markdown(assistant_text)
            if speech_bytes is not None:
                st.audio(speech_bytes, format="audio/mp3")
            else:
                st.caption("(Audio playback unavailable for this response)")

    prompt = st.chat_input("Type your message")
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.spinner("Laoshi is responding..."):
            assistant_text = respond(rt_client)
        speech_bytes = text_to_speech(client, assistant_text)
        assistant_message = {"role": "assistant", "content": assistant_text}
        if speech_bytes is not None:
            assistant_message["audio_b64"] = base64.b64encode(speech_bytes).decode("utf-8")

        st.session_state.messages.append(assistant_message)
        with st.chat_message("assistant"):
            st.markdown(assistant_text)
            if speech_bytes is not None:
                st.audio(speech_bytes, format="audio/mp3")
            else:
                st.caption("(Audio playback unavailable for this response)")


if __name__ == "__main__":
    main()