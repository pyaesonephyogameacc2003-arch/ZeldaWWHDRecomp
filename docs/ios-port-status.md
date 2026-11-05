# iOS port investigation

Status: early platform groundwork; this branch does not yet contain an iOS app or a working IPA build.

## Implemented groundwork

- Top-level CMake now detects `CMAKE_SYSTEM_NAME=iOS` separately from macOS.
- iOS defaults to the Vulkan renderer path and SDL host rather than the AppKit-backed Metal host.
- The macOS-only AppKit Vulkan menu is excluded from iOS builds, and the SDL host link list no longer links AppKit on iOS.
- These changes only select a plausible host/backend combination. They are not proof that SDL3 + MoltenVK, the app lifecycle, or the runtime can build or run on iOS.

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
2. Implement and verify the SDL3 iOS presentation host, UIKit lifecycle integration, and SDL iOS entry point; the current runtime still assumes a desktop-style executable in several places.
3. Add touch/controller input, app lifecycle pause/resume, iOS audio-session handling, and sandbox document import for the user's own legally obtained game dump.
4. Audit fixed-address guest-memory reservations and executable-memory/JIT assumptions on iOS. This is a critical feasibility gate; do not assume an IPA can run merely because it links.
5. Add an iOS application bundle target, Info.plist, ARM64 Xcode build, and unsigned IPA packaging workflow.
6. Build on GitHub Actions, fix compiler/linker errors, and only call it device-ready after installation and runtime testing on an iPhone.

## Guardrails

- Do not add a placeholder workflow that produces an IPA-shaped but nonfunctional app.
- Do not modify the existing graphics/FPS settings or silently change their defaults.
- Do not include Nintendo game data, keys, or copyrighted assets in the repository or build artifacts. The user supplies their own game files.
- Keep all experiments on this branch until the iOS build and host are validated.
