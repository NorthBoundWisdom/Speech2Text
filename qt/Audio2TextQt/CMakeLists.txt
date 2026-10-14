cmake_minimum_required(VERSION 3.24)

set(AUDIO2TEXTQT_RELEASE_VERSION "0.9.3" CACHE STRING "Numeric release version")
project(Audio2TextQt
    VERSION ${AUDIO2TEXTQT_RELEASE_VERSION}
    DESCRIPTION "SonaFolio Qt/QML client"
    LANGUAGES CXX
)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_AUTOMOC ON)
set(CMAKE_AUTORCC ON)

# Shared Qt loads QML plugins at runtime. Avoid importing unrelated SDK plugin
# targets; the app registers its static GeoControls modules explicitly.
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

find_package(Qt6 REQUIRED COMPONENTS Core Gui Qml Quick QuickControls2 QuickDialogs2 Svg QuickTest)
qt_standard_project_setup(REQUIRES 6.8)

set(GEOCONTROLS_SOURCE_ROOT "$ENV{GEOCONTROLS_SOURCE_ROOT}" CACHE PATH "FreeCM GeoControls source root")
if(NOT EXISTS "${GEOCONTROLS_SOURCE_ROOT}/Controls/CMakeLists.txt")
    message(FATAL_ERROR "GeoControls source root is required. Run python configs/source_roots.py init-seeds, then materialize; configure through configs/qt_workflow.py.")
endif()
set(GEOCONTROLS_BUILD_DEMO OFF CACHE BOOL "Only build the reusable controls" FORCE)
set(GEOCONTROLS_INSTALL_SDK OFF CACHE BOOL "Consume GeoControls from its source root" FORCE)
add_subdirectory("${GEOCONTROLS_SOURCE_ROOT}" "${CMAKE_CURRENT_BINARY_DIR}/_deps/geocontrols")
add_library(GeoControls::Controls ALIAS GeoControlsControls)
add_library(GeoControls::AppShell ALIAS GeoControlsAppShell)

qt_add_executable(Audio2TextQt
    src/AppPaths.cpp
    src/AppPaths.h
    src/GeoControlsSetup.cpp
    src/GeoControlsSetup.h
    src/AtotServiceClient.cpp
    src/AtotServiceClient.h
    src/JobController.cpp
    src/JobController.h
    src/LibraryController.cpp
    src/LibraryController.h
    src/SettingsController.cpp
    src/SettingsController.h
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
    IMPORT_PATH
        "${CMAKE_CURRENT_BINARY_DIR}/_deps/geocontrols/Controls"
        "${CMAKE_CURRENT_BINARY_DIR}/_deps/geocontrols/AppShell"
    DEPENDENCIES GeoControls GeoControls.AppShell
    QML_FILES
        qml/Main.qml
        qml/LibraryToolBar.qml
        qml/DocumentTabs.qml
        qml/DesktopWorkspace.qml
        qml/SourceColumn.qml
        qml/SidebarIcon.qml
        qml/ApplicationStatusPanel.qml
        qml/ItemListColumn.qml
        qml/DetailPane.qml
        qml/MarkdownView.qml
        qml/SubscriptionDetailPane.qml
        qml/ImportDialog.qml
        qml/SettingsDialog.qml
        qml/JobLogPane.qml
)

set_target_properties(Audio2TextQt PROPERTIES OUTPUT_NAME "SonaFolioQt")
# Static GeoControls modules are registered in GeoControlsSetup.cpp. Suppress
# only Qt's static-plugin linker finalizer, retaining the deployment import scan.
set_property(TARGET Audio2TextQt PROPERTY _QT_QML_PLUGINS_IMPORTED TRUE)

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
    GeoControls::AppShell
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
            --qmlimport "${CMAKE_CURRENT_BINARY_DIR}/_deps/geocontrols/Controls"
            --qmlimport "${CMAKE_CURRENT_BINARY_DIR}/_deps/geocontrols/AppShell"
            "$<TARGET_FILE:Audio2TextQt>"
        COMMAND "${CMAKE_COMMAND}" -E make_directory
            "$<TARGET_FILE_DIR:Audio2TextQt>/platforms"
        COMMAND "${CMAKE_COMMAND}" -E copy_if_different
            "${AUDIO2TEXTQT_QT_PREFIX_DIR}/plugins/platforms/qoffscreen.dll"
            "${AUDIO2TEXTQT_QT_PREFIX_DIR}/plugins/platforms/qminimal.dll"
            "$<TARGET_FILE_DIR:Audio2TextQt>/platforms"
        COMMENT "Deploying Qt runtime for SonaFolio Qt"
        VERBATIM
    )
