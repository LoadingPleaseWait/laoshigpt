"""Browser-friendly Streamlit app for Lǎoshī."""

from __future__ import annotations

import base64
import os
import wave
from io import BytesIO

import streamlit as st

from src.audio_util import CHANNELS, SAMPLE_RATE, audio_to_pcm16_base64
from src.laoshi_prompt import INITIAL_GREETING
from src.realtime_session import StreamlitRealtimeSession


def init_state() -> None:
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": INITIAL_GREETING,
            }
        ]
    if "audio_input_key" not in st.session_state:
        st.session_state.audio_input_key = 0


def render_messages() -> None:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message["role"] == "assistant" and message.get("audio_b64"):
                st.audio(base64.b64decode(message["audio_b64"]), format="audio/wav", autoplay=True)


def pcm16_to_wav_bytes(pcm_data: bytes) -> bytes:
    buffer = BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(CHANNELS)
        wav_file.setsampwidth(2)
        wav_file.setframerate(SAMPLE_RATE)
        wav_file.writeframes(pcm_data)
    return buffer.getvalue()


def get_realtime_session() -> StreamlitRealtimeSession:
    session = st.session_state.get("realtime_session")
    if not isinstance(session, StreamlitRealtimeSession):
        session = StreamlitRealtimeSession()
        st.session_state.realtime_session = session
    return session


def reset_chat() -> None:
    session = st.session_state.pop("realtime_session", None)
    if isinstance(session, StreamlitRealtimeSession):
        session.close()
    st.session_state.messages = []
    st.session_state.audio_input_key = 0
    init_state()


def main() -> None:
    st.set_page_config(page_title="Lǎoshī Web", page_icon="🧑‍🏫")
    st.title("🧑‍🏫 Lǎoshī (Streamlit)")
    st.caption("Web version of your prototype")

    if not os.getenv("OPENAI_API_KEY"):
        st.error("Please set OPENAI_API_KEY before running this app.")
        st.stop()

    init_state()

    if st.button("Reset chat"):
        reset_chat()
        st.rerun()

    render_messages()

    audio_input = st.audio_input("Record your message", key=f"audio_input_{st.session_state.audio_input_key}")
    if audio_input is not None:
        audio_bytes = audio_input.getvalue()
        if not audio_bytes:
            st.warning("No audio was captured. Please record again.")
            st.stop()

        pcm_bytes = audio_to_pcm16_base64(audio_bytes)

        with st.spinner("Lǎoshī is responding..."):
            result = get_realtime_session().submit_audio(pcm_bytes)

        user_text = result.user_text or "Voice message"
        st.session_state.messages.append({"role": "user", "content": user_text})
        with st.chat_message("user"):
            st.markdown(user_text)

        assistant_text = result.assistant_text
        speech_bytes = None
        if result.error:
            assistant_text = f"(Realtime API error: {result.error})"
            stale_session = st.session_state.pop("realtime_session", None)
            if isinstance(stale_session, StreamlitRealtimeSession):
                stale_session.close()
        elif result.assistant_audio is not None:
            speech_bytes = pcm16_to_wav_bytes(result.assistant_audio)

        assistant_message = {"role": "assistant", "content": assistant_text}
        if speech_bytes is not None:
            assistant_message["audio_b64"] = base64.b64encode(speech_bytes).decode("utf-8")

        st.session_state.messages.append(assistant_message)
        with st.chat_message("assistant"):
            st.markdown(assistant_text)
            if speech_bytes is not None:
                st.audio(speech_bytes, format="audio/wav", autoplay=True)
            elif not result.error:
                st.caption("(Audio playback unavailable for this response)")

        st.session_state.audio_input_key += 1
        st.rerun()


if __name__ == "__main__":
    main()
