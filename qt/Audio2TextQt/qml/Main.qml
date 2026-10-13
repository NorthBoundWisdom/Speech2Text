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
                ToolButton {
                    text: "Status"
                    Accessible.name: "Application Status"
                    ToolTip.visible: hovered
                    ToolTip.text: "View processing and library status"
                    onClicked: statusPopup.open()
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
                    onLogsRequested: logDialog.open()
                }
            }
            listContent: Component { ItemListColumn {} }
            detailContent: Component { DetailPane {} }
        }
    }

    Popup {
        id: statusPopup
        parent: root.contentItem
        x: 10
        y: 42
        width: 360
        height: Math.min(440, statusDetails.implicitHeight + topPadding + bottomPadding)
        modal: false
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        ScrollView {
            id: statusScroll
            anchors.fill: parent
            contentWidth: availableWidth
            ApplicationStatusPanel {
                id: statusDetails
                width: statusScroll.availableWidth
                running: jobController.running
                stage: jobController.stage
                errorText: jobController.lastError
                queuedCount: jobController.queuedJobCount
                libraryMessage: libraryController.statusMessage
                textColor: themeController.text
                mutedColor: themeController.muted
                errorColor: themeController.danger
                surfaceColor: themeController.panelAlt
                onLogsRequested: { statusPopup.close(); logDialog.open() }
            }
        }
    }

    Dialog {
        id: logDialog
        title: "Task log"
        modal: false
        parent: root.contentItem
        x: 10
        y: 42
        width: Math.min(760, root.width - 20)
        height: Math.min(480, root.height - 60)
        standardButtons: Dialog.Close
        JobLogPane { anchors.fill: parent; expanded: true }
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
