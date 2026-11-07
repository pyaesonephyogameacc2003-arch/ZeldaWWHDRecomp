// iOS has the SDL host but no AppKit menu bar. Keep the Vulkan renderer's
// desktop menu hook linkable while exposing graphics settings in the in-game UI.
#include <SDL3/SDL.h>

namespace gfxvk {
void install_graphics_menu(SDL_Window*) {}
}  // namespace gfxvk
