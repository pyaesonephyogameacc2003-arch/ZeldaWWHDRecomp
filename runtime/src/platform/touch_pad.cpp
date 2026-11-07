// Android on-screen controls (android/.../TouchControls.java): the buttons and sticks drawn over the
// game are a virtual SDL gamepad, so the game reads them like any controller (input_sdl.cpp opens
// it on SDL_EVENT_GAMEPAD_ADDED). The gamepad exists while the controls are shown.
#ifdef __ANDROID__
#include <SDL3/SDL.h>
#include <jni.h>
#include <mutex>
#include "../runtime.h"
#include "touch_face.h"
#include "touch_options.h"
#include "../mods/mods.h"
#include "phone_rumble.h"
#include "../gfx/display_modes.h"
#include "../overlay/hostui.h"
#include "../overlay/overlay.h"

namespace {
std::mutex g_mu;
SDL_JoystickID g_id = 0;
SDL_Joystick* g_pad = nullptr;

bool attach() {
    if (g_pad) return true;
    if (!SDL_WasInit(SDL_INIT_JOYSTICK)) return false;  // before input::init: try on the next touch
    SDL_VirtualJoystickDesc desc;
    SDL_INIT_INTERFACE(&desc);
    desc.type = SDL_JOYSTICK_TYPE_GAMEPAD;
    desc.naxes = SDL_GAMEPAD_AXIS_COUNT;
    desc.nbuttons = SDL_GAMEPAD_BUTTON_COUNT;
    desc.name = "Touch controls";
    g_id = SDL_AttachVirtualJoystick(&desc);
    if (!g_id) { LOG("[input] touch controls: %s", SDL_GetError()); return false; }
    g_pad = SDL_OpenJoystick(g_id);
    if (!g_pad) { SDL_DetachVirtualJoystick(g_id); g_id = 0; return false; }
    LOG("[input] touch controls on");
    return true;
}
}  // namespace

// buttons: bit n is SDL_GamepadButton n, except the face buttons; face: bit 0..3 = the drawn A, B,
// X, Y (touch_face.h presses the pad buttons the mapping binds to them); sticks -1..1 (y down),
// triggers 0..1
extern "C" JNIEXPORT void JNICALL Java_org_wwhdrecomp_wwhd_TouchControls_nativeSetPad(
    JNIEnv*, jclass, jint buttons, jint face, jfloat lx, jfloat ly, jfloat rx, jfloat ry, jfloat lt, jfloat rt) {
    std::lock_guard<std::mutex> lk(g_mu);
    if (!attach()) return;
    if (buttons || face || lx || ly || rx || ry || lt || rt) phone_rumble::last_input_touch = true;
    auto axis = [](float v) { return (Sint16)SDL_clamp(v * 32767.0f, -32768.0f, 32767.0f); };
    SDL_SetJoystickVirtualAxis(g_pad, SDL_GAMEPAD_AXIS_LEFTX, axis(lx));
    SDL_SetJoystickVirtualAxis(g_pad, SDL_GAMEPAD_AXIS_LEFTY, axis(ly));
    SDL_SetJoystickVirtualAxis(g_pad, SDL_GAMEPAD_AXIS_RIGHTX, axis(rx));
    SDL_SetJoystickVirtualAxis(g_pad, SDL_GAMEPAD_AXIS_RIGHTY, axis(ry));
    SDL_SetJoystickVirtualAxis(g_pad, SDL_GAMEPAD_AXIS_LEFT_TRIGGER, axis(lt));
    SDL_SetJoystickVirtualAxis(g_pad, SDL_GAMEPAD_AXIS_RIGHT_TRIGGER, axis(rt));
    const uint32_t pressed = uint32_t(buttons) | touch_face::buttons(uint32_t(face), input_map::current());
    for (int b = 0; b < SDL_GAMEPAD_BUTTON_COUNT && b < 31; b++)
        SDL_SetJoystickVirtualButton(g_pad, b, (pressed >> b) & 1);
}

// the controls were hidden: the gamepad goes away (a physical controller is the only one again)
extern "C" JNIEXPORT void JNICALL Java_org_wwhdrecomp_wwhd_TouchControls_nativeDetachPad(JNIEnv*, jclass) {
    std::lock_guard<std::mutex> lk(g_mu);
    phone_rumble::last_input_touch = false;
    if (!g_pad) return;
    SDL_CloseJoystick(g_pad);
    SDL_DetachVirtualJoystick(g_id);
    g_pad = nullptr;
    g_id = 0;
    LOG("[input] touch controls off");
}
#endif

