# laoshigpt — TUI Backend (C++)

Terminal-based Mandarin conversation practice client.
Connects to the laoshigpt API backend over HTTP.

## Project Structure

    backend/
    ├── CMakeLists.txt
    ├── README.md
    └── src/
        ├── main.cpp               -- entry point, session loop
        ├── tui/
        │   ├── tui.hpp/cpp        -- terminal rendering, PTT prompts
        ├── audio/
        │   ├── audio_capture.hpp/cpp  -- mic capture, WAV output
        ├── api/
        │   ├── api_client.hpp/cpp -- HTTP calls to backend
        └── session/
            ├── session.hpp/cpp    -- session state, turn history

## Build

    mkdir build && cd build
    cmake ..
    cmake --build .
    ./bin/laoshigpt

## Environment Variables

    LAOSHI_API_BASE   Backend URL (default: http://localhost:8000)
    LAOSHI_API_KEY    API auth key (leave blank for local dev)

## Current Status (Stub)

All components are stubbed — the app will run and show the full UI flow
but audio capture returns silence and API calls return a hardcoded response.

Replace stubs in order:
1. audio/audio_capture.cpp  -- integrate PortAudio for real mic capture
2. api/api_client.cpp       -- integrate HTTP client (cpp-httplib or libcurl)
3. tui/tui.cpp              -- upgrade PTT to raw keypress (non-blocking input)
4. api/api_client.cpp       -- integrate TTS audio download + play_tts()

## Dependencies (not yet linked — see CMakeLists.txt)

- PortAudio       audio capture
- cpp-httplib     HTTP client (header-only, easy to drop in)
- libcurl         alternative HTTP client
