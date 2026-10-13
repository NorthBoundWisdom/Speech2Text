import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtCore

ApplicationWindow {
    id: root
    visible: true
    width: 1320
    height: 860
    minimumWidth: 980
    minimumHeight: 620
    title: "SonaFolio"
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

        ToolBar {
            Layout.fillWidth: true
            RowLayout {
                anchors.fill: parent
                ToolButton {
                    text: "Sources"
                    checkable: true
                    checked: !workspace.sourceCollapsed
                    Accessible.name: workspace.sourceCollapsed ? "Show Sources" : "Hide Sources"
                    ToolTip.visible: hovered
                    ToolTip.text: Accessible.name
                    onClicked: workspace.toggleSources()
                }
                ToolButton {
                    text: "Episode List"
                    checkable: true
                    checked: !workspace.listCollapsed
                    Accessible.name: workspace.listCollapsed ? "Show Episode List" : "Hide Episode List"
                    ToolTip.visible: hovered
                    ToolTip.text: Accessible.name
                    onClicked: workspace.toggleList()
                }
                Item { Layout.fillWidth: true }
            }
        }

        DesktopWorkspace {
            id: workspace
            Layout.fillWidth: true
            Layout.fillHeight: true
            sourceWidth: workspacePreferences.sourceWidth
            listWidth: workspacePreferences.listWidth
            sourceCollapsed: workspacePreferences.sourceCollapsed
            listCollapsed: workspacePreferences.listCollapsed
            onSourceWidthChanged: workspacePreferences.sourceWidth = sourceWidth
            onListWidthChanged: workspacePreferences.listWidth = listWidth
            onSourceCollapsedChanged: workspacePreferences.sourceCollapsed = sourceCollapsed
            onListCollapsedChanged: workspacePreferences.listCollapsed = listCollapsed

            sourceContent: Component {
                SourceColumn {
                    onImportRequested: importDialog.open()
                    onSettingsRequested: settingsDialog.open()
                }
            }
            listContent: Component { ItemListColumn {} }
            detailContent: Component { DetailPane {} }
        }

        JobLogPane {
            Layout.fillWidth: true
            Layout.preferredHeight: root.logExpanded || jobController.running || jobController.lastError.length > 0 ? 190 : 34
            expanded: root.logExpanded || jobController.running || jobController.lastError.length > 0
            onToggleRequested: root.logExpanded = !root.logExpanded
        }
    }

    Settings {
        id: workspacePreferences
        category: "LibraryWorkspace"
        property real sourceWidth: 270
        property real listWidth: 360
        property bool sourceCollapsed: false
        property bool listCollapsed: false
    }

    Shortcut {
        sequence: "Ctrl+Shift+S"
        onActivated: workspace.toggleSources()
    }
    Shortcut {
        sequence: "Ctrl+Shift+L"
        onActivated: workspace.toggleList()
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
