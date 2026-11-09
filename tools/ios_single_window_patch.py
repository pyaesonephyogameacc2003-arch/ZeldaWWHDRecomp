#!/usr/bin/env python3
"""iOS: one SDL window only — no GamePad window at init or on demand."""
from pathlib import Path
import sys


def main() -> None:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    path = root / "runtime/src/gfx/vulkan/backend.cpp"
    text = path.read_text()
    changed = False

    old_avail = (
        "bool gamepad_window_available() {\n"
        "#ifdef __ANDROID__\n"
        "  return false;\n"
        "#else\n"
        '  return !getenv("WWHD_NO_GAMEPAD");\n'
        "#endif\n"
        "}"
    )
    new_avail = (
        "bool gamepad_window_available() {\n"
        "#if defined(__ANDROID__) || defined(WWHD_IOS_STATIC_MOLTENVK)\n"
        "  return false;\n"
        "#else\n"
        '  return !getenv("WWHD_NO_GAMEPAD");\n'
        "#endif\n"
        "}"
    )
    if old_avail in text:
        text = text.replace(old_avail, new_avail, 1)
        changed = True
        print("gamepad_window_available ok")
    elif (
        "#if defined(__ANDROID__) || defined(WWHD_IOS_STATIC_MOLTENVK)\n  return false;"
        in text
    ):
        print("gamepad_window_available already patched")
    else:
        raise SystemExit("gamepad_window_available pattern missing")

    old_ensure = "SDL_Window* ensure_gamepad_window(bool create) {\n#if !defined(__ANDROID__)\n"
    new_ensure = (
        "SDL_Window* ensure_gamepad_window(bool create) {\n"
        "#if !defined(__ANDROID__) && !defined(WWHD_IOS_STATIC_MOLTENVK)\n"
    )
    if old_ensure in text:
        text = text.replace(old_ensure, new_ensure, 1)
        changed = True
        print("ensure_gamepad_window ok")
    elif "!defined(WWHD_IOS_STATIC_MOLTENVK)" in text:
        print("ensure_gamepad_window already patched")
    else:
        raise SystemExit("ensure_gamepad_window pattern missing")

    if changed:
        path.write_text(text)
    print("done")


if __name__ == "__main__":
    main()
