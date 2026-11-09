#!/usr/bin/env python3
"""Match Android Settings UI on iOS: mobile_ui phone layout + screen DPI."""
from pathlib import Path
import sys


def patch_overlay(root: Path) -> None:
    path = root / "runtime/src/overlay/overlay.cpp"
    text = path.read_text()
    old = '''#ifdef __ANDROID__
    static const bool loadedUiSize = [] {
        std::string saved;
        if (hostui::get("uiSize", saved)) g_ui_size = std::clamp(atoi(saved.c_str()), 0, 3);
        return true;
    }();
    (void)loadedUiSize;
    // phones get a more compact layout than tablets and handhelds (mobile_ui.h); a UI size the player chose decides
    const mobile_ui::Layout ui = mobile_ui::layout(g_android_dpi, g_density, g_ui_size, float(pw), float(ph));
    mobile_ui::apply_touch_style(ImGui::GetStyle(), ui);
    const float scale = ui.scale;
#else
    const float scale = mobile_ui::desktop_scale(g_density.load(), float(ph));
#endif'''
    new = '''#if defined(__ANDROID__) || defined(WWHD_IOS_STATIC_MOLTENVK)
    static const bool loadedUiSize = [] {
        std::string saved;
        if (hostui::get("uiSize", saved)) g_ui_size = std::clamp(atoi(saved.c_str()), 0, 3);
        return true;
    }();
    (void)loadedUiSize;
    // phones get a more compact layout than tablets and handhelds (mobile_ui.h); a UI size the player chose decides
    // iOS uses the same phone/tablet rules as Android so Settings matches the Android app.
    const mobile_ui::Layout ui = mobile_ui::layout(g_android_dpi, g_density, g_ui_size, float(pw), float(ph));
    mobile_ui::apply_touch_style(ImGui::GetStyle(), ui);
    const float scale = ui.scale;
#else
    const float scale = mobile_ui::desktop_scale(g_density.load(), float(ph));
#endif'''
    if old not in text:
        if "WWHD_IOS_STATIC_MOLTENVK" in text and "mobile_ui::layout(g_android_dpi" in text:
            print("overlay mobile_ui already patched")
            return
        raise SystemExit("overlay mobile_ui block not found")
    path.write_text(text.replace(old, new, 1))
    print("overlay mobile_ui for iOS ok")


def patch_backend_dpi(root: Path) -> None:
    path = root / "runtime/src/gfx/vulkan/backend.cpp"
    text = path.read_text()
    if "set_android_screen_dpi" in text and "WWHD_IOS_STATIC_MOLTENVK" in text and "UIScreen" in text:
        print("backend iOS dpi already patched")
        return
    # After TV window create + density set, inject iOS DPI from native scale (~163/326).
    needle = "overlay::set_density(SDL_GetWindowPixelDensity(R.tv.window));"
    if needle not in text:
        # try alternate
        if "set_density(SDL_GetWindowPixelDensity" not in text:
            raise SystemExit("set_density window call not found")
    # Find the exact line in init
    old = '''    overlay::set_density(SDL_GetWindowPixelDensity(R.tv.window));'''
    # may appear multiple times - only in init path. Check count
    if text.count(old) == 0:
        old2 = "  overlay::set_density(SDL_GetWindowPixelDensity(R.tv.window));"
        if old2 in text:
            old = old2
        else:
            raise SystemExit("set_density exact line not found")
    new = old + '''
#if defined(WWHD_IOS_STATIC_MOLTENVK)
  // Same physical DPI path as Android: mobile_ui phone layout needs inches, not points.
  // iPhone logical DPI is ~163 * nativeScale (2x/3x).
  {
    float dpi = 163.0f * SDL_GetWindowDisplayScale(R.tv.window);
    if (dpi < 120.0f) dpi = 163.0f * SDL_GetWindowPixelDensity(R.tv.window);
    if (dpi < 120.0f) dpi = 326.0f;
    overlay::set_android_screen_dpi(dpi);
    LOG("[display] iOS settings DPI %.0f (Android-style mobile_ui)", dpi);
  }
#endif'''
    # Only replace first occurrence in init (first in file is usually load path)
    # Prefer the one near CreateWindow TV
    idx = text.find("R.tv.window = SDL_CreateWindow")
    if idx < 0:
        raise SystemExit("TV CreateWindow not found")
    dens = text.find(old.strip() if False else "overlay::set_density(SDL_GetWindowPixelDensity(R.tv.window))", idx)
    if dens < 0:
        dens = text.find("overlay::set_density(SDL_GetWindowPixelDensity(R.tv.window))", 0)
    if dens < 0:
        raise SystemExit("set_density after window not found")
    # get full line
    line_start = text.rfind("\n", 0, dens) + 1
    line_end = text.find("\n", dens)
    line = text[line_start:line_end]
    if "set_density" not in line:
        raise SystemExit("bad density line")
    insert = line + '''
#if defined(WWHD_IOS_STATIC_MOLTENVK)
  // Same physical DPI path as Android: mobile_ui phone layout needs inches, not points.
  {
    float dpi = 163.0f * SDL_GetWindowDisplayScale(R.tv.window);
    if (dpi < 120.0f) dpi = 163.0f * SDL_GetWindowPixelDensity(R.tv.window);
    if (dpi < 120.0f) dpi = 326.0f;
    overlay::set_android_screen_dpi(dpi);
    LOG("[display] iOS settings DPI %.0f (Android-style mobile_ui)", dpi);
  }
#endif'''
    text = text[:line_start] + insert + text[line_end:]
    path.write_text(text)
    print("backend iOS DPI ok")


def patch_touch_hide_when_settings(root: Path) -> None:
    path = root / "runtime/src/platform/touch_pad.cpp"
    text = path.read_text()
    if "if(overlay::is_open()) return;" in text and "draw_overlay" in text:
        # ensure draw_overlay early-outs when settings open (Android settingsOpen)
        pass
    old = '''void draw_overlay() {
    std::lock_guard<std::mutex> lock(mu);
    ImGuiIO& io=ImGui::GetIO();
'''
    new = '''void draw_overlay() {
    std::lock_guard<std::mutex> lock(mu);
    // Android TouchControls hides the pad while Settings is open.
    if (overlay::is_open()) return;
    ImGuiIO& io=ImGui::GetIO();
'''
    if "if (overlay::is_open()) return;" in text:
        print("touch_pad hide-on-settings already present")
        return
    if old not in text:
        raise SystemExit("draw_overlay start not found")
    path.write_text(text.replace(old, new, 1))
    print("touch_pad hide when settings ok")


def main() -> None:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    patch_overlay(root)
    patch_backend_dpi(root)
    patch_touch_hide_when_settings(root)


if __name__ == "__main__":
    main()
