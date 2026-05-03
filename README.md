# LaoshiGPT

AI-based Chinese tutoring app with two interfaces:

- **Web app (recommended):** Streamlit UI in your browser (`app.py`)
- **Terminal app (legacy/prototype):** Textual push-to-talk realtime app (`src/laoshi_prototype.py`)

---

## 1) Prerequisites

- Python **3.9+**
- An OpenAI API key

Set your API key in the shell before running either app:

```bash
export OPENAI_API_KEY="your_api_key_here"
```

---

## 2) Install dependencies

From the project root:

```bash
pip install -r requirements.txt
```

### System audio dependencies (for microphone/audio features)

#### macOS
```bash
brew install portaudio ffmpeg
```

#### Debian/Ubuntu Linux
```bash
sudo apt update
sudo apt install -y portaudio19-dev ffmpeg
```

---

## 3) Run the web app (Streamlit)

This is the main browser-based experience.

```bash
streamlit run app.py
```

Then open the URL shown by Streamlit (usually `http://localhost:8501`).

### Web app features

- Chat interface in browser
- Optional microphone input (`st.audio_input`) with transcription
- Assistant text response
- In-browser TTS playback of assistant responses

---

## 4) Run the terminal prototype (optional)

If you want the original Textual realtime push-to-talk interface:

```bash
python src/laoshi_prototype.py
```

Notes:
- Press **space** to toggle recording
- Press **q** to quit

---

## 5) Troubleshooting

- **`OPENAI_API_KEY is not set`**
  - Make sure you exported the variable in the same shell session.

- **No microphone/audio input**
  - Verify OS microphone permissions for your terminal/browser.
  - Confirm `portaudio` is installed.

- **TTS/audio playback unavailable**
  - The app will still return text if speech generation fails.

- **Dependency issues**
  - Re-run: `pip install -r requirements.txt`
