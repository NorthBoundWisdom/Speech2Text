cmake_minimum_required(VERSION 3.24)

set(AUDIO2TEXTQT_RELEASE_VERSION "0.1.0" CACHE STRING "Numeric release version")
project(Audio2TextQt
    VERSION ${AUDIO2TEXTQT_RELEASE_VERSION}
    DESCRIPTION "Audio2Text Qt/QML client"
    LANGUAGES CXX
)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_AUTOMOC ON)
set(CMAKE_AUTORCC ON)

# The app uses shared Qt. Letting Qt's CMake package auto-import every installed
# QML plugin can surface warnings from optional Qt modules that this client never uses.
set(QT_SKIP_AUTO_PLUGIN_INCLUSION ON)
set(QT_SKIP_AUTO_QML_PLUGIN_INCLUSION ON)

if(WIN32 AND NOT TARGET WrapVulkanHeaders::WrapVulkanHeaders)
    add_library(WrapVulkanHeaders::WrapVulkanHeaders INTERFACE IMPORTED)
    set_target_properties(WrapVulkanHeaders::WrapVulkanHeaders PROPERTIES
        _qt_is_nolink_target TRUE
        _qt_skip_include_dir_for_pri TRUE
    )
endif()
if(WIN32)
    enable_language(RC)
endif()

find_package(Qt6 REQUIRED COMPONENTS Core Gui Qml Quick QuickControls2)
qt_standard_project_setup(REQUIRES 6.8)

qt_add_executable(Audio2TextQt
    src/AppPaths.cpp
    src/AppPaths.h
    src/AtotServiceClient.cpp
    src/AtotServiceClient.h
    src/JobController.cpp
    src/JobController.h
    src/LibraryController.cpp
    src/LibraryController.h
    src/SettingsController.cpp
    src/SettingsController.h
    src/ThemeController.cpp
    src/ThemeController.h
    src/main.cpp
    resource.qrc
)

# A real QML module lets Qt's deployment API discover imports on all desktop platforms.
qt_add_qml_module(Audio2TextQt
    URI Audio2TextQt
    VERSION 1.0
    RESOURCE_PREFIX "/"
    OUTPUT_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/qml/Audio2TextQt"
    NO_CACHEGEN
    QML_FILES
        qml/Main.qml
        qml/SourceColumn.qml
        qml/ItemListColumn.qml
        qml/DetailPane.qml
        qml/MarkdownView.qml
        qml/SubscriptionDetailPane.qml
        qml/ImportDialog.qml
        qml/SettingsDialog.qml
        qml/JobLogPane.qml
)

target_include_directories(Audio2TextQt PRIVATE src)

if(MSVC)
    target_compile_options(Audio2TextQt PRIVATE /W4)
elseif(CMAKE_CXX_COMPILER_ID MATCHES "^(AppleClang|Clang|GNU)$")
    target_compile_options(Audio2TextQt PRIVATE -Wall -Wextra -Wpedantic)
endif()

target_link_libraries(Audio2TextQt
PRIVATE
    Qt6::Core
    Qt6::Gui
    Qt6::Qml
    Qt6::Quick
    Qt6::QuickControls2
)

target_compile_definitions(Audio2TextQt
PRIVATE
    AUDIO2TEXTQT_VERSION="${PROJECT_VERSION}"
)

if(WIN32)
    target_sources(Audio2TextQt PRIVATE resources/app-icon.rc)
    set_target_properties(Audio2TextQt PROPERTIES WIN32_EXECUTABLE TRUE)
    get_filename_component(AUDIO2TEXTQT_QT_CMAKE_DIR "${Qt6_DIR}" DIRECTORY)
    get_filename_component(AUDIO2TEXTQT_QT_CMAKE_DIR "${AUDIO2TEXTQT_QT_CMAKE_DIR}" DIRECTORY)
    get_filename_component(AUDIO2TEXTQT_QT_PREFIX_DIR "${AUDIO2TEXTQT_QT_CMAKE_DIR}" DIRECTORY)
    find_program(AUDIO2TEXTQT_WINDEPLOYQT_EXECUTABLE
        NAMES windeployqt
        HINTS "${AUDIO2TEXTQT_QT_PREFIX_DIR}/bin"
        REQUIRED
    )
    add_custom_command(TARGET Audio2TextQt POST_BUILD
        COMMAND "${AUDIO2TEXTQT_WINDEPLOYQT_EXECUTABLE}"
            --verbose 0
            --no-compiler-runtime
            --no-opengl-sw
            --no-system-d3d-compiler
            --qmldir "${CMAKE_CURRENT_SOURCE_DIR}/qml"
            "$<TARGET_FILE:Audio2TextQt>"
        COMMAND "${CMAKE_COMMAND}" -E make_directory
            "$<TARGET_FILE_DIR:Audio2TextQt>/platforms"
        COMMAND "${CMAKE_COMMAND}" -E copy_if_different
            "${AUDIO2TEXTQT_QT_PREFIX_DIR}/plugins/platforms/qoffscreen.dll"
            "${AUDIO2TEXTQT_QT_PREFIX_DIR}/plugins/platforms/qminimal.dll"
            "$<TARGET_FILE_DIR:Audio2TextQt>/platforms"
        COMMENT "Deploying Qt runtime for Audio2TextQt"
        VERBATIM
    )
