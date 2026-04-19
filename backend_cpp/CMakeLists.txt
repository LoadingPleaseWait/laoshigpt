cmake_minimum_required(VERSION 3.20)
project(laoshigpt VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Output binaries to build/bin
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin)

# Source files
set(SOURCES
    src/main.cpp
    src/tui/tui.cpp
    src/audio/audio_capture.cpp
    src/api/api_client.cpp
    src/session/session.cpp
)

add_executable(laoshigpt ${SOURCES})

target_include_directories(laoshigpt PRIVATE src)

# TODO: link PortAudio for real audio capture
# find_package(portaudio REQUIRED)
# target_link_libraries(laoshigpt PRIVATE portaudio)

# TODO: link an HTTP client library (e.g. libcurl or cpp-httplib) for API calls
# target_link_libraries(laoshigpt PRIVATE curl)

# Platform-specific terminal handling
if(WIN32)
    # Windows console API available by default
    target_compile_definitions(laoshigpt PRIVATE PLATFORM_WINDOWS)
else()
    # Link ncurses on Linux/macOS for terminal control
    # find_package(Curses REQUIRED)
    # target_link_libraries(laoshigpt PRIVATE ${CURSES_LIBRARIES})
    target_compile_definitions(laoshigpt PRIVATE PLATFORM_UNIX)
endif()

message(STATUS "laoshigpt TUI configured (C++20, stub mode)")
