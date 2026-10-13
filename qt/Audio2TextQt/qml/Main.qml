import QtQuick
import QtQuick.Controls as QQC
import GeoControls 1.0
import GeoControls.AppShell 1.0
import QtQuick.Layouts
import QtCore

ApplicationShell {
    id: root
    visible: true
    width: 1320
    height: 860
    minimumWidth: 980
    minimumHeight: 620
    title: "SonaFolio"
    ColumnLayout {
        objectName: "workspaceBody"
        anchors.fill: parent
        spacing: 0

        CustomToolBar {
            Layout.fillWidth: true
            RowLayout {
                anchors.fill: parent
                CustomToolButton {
                    display: QQC.AbstractButton.TextOnly
                    focusPolicy: Qt.StrongFocus
                    defaultPadding: Fonts.size8
                    text: "Sources"
                    checkable: true
                    checked: !workspace.sourceCollapsed
                    Accessible.name: workspace.sourceCollapsed ? "Show Sources" : "Hide Sources"
                    tooltip: Accessible.name
                    onClicked: workspace.toggleSources()
                }
                CustomToolButton {
                    display: QQC.AbstractButton.TextOnly
                    focusPolicy: Qt.StrongFocus
                    defaultPadding: Fonts.size8
                    text: "Episode List"
                    checkable: true
                    checked: !workspace.listCollapsed
                    Accessible.name: workspace.listCollapsed ? "Show Episode List" : "Hide Episode List"
                    tooltip: Accessible.name
                    onClicked: workspace.toggleList()
                }
                CustomToolButton {
                    display: QQC.AbstractButton.TextOnly
                    focusPolicy: Qt.StrongFocus
                    defaultPadding: Fonts.size8
                    text: "Status"
                    Accessible.name: "Application Status"
                    tooltip: "View processing and library status"
                    onClicked: statusPopup.open()
                }
                Item {
                    Layout.fillWidth: true
                }
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
            listContent: Component {
                ItemListColumn {}
            }
            detailContent: Component {
                DetailPane {}
            }
        }
    }

    CustomPopup {
        id: statusPopup
        parent: root.contentItem
        x: 10
        y: 42
        width: 360
        height: Math.min(440, statusDetails.implicitHeight + topPadding + bottomPadding)
        modal: false
        closePolicy: QQC.Popup.CloseOnEscape | QQC.Popup.CloseOnPressOutside
        CustomScrollView {
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
                textColor: Theme.textColor
                mutedColor: Theme.placeholderTextColor
                errorColor: Theme.errorColor
                surfaceColor: Theme.alternateBaseColor
                onLogsRequested: {
                    statusPopup.close();
                    logDialog.open();
                }
            }
        }
    }

    CustomDialog {
        id: logDialog
        title: "Task log"
        modal: false
        parent: root.contentItem
        x: 10
        y: 42
        width: Math.min(760, root.width - 20)
        height: Math.min(480, root.height - 60)
        standardButtons: QQC.Dialog.Close
        JobLogPane {
            anchors.fill: parent
            expanded: true
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
            jobController.clearLog();
            console.warn(message);
        }
    }
}
