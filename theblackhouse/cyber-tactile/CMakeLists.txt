cmake_minimum_required(VERSION 3.20)
project(blackhouse_cyber_tactile LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

add_library(blackhouse_cyber_tactile
    src/cyber_tactile.cpp
)
target_include_directories(blackhouse_cyber_tactile PUBLIC include)
target_compile_options(blackhouse_cyber_tactile PRIVATE -Wall -Wextra -Wpedantic -Werror)

add_executable(blackhouse_cyber_tactile_demo src/demo.cpp)
target_link_libraries(blackhouse_cyber_tactile_demo PRIVATE blackhouse_cyber_tactile)
target_compile_options(blackhouse_cyber_tactile_demo PRIVATE -Wall -Wextra -Wpedantic -Werror)

enable_testing()
add_executable(blackhouse_cyber_tactile_tests tests/test_pipeline.cpp)
target_link_libraries(blackhouse_cyber_tactile_tests PRIVATE blackhouse_cyber_tactile)
target_compile_options(blackhouse_cyber_tactile_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
add_test(NAME blackhouse_cyber_tactile_tests COMMAND blackhouse_cyber_tactile_tests)
