#include <iostream>
#include <string>
#include <cstdlib>

#include "tui/tui.hpp"
#include "audio/audio_capture.hpp"
#include "api/api_client.hpp"
#include "session/session.hpp"

// ---------------------------------------------------------------------------
// Configuration — override with env vars or a config file later
// ---------------------------------------------------------------------------

static const std::string DEFAULT_API_BASE = "http://localhost:8000";

static std::string get_env(const char* name, const std::string& fallback) {
    const char* val = std::getenv(name);
    return val ? std::string(val) : fallback;
}

// ---------------------------------------------------------------------------
// Main conversation loop
// ---------------------------------------------------------------------------

static void run_session(Session& session) {
    while (true) {
        // 1. Wait for user to initiate push-to-talk
        tui_wait_for_ptt_start();

        // 2. Capture audio until PTT released
        start_recording();
        float duration = tui_wait_for_ptt_release();

        AudioBuffer audio = stop_recording();

        if (audio.empty() || duration < 0.3f) {
            tui_print_status("Recording too short — try again.");
            continue;
        }

        tui_print_status("Sending to tutor...");

        // 3. Save audio to WAV for HTTP upload
        std::string wav_path = save_to_temp_wav(audio);
        if (wav_path.empty()) {
            tui_print_error("Failed to save audio. Try again.");
            continue;
        }

        // 4. Send to backend API and get structured tutor response
        TutorResponse resp = send_turn(
            wav_path,
            session.id,
            static_cast<int>(session.hsk_level)
        );

        if (!resp.ok) {
            tui_print_error("Tutor response failed: " + resp.error_message);
            if (!tui_ask_continue()) break;
            continue;
        }

        // 5. Display the tutor's response
        tui_print_response(resp);

        // 6. Play TTS audio if available
        if (!resp.tts_audio_path.empty()) {
            play_tts(resp.tts_audio_path);
        }

        // 7. Record the turn in session history
        Turn turn;
        turn.user_audio_path    = wav_path;
        turn.assistant_reply_zh = resp.reply_zh;
        turn.assistant_reply_en = resp.reply_en;
        turn.pinyin             = resp.pinyin;
        turn.had_correction     = resp.had_correction;
        add_turn(session, turn);

        // 8. Ask user if they want to keep going
        if (!tui_ask_continue()) break;
    }
}

// ---------------------------------------------------------------------------
// Entry point
// ---------------------------------------------------------------------------

int main() {
    // Read config from environment
    std::string api_base = get_env("LAOSHI_API_BASE", DEFAULT_API_BASE);
    std::string api_key  = get_env("LAOSHI_API_KEY",  "");

    // Initialise subsystems
    tui_init();
    tui_print_banner();

    if (!audio_init()) {
        tui_print_error("Failed to initialise audio backend. Exiting.");
        tui_shutdown();
        return 1;
    }

    if (!api_init(api_base, api_key)) {
        tui_print_error("Failed to initialise API client. Exiting.");
        audio_shutdown();
        tui_shutdown();
        return 1;
    }

    // Let user pick HSK level
    HskLevel level = tui_select_hsk_level();

    // Create session
    Session session = create_session(level);
    tui_print_status("Session started: " + session.id);
    std::cout << "\n";

    // Run the main loop
    run_session(session);

    // Print summary and clean up
    print_summary(session);

    audio_shutdown();
    tui_shutdown();

    return 0;
}
