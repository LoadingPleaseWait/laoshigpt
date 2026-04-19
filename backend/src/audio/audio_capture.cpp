#include "audio_capture.hpp"

#include <iostream>
#include <fstream>
#include <cstring>
#include <cstdio>

// ---------------------------------------------------------------------------
// STUB IMPLEMENTATION
// Replace with real PortAudio calls when integrating actual audio hardware.
//
// PortAudio reference: http://www.portaudio.com/
// Install: brew install portaudio  /  apt install libportaudio2  /  vcpkg install portaudio
// ---------------------------------------------------------------------------

bool audio_init() {
    // TODO: Pa_Initialize()
    std::cout << "[audio] Audio backend initialised (stub)\n";
    return true;
}

void audio_shutdown() {
    // TODO: Pa_Terminate()
    std::cout << "[audio] Audio backend shut down (stub)\n";
}

void start_recording() {
    // TODO: open PortAudio input stream, start capture to a ring buffer
    std::cout << "[audio] Recording started...\n";
}

AudioBuffer stop_recording() {
    // TODO: stop PortAudio stream, drain ring buffer into AudioBuffer
    std::cout << "[audio] Recording stopped.\n";

    // Return a dummy silent buffer so the rest of the pipeline can run
    AudioBuffer buf;
    buf.sample_rate = 16000;
    buf.channels    = 1;
    buf.samples.assign(16000, 0); // 1 second of silence
    return buf;
}

// ---------------------------------------------------------------------------
// WAV file helper
// Writes a minimal PCM WAV so audio can be sent to an HTTP endpoint.
// ---------------------------------------------------------------------------

static void write_wav_header(std::ofstream& f, int sample_rate,
                              int channels, int num_samples) {
    int byte_rate   = sample_rate * channels * 2; // 16-bit = 2 bytes
    int block_align = channels * 2;
    int data_size   = num_samples * channels * 2;
    int chunk_size  = 36 + data_size;

    auto write32 = [&](int v)  { f.write(reinterpret_cast<char*>(&v), 4); };
    auto write16 = [&](short v){ f.write(reinterpret_cast<char*>(&v), 2); };

    f.write("RIFF", 4);
    write32(chunk_size);
    f.write("WAVE", 4);
    f.write("fmt ", 4);
    write32(16);           // sub-chunk size
    write16(1);            // PCM format
    write16(channels);
    write32(sample_rate);
    write32(byte_rate);
    write16(block_align);
    write16(16);           // bits per sample
    f.write("data", 4);
    write32(data_size);
}

std::string save_to_temp_wav(const AudioBuffer& buf) {
    // TODO: use std::filesystem::temp_directory_path() in production
    std::string path = "laoshi_tmp_audio.wav";

    std::ofstream f(path, std::ios::binary);
    if (!f) {
        std::cerr << "[audio] Failed to open temp WAV file: " << path << "\n";
        return "";
    }

    write_wav_header(f, buf.sample_rate, buf.channels,
                     static_cast<int>(buf.samples.size()));
    f.write(reinterpret_cast<const char*>(buf.samples.data()),
            buf.samples.size() * sizeof(int16_t));

    std::cout << "[audio] Saved " << buf.duration() << "s audio to " << path << "\n";
    return path;
}
