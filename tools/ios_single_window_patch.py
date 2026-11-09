#!/usr/bin/env python3
"""iOS: do not create a second SDL GamePad window (one window per display)."""
from pathlib import Path
import sys


def main() -> None:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    path = root / "runtime/src/gfx/vulkan/backend.cpp"
    text = path.read_text()
    if "WWHD_IOS_STATIC_MOLTENVK" in text and "one window per display" in text:
        print("already patched")
        return

    old_flags = """#ifdef __ANDROID__
  SDL_AddEventWatch(lifecycle_watch, nullptr);
  const SDL_WindowFlags windowFlags = SDL_WINDOW_VULKAN | SDL_WINDOW_FULLSCREEN;
#else
"""
    new_flags = """#ifdef __ANDROID__
  SDL_AddEventWatch(lifecycle_watch, nullptr);
  const SDL_WindowFlags windowFlags = SDL_WINDOW_VULKAN | SDL_WINDOW_FULLSCREEN;
#elif defined(WWHD_IOS_STATIC_MOLTENVK)
  const SDL_WindowFlags windowFlags = SDL_WINDOW_VULKAN | SDL_WINDOW_FULLSCREEN |
                                      SDL_WINDOW_HIGH_PIXEL_DENSITY;
#else
"""
    if old_flags not in text:
        raise SystemExit("windowFlags block not found")
    text = text.replace(old_flags, new_flags, 1)

    old_drc = """#ifdef __ANDROID__
  quest_theater::initialize();
  // one surface: the GamePad picture is drawn into it (display_modes.h: picture-in-picture, GamePad
  // only), never a window of its own
#else
  if (!getenv("WWHD_NO_GAMEPAD") && (!overlay::window_target::gamescope_session() ||
      ::hostui::startup_drc_mode() == gfx::kDrcWindow)) {
"""
    new_drc = """#if defined(__ANDROID__) || defined(WWHD_IOS_STATIC_MOLTENVK)
#ifdef __ANDROID__
  quest_theater::initialize();
#endif
  // one surface: the GamePad picture is drawn into the TV window (display_modes.h).
  // iOS allows only one window per display (SDL: "Only one window allowed per display").
#else
  if (!getenv("WWHD_NO_GAMEPAD") && (!overlay::window_target::gamescope_session() ||
      ::hostui::startup_drc_mode() == gfx::kDrcWindow)) {
"""
    if old_drc not in text:
        raise SystemExit("GamePad window block not found")
    text = text.replace(old_drc, new_drc, 1)

    path.write_text(text)
    print("iOS single-window patch ok")


if __name__ == "__main__":
    main()