#ifdef __ANDROID__
extern "C" JNIEXPORT jint JNICALL Java_org_wwhdrecomp_wwhd_TouchControls_nativeTouchState(JNIEnv*, jclass) {
    return (gfx::touch_buttons_visible() ? 1 : 0) | (gfx::g_touch_controls ? 2 : 0) | (overlay::captures() ? 4 : 0);
}
extern "C" JNIEXPORT void JNICALL Java_org_wwhdrecomp_wwhd_TouchControls_nativeRevealButtons(JNIEnv*, jclass) {
    gfx::reveal_touch_buttons();
}
extern "C" JNIEXPORT void JNICALL Java_org_wwhdrecomp_wwhd_TouchControls_nativeShowControls(JNIEnv*, jclass, jboolean shown) {
    gfx::g_touch_controls = shown;
    hostui::set("touchControls", shown ? "1" : "0");
}
#endif

#ifdef __ANDROID__
extern "C" JNIEXPORT void JNICALL Java_org_wwhdrecomp_wwhd_TouchControls_nativeScreenDpi(JNIEnv*, jclass, jfloat dpi) {
    overlay::set_android_screen_dpi(dpi);
}
#endif

#ifdef __ANDROID__
extern "C" JNIEXPORT void JNICALL Java_org_wwhdrecomp_wwhd_TouchControls_nativeControllerConnected(JNIEnv*, jclass, jboolean connected) {
    gfx::g_touch_controller = connected;
}
#endif

#ifdef __ANDROID__
// TouchControls.nativeTouchOptions(int[] out): the touch options as touch_style.h pack() lays them out;
// returns the layout's version
extern "C" JNIEXPORT jint JNICALL Java_org_wwhdrecomp_wwhd_TouchControls_nativeTouchOptions(JNIEnv* env, jclass, jintArray out) {
    int32_t v[touch_style::kPackLen];
    touch_style::pack(touch_options::get(), v, touch_style::kPackLen);
    if (out) {
        const jsize n = env->GetArrayLength(out);
        env->SetIntArrayRegion(out, 0, n < touch_style::kPackLen ? n : touch_style::kPackLen, reinterpret_cast<const jint*>(v));
    }
    return touch_style::kPackVersion;
}
// TouchControls.nativeFreeTouch (a finger on no control: touch_style::Free) is in gfx/vulkan/backend.cpp,
// next to the finger routing whose GamePad-touch areas it must agree with.
// the swipe camera: the finger moved by (dx, dy) pixels on a display of dpi
extern "C" JNIEXPORT void JNICALL Java_org_wwhdrecomp_wwhd_TouchControls_nativeSwipe(JNIEnv*, jclass, jfloat dx, jfloat dy, jfloat dpi) {
    phone_rumble::last_input_touch = true;
    mods::swipe_add(dx, dy, dpi);
}
#endif


// iOS on-screen virtual controller. SDL finger events are tracked independently so both sticks
// and action buttons can be held at the same time. The overlay is drawn by the existing ImGui
// renderer; no UIKit window or second rendering surface is required.
#if defined(__APPLE__)
#include <TargetConditionals.h>
#if TARGET_OS_IOS
#include <imgui.h>
#include <algorithm>
#include <cmath>
#include <map>
#include <mutex>
#include "touch_pad.h"