elseif(APPLE)
    set_target_properties(Audio2TextQt PROPERTIES
        MACOSX_BUNDLE TRUE
        MACOSX_BUNDLE_BUNDLE_NAME "Audio2TextQt"
        MACOSX_BUNDLE_GUI_IDENTIFIER "local.audio2text.Audio2TextQt"
        MACOSX_BUNDLE_SHORT_VERSION_STRING "${PROJECT_VERSION}"
        MACOSX_BUNDLE_BUNDLE_VERSION "${PROJECT_VERSION}"
    )
endif()

install(TARGETS Audio2TextQt BUNDLE DESTINATION . RUNTIME DESTINATION bin)
# Deployed headless smoke checks must use bundled platform plugins, not the SDK.
if(APPLE)
    set(AUDIO2TEXTQT_PLATFORM_PLUGIN_DIR "Audio2TextQt.app/Contents/PlugIns/platforms")
else()
    set(AUDIO2TEXTQT_PLATFORM_PLUGIN_DIR "plugins/platforms")
endif()
include("${Qt6Gui_DIR}/Qt6QOffscreenIntegrationPluginTargets.cmake")
include("${Qt6Gui_DIR}/Qt6QMinimalIntegrationPluginTargets.cmake")
install(IMPORTED_RUNTIME_ARTIFACTS Qt6::QOffscreenIntegrationPlugin Qt6::QMinimalIntegrationPlugin
    LIBRARY DESTINATION ${AUDIO2TEXTQT_PLATFORM_PLUGIN_DIR}
    RUNTIME DESTINATION ${AUDIO2TEXTQT_PLATFORM_PLUGIN_DIR}
)
set(AUDIO2TEXTQT_DEPLOY_OPTIONS)
if(WIN32)
    list(APPEND AUDIO2TEXTQT_DEPLOY_OPTIONS --no-opengl-sw --no-system-d3d-compiler)
    if(Qt6_VERSION VERSION_GREATER_EQUAL "6.10")
        list(APPEND AUDIO2TEXTQT_DEPLOY_OPTIONS --no-system-dxc-compiler)
    endif()
elseif(APPLE)
    list(APPEND AUDIO2TEXTQT_DEPLOY_OPTIONS -appstore-compliant -always-overwrite)
endif()
qt_generate_deploy_qml_app_script(
    TARGET Audio2TextQt
    OUTPUT_SCRIPT AUDIO2TEXTQT_DEPLOY_SCRIPT
    NO_TRANSLATIONS
    NO_COMPILER_RUNTIME
    DEPLOY_TOOL_OPTIONS ${AUDIO2TEXTQT_DEPLOY_OPTIONS}
)
install(SCRIPT ${AUDIO2TEXTQT_DEPLOY_SCRIPT})

enable_testing()
add_test(NAME Audio2TextQtQmlSmoke COMMAND Audio2TextQt --smoke-quit)
set(AUDIO2TEXTQT_SMOKE_ENV "QT_QPA_PLATFORM=offscreen;QT_QUICK_BACKEND=software")
if(WIN32 AND DEFINED ENV{SystemRoot} AND EXISTS "$ENV{SystemRoot}/Fonts")
    file(TO_CMAKE_PATH "$ENV{SystemRoot}/Fonts" AUDIO2TEXTQT_WINDOWS_FONT_DIR)
    list(APPEND AUDIO2TEXTQT_SMOKE_ENV "QT_QPA_FONTDIR=${AUDIO2TEXTQT_WINDOWS_FONT_DIR}")
endif()
set_tests_properties(Audio2TextQtQmlSmoke PROPERTIES ENVIRONMENT "${AUDIO2TEXTQT_SMOKE_ENV}")
