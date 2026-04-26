LaoShiGPT
---------

An AI-based language learning app.

## Dependencies
On Mac, you'll also need `brew install portaudio ffmpeg`

On Linux, you'll need to install portaudio. On Debian-based distributions, you can achieve that with `sudo apt install portaudio19-dev`

Make sure you install the pip packages mentioned at the top of src/laoshi_prototype.py with:

`pip3 install textual numpy pyaudio pydub sounddevice openai[realtime]`

## Running
After setting and exporting `OPENAI_API_KEY`, you can run the app with:
`python3 src/laoshi_prototype.py`
