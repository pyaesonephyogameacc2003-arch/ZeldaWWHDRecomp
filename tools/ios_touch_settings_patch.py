#!/usr/bin/env python3
"""iOS: Settings button on touch pad + accept finger events without window id."""
from pathlib import Path
import sys


def patch_touch_pad(root: Path) -> None:
    path = root / "runtime/src/platform/touch_pad.cpp"
    text = path.read_text()
    if "SET" in text and "overlay::set_open" in text:
        print("touch_pad already has Settings button")
        return

    old_inc = '''#if TARGET_OS_IOS
#include <imgui.h>
#include <algorithm>
#include <cmath>
#include <map>
#include <mutex>
#include "touch_pad.h"
'''
    new_inc = '''#if TARGET_OS_IOS
#include <imgui.h>
#include <algorithm>
#include <cmath>
#include <map>
#include <mutex>
#include "touch_pad.h"
#include "../overlay/overlay.h"
'''
    if old_inc not in text:
        raise SystemExit("touch_pad includes not found")
    text = text.replace(old_inc, new_inc, 1)

    old_down = '''    if(e.type==SDL_EVENT_FINGER_DOWN) {
        if(shown && e.tfinger.x<.13f && e.tfinger.y<.13f) {
            shown=false;
            for(auto& p:fingers) release(p.second);
            fingers.clear(); lx=ly=rx=ry=lt=rt=0; buttons=0; publish();
            return true;
        }
        if(!shown) { if(e.tfinger.x<.13f && e.tfinger.y<.13f) { shown=true; return true; } return false; }
'''
    new_down = '''    if(e.type==SDL_EVENT_FINGER_DOWN) {
        // Top-right: open/close Settings overlay (no Esc/Home on a phone).
        if(shown && e.tfinger.x>.86f && e.tfinger.y<.13f) {
            overlay::set_open(!overlay::is_open(), overlay::OpenReason::API);
            return true;
        }
        if(shown && e.tfinger.x<.13f && e.tfinger.y<.13f) {
            shown=false;
            for(auto& p:fingers) release(p.second);
            fingers.clear(); lx=ly=rx=ry=lt=rt=0; buttons=0; publish();
            return true;
        }
        if(!shown) { if(e.tfinger.x<.13f && e.tfinger.y<.13f) { shown=true; return true; } return false; }
'''
    if old_down not in text:
        raise SystemExit("finger down handler not found")
    text = text.replace(old_down, new_down, 1)

    old_draw = '''    circle(d,ImVec2(w*.43f,h*.92f),s*.045f,"−",buttons&(1u<<SDL_GAMEPAD_BUTTON_BACK));
    circle(d,ImVec2(w*.57f,h*.92f),s*.045f,"+",buttons&(1u<<SDL_GAMEPAD_BUTTON_START));
    circle(d,ImVec2(s*.07f,s*.07f),s*.035f,"×");
    d->AddText(ImVec2(w*.02f,h*.025f),IM_COL32(255,255,255,190),"WWHD TOUCH");
'''
    new_draw = '''    circle(d,ImVec2(w*.43f,h*.92f),s*.045f,"−",buttons&(1u<<SDL_GAMEPAD_BUTTON_BACK));
    circle(d,ImVec2(w*.57f,h*.92f),s*.045f,"+",buttons&(1u<<SDL_GAMEPAD_BUTTON_START));
    circle(d,ImVec2(s*.07f,s*.07f),s*.035f,"×");
    circle(d,ImVec2(w-s*.07f,s*.07f),s*.035f,"SET",overlay::is_open());
    d->AddText(ImVec2(w*.02f,h*.025f),IM_COL32(255,255,255,190),"WWHD TOUCH");
'''
    if old_draw not in text:
        raise SystemExit("draw_overlay footer not found")
    text = text.replace(old_draw, new_draw, 1)

    path.write_text(text)
    print("touch_pad Settings button ok")


def patch_backend(root: Path) -> None:
    path = root / "runtime/src/gfx/vulkan/backend.cpp"
    text = path.read_text()
    old = '''#if defined(__APPLE__)
  if ((event.type == SDL_EVENT_FINGER_DOWN || event.type == SDL_EVENT_FINGER_MOTION ||
       event.type == SDL_EVENT_FINGER_UP || event.type == SDL_EVENT_FINGER_CANCELED) &&
      event.tfinger.windowID == tvId && !overlay::captures() && touch_pad::handle_event(event)) return true;
#endif'''
    new = '''#if defined(__APPLE__)
  // iOS often reports windowID 0 for fingers; still route to the virtual pad.
  if ((event.type == SDL_EVENT_FINGER_DOWN || event.type == SDL_EVENT_FINGER_MOTION ||
       event.type == SDL_EVENT_FINGER_UP || event.type == SDL_EVENT_FINGER_CANCELED) &&
      (event.tfinger.windowID == tvId || event.tfinger.windowID == 0) &&
      !overlay::captures() && touch_pad::handle_event(event)) return true;
#endif'''
    if old not in text:
        if "event.tfinger.windowID == tvId || event.tfinger.windowID == 0" in text:
            print("backend finger routing already patched")
            return
        raise SystemExit("backend finger routing not found")
    path.write_text(text.replace(old, new, 1))
    print("backend finger routing ok")


def main() -> None:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    patch_touch_pad(root)
    patch_backend(root)


if __name__ == "__main__":
    main()
