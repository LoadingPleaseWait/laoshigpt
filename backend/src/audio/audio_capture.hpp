#pragma once

#include <string>
#include <vector>
#include <cstdint>

// Raw PCM audio buffer: 16-bit signed samples, 16kHz mono
struct AudioBuffer {
    std::vector<int16_t> samples;
    int                  sample_rate = 16000;
    int                  channels    = 1;

    bool  empty()    const { return samples.empty(); }
    float duration() const {
        if (sample_rate == 0) return 0.f;
        return static_cast<float>(samples.size()) / static_cast<float>(sample_rate);
    }
};

// Push-to-talk interface
// Call start_recording() when user presses the PTT key.
// Call stop_recording()  when user releases it.
// The returned AudioBuffer contains everything captured between the two calls.

bool        audio_init();           // initialise audio backend (PortAudio etc.)
void        audio_shutdown();       // clean up

void        start_recording();      // begin capturing microphone input
AudioBuffer stop_recording();       // stop capturing; return buffered audio

// Save audio to a temporary WAV file and return the path.
// Useful when feeding audio to an HTTP endpoint instead of a streaming socket.
std::string save_to_temp_wav(const AudioBuffer& buf);
