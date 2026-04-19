#pragma once

#include <string>
#include <vector>
#include <chrono>

// HSK levels supported by the tutor
enum class HskLevel {
    HSK1 = 1,
    HSK2 = 2,
    HSK3 = 3,
};

// A single conversation turn
struct Turn {
    std::string user_audio_path;   // path to recorded audio file (temp)
    std::string assistant_reply_zh;
    std::string assistant_reply_en; // correction / coaching note in English
    std::string pinyin;
    bool        had_correction = false;
};

// Active session state
struct Session {
    std::string              id;
    HskLevel                 hsk_level = HskLevel::HSK3;
    std::vector<Turn>        turns;
    std::chrono::system_clock::time_point started_at;

    int  turn_count() const { return static_cast<int>(turns.size()); }
    bool is_active()  const { return !id.empty(); }
};

// Create a new session with a generated ID
Session create_session(HskLevel level);

// Append a completed turn to the session
void add_turn(Session& session, Turn turn);

// Print a session summary to stdout
void print_summary(const Session& session);
