# Vendored official cgltf1.15, immutable upstream commit and verified bytes.
# Runtime import is memory-only; no build/runtime network fallback exists.
set(AIBS_CGLTF_HEADER "${CMAKE_CURRENT_LIST_DIR}/../third_party/cgltf/cgltf.h")
set(AIBS_CGLTF_INCLUDE_DIR "${CMAKE_CURRENT_LIST_DIR}/../third_party/cgltf")
file(SHA256 "${AIBS_CGLTF_HEADER}" AIBS_CGLTF_SHA256)
if(NOT AIBS_CGLTF_SHA256 STREQUAL "e378a21c084bf1f288bb799de827bb26906efb024255f1ecf1705ea13f11c6ec")
  message(FATAL_ERROR "Pinned cgltf1.15 header bytes do not match the approved dependency")
endif()
install(FILES "${CMAKE_CURRENT_LIST_DIR}/../third_party/cgltf/LICENSE.txt"
  DESTINATION share/licenses/AIBS/cgltf)
