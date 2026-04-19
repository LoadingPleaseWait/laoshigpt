#include "session.hpp"

#include <iostream>
#include <sstream>
#include <iomanip>
#include <random>

// -- Helpers ------------------------------------------------------------------

static std::string generate_id() {
    std::mt19937 rng(std::random_device{}());
    std::uniform_int_distribution<int> dist(0, 15);
    const char* hex = "0123456789abcdef";
    std::string id = "sess_";
    for (int i = 0; i < 8; ++i) id += hex[dist(rng)];
    return id;
}

static std::string hsk_label(HskLevel level) {
    switch (level) {
        case HskLevel::HSK1: return "HSK1";
        case HskLevel::HSK2: return "HSK2";
        case HskLevel::HSK3: return "HSK3";
    }
    return "Unknown";
}

// -- Public API ---------------------------------------------------------------

Session create_session(HskLevel level) {
    Session s;
    s.id         = generate_id();
    s.hsk_level  = level;
    s.started_at = std::chrono::system_clock::now();
    return s;
}

void add_turn(Session& session, Turn turn) {
    session.turns.push_back(std::move(turn));
}

void print_summary(const Session& session) {
    std::cout << "\n";
    std::cout << "========================================\n";
    std::cout << "  Session Summary\n";
    std::cout << "========================================\n";
    std::cout << "  ID        : " << session.id << "\n";
    std::cout << "  Level     : " << hsk_label(session.hsk_level) << "\n";
    std::cout << "  Turns     : " << session.turn_count() << "\n";

    int corrections = 0;
    for (const auto& t : session.turns) {
        if (t.had_correction) ++corrections;
    }
    std::cout << "  Corrections : " << corrections << "\n";
    std::cout << "========================================\n\n";
}
