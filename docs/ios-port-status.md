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


## Fixed-address memory audit (2026-11-06)

- The 4 GiB guest address window is defined by `PPC_MEM_BASE` in `runtime/include/ppc.h`. The current non-Android Apple value is `0x200000000000`; iOS therefore inherits the macOS address rather than an iOS-validated base.
- `runtime/src/core.cpp::mem::init()` enters the broad `__APPLE__` branch and calls `mach_vm_allocate(mach_task_self(), &addr, 0x100000000, VM_FLAGS_FIXED)`, then protects the first 64 KiB with `mprotect(PROT_NONE)`.
- This confirms the reservation mechanism and its fixed 4 GiB requirement, but not that iOS will accept the address under its process address-space layout or that the allocation behaves correctly on a non-jailbroken device. Do not replace it with an arbitrary address or `MAP_FIXED` fallback without an iOS SDK/device test.
- The generated PowerPC code is compiled into the native application; the guest-memory reservation is a separate requirement from executable JIT allocation. The current source audit has not yet established whether every runtime code-modification path is compatible with iOS code-signing and executable-memory restrictions.
- The next memory gate is a minimal iOS-targeted reservation probe using the same address, size, Mach VM flags, and null-page guard, followed by a real device run. The probe must fail cleanly and report the Mach error instead of crashing during startup.


## Guest-memory write tracking audit (2026-11-06)

- After reserving the 4 GiB guest window, `mem::init()` calls `wwatch::init()`. The write tracker allocates per-host-page metadata, installs SIGSEGV/SIGBUS handlers, and changes guest pages between read-only and read-write with `mprotect`.
- The tracker derives its page shift from `host::page_size()`, so it does not hard-code 4 KiB pages. This is useful for modern Apple devices, but the 16 KiB page-size path still needs an iOS compile/runtime test.
- Its signal handler calls the write-fault path, which invokes `mprotect` from signal context and chains unhandled faults to the previously installed handlers. The ordering and handler interaction must be verified on iOS; do not assume macOS behavior proves iOS behavior.
- The current startup order installs the main crash handler before guest-memory initialization, and the write tracker later saves/chains the prior SIGSEGV/SIGBUS handlers. This interaction is part of the iOS smoke-test gate.
- A minimal iOS probe should test: fixed 4 GiB reservation, null-page protection, one write-watch arm/fault/unprotect cycle, and correct forwarding of an unrelated SIGSEGV/SIGBUS. If any step is unsupported or unstable, the app must disable write tracking safely or use a separately validated fallback before a full game build.


## iOS Objective-C++ build-language fix (2026-11-06)

- The iOS Vulkan target includes `runtime/src/platform/native.mm` for Foundation autorelease-pool boundaries.
- CMake previously enabled Objective-C++ only for the macOS Metal renderer. The iOS Vulkan configuration could therefore reach an Objective-C++ source without enabling the OBJCXX language.
- The iOS platform branch now explicitly enables OBJCXX and sets its language standard to C++20. This removes that CMake language-configuration gap; it is not a substitute for an Xcode/iOS SDK compile.


## iOS touch routing and display-host audit (2026-11-06)

- `runtime/src/platform/touch_pad.cpp` and `touch_options.cpp` expose the on-screen virtual gamepad through Android JNI only. On iOS those translation units currently compile as no-op files.
- The Vulkan SDL host has a generic mouse/touch path, but the dedicated multi-finger SDL finger routing in `runtime/src/gfx/vulkan/backend.cpp` is guarded by `__ANDROID__`. It handles Android GamePad screen touch, view switching, touch-talk/mod gestures, and Android touch-to-mouse filtering. iOS does not currently get that routing.
- The Android virtual gamepad is not a ready-made iOS control surface: it depends on Java `TouchControls`, JNI callbacks, Android-specific visibility/options state, and Android-only event routing.
- The SDL Vulkan backend creates a TV window and, when dual-screen mode is enabled, a second GamePad window. iOS single-window/multi-window behavior and the intended one-screen layout have not been validated. An iOS host should explicitly choose a supported one-screen presentation and map UIKit/SDL finger events to the existing guest touch/gamepad APIs.
- Do not mark touchscreen play as supported until a device test covers simultaneous multi-touch, sticks/buttons, overlay interaction, finger cancellation, background/foreground transitions, and the GamePad touch surface.


## iOS keyboard-keycode header fix (2026-11-06)

- `runtime/src/platform/keycodes.h` previously selected Apple's Carbon header for every `__APPLE__` target.
- Carbon is a macOS desktop API and is not an iOS dependency. The header now uses Carbon only for Apple non-iOS builds; iOS uses the existing portable physical-keycode constants already provided for non-Apple hosts.
- This removes one known iOS SDK header-availability blocker for the SDL input source. It does not add touchscreen controls or establish that the full SDL input source compiles on iOS.

## Build-input and iOS feasibility gate (2026-11-06)

- The top-level CMake configure requires generated PowerPC sources matching `GEN_DIR` (default `build/gen`): at least one `code_*.c`, plus `table.c` and `imports.c`. A clean checkout without the user's own Wind Waker HD RPX/recompiler output cannot produce the gamecode target.
- The repository tree does not contain the default generated `build/gen/code_*.c` output. A GitHub Actions workflow cannot create a playable game binary from this source tree alone; it needs user-supplied, legally obtained game input and a reproducible generation step or a separately supplied generated-code artifact.
- The current iOS CMake target also builds the full project, including desktop-oriented test/tool targets later in the root CMake file. The iOS generator/build target selection must be checked so unrelated host test executables are not accidentally built for iPhoneOS.
- The runtime's `PPC_MEM_BASE` is 32 TiB on Apple targets, while the code requests an exact 4 GiB fixed Mach VM allocation. This remains a hard runtime gate on iOS, not something that can be solved safely by changing the address based on guesswork.
- Therefore no iOS IPA workflow has been added yet: a workflow that merely packages an empty app or skips the missing gamecode would create a misleading IPA artifact. The next legitimate build step requires a reproducible user-owned game-input handoff and an iOS-targeted compile/probe for Vulkan, fixed guest memory, and write tracking.



## MoltenVK CMake integration (2026-11-07)

- A pinned iOS-only MoltenVK package build completed successfully on GitHub Actions (run 42298575799). The package contains dynamic and static iOS XCFrameworks; the app integration uses the static XCFramework to avoid runtime framework embedding.
- Added `cmake/IOSDependencies.cmake`. It accepts the externally built static XCFramework and its public include directory, validates the iOS arm64 slice and Vulkan headers, and exposes an imported `Vulkan::Vulkan` target. No third-party framework binary or game data is committed.
- Updated the iOS CMake path to use this imported target instead of FindVulkan, and added the Metal/IOSurface system frameworks required by MoltenVK.
- Added the manually dispatched `iOS CMake Dependency Integration Probe` workflow on the default branch. It checks out this branch, rebuilds the pinned MoltenVK package, configures the iOS Xcode project with a temporary dummy gamecode fixture, and compiles dependency/shared-source targets only.
- This probe is not a game build and does not create an IPA. It is intended to expose CMake, SDK, dependency, and shared-source compile errors before attempting the full runtime build.
- Remaining gates: full runtime source compilation with the user's gamecode generated ephemerally in the same runner; SDL3 iOS Vulkan loader/surface behavior; touch controller UI; app lifecycle/audio; fixed 4 GiB guest-memory reservation and write tracking; JIT/code-signing compatibility; then actual iPhone device validation.
