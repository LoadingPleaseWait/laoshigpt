#include "api_client.hpp"

#include <iostream>

// ---------------------------------------------------------------------------
// STUB IMPLEMENTATION
// Replace HTTP calls with libcurl or cpp-httplib when backend is ready.
//
// cpp-httplib (header-only):  https://github.com/yhirose/cpp-httplib
// libcurl:                    https://curl.se/libcurl/
// ---------------------------------------------------------------------------

static std::string g_base_url;
static std::string g_api_key;

bool api_init(const std::string& base_url, const std::string& api_key) {
    g_base_url = base_url;
    g_api_key  = api_key;
    std::cout << "[api] Client initialised — endpoint: " << base_url << "\n";
    return true;
}

TutorResponse send_turn(const std::string& audio_path,
                        const std::string& session_id,
                        int                hsk_level) {
    // TODO: POST multipart/form-data to g_base_url + "/v1/chat/turn"
    // Fields:
    //   session_id  = session_id
    //   hsk_level   = hsk_level
    //   audio       = @audio_path  (WAV file)
    //
    // Expected JSON response shape:
    // {
    //   "reply_zh":             "...",
    //   "reply_en":             "...",
    //   "pinyin":               "...",
    //   "correction_original":  "...",
    //   "correction_fixed":     "...",
    //   "correction_reason":    "...",
    //   "next_prompt":          "...",
    //   "tts_audio_url":        "..."
    // }

    std::cout << "[api] Sending turn to " << g_base_url << "/v1/chat/turn\n";
    std::cout << "[api]   session_id : " << session_id << "\n";
    std::cout << "[api]   hsk_level  : " << hsk_level  << "\n";
    std::cout << "[api]   audio_path : " << audio_path << "\n";

    // --- Stub response ---
    TutorResponse resp;
    resp.ok          = true;
    resp.reply_zh    = "你好！你今天怎么样？";
    resp.reply_en    = "(Stub) Hello! How are you today?";
    resp.pinyin      = "Nǐ hǎo! Nǐ jīntiān zěnmeyàng?";
    resp.next_prompt = "请告诉我你的名字。";
    resp.had_correction = false;
    return resp;
}

void play_tts(const std::string& audio_path) {
    if (audio_path.empty()) {
        std::cout << "[audio] No TTS audio to play.\n";
        return;
    }
    // TODO: use platform audio API to play the file
    //   Windows : PlaySound() / MCI
    //   macOS   : afplay (system call) or AudioToolbox
    //   Linux   : aplay / SDL2
    std::cout << "[audio] Playing TTS: " << audio_path << " (stub — no playback)\n";
}
