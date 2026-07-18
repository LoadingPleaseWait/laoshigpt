"""Browser-friendly Streamlit app for Lǎoshī."""

from __future__ import annotations

import base64
import os
import time
import wave
from io import BytesIO

import streamlit as st
from streamlit_webrtc import WebRtcMode, webrtc_streamer

from src.audio_util import CHANNELS, SAMPLE_RATE, audio_to_pcm16_base64
from src.hands_free_audio import HandsFreeAudioBridge, pcm16_duration_seconds
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
    if "hands_free_bridge" not in st.session_state:
        st.session_state.hands_free_bridge = HandsFreeAudioBridge()
    if "hands_free_active" not in st.session_state:
        st.session_state.hands_free_active = False
    if "hands_free_resume_at" not in st.session_state:
        st.session_state.hands_free_resume_at = 0.0
    if "hands_free_webrtc_key" not in st.session_state:
        st.session_state.hands_free_webrtc_key = 0


def render_messages() -> None:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message["role"] == "assistant" and message.get("audio_b64"):
                st.audio(base64.b64decode(message["audio_b64"]), format="audio/wav", autoplay=True)
            elif message["role"] == "assistant" and message.get("audio_unavailable"):
                st.caption("(Audio playback unavailable for this response)")


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


def append_turn_result(result, *, hands_free: bool = False) -> None:
    user_text = result.user_text or "Voice message"
    st.session_state.messages.append({"role": "user", "content": user_text})

    assistant_text = result.assistant_text
    speech_bytes = None
    if result.error:
        assistant_text = f"(Realtime API error: {result.error})"
        stale_session = st.session_state.pop("realtime_session", None)
        if isinstance(stale_session, StreamlitRealtimeSession):
            stale_session.close()
        if hands_free:
            bridge = st.session_state.get("hands_free_bridge")
            if isinstance(bridge, HandsFreeAudioBridge):
                bridge.set_stopped(True)
            st.session_state.hands_free_active = False
            st.session_state.hands_free_webrtc_key += 1
            st.session_state.hands_free_resume_at = 0.0
    elif result.assistant_audio is not None:
        speech_bytes = pcm16_to_wav_bytes(result.assistant_audio)

    assistant_message = {"role": "assistant", "content": assistant_text}
    if speech_bytes is not None:
        assistant_message["audio_b64"] = base64.b64encode(speech_bytes).decode("utf-8")
        st.session_state.hands_free_resume_at = time.time() + pcm16_duration_seconds(result.assistant_audio) + 0.25
    elif not result.error:
        assistant_message["audio_unavailable"] = True

    st.session_state.messages.append(assistant_message)


def reset_chat() -> None:
    bridge = st.session_state.get("hands_free_bridge")
    if isinstance(bridge, HandsFreeAudioBridge):
        bridge.set_stopped(True)
    st.session_state.hands_free_active = False
    st.session_state.hands_free_resume_at = 0.0
    st.session_state.hands_free_webrtc_key += 1
    session = st.session_state.pop("realtime_session", None)
    if isinstance(session, StreamlitRealtimeSession):
        session.close()
    st.session_state.messages = []
    st.session_state.audio_input_key = 0
    init_state()


def render_hands_free_controls() -> None:
    st.subheader("Hands-Free")
    st.caption("Click START below to begin. Mic pauses while Laoshi speaks.")

    bridge = st.session_state.hands_free_bridge
    session = get_realtime_session()

    def audio_frame_callback(frame):
        bridge.push_frame(frame)
        return frame

    ctx = webrtc_streamer(
        key=f"laoshi_hands_free_{st.session_state.hands_free_webrtc_key}",
        mode=WebRtcMode.SENDONLY,
        audio_frame_callback=audio_frame_callback,
        media_stream_constraints={"video": False, "audio": True},
        async_processing=True,
    )

    active = bool(ctx.state.playing)
    st.session_state.hands_free_active = active
    bridge.set_stopped(not active)

    if active:
        session.start_streaming()
        if time.time() < st.session_state.hands_free_resume_at:
            st.caption("Assistant speaking")
        else:
            st.info("Listening")
    else:
        session.stop_streaming()
        st.caption("Stopped")

    last_message = st.session_state.messages[-1] if st.session_state.messages else None
    if (
        isinstance(last_message, dict)
        and last_message.get("role") == "assistant"
        and str(last_message.get("content", "")).startswith("(Realtime API error:")
    ):
        st.caption("Realtime API error")


@st.fragment(run_every="500ms")
def poll_hands_free_turns() -> None:
    if not st.session_state.get("hands_free_active"):
        return

    bridge = st.session_state.hands_free_bridge
    now = time.time()
    bridge.set_paused(now < st.session_state.hands_free_resume_at)

    session = get_realtime_session()
    for pcm_bytes in bridge.pop_pcm16_chunks():
        session.append_stream_audio(pcm_bytes)

    result = session.poll_stream_result()
    if result is not None:
        bridge.set_paused(True)
        append_turn_result(result, hands_free=True)
        st.rerun()


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
    render_hands_free_controls()
    poll_hands_free_turns()

    with st.expander("Manual recording fallback"):
        audio_input = st.audio_input("Record your message", key=f"audio_input_{st.session_state.audio_input_key}")
    if audio_input is not None:
        audio_bytes = audio_input.getvalue()
        if not audio_bytes:
            st.warning("No audio was captured. Please record again.")
            st.stop()

        pcm_bytes = audio_to_pcm16_base64(audio_bytes)

        with st.spinner("Lǎoshī is responding..."):
            result = get_realtime_session().submit_audio(pcm_bytes)

        append_turn_result(result)
        st.session_state.audio_input_key += 1
        st.rerun()


if __name__ == "__main__":
    main()
