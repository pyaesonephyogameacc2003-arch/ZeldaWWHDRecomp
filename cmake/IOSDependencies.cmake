# iOS Vulkan provider: static MoltenVK XCFramework.
#
# The iOS dependency workflow builds MoltenVK and passes:
#   -DWWHD_IOS_MOLTENVK_XCFRAMEWORK=/path/to/MoltenVK.xcframework
#   -DWWHD_IOS_MOLTENVK_INCLUDE_DIR=/path/to/Package/Release/MoltenVK/include
#
# We deliberately use the device slice only. The app target is arm64/iPhoneOS,
# not an iOS Simulator binary. Keeping this as an imported target avoids copying
# third-party binaries into the source tree.
set(WWHD_IOS_MOLTENVK_XCFRAMEWORK "" CACHE PATH "Static MoltenVK.xcframework for iOS device builds")
set(WWHD_IOS_MOLTENVK_INCLUDE_DIR "" CACHE PATH "MoltenVK package include directory")

if(NOT WWHD_IOS_MOLTENVK_XCFRAMEWORK)
  message(FATAL_ERROR "Set WWHD_IOS_MOLTENVK_XCFRAMEWORK to the static MoltenVK.xcframework")
endif()
if(NOT WWHD_IOS_MOLTENVK_INCLUDE_DIR)
  message(FATAL_ERROR "Set WWHD_IOS_MOLTENVK_INCLUDE_DIR to MoltenVK/Package/Release/MoltenVK/include")
endif()

set(_wwhd_moltenvk_framework
    "${WWHD_IOS_MOLTENVK_XCFRAMEWORK}/ios-arm64/MoltenVK.framework")
set(_wwhd_moltenvk_binary "${_wwhd_moltenvk_framework}/MoltenVK")

if(NOT EXISTS "${WWHD_IOS_MOLTENVK_XCFRAMEWORK}/Info.plist")
  message(FATAL_ERROR "Not an XCFramework: ${WWHD_IOS_MOLTENVK_XCFRAMEWORK}")
endif()
if(NOT EXISTS "${_wwhd_moltenvk_binary}")
  message(FATAL_ERROR "Missing iOS arm64 MoltenVK binary: ${_wwhd_moltenvk_binary}")
endif()
if(NOT EXISTS "${WWHD_IOS_MOLTENVK_INCLUDE_DIR}/vulkan/vulkan.h")
  message(FATAL_ERROR "MoltenVK Vulkan headers not found under ${WWHD_IOS_MOLTENVK_INCLUDE_DIR}")
endif()
if(TARGET Vulkan::Vulkan)
  message(FATAL_ERROR "Vulkan::Vulkan already exists before the iOS MoltenVK provider is configured")
endif()

add_library(Vulkan::Vulkan UNKNOWN IMPORTED GLOBAL)
set_target_properties(Vulkan::Vulkan PROPERTIES
  IMPORTED_LOCATION "${_wwhd_moltenvk_binary}"
  INTERFACE_INCLUDE_DIRECTORIES "${WWHD_IOS_MOLTENVK_INCLUDE_DIR}")

# Match the variables commonly exposed by FindVulkan for downstream CMake code.
set(Vulkan_FOUND TRUE)
set(Vulkan_VERSION "1.3")
set(Vulkan_INCLUDE_DIR "${WWHD_IOS_MOLTENVK_INCLUDE_DIR}")
set(Vulkan_INCLUDE_DIRS "${WWHD_IOS_MOLTENVK_INCLUDE_DIR}")
set(Vulkan_LIBRARY "${_wwhd_moltenvk_binary}")
set(Vulkan_LIBRARIES Vulkan::Vulkan)

message(STATUS "iOS Vulkan provider: static MoltenVK (${_wwhd_moltenvk_binary})")
message(STATUS "iOS Vulkan headers: ${WWHD_IOS_MOLTENVK_INCLUDE_DIR}")
