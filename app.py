"""Browser-friendly Streamlit app for Lǎoshī."""

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

LAOSHI_INSTRUCTIONS = """You are an interactive Chinese language tutor. When the session starts,
in English, ask what the student's current level is, what the student's goals are, which Sinitic
language the student would like to practice, and whether the student would prefer that instructions
and explanations be given in English or in the target language. Obey the student's preferences. You
are tutoring a native US English speaker. You are helping your student practice conversing in the
target language. When speaking Chinese, you must speak slowly and only use HSK-3 vocabulary. When
speaking in Chinese, never use vocabulary outside of HSK-3 under any circumstances. Format your
responses so that they are concise. When transcribing Mandarin output, please use Traditional Chinese
characters and Hanyu Pinyin (unless the student requests otherwise). When transcribing Cantonese
output, please use Traditional Chinese characters and Jyutping (unless the student requests
otherwise). Don't ask the student to say the same phrase more than 3 times in a row, unless the
student's pronounciation is unintelligible or the student requests to continue practicing that
phrase. Here is the list of HSK-3 words in Traditional Chinese:
阿姨,啊,矮,愛,愛好,安靜,八,把,爸爸,吧,白,百,班,搬,辦法,辦公室,半,幫忙,幫助,包,飽,報紙,杯子,北方,北京,被,本,鼻子,比,比較,比賽,必須,變化,便宜,表示,表演,別,別人,賓館,冰箱,不,不客氣,才,菜,菜單,參加,艸,層,茶,差,唱歌,超市,襯衫,成绩,城市,吃,遲到,出,出現,出租車,除了,廚房,穿,舩,旾,詞語,次,聰明,从,錯,打電話,打籃球,打掃,打算,大,大家,帶,擔心,但是,蛋糕,當然,到,地,地方,地鐵,地圖,的,得,燈,低,弟弟,第一,點,電腦,電視,電梯,電影,電子,東,東西,鼕,懂,動物,都,讀,短,段,鍛鍊,對不起,多,多麼,多少,餓,兒子,而且,耳朵,二,發燒,發現,飯館,方便,房間,放,放心,飛機,非常,分,分鐘,服務員,附近,復習,敢,感冒,乾淨,剛才,高,高興,告訴,哥哥,個,給,根據,跟,更,工作,公共汽車,公斤,公司,公園,狗,故事,刮,關,關係,關心,關於,貴,國家,果汁,過去,還,還是,孩子,害怕,漢語,好,好吃,號,喝,和,河,黑,黑板,很,红,後面,護照,花,花園,畫,壞,環境,換,歡迎,黃,回,回答,會,會議,火車站,或者,機場,機會,雞蛋,極,几,幾乎,記得,季節,傢,檢查,簡單,見面,件,健康,講,角,腳,叫,教,教室,接,街道,節目,節日,結婚,結束,解決,介紹,借,姐姐,今天,近,進,經常,經過,經理,九,久,舊,就,舉行,句子,決定,覺得,咖啡,開,開始,看,看見,考試,可愛,可能,可以,渴,刻,客人,課,空調,口,哭,袴子,塊,快,快樂,筷子,來,藍,老,老師,了,了解,累,冷,離,離開,禮物,裏,歷史,臉,練習,兩,輛,鄰居,零,六,樓,路,旅遊,綠,媽媽,馬,馬上,嗎,買,賣,滿意,慢,忙,貓,帽子,沒,沒關係,每,妹妹,門,米,米飯,麵包,麵條,名字,明白,明天,拿,哪,那,奶奶,男人,南,難,難過,呢,能,你,年,年級,年輕,鳥,您,牛奶,努力,女兒,女人,爬山,盤子,旁邊,胖,跑步,朋友,啤酒,票,漂亮,蘋果,葡萄,普通話,七,妻子,其實,其他,奇怪,騎,起床,千,鉛筆,前面,錢,清楚,晴,請,秋,去,去年,裙子,然後,讓,熱,熱情,人,認識,認為,認真,日,容易,如果,三,傘,商店,上,上班,上網,上午,少,身體,什麼,生病,生氣,生日,聲音,十,時候,時間,使,世界,事情,是,手錶,手機,瘦,書,叔叔,舒服,樹,數學,刷,雙,誰,水,水果,水平,睡覺,說話,司機,四,送,雖然,嵗,所以,他,它,她,太,太陽,糖,特別,疼,踢,提高,題,體育,天氣,甜,條,跳舞,听,同事,同學,同意,頭髮,突然,圖書館,腿,外,完,完成,玩,晚上,㼝,万,忘記,為,為了,為什麼,位,喂,文化,問,問題,我,我們,五,希望,習慣,洗,洗手間,洗澡,喜歡,西,西瓜,下,下午,下雨,夏,先,先生,現在,相同,相信,香蕉,想,向,像,小,小姐,小時,小心,校長,笑,些,鞋,寫,謝謝,新,新聞,新鮮,信,星期,行李箱,興趣,姓,熊貓,休息,需要,選擇,學生,學習,學校,雪,顏色,眼鏡,眼睛,羊肉,葯,要,要求,也,爺爺,一,一般,一邊,一定,一共,一會兒,一起,一下,一樣,一直,衣服,醫生,醫院,已經,以後,以前,以為,椅子,意思,因為,陰,音樂,銀行,飲料,應該,影響,用,遊戲,游泳,有,有名,又,右邊,魚,遇到,元,遠,願意,月,月亮,越,云,運動,再,再見,在,早上,怎麼,怎麼樣,站,張,長,丈夫,找,照顧,照片,照相機,這,著,著急 ,真,正在,知道,只,中國,中間,中午,中文,終於,種,重要,週末,主要,住,注意,祝,準備,桌子,字,字典,自己,自行車,總是,走,嘴,最,最後,最近,昨天,左邊,作業,作用,坐,做.
Only use those words when speaking Chinese.
"""

FOLLOWUP_INSTRUCTIONS = """You are in an ongoing conversation.
Use the provided conversation history and continue naturally.
Do not re-introduce yourself or re-ask onboarding questions unless the user asks to restart.
"""


def init_state() -> None:
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "Hi! I’m Lǎoshī 👋 Please tell me what your current level is, what your goals are, which Sinitic language you would like to practice, and whether you would prefer instructions and explanations be given in English or in the target language.",
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
    has_user_history = any(message.get("role") == "user" for message in st.session_state.messages)

    if has_user_history:
        instructions = f"{LAOSHI_INSTRUCTIONS}\n\n{FOLLOWUP_INSTRUCTIONS}{history_context}"
    else:
        instructions = f"{LAOSHI_INSTRUCTIONS}{history_context}"

    async with rt_client.realtime.connect(model=MODEL_NAME) as connection:
        await connection.session.update(
            session={
                "instructions": instructions,
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
    st.set_page_config(page_title="Lǎoshī Web", page_icon="🧑‍🏫")
    st.title("🧑‍🏫 Lǎoshī (Streamlit)")
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
        user_text = "🎤 Voice message"
        st.session_state.messages.append({"role": "user", "content": user_text})
        with st.chat_message("user"):
            st.markdown(user_text)

        with st.spinner("Lǎoshī is responding..."):
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
