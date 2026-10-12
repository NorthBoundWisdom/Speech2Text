import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    id: root
    visible: true
    width: 1320
    height: 860
    minimumWidth: 980
    minimumHeight: 620
    title: "Audio2Text"
    color: themeController.window

    palette {
        window: themeController.window
        windowText: themeController.text
        base: themeController.panel
        alternateBase: themeController.panelAlt
        text: themeController.text
        button: themeController.panelAlt
        buttonText: themeController.text
        highlight: themeController.accent
        highlightedText: "#ffffff"
        placeholderText: themeController.muted
    }

    property bool logExpanded: false

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        SplitView {
            id: workspace
            orientation: Qt.Horizontal
            Layout.fillWidth: true
            Layout.fillHeight: true

            handle: Rectangle {
                implicitWidth: 6
                implicitHeight: 8
                color: SplitHandle.pressed
                    ? "#dbe7f5"
                    : (SplitHandle.hovered ? "#eef4fb" : "#f4f7fa")
            }

            SourceColumn {
                SplitView.preferredWidth: 270
                SplitView.minimumWidth: 210
                onImportRequested: importDialog.open()
                onSettingsRequested: settingsDialog.open()
            }

            ItemListColumn {
                SplitView.preferredWidth: 360
                SplitView.minimumWidth: 280
            }

            DetailPane {
                SplitView.fillWidth: true
                SplitView.minimumWidth: 420
            }
        }

        JobLogPane {
            Layout.fillWidth: true
            Layout.preferredHeight: root.logExpanded || jobController.running || jobController.lastError.length > 0 ? 190 : 34
            expanded: root.logExpanded || jobController.running || jobController.lastError.length > 0
            onToggleRequested: root.logExpanded = !root.logExpanded
        }
    }

    ImportDialog {
        id: importDialog
    }

    SettingsDialog {
        id: settingsDialog
    }

    Connections {
        target: libraryController
        function onErrorRaised(message) {
            jobController.clearLog()
            console.warn(message)
        }
    }

}
