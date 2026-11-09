#!/usr/bin/env python3
"""Patch CMakeLists.txt and backend.cpp for iOS static MoltenVK."""
from pathlib import Path
import re
import sys


def patch_cmake(root: Path) -> None:
    path = root / "CMakeLists.txt"
    text = path.read_text()
    old = (
        '    target_link_libraries(wwhd PRIVATE "${WWHD_IOS_MOLTENVK_ARCHIVE}" '
        "glslang::glslang glslang::SPIRV glslang::glslang-default-resource-limits)"
    )
    new = (
        '    target_link_options(wwhd PRIVATE "LINKER:-force_load,${WWHD_IOS_MOLTENVK_ARCHIVE}")\n'
        "    target_link_libraries(wwhd PRIVATE "
        "glslang::glslang glslang::SPIRV glslang::glslang-default-resource-limits)"
    )
    if old not in text:
        if "LINKER:-force_load,${WWHD_IOS_MOLTENVK_ARCHIVE}" in text:
            print("cmake already patched")
            return
        raise SystemExit("cmake pattern missing")
    path.write_text(text.replace(old, new, 1))
    print("cmake force_load ok")


def patch_backend(root: Path) -> None:
    path = root / "runtime/src/gfx/vulkan/backend.cpp"
    text = path.read_text()
    if "WWHD_IOS_STATIC_MOLTENVK" in text and "_NSGetExecutablePath" in text:
        print("backend already patched")
        return
    pat = re.compile(
        r"  if \(!SDL_Vulkan_LoadLibrary\(nullptr\)\)\n"
        r"    exception_report::raise\(std::string\(\"Vulkan is not installed[\s\S]*?"
        r"\+ kUpdateDriver\);\n"
        r"  auto gipa = reinterpret_cast<PFN_vkGetInstanceProcAddr>\("
        r"SDL_Vulkan_GetVkGetInstanceProcAddr\(\)\);\n"
        r"#ifdef __ANDROID__\n"
        r"  if \(auto custom = drivers::open_custom\(\)\) gipa = custom;\n"
        r"#endif\n"
        r"  load_global_functions\(gipa\);"
    )
    match = pat.search(text)
    if not match:
        raise SystemExit("backend load block not found")
    ios = """#if defined(WWHD_IOS_STATIC_MOLTENVK)
  {
    char exePath[4096];
    uint32_t exeSize = sizeof(exePath);
    const char *loadPath = nullptr;
    if (_NSGetExecutablePath(exePath, &exeSize) == 0)
      loadPath = exePath;
    if (!SDL_Vulkan_LoadLibrary(loadPath)) {
      auto gipaDlsym = reinterpret_cast<PFN_vkGetInstanceProcAddr>(
          dlsym(RTLD_DEFAULT, "vkGetInstanceProcAddr"));
      if (!gipaDlsym)
        exception_report::raise(std::string("iOS static MoltenVK missing: ") + SDL_GetError());
      LOG("[vulkan] SDL_Vulkan_LoadLibrary failed (%s); using dlsym static MoltenVK",
          SDL_GetError());
      load_global_functions(gipaDlsym);
    } else {
      auto gipa = reinterpret_cast<PFN_vkGetInstanceProcAddr>(
          SDL_Vulkan_GetVkGetInstanceProcAddr());
      if (!gipa)
        gipa = reinterpret_cast<PFN_vkGetInstanceProcAddr>(
            dlsym(RTLD_DEFAULT, "vkGetInstanceProcAddr"));
      if (!gipa)
        exception_report::raise("iOS static MoltenVK: null gipa");
      LOG("[vulkan] loader: static MoltenVK in app image");
      load_global_functions(gipa);
    }
  }
#else
"""
    replacement = ios + match.group(0) + "\n#endif"
    path.write_text(text[: match.start()] + replacement + text[match.end() :])
    print("backend iOS load path ok")


def main() -> None:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    patch_cmake(root)
    patch_backend(root)


if __name__ == "__main__":
    main()
