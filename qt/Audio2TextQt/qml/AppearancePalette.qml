import QtQuick

// Implements GeoControls' public Theme.helper contract for the application.
Item {
    visible: false
    property string mode: settingsController.appearanceMode
    property int systemColorScheme: Qt.styleHints.colorScheme
    readonly property bool dark: mode === "dark" || (mode === "system" && systemColorScheme === Qt.Dark)
    readonly property int appearance: dark ? 1 : 0

    function applyNativeAppearance() {
        Qt.styleHints.colorScheme = mode === "dark" ? Qt.Dark : mode === "light" ? Qt.Light : Qt.Unknown;
    }
    onModeChanged: applyNativeAppearance()
    Component.onCompleted: applyNativeAppearance()

    readonly property color windowColor: dark ? "#202226" : "#f6f7f9"
    readonly property color windowTextColor: textColor
    readonly property color baseColor: dark ? "#25272c" : "#ffffff"
    readonly property color alternateBaseColor: dark ? "#30333a" : "#eef1f5"
    readonly property color textColor: dark ? "#e9ebef" : "#202124"
    readonly property color placeholderTextColor: dark ? "#a5acb8" : "#67717e"
    readonly property color disabledTextColor: dark ? "#767e8b" : "#8f98a3"
    readonly property color lightColor: dark ? "#3a3e46" : "#ffffff"
    readonly property color midlightColor: dark ? "#414651" : "#d8dde5"
    readonly property color midColor: dark ? "#535b69" : "#b6bec8"
    readonly property color darkColor: dark ? "#17191d" : "#b9c0c9"
    readonly property color shadowColor: dark ? "#80000000" : "#26000000"
    readonly property color accentColor: dark ? "#91b9ff" : "#2563eb"
    readonly property color linkColor: accentColor
    readonly property color highlightColor: dark ? "#316ed6" : "#2563eb"
    readonly property color highlightedTextColor: "#ffffff"
    readonly property color buttonColor: dark ? "#363a42" : "#edf0f4"
    readonly property color buttonTextColor: textColor
    readonly property color buttonHoveredColor: dark ? "#414956" : "#e2e8f0"
    readonly property color buttonPressedColor: dark ? "#4b5565" : "#d3dce8"
    readonly property color buttonDisabledColor: dark ? "#2d3036" : "#e2e6ec"
    readonly property color dividerColor: dark ? "#434852" : "#d4dae3"
    readonly property color railSurfaceColor: dark ? "#292c32" : "#f1f4f8"
    readonly property color inputSurfaceColor: dark ? "#1f2126" : "#ffffff"
    readonly property color pageSurfaceColor: windowColor
    readonly property color contentSurfaceColor: baseColor
    readonly property color popupSurfaceColor: dark ? "#2c2f36" : "#ffffff"
    readonly property color toolbarSurfaceColor: windowColor
    readonly property color actionButtonColor: buttonColor
    readonly property color actionButtonHoveredColor: buttonHoveredColor
    readonly property color actionButtonPressedColor: buttonPressedColor
    readonly property color actionButtonBorderColor: dividerColor
    readonly property color infoColor: accentColor
    readonly property color successColor: dark ? "#8bd5a0" : "#15803d"
    readonly property color warningColor: dark ? "#f0bd72" : "#a25800"
    readonly property color errorColor: dark ? "#ff9292" : "#dc2626"
    readonly property font appFont: Qt.application.font
    readonly property font monoFont: Qt.font({ family: "monospace" })
}
