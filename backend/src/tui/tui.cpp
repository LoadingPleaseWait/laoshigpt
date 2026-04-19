#include "tui.hpp"

#include <iostream>
#include <string>
#include <limits>
#include <thread>
#include <chrono>

#ifdef PLATFORM_WINDOWS
  #include <conio.h>       // _getch(), kbhit()
  #include <windows.h>
#else
  #include <termios.h>
  #include <unistd.h>
  #include <sys/select.h>
#endif

// ---------------------------------------------------------------------------
// ANSI colour helpers (work on Windows 10+ with VT mode enabled)
// ---------------------------------------------------------------------------

static const char* RESET  = "\033[0m";
static const char* BOLD   = "\033[1m";
static const char* DIM    = "\033[2m";
static const char* RED    = "\033[31m";
static const char* GREEN  = "\033[32m";
static const char* YELLOW = "\033[33m";
static const char* CYAN   = "\033[36m";

// ---------------------------------------------------------------------------
// Platform: enable ANSI on Windows
// ---------------------------------------------------------------------------

static void enable_ansi_windows() {
#ifdef PLATFORM_WINDOWS
    HANDLE hOut = GetStdHandle(STD_OUTPUT_HANDLE);
    DWORD mode  = 0;
    GetConsoleMode(hOut, &mode);
    SetConsoleMode(hOut, mode | ENABLE_VIRTUAL_TERMINAL_PROCESSING);
#endif
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

void tui_init() {
    enable_ansi_windows();
    // TODO: optionally hide cursor:  std::cout << "\033[?25l";
}

void tui_shutdown() {
    // Restore cursor if hidden:   std::cout << "\033[?25h";
    std::cout << RESET;
}

void tui_clear() {
    std::cout << "\033[2J\033[H";
}

void tui_print_banner() {
    tui_clear();
    std::cout << BOLD << CYAN;
    std::cout << "================================================\n";
    std::cout << "   老师GPT  —  Mandarin Conversation Practice   \n";
    std::cout << "================================================\n";
    std::cout << RESET;
    std::cout << DIM << "  Push-to-talk Mandarin tutor | HSK vocabulary\n" << RESET;
    std::cout << "\n";
}

HskLevel tui_select_hsk_level() {
    std::cout << BOLD << "Select your HSK level:\n" << RESET;
    std::cout << "  [1] HSK 1  (~150 words)\n";
    std::cout << "  [2] HSK 2  (~300 words)\n";
    std::cout << "  [3] HSK 3  (~600 words)\n";
    std::cout << "\n> ";

    int choice = 3;
    std::cin >> choice;
    std::cin.ignore(std::numeric_limits<std::streamsize>::max(), '\n');

    switch (choice) {
        case 1:  return HskLevel::HSK1;
        case 2:  return HskLevel::HSK2;
        default: return HskLevel::HSK3;
    }
}

void tui_wait_for_ptt_start() {
    std::cout << "\n";
    std::cout << BOLD << YELLOW
              << "  [ SPACE ] Hold to speak   [ Q ] Quit\n"
              << RESET;
    std::cout << DIM << "  Waiting...\n" << RESET;

    // TODO: switch to raw/non-blocking terminal input so we can detect
    // key-hold vs key-press.  For now, any ENTER press starts recording.
    std::cout << "\n  Press ENTER to start recording > ";
    std::cin.get();

    std::cout << GREEN << "  Recording... (press ENTER to stop)\n" << RESET;
}

float tui_wait_for_ptt_release() {
    // TODO: real implementation should measure wall-clock time between
    // PTT key-down and key-up using non-blocking input.
    auto t0 = std::chrono::steady_clock::now();

    std::cin.get(); // wait for ENTER (simulating key release)

    auto t1  = std::chrono::steady_clock::now();
    float dt = std::chrono::duration<float>(t1 - t0).count();
    return dt;
}

void tui_print_response(const TutorResponse& resp) {
    std::cout << "\n";
    std::cout << BOLD << CYAN << "  老师:\n" << RESET;
    std::cout << "  " << BOLD << resp.reply_zh  << RESET << "\n";

    if (!resp.pinyin.empty())
        std::cout << DIM << "  " << resp.pinyin << RESET << "\n";

    if (!resp.reply_en.empty())
        std::cout << "  " << resp.reply_en << "\n";

    if (resp.had_correction) {
        std::cout << "\n";
        std::cout << YELLOW << "  Correction:\n" << RESET;
        std::cout << "    You said : " << RED   << resp.correction_original << RESET << "\n";
        std::cout << "    Better   : " << GREEN << resp.correction_fixed    << RESET << "\n";
        if (!resp.correction_reason.empty())
            std::cout << DIM << "    Reason   : " << resp.correction_reason << RESET << "\n";
    }

    if (!resp.next_prompt.empty()) {
        std::cout << "\n";
        std::cout << DIM << "  → " << resp.next_prompt << RESET << "\n";
    }

    std::cout << "\n";
}

void tui_print_status(const std::string& msg) {
    std::cout << DIM << "  " << msg << RESET << "\n";
}

void tui_print_error(const std::string& msg) {
    std::cout << RED << "  [error] " << msg << RESET << "\n";
}

bool tui_ask_continue() {
    std::cout << DIM << "  Continue? [y/n] > " << RESET;
    char c = 'y';
    std::cin >> c;
    std::cin.ignore(std::numeric_limits<std::streamsize>::max(), '\n');
    return (c == 'y' || c == 'Y');
}
