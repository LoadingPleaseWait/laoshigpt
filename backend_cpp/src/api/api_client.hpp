#pragma once

#include <string>
#include "session/session.hpp"
#include "audio/audio_capture.hpp"

// Response from one tutor turn
struct TutorResponse {
    std::string reply_zh;           // Mandarin reply
    std::string reply_en;           // English coaching note / correction
    std::string pinyin;
    std::string correction_original;
    std::string correction_fixed;
    std::string correction_reason;
    std::string next_prompt;        // AI's follow-up question / prompt
    std::string tts_audio_path;     // path to downloaded TTS audio file (if any)
    bool        had_correction = false;
    bool        ok             = false; // false means the request failed
    std::string error_message;
};

// Initialise the API client (base URL, auth token, etc.)
bool api_init(const std::string& base_url, const std::string& api_key);

// Send one push-to-talk turn to the backend and get a structured response.
// audio_path: path to WAV file captured from microphone
// session_id: current session ID for conversation continuity
// hsk_level:  HSK level as integer (1, 2, or 3)
TutorResponse send_turn(const std::string& audio_path,
                        const std::string& session_id,
                        int                hsk_level);

// Play back TTS audio received from the server.
// In stub mode this just prints a message.
void play_tts(const std::string& audio_path);