elseif(APPLE)
    set_target_properties(Audio2TextQt PROPERTIES
        MACOSX_BUNDLE TRUE
        MACOSX_BUNDLE_BUNDLE_NAME "SonaFolio"
        MACOSX_BUNDLE_GUI_IDENTIFIER "local.audio2text.Audio2TextQt"
        MACOSX_BUNDLE_SHORT_VERSION_STRING "${PROJECT_VERSION}"
        MACOSX_BUNDLE_BUNDLE_VERSION "${PROJECT_VERSION}"
    )
endif()

install(TARGETS Audio2TextQt BUNDLE DESTINATION . RUNTIME DESTINATION bin)
# Deployed headless smoke checks must use bundled platform plugins, not the SDK.
if(APPLE)
    set(AUDIO2TEXTQT_PLATFORM_PLUGIN_DIR "SonaFolioQt.app/Contents/PlugIns/platforms")
else()
    set(AUDIO2TEXTQT_PLATFORM_PLUGIN_DIR "plugins/platforms")
endif()
include("${Qt6Gui_DIR}/Qt6QOffscreenIntegrationPluginTargets.cmake")
include("${Qt6Gui_DIR}/Qt6QMinimalIntegrationPluginTargets.cmake")
if(WIN32)
    # Explicit filenames avoid Qt's manual plugin targets selecting Debug DLLs
    # when the SDK publishes its release binaries as RelWithDebInfo.
    install(FILES
        "${AUDIO2TEXTQT_QT_PREFIX_DIR}/plugins/platforms/qoffscreen.dll"
        "${AUDIO2TEXTQT_QT_PREFIX_DIR}/plugins/platforms/qminimal.dll"
        DESTINATION ${AUDIO2TEXTQT_PLATFORM_PLUGIN_DIR}
        CONFIGURATIONS Release RelWithDebInfo MinSizeRel
    )
    install(FILES
        "${AUDIO2TEXTQT_QT_PREFIX_DIR}/plugins/platforms/qoffscreend.dll"
        "${AUDIO2TEXTQT_QT_PREFIX_DIR}/plugins/platforms/qminimald.dll"
        DESTINATION ${AUDIO2TEXTQT_PLATFORM_PLUGIN_DIR}
        CONFIGURATIONS Debug
    )
else()
    install(IMPORTED_RUNTIME_ARTIFACTS Qt6::QOffscreenIntegrationPlugin Qt6::QMinimalIntegrationPlugin
        LIBRARY DESTINATION ${AUDIO2TEXTQT_PLATFORM_PLUGIN_DIR}
        RUNTIME DESTINATION ${AUDIO2TEXTQT_PLATFORM_PLUGIN_DIR}
    )
endif()

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
set_tests_properties(Audio2TextQtQmlSmoke PROPERTIES ENVIRONMENT "${AUDIO2TEXTQT_SMOKE_ENV}" TIMEOUT 45)

qt_add_executable(Audio2TextQtWorkspaceTests ../../tests/qt_workspace/runner.cpp
    resource.qrc
    src/GeoControlsSetup.cpp src/GeoControlsSetup.h
    src/AppPaths.cpp src/AppPaths.h
    src/SettingsController.cpp src/SettingsController.h
    src/LibraryController.cpp src/LibraryController.h
    src/JobController.cpp src/JobController.h
    src/AtotServiceClient.cpp src/AtotServiceClient.h)
set_target_properties(Audio2TextQtWorkspaceTests PROPERTIES QT_QML_MODULE_NO_IMPORT_SCAN ON)
set_target_properties(Audio2TextQtWorkspaceTests PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/test-bin"
    WIN32_EXECUTABLE FALSE)
target_include_directories(Audio2TextQtWorkspaceTests PRIVATE src)
target_link_libraries(Audio2TextQtWorkspaceTests PRIVATE Qt6::QuickTest GeoControls::AppShell)
target_compile_definitions(Audio2TextQtWorkspaceTests PRIVATE
    QUICK_TEST_SOURCE_DIR="${CMAKE_CURRENT_SOURCE_DIR}/../../tests/qt_workspace")
add_test(NAME Audio2TextQtWorkspaceLayout
    COMMAND Audio2TextQtWorkspaceTests -o -,txt
        -o "${CMAKE_CURRENT_BINARY_DIR}/qt-workspace-results.txt,txt")
