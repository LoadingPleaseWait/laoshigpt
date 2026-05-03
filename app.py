"""Browser-friendly Streamlit app for Laoshi."""

from __future__ import annotations

import os

import streamlit as st
from openai import OpenAI

MODEL_NAME = "gpt-4o-mini"

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


def transcribe_audio(client: OpenAI, audio_bytes: bytes) -> str:
    result = client.audio.transcriptions.create(
        model="gpt-4o-mini-transcribe",
        file=("input.wav", audio_bytes, "audio/wav"),
    )
    return result.text


def respond(client: OpenAI) -> str:
    completion = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": LAOSHI_INSTRUCTIONS},
            *st.session_state.messages,
        ],
        temperature=0.5,
    )
    return completion.choices[0].message.content or ""


def main() -> None:
    st.set_page_config(page_title="Laoshi Web", page_icon="🧑‍🏫")
    st.title("🧑‍🏫 Laoshi (Streamlit)")
    st.caption("Web version of your prototype")

    if not os.getenv("OPENAI_API_KEY"):
        st.error("Please set OPENAI_API_KEY before running this app.")
        st.stop()

    client = OpenAI()
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
            assistant_text = respond(client)
        st.session_state.messages.append({"role": "assistant", "content": assistant_text})
        with st.chat_message("assistant"):
            st.markdown(assistant_text)

    prompt = st.chat_input("Type your message")
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.spinner("Laoshi is responding..."):
            assistant_text = respond(client)
        st.session_state.messages.append({"role": "assistant", "content": assistant_text})
        with st.chat_message("assistant"):
            st.markdown(assistant_text)


if __name__ == "__main__":
    main()