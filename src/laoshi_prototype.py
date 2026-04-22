#!/usr/bin/env uv run
####################################################################
# TUI app with a push to talk interface to the Realtime API        #
# If you have `uv` installed and the `OPENAI_API_KEY`              #
# environment variable set, you can run this example with just     #
#                                                                  #
# `./src/laoshi_prototype.py`                                      #
#                                                                  #
# On Mac, you'll also need `brew install portaudio ffmpeg`         #
####################################################################
#
# /// script
# requires-python = ">=3.9"
# dependencies = [
#     "textual",
#     "numpy",
#     "pyaudio",
#     "pydub",
#     "sounddevice",
#     "openai[realtime]",
# ]
#
# [tool.uv.sources]
# openai = { path = "../../", editable = true }
# ///

# This is based on a file from OpenAI but it has been modified

from __future__ import annotations

import base64
import asyncio
from typing import Any, cast
from typing_extensions import override

from textual import events
from audio_util import CHANNELS, SAMPLE_RATE, AudioPlayerAsync
from textual.app import App, ComposeResult
from textual.widgets import Button, Static, RichLog
from textual.reactive import reactive
from textual.containers import Container

from openai import AsyncOpenAI
from openai.types.realtime.session_update_event_param import Session # this line was edited
from openai.resources.realtime.realtime import AsyncRealtimeConnection


class SessionDisplay(Static):
    """A widget that shows the current session ID."""

    session_id = reactive("")

    @override
    def render(self) -> str:
        return f"Session ID: {self.session_id}" if self.session_id else "Connecting..."


class AudioStatusIndicator(Static):
    """A widget that shows the current audio recording status."""

    is_recording = reactive(False)

    @override
    def render(self) -> str:
        status = (
            "🔴 Recording... (Press K to stop)" if self.is_recording else "⚪ Press K to start recording (Q to quit)"
        )
        return status


