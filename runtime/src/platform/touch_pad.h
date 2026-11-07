#pragma once
#include <SDL3/SDL.h>

// iOS virtual gamepad; no-op on other platforms.
namespace touch_pad {
bool enabled();
bool handle_event(const SDL_Event& event);
void draw_overlay();
void reset();
}