namespace touch_pad {
namespace {
enum class Owner { None, LeftStick, RightStick, Button };
struct Finger { Owner owner=Owner::None; int code=-1; float x=0, y=0; };
std::mutex mu;
std::map<SDL_FingerID,Finger> fingers;
SDL_JoystickID joystick_id=0;
SDL_Joystick* joystick=nullptr;
bool shown=true;
float lx=0,ly=0,rx=0,ry=0,lt=0,rt=0;
uint32_t buttons=0;

bool attach() {
    if (joystick) return true;
    if (!SDL_WasInit(SDL_INIT_JOYSTICK)) return false;
    SDL_VirtualJoystickDesc desc;
    SDL_INIT_INTERFACE(&desc);
    desc.type=SDL_JOYSTICK_TYPE_GAMEPAD;
    desc.naxes=SDL_GAMEPAD_AXIS_COUNT;
    desc.nbuttons=SDL_GAMEPAD_BUTTON_COUNT;
    desc.name="Wind Waker Touch";
    joystick_id=SDL_AttachVirtualJoystick(&desc);
    if (!joystick_id) { SDL_Log("[touch] virtual gamepad attach failed: %s",SDL_GetError()); return false; }
    joystick=SDL_OpenJoystick(joystick_id);
    if (!joystick) { SDL_DetachVirtualJoystick(joystick_id); joystick_id=0; return false; }
    SDL_Log("[touch] iOS virtual gamepad attached");
    return true;
}
Sint16 axis(float v) { return Sint16(std::clamp(v,-1.0f,1.0f)*32767.0f); }
void publish() {
    if (!attach()) return;
    SDL_SetJoystickVirtualAxis(joystick,SDL_GAMEPAD_AXIS_LEFTX,axis(lx));
    SDL_SetJoystickVirtualAxis(joystick,SDL_GAMEPAD_AXIS_LEFTY,axis(ly));
    SDL_SetJoystickVirtualAxis(joystick,SDL_GAMEPAD_AXIS_RIGHTX,axis(rx));
    SDL_SetJoystickVirtualAxis(joystick,SDL_GAMEPAD_AXIS_RIGHTY,axis(ry));
    SDL_SetJoystickVirtualAxis(joystick,SDL_GAMEPAD_AXIS_LEFT_TRIGGER,axis(lt));
    SDL_SetJoystickVirtualAxis(joystick,SDL_GAMEPAD_AXIS_RIGHT_TRIGGER,axis(rt));
    for (int i=0;i<SDL_GAMEPAD_BUTTON_COUNT;i++)
        SDL_SetJoystickVirtualButton(joystick,i,(buttons>>i)&1u);
}
void release(Finger& f) {
    if (f.owner==Owner::Button && f.code>=0) buttons &= ~(1u<<f.code);
    if (f.owner==Owner::LeftStick) lx=ly=0;
    if (f.owner==Owner::RightStick) rx=ry=0;
    if (f.code==100) lt=0;
    if (f.code==101) rt=0;
}
void stick(float x,float y,float cx,float cy,float radius,float& ox,float& oy) {
    float dx=(x-cx)/radius,dy=(y-cy)/radius;
    float d=std::sqrt(dx*dx+dy*dy);
    if(d>1.0f){dx/=d;dy/=d;}
    const float dead=0.12f;
    float m=std::sqrt(dx*dx+dy*dy);
    if(m<dead) ox=oy=0;
    else { float scaled=(m-dead)/(1.0f-dead); ox=dx/m*scaled; oy=dy/m*scaled; }
}
int button_at(float x,float y) {
    auto near=[&](float cx,float cy,float r){float dx=x-cx,dy=y-cy;return dx*dx+dy*dy<=r*r;};
    if(near(.91f,.44f,.052f)) return SDL_GAMEPAD_BUTTON_SOUTH; // A
    if(near(.84f,.51f,.052f)) return SDL_GAMEPAD_BUTTON_EAST;  // B
    if(near(.84f,.37f,.052f)) return SDL_GAMEPAD_BUTTON_WEST;  // X
    if(near(.77f,.44f,.052f)) return SDL_GAMEPAD_BUTTON_NORTH; // Y
    if(near(.14f,.38f,.04f)) return SDL_GAMEPAD_BUTTON_DPAD_UP;
    if(near(.14f,.53f,.04f)) return SDL_GAMEPAD_BUTTON_DPAD_DOWN;
    if(near(.07f,.455f,.04f)) return SDL_GAMEPAD_BUTTON_DPAD_LEFT;
    if(near(.21f,.455f,.04f)) return SDL_GAMEPAD_BUTTON_DPAD_RIGHT;
    if(near(.32f,.15f,.05f)) return SDL_GAMEPAD_BUTTON_LEFT_SHOULDER;
    if(near(.68f,.15f,.05f)) return SDL_GAMEPAD_BUTTON_RIGHT_SHOULDER;
    if(near(.43f,.92f,.045f)) return SDL_GAMEPAD_BUTTON_BACK;
    if(near(.57f,.92f,.045f)) return SDL_GAMEPAD_BUTTON_START;
    return -1;
}
void update(Finger& f,float x,float y) {
    f.x=x; f.y=y;
    if(f.owner==Owner::LeftStick) stick(x,y,.17f,.73f,.145f,lx,ly);
    else if(f.owner==Owner::RightStick) stick(x,y,.78f,.73f,.13f,rx,ry);
    else if(f.owner==Owner::Button) {
        // Trigger zones are analog; all other controls are digital.
        if(f.code==100) lt=std::clamp((.28f-y)/.16f,0.0f,1.0f);
        else if(f.code==101) rt=std::clamp((.28f-y)/.16f,0.0f,1.0f);
    }
}
void circle(ImDrawList* d,ImVec2 c,float r,const char* label,bool active=false) {
    const ImU32 fill=active?IM_COL32(90,190,235,170):IM_COL32(25,35,48,115);
    d->AddCircleFilled(c,r,fill,32);
    d->AddCircle(c,r,IM_COL32(235,245,255,170),32,2.0f);
    ImVec2 sz=ImGui::CalcTextSize(label);
    d->AddText(ImVec2(c.x-sz.x*.5f,c.y-sz.y*.5f),IM_COL32(255,255,255,235),label);
}
} // namespace

bool handle_event(const SDL_Event& e) {
    if(e.type!=SDL_EVENT_FINGER_DOWN && e.type!=SDL_EVENT_FINGER_MOTION &&
       e.type!=SDL_EVENT_FINGER_UP && e.type!=SDL_EVENT_FINGER_CANCELED) return false;
    std::lock_guard<std::mutex> lock(mu);
    if(e.type==SDL_EVENT_FINGER_DOWN) {
        if(!shown) { if(e.tfinger.x<.13f && e.tfinger.y<.13f) shown=true; return true; }
        Finger f;
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
        fingers[e.tfinger.fingerID]=f;
        update(fingers[e.tfinger.fingerID],x,y);
        publish();
        return f.owner!=Owner::None;
    }
    auto it=fingers.find(e.tfinger.fingerID);
    if(it==fingers.end()) return false;
    if(e.type==SDL_EVENT_FINGER_MOTION) update(it->second,e.tfinger.x,e.tfinger.y);
    else { release(it->second); fingers.erase(it); }
    publish();
    return true;
}
void reset() {
    std::lock_guard<std::mutex> lock(mu);
    for(auto& p:fingers) release(p.second);
    fingers.clear(); lx=ly=rx=ry=lt=rt=0; buttons=0; publish();
}
void draw_overlay() {
    std::lock_guard<std::mutex> lock(mu);
    ImGuiIO& io=ImGui::GetIO();
    ImDrawList* d=ImGui::GetForegroundDrawList();
    const float w=io.DisplaySize.x,h=io.DisplaySize.y,s=std::min(w,h);
    if(!shown) { circle(d,ImVec2(s*.07f,s*.07f),s*.035f,"PAD"); return; }
    circle(d,ImVec2(w*.17f,h*.73f),s*.145f,"L",lx!=0||ly!=0);
    circle(d,ImVec2(w*.78f,h*.73f),s*.13f,"R",rx!=0||ry!=0);
    circle(d,ImVec2(w*.91f,h*.44f),s*.052f,"A",buttons&(1u<<SDL_GAMEPAD_BUTTON_SOUTH));
    circle(d,ImVec2(w*.84f,h*.51f),s*.052f,"B",buttons&(1u<<SDL_GAMEPAD_BUTTON_EAST));
    circle(d,ImVec2(w*.84f,h*.37f),s*.052f,"X",buttons&(1u<<SDL_GAMEPAD_BUTTON_WEST));
    circle(d,ImVec2(w*.77f,h*.44f),s*.052f,"Y",buttons&(1u<<SDL_GAMEPAD_BUTTON_NORTH));
    circle(d,ImVec2(w*.14f,h*.38f),s*.04f,"▲",buttons&(1u<<SDL_GAMEPAD_BUTTON_DPAD_UP));
    circle(d,ImVec2(w*.14f,h*.53f),s*.04f,"▼",buttons&(1u<<SDL_GAMEPAD_BUTTON_DPAD_DOWN));
    circle(d,ImVec2(w*.07f,h*.455f),s*.04f,"◀",buttons&(1u<<SDL_GAMEPAD_BUTTON_DPAD_LEFT));
    circle(d,ImVec2(w*.21f,h*.455f),s*.04f,"▶",buttons&(1u<<SDL_GAMEPAD_BUTTON_DPAD_RIGHT));
    circle(d,ImVec2(w*.32f,h*.15f),s*.05f,"L",buttons&(1u<<SDL_GAMEPAD_BUTTON_LEFT_SHOULDER));
    circle(d,ImVec2(w*.68f,h*.15f),s*.05f,"R",buttons&(1u<<SDL_GAMEPAD_BUTTON_RIGHT_SHOULDER));
    circle(d,ImVec2(w*.14f,h*.15f),s*.05f,"ZL",lt>0);
    circle(d,ImVec2(w*.86f,h*.15f),s*.05f,"ZR",rt>0);
    circle(d,ImVec2(w*.43f,h*.92f),s*.045f,"−",buttons&(1u<<SDL_GAMEPAD_BUTTON_BACK));
    circle(d,ImVec2(w*.57f,h*.92f),s*.045f,"+",buttons&(1u<<SDL_GAMEPAD_BUTTON_START));
    d->AddText(ImVec2(w*.02f,h*.025f),IM_COL32(255,255,255,190),"WWHD TOUCH");
}
} // namespace touch_pad
#endif
#endif