class RealtimeApp(App[None]):
    CSS = """
        Screen {
            background: #1a1b26;  /* Dark blue-grey background */
        }

        Container {
            border: double rgb(91, 164, 91);
        }

        Horizontal {
            width: 100%;
        }

        #input-container {
            height: 5;  /* Explicit height for input container */
            margin: 1 1;
            padding: 1 2;
        }

        Input {
            width: 80%;
            height: 3;  /* Explicit height for input */
        }

        Button {
            width: 20%;
            height: 3;  /* Explicit height for button */
        }

        #bottom-pane {
            width: 100%;
            height: 82%;  /* Reduced to make room for session display */
            border: round rgb(205, 133, 63);
            content-align: center middle;
        }

        #status-indicator {
            height: 3;
            content-align: center middle;
            background: #2a2b36;
            border: solid rgb(91, 164, 91);
            margin: 1 1;
        }

        #session-display {
            height: 3;
            content-align: center middle;
            background: #2a2b36;
            border: solid rgb(91, 164, 91);
            margin: 1 1;
        }

        Static {
            color: white;
        }
    """

    client: AsyncOpenAI
    should_send_audio: asyncio.Event
    audio_player: AudioPlayerAsync
    last_audio_item_id: str | None
    connection: AsyncRealtimeConnection | None
    session: Session | None
    connected: asyncio.Event

    def __init__(self) -> None:
        super().__init__()
        self.connection = None
        self.session = None
        self.client = AsyncOpenAI()
        self.audio_player = AudioPlayerAsync()
        self.last_audio_item_id = None
        self.should_send_audio = asyncio.Event()
        self.connected = asyncio.Event()

    @override
    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        with Container():
            yield SessionDisplay(id="session-display")
            yield AudioStatusIndicator(id="status-indicator")
            yield RichLog(id="bottom-pane", wrap=True, highlight=True, markup=True)

    async def on_mount(self) -> None:
        self.run_worker(self.handle_realtime_connection())
        self.run_worker(self.send_mic_audio())

    async def handle_realtime_connection(self) -> None:
        async with self.client.realtime.connect(model="gpt-realtime") as conn:
            self.connection = conn
            self.connected.set()

            # note: this is the default and can be omitted
            # if you want to manually handle VAD yourself, then set `'turn_detection': None`
            await conn.session.update(
                session={
                    "audio": {
                        "input": {"turn_detection": {"type": "server_vad"}},
                    },
                    "model": "gpt-realtime",
                    "type": "realtime",
                    "instructions": "You are a Mandarin Chinese language tutor with over 10 years of experience. \
        You are tutoring a native US English speaker. You are helping your student practice conversing in Mandarin Chinese. \
        When speaking Mandarin Chinese, you must speak slowly and only use HSK-3 vocabulary. Never use vocabulary outside of HSK-3 \
        under any circumstances. Format your responses so that they are concise. For Chinese text output, please use \
        Traditional Chinese. Here is the list of HSK-3 words in Traditional Chinese: 阿姨,啊,矮,愛,愛好,安靜,八,把,爸爸,吧,白,百,班,搬,辦法,辦公室,半,幫忙,幫助,包,飽,報紙,杯子,北方,北京,被,本,鼻子,比,比較,比賽,必須,變化,便宜,表示,表演,別,別人,賓館,冰箱,不,不客氣,才,菜,菜單,參加,艸,層,茶,差,唱歌,超市,襯衫,成绩,城市,吃,遲到,出,出現,出租車,除了,廚房,穿,舩,旾,詞語,次,聰明,从,錯,打電話,打籃球,打掃,打算,大,大家,帶,擔心,但是,蛋糕,當然,到,地,地方,地鐵,地圖,的,得,燈,低,弟弟,第一,點,電腦,電視,電梯,電影,電子,東,東西,鼕,懂,動物,都,讀,短,段,鍛鍊,對不起,多,多麼,多少,餓,兒子,而且,耳朵,二,發燒,發現,飯館,方便,房間,放,放心,飛機,非常,分,分鐘,服務員,附近,復習,敢,感冒,乾淨,剛才,高,高興,告訴,哥哥,個,給,根據,跟,更,工作,公共汽車,公斤,公司,公園,狗,故事,刮,關,關係,關心,關於,貴,國家,果汁,過去,還,還是,孩子,害怕,漢語,好,好吃,號,喝,和,河,黑,黑板,很,红,後面,護照,花,花園,畫,壞,環境,換,歡迎,黃,回,回答,會,會議,火車站,或者,機場,機會,雞蛋,極,几,幾乎,記得,季節,傢,檢查,簡單,見面,件,健康,講,角,腳,叫,教,教室,接,街道,節目,節日,結婚,結束,解決,介紹,借,姐姐,今天,近,進,經常,經過,經理,九,久,舊,就,舉行,句子,決定,覺得,咖啡,開,開始,看,看見,考試,可愛,可能,可以,渴,刻,客人,課,空調,口,哭,袴子,塊,快,快樂,筷子,來,藍,老,老師,了,了解,累,冷,離,離開,禮物,裏,歷史,臉,練習,兩,輛,鄰居,零,六,樓,路,旅遊,綠,媽媽,馬,馬上,嗎,買,賣,滿意,慢,忙,貓,帽子,沒,沒關係,每,妹妹,門,米,米飯,麵包,麵條,名字,明白,明天,拿,哪,那,奶奶,男人,南,難,難過,呢,能,你,年,年級,年輕,鳥,您,牛奶,努力,女兒,女人,爬山,盤子,旁邊,胖,跑步,朋友,啤酒,票,漂亮,蘋果,葡萄,普通話,七,妻子,其實,其他,奇怪,騎,起床,千,鉛筆,前面,錢,清楚,晴,請,秋,去,去年,裙子,然後,讓,熱,熱情,人,認識,認為,認真,日,容易,如果,三,傘,商店,上,上班,上網,上午,少,身體,什麼,生病,生氣,生日,聲音,十,時候,時間,使,世界,事情,是,手錶,手機,瘦,書,叔叔,舒服,樹,數學,刷,雙,誰,水,水果,水平,睡覺,說話,司機,四,送,雖然,嵗,所以,他,它,她,太,太陽,糖,特別,疼,踢,提高,題,體育,天氣,甜,條,跳舞,听,同事,同學,同意,頭髮,突然,圖書館,腿,外,完,完成,玩,晚上,㼝,万,忘記,為,為了,為什麼,位,喂,文化,問,問題,我,我們,五,希望,習慣,洗,洗手間,洗澡,喜歡,西,西瓜,下,下午,下雨,夏,先,先生,現在,相同,相信,香蕉,想,向,像,小,小姐,小時,小心,校長,笑,些,鞋,寫,謝謝,新,新聞,新鮮,信,星期,行李箱,興趣,姓,熊貓,休息,需要,選擇,學生,學習,學校,雪,顏色,眼鏡,眼睛,羊肉,葯,要,要求,也,爺爺,一,一般,一邊,一定,一共,一會兒,一起,一下,一樣,一直,衣服,醫生,醫院,已經,以後,以前,以為,椅子,意思,因為,陰,音樂,銀行,飲料,應該,影響,用,遊戲,游泳,有,有名,又,右邊,魚,遇到,元,遠,願意,月,月亮,越,云,運動,再,再見,在,早上,怎麼,怎麼樣,站,張,長,丈夫,找,照顧,照片,照相機,這,著,著急 ,真,正在,知道,只,中國,中間,中午,中文,終於,種,重要,週末,主要,住,注意,祝,準備,桌子,字,字典,自己,自行車,總是,走,嘴,最,最後,最近,昨天,左邊,作業,作用,坐,做 \
        Only use those words when speaking Chinese."
                }
            )

            acc_items: dict[str, Any] = {}

            async for event in conn:
                if event.type == "session.created":
                    self.session = event.session
                    session_display = self.query_one(SessionDisplay)
                    assert event.session.id is not None
                    session_display.session_id = event.session.id
                    continue

                if event.type == "session.updated":
                    self.session = event.session
                    continue

                if event.type == "response.output_audio.delta":
                    if event.item_id != self.last_audio_item_id:
                        self.audio_player.reset_frame_count()
                        self.last_audio_item_id = event.item_id

                    bytes_data = base64.b64decode(event.delta)
                    self.audio_player.add_data(bytes_data)
                    continue

                if event.type == "response.output_audio_transcript.delta":
                    try:
                        text = acc_items[event.item_id]
                    except KeyError:
                        acc_items[event.item_id] = event.delta
                    else:
                        acc_items[event.item_id] = text + event.delta

                    # Clear and update the entire content because RichLog otherwise treats each delta as a new line
                    bottom_pane = self.query_one("#bottom-pane", RichLog)
                    bottom_pane.clear()
                    bottom_pane.write(acc_items[event.item_id])
                    continue

    async def _get_connection(self) -> AsyncRealtimeConnection:
        await self.connected.wait()
        assert self.connection is not None
        return self.connection

    async def send_mic_audio(self) -> None:
        import sounddevice as sd  # type: ignore

        sent_audio = False

        device_info = sd.query_devices()
        print(device_info)

        read_size = int(SAMPLE_RATE * 0.02)

        stream = sd.InputStream(
            channels=CHANNELS,
            samplerate=SAMPLE_RATE,
            dtype="int16",
        )
        stream.start()

        status_indicator = self.query_one(AudioStatusIndicator)

        try:
            while True:
                if stream.read_available < read_size:
                    await asyncio.sleep(0)
                    continue

                await self.should_send_audio.wait()
                status_indicator.is_recording = True

                data, _ = stream.read(read_size)

                connection = await self._get_connection()
                if not sent_audio:
                    asyncio.create_task(connection.send({"type": "response.cancel"}))
                    sent_audio = True

                await connection.input_audio_buffer.append(audio=base64.b64encode(cast(Any, data)).decode("utf-8"))

                await asyncio.sleep(0)
        except KeyboardInterrupt:
            pass
        finally:
            stream.stop()
            stream.close()

    async def on_key(self, event: events.Key) -> None:
        """Handle key press events."""
        if event.key == "enter":
            self.query_one(Button).press()
            return

        if event.key == "q":
            self.exit()
            return

        if event.key == "k":
            status_indicator = self.query_one(AudioStatusIndicator)
            if status_indicator.is_recording:
                self.should_send_audio.clear()
                status_indicator.is_recording = False

                if self.session and self.session.turn_detection is None:
                    # The default in the API is that the model will automatically detect when the user has
                    # stopped talking and then start responding itself.
                    #
                    # However if we're in manual `turn_detection` mode then we need to
                    # manually tell the model to commit the audio buffer and start responding.
                    conn = await self._get_connection()
                    await conn.input_audio_buffer.commit()
                    await conn.response.create()
            else:
                self.should_send_audio.set()
                status_indicator.is_recording = True


if __name__ == "__main__":
    app = RealtimeApp()
    app.run()
