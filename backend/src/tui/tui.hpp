#pragma once

#include <string>
#include "session/session.hpp"
#include "api/api_client.hpp"

// Initialise terminal (hide cursor, configure raw input if needed)
void tui_init();

// Restore terminal to normal state
void tui_shutdown();

// Clear the screen
void tui_clear();

// Print the welcome banner and instructions
void tui_print_banner();

// Prompt the user to select an HSK level; returns the chosen level
HskLevel tui_select_hsk_level();

// Print the push-to-talk prompt and wait for SPACE to be held.
// Returns true while the key is held — caller loops until released.
// In practice: block until SPACE pressed (start), then return.
void tui_wait_for_ptt_start();

// Block until PTT key released; return duration held in seconds
float tui_wait_for_ptt_release();

// Display the tutor's response to the user
void tui_print_response(const TutorResponse& resp);

// Display a status / info message in a muted style
void tui_print_status(const std::string& msg);

// Display an error message
void tui_print_error(const std::string& msg);

// Ask the user if they want to continue; returns true = yes, false = quit
bool tui_ask_continue();
