# iOS port investigation

Status: investigation only; this branch does not yet contain an iOS app or a working IPA build.

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

1. Introduce an explicit iOS platform branch in CMake without changing macOS, Android, Windows, or Linux behavior.
2. Choose and implement a supported iOS presentation host (UIKit + CAMetalLayer/MTKView, or a verified SDL3 iOS host) and connect the existing renderer's presentation path.
3. Add touch/controller input, app lifecycle pause/resume, audio-session handling, and sandbox document import for the user's own legally obtained game dump.
4. Audit fixed-address guest-memory reservations and executable-memory/JIT assumptions on iOS. This is a critical feasibility gate; do not assume an IPA can run merely because it links.
5. Add an iOS arm64 CMake/Xcode build and unsigned IPA packaging workflow.
6. Build on GitHub Actions, fix compiler/linker errors, and only call it device-ready after installation and runtime testing on an iPhone.

## Guardrails

- Do not add a placeholder workflow that produces an IPA-shaped but nonfunctional app.
- Do not modify the existing graphics/FPS settings or silently change their defaults.
- Do not include Nintendo game data, keys, or copyrighted assets in the repository or build artifacts. The user supplies their own game files.
- Keep all experiments on this branch until the iOS build and host are validated.
