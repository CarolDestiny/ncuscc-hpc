cmake_minimum_required(VERSION 3.16)
project(ncuscc_hpc LANGUAGES CXX)

if(NOT CMAKE_SYSTEM_NAME STREQUAL "Linux")
    message(FATAL_ERROR "Build inside Linux or WSL 2")
endif()

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)
include(CTest)

# Preserve the original stage-1 build file and avoid registering absent tests.
set(_ncuscc_saved_testing "${BUILD_TESTING}")
if(BUILD_TESTING AND
   (NOT EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/chaosuan-1/tests/integration_test.py" OR
    NOT EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/chaosuan-1/tests/lifecycle_test.py"))
    message(STATUS "Stage 1: original test scripts missing; use scripts/verify.py for the smoke check")
    set(BUILD_TESTING OFF)
endif()
add_subdirectory(chaosuan-1)
set(BUILD_TESTING "${_ncuscc_saved_testing}")
unset(_ncuscc_saved_testing)

add_subdirectory(chaosuan-2)
add_subdirectory(chaosuan-3)
