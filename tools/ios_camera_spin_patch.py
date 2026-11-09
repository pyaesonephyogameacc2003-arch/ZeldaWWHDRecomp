#!/usr/bin/env python3
"""Fix iOS view spinning: stickier right-stick release + tighter stick hit zones."""
from pathlib import Path
import sys


def patch_backend(root: Path) -> None:
    path = root / "runtime/src/gfx/vulkan/backend.cpp"
    text = path.read_text()
    old = '''#if defined(__APPLE__)
  // iOS often reports windowID 0 for fingers; still route to the virtual pad.
  if ((event.type == SDL_EVENT_FINGER_DOWN || event.type == SDL_EVENT_FINGER_MOTION ||
       event.type == SDL_EVENT_FINGER_UP || event.type == SDL_EVENT_FINGER_CANCELED) &&
      (event.tfinger.windowID == tvId || event.tfinger.windowID == 0) &&
      !overlay::captures() && touch_pad::handle_event(event)) return true;
#endif'''
    new = '''#if defined(__APPLE__)
  // iOS often reports windowID 0 for fingers; still route to the virtual pad.
  // Finger UP/CANCEL must always reach the pad even if windowID mismatches, or the
  // right stick stays non-zero and the camera spins while Link stands still.
  if (event.type == SDL_EVENT_FINGER_DOWN || event.type == SDL_EVENT_FINGER_MOTION ||
      event.type == SDL_EVENT_FINGER_UP || event.type == SDL_EVENT_FINGER_CANCELED) {
    const bool idOk = event.tfinger.windowID == tvId || event.tfinger.windowID == 0 ||
                      event.type == SDL_EVENT_FINGER_UP || event.type == SDL_EVENT_FINGER_CANCELED;
    if (idOk && (event.type == SDL_EVENT_FINGER_UP || event.type == SDL_EVENT_FINGER_CANCELED ||
                 !overlay::captures()) &&
        touch_pad::handle_event(event)) return true;
  }
#endif'''
    if old not in text:
        if "Finger UP/CANCEL must always reach" in text:
            print("backend already patched")
            return
        raise SystemExit("backend finger block not found")
    path.write_text(text.replace(old, new, 1))
    print("backend finger up routing ok")


def patch_touch_pad(root: Path) -> None:
    path = root / "runtime/src/platform/touch_pad.cpp"
    text = path.read_text()
    if "tighter stick zones" in text:
        print("touch_pad stick zones already patched")
    else:
        old = '''        Finger f;
        const float x=e.tfinger.x,y=e.tfinger.y;
        if(x<.34f && y>.55f) f.owner=Owner::LeftStick;
        else if(x>.62f && y>.55f) f.owner=Owner::RightStick;
        else {
            f.owner=Owner::Button;
            if(y<.29f && x<.22f) f.code=100;
            else if(y<.29f && x>.78f) f.code=101;
            else f.code=button_at(x,y);
            if(f.code<0) f.owner=Owner::None;
            else if(f.code<SDL_GAMEPAD_BUTTON_COUNT) buttons|=1u<<f.code;
        }
'''
        new = '''        Finger f;
        const float x=e.tfinger.x,y=e.tfinger.y;
        // tighter stick zones (was whole corners) — loose right-stick grab made the camera spin
        auto near=[&](float cx,float cy,float r){float dx=x-cx,dy=y-cy;return dx*dx+dy*dy<=r*r;};
        if(near(.17f,.73f,.16f)) f.owner=Owner::LeftStick;
        else if(near(.78f,.73f,.15f)) f.owner=Owner::RightStick;
        else {
            f.owner=Owner::Button;
            if(y<.29f && x<.22f) f.code=100;
            else if(y<.29f && x>.78f) f.code=101;
            else f.code=button_at(x,y);
            if(f.code<0) f.owner=Owner::None;
            else if(f.code<SDL_GAMEPAD_BUTTON_COUNT) buttons|=1u<<f.code;
        }
'''
        if old not in text:
            raise SystemExit("stick assignment block not found")
        text = text.replace(old, new, 1)
        print("touch_pad tighter stick zones ok")

    # larger deadzone for camera stick
    old_dead = '''    const float dead=0.12f;
    float m=std::sqrt(dx*dx+dy*dy);
    if(m<dead) ox=oy=0;
    else { float scaled=(m-dead)/(1.0f-dead); ox=dx/m*scaled; oy=dy/m*scaled; }
'''
    new_dead = '''    // Higher deadzone reduces camera drift from imprecise thumb placement on glass.
    const float dead=0.20f;
    float m=std::sqrt(dx*dx+dy*dy);
    if(m<dead) ox=oy=0;
    else { float scaled=(m-dead)/(1.0f-dead); ox=dx/m*scaled; oy=dy/m*scaled; }
'''
    if "dead=0.20f" in text:
        print("deadzone already 0.20")
    elif old_dead not in text:
        raise SystemExit("deadzone block not found")
    else:
        text = text.replace(old_dead, new_dead, 1)
        print("stick deadzone ok")

    # reset sticks when opening settings
    old_set = '''        if(shown && e.tfinger.x>.86f && e.tfinger.y<.13f) {
            overlay::set_open(!overlay::is_open(), overlay::OpenReason::API);
            return true;
        }
'''
    new_set = '''        if(shown && e.tfinger.x>.86f && e.tfinger.y<.13f) {
            for(auto& p:fingers) release(p.second);
            fingers.clear(); lx=ly=rx=ry=lt=rt=0; buttons=0; publish();
            overlay::set_open(!overlay::is_open(), overlay::OpenReason::API);
            return true;
        }
'''
    if "for(auto& p:fingers) release(p.second);\n            fingers.clear(); lx=ly=rx=ry=lt=rt=0; buttons=0; publish();\n            overlay::set_open" in text:
        print("settings clear already present")
    elif old_set not in text:
        print("settings block skipped (pattern missing)")
    else:
        text = text.replace(old_set, new_set, 1)
        print("settings clears sticks ok")

    path.write_text(text)
    print("touch_pad done")


def main() -> None:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    patch_backend(root)
    patch_touch_pad(root)


if __name__ == "__main__":
    main()
