# iOS port investigation

Status: early platform groundwork; this branch does not yet contain an iOS app or a working IPA build.

## Implemented groundwork

- Top-level CMake now detects `CMAKE_SYSTEM_NAME=iOS` separately from macOS.
- iOS defaults to the Vulkan renderer path and SDL host rather than the AppKit-backed Metal host.
- The macOS-only AppKit Vulkan menu is excluded from iOS builds, and the SDL host link list no longer links AppKit on iOS.
- Added an initial iOS `MACOSX_BUNDLE` target, iOS bundle identifier/deployment settings, a landscape-only `ios/Info.plist.in`, and the SDL3 platform entry-point header in `main.cpp`.
- The SDL host's input implementation is currently desktop-oriented: its key mapping uses macOS virtual-key constants, and the shared event handler has no native iOS touch-to-gamepad mapping. Existing Android touch controls are separate Android-specific code and are not automatically available on iOS.
- The Vulkan path requires an iOS-compatible Vulkan loader and MoltenVK build; the existing release helper packages macOS dylibs, not iOS frameworks.
- The bundled SDL3 dependency configuration now selects a static SDL3 library for iOS app targets instead of requesting a standalone shared SDL library; desktop and installer settings remain on their existing paths.
- These changes only establish build-system and app-bundle scaffolding. They are not proof that SDL3 + MoltenVK, the app lifecycle, or the runtime can build or run on iOS.

## Target

- iPhone 15 (A16), iOS arm64.
- Keep the existing in-game Graphics Settings and FPS Settings unchanged.
- Do not change the default renderer, resolution, frame pacing, or game-side settings as part of the initial host port.
- Build and package an unsigned IPA with a macOS GitHub Actions runner after the iOS host compiles.

## Confirmed blockers in the current source

1. The top-level CMake configuration treats Apple as macOS. The default Apple renderer is `BOTH`, and the Metal path is explicitly described as macOS-only.
2. The Metal host sources are collected with `runtime/src/gfx/*.mm`. The display implementation `runtime/src/gfx/display.mm` imports AppKit and uses NSWindow/NSView/NSApp APIs. Those APIs do not exist on iOS.
3. The Metal link list includes AppKit, Carbon, and desktop audio frameworks. This must be split into macOS and iOS framework sets.
4. The current SDL host is selected only for Vulkan-only builds. It is not currently an iOS app target or a tested iOS lifecycle/presentation integration.
5. The runtime also contains desktop-oriented controls, menus, file dialogs, and window assumptions that need auditing before an iOS app can launch reliably.

## Port sequence

1. Verify the iOS CMake toolchain and dependency build (SDL3, Vulkan headers/loader, MoltenVK, glslang, zlib, and LZ4) on a macOS runner.
2. Add an iOS-specific SDL input path: map touch gestures to the existing gamepad state, preserve external controller support, and handle background/foreground events. Do not reuse Android Java touch code.
3. Build and package an iOS-compatible Vulkan loader + MoltenVK framework (the existing macOS packaging script is not reusable as-is), then verify SDL3's iOS Vulkan surface creation.
4. Add app lifecycle pause/resume, iOS audio-session handling, and sandbox document import for the user's own legally obtained game dump.
5. Audit fixed-address guest-memory reservations and executable-memory/JIT assumptions on iOS. This is a critical feasibility gate; do not assume an IPA can run merely because it links.
6. Add an ARM64 Xcode build and unsigned IPA packaging only after the renderer, input, memory and JIT gates pass.
7. Build on GitHub Actions, fix compiler/linker errors, and only call it device-ready after installation and runtime testing on an iPhone.

## Guardrails

- Do not add a placeholder workflow that produces an IPA-shaped but nonfunctional app.
- Do not modify the existing graphics/FPS settings or silently change their defaults.
- Do not include Nintendo game data, keys, or copyrighted assets in the repository or build artifacts. The user supplies their own game files.
- Keep all experiments on this branch until the iOS build and host are validated.


## Additional source audit (2026-11-06)

- `cmake/WindowsDependencies.cmake` previously forced SDL3 shared-library mode for the SDL host. iOS application targets now select SDL3 static mode, so SDL is linked into the app bundle; non-iOS desktop and installer behavior is unchanged.
- `runtime/src/platform/input_sdl.cpp` still maps SDL keyboard scancodes through macOS `kVK_*` constants and has no iOS touch UI implementation. This is not a build-only issue: without a touch-to-gamepad layer, a phone user cannot reliably play using the screen.
- `runtime/src/platform/native.mm` only supplies an Objective-C autorelease-pool wrapper using Foundation; it does not provide an iOS Vulkan surface or solve MoltenVK packaging.
- `runtime/src/platform/host.h` uses Apple Mach-O executable symbols, Apple thread QoS, and Apple memory-residency APIs under the broad `__APPLE__` condition. These APIs need an iOS SDK compile check; their presence in an Apple build is not proof of iOS runtime compatibility.
- The Vulkan CMake branch on Apple links `Vulkan::Vulkan` and glslang directly for the SDL host. An iOS toolchain still needs an iOS-built Vulkan loader/MoltenVK package and a valid CMake package config; the current repository dependency script does not produce that framework.
- Guest-memory mapping and executable-memory/JIT behavior remain unverified. No claim is made that the runtime can execute on a non-jailbroken iPhone until those checks and an actual device test pass.

- The SDL touch-controller bridge in `runtime/src/platform/touch_pad.cpp` and its Java view `android/.../TouchControls.java` are guarded by `__ANDROID__`; iOS currently has no equivalent on-screen controller. SDL touch-as-mouse events alone do not reproduce the Android virtual gamepad, context buttons, sticks, and touch gestures.
- The editor MCP localhost server is desktop tooling and is now excluded from iOS runtime sources; its CMake option defaults OFF for iOS while retaining the existing ON default on other platforms.
- This is a source-level change only. It does not establish that an iOS SDK compile, IPA package, or device launch succeeds.