set_tests_properties(Audio2TextQtWorkspaceLayout PROPERTIES
    ENVIRONMENT "${AUDIO2TEXTQT_SMOKE_ENV}" TIMEOUT 45)
if(WIN32)
    add_custom_command(TARGET Audio2TextQtWorkspaceTests POST_BUILD
        COMMAND "${AUDIO2TEXTQT_WINDEPLOYQT_EXECUTABLE}"
            --verbose 0 --no-compiler-runtime --no-opengl-sw --no-system-d3d-compiler
            --qmldir "${CMAKE_CURRENT_SOURCE_DIR}/../../tests/qt_workspace"
            --qmlimport "${CMAKE_CURRENT_BINARY_DIR}/_deps/geocontrols/Controls"
            --qmlimport "${CMAKE_CURRENT_BINARY_DIR}/_deps/geocontrols/AppShell"
            "$<TARGET_FILE:Audio2TextQtWorkspaceTests>"
        COMMAND "${AUDIO2TEXTQT_WINDEPLOYQT_EXECUTABLE}"
            --verbose 0 --no-compiler-runtime --no-opengl-sw --no-system-d3d-compiler
            --qmldir "${CMAKE_CURRENT_SOURCE_DIR}/qml"
            --qmlimport "${CMAKE_CURRENT_BINARY_DIR}/_deps/geocontrols/Controls"
            --qmlimport "${CMAKE_CURRENT_BINARY_DIR}/_deps/geocontrols/AppShell"
            "$<TARGET_FILE:Audio2TextQtWorkspaceTests>"
        COMMAND "${CMAKE_COMMAND}" -E make_directory
            "$<TARGET_FILE_DIR:Audio2TextQtWorkspaceTests>/platforms"
        COMMAND "${CMAKE_COMMAND}" -E copy_if_different
            "${AUDIO2TEXTQT_QT_PREFIX_DIR}/plugins/platforms/qoffscreen.dll"
            "${AUDIO2TEXTQT_QT_PREFIX_DIR}/plugins/platforms/qminimal.dll"
            "$<TARGET_FILE_DIR:Audio2TextQtWorkspaceTests>/platforms"
        VERBATIM)
endif()

qt_add_executable(Audio2TextQtLanguageSettingsTests
    ../../tests/qt_settings/test_language_settings.cpp
    src/SettingsController.cpp src/SettingsController.h
    src/AppPaths.cpp src/AppPaths.h)
target_include_directories(Audio2TextQtLanguageSettingsTests PRIVATE src)
target_link_libraries(Audio2TextQtLanguageSettingsTests PRIVATE Qt6::Core)
set_target_properties(Audio2TextQtLanguageSettingsTests PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/test-bin"
    WIN32_EXECUTABLE FALSE)
add_test(NAME Audio2TextQtLanguageSettings COMMAND Audio2TextQtLanguageSettingsTests)
qt_add_executable(Audio2TextQtSharedRuntimeTests
    ../../tests/qt_settings/test_shared_runtime.cpp
    src/SettingsController.cpp src/SettingsController.h
    src/LibraryController.cpp src/LibraryController.h
    src/AppPaths.cpp src/AppPaths.h)
target_include_directories(Audio2TextQtSharedRuntimeTests PRIVATE src)
target_link_libraries(Audio2TextQtSharedRuntimeTests PRIVATE Qt6::Core)
set_target_properties(Audio2TextQtSharedRuntimeTests PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/test-bin"
    WIN32_EXECUTABLE FALSE)
add_test(NAME Audio2TextQtSharedRuntime COMMAND Audio2TextQtSharedRuntimeTests)
if(WIN32)
    add_custom_command(TARGET Audio2TextQtLanguageSettingsTests POST_BUILD
        COMMAND "${AUDIO2TEXTQT_WINDEPLOYQT_EXECUTABLE}"
            --verbose 0 --no-compiler-runtime --no-opengl-sw --no-system-d3d-compiler
            "$<TARGET_FILE:Audio2TextQtLanguageSettingsTests>"
        VERBATIM)
endif()

if(WIN32)
    add_custom_command(TARGET Audio2TextQtSharedRuntimeTests POST_BUILD
        COMMAND "${AUDIO2TEXTQT_WINDEPLOYQT_EXECUTABLE}"
            --verbose 0 --no-compiler-runtime --no-opengl-sw --no-system-d3d-compiler
            "$<TARGET_FILE:Audio2TextQtSharedRuntimeTests>"
        VERBATIM)
endif()
