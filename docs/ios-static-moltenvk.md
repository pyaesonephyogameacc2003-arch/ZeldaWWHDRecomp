# iOS static MoltenVK load fix

## Problem
LiveContainer fails with:

```
Failed to load Vulkan Portability library
```

Because the iOS build links **static** MoltenVK (`libMoltenVK.a`) and there is no `libvulkan` / `MoltenVK` dylib for `SDL_Vulkan_LoadLibrary(nullptr)` to `dlopen`.

## Fix (branch `fix/ios-static-moltenvk-load`)

1. **`cmake/IOSDependencies.cmake`** (already pushed)
   - Imports static MoltenVK XCFramework as `Vulkan::Vulkan`.

2. **`CMakeLists.txt`**
   - Set `WWHD_IOS` when `CMAKE_SYSTEM_NAME` is iOS.
   - `include(cmake/IOSDependencies.cmake)` early.
   - Skip `find_package(Vulkan)` on iOS when the imported target exists.
   - `LINKER:-force_load` the static archive so it survives `VK_NO_PROTOTYPES`.

3. **`runtime/src/gfx/vulkan/backend.cpp`**
   - On iOS, take the address of the linked `vkGetInstanceProcAddr` instead of `SDL_Vulkan_LoadLibrary`.
   - Create the surface with `VK_EXT_metal_surface` + `SDL_Metal_CreateView` / `SDL_Metal_GetLayer`.

## Rebuild
Trigger the iOS ARM64 Runtime Build workflow on this branch, download the encrypted IPA, decrypt with the same password, and sideload.
