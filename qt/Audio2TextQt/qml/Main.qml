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

        LibraryToolBar {
            id: libraryToolBar
            Layout.fillWidth: true
            sourcesVisible: !workspace.sourceCollapsed
            episodeListVisible: !workspace.listCollapsed
            statusOpen: statusPopup.opened
            onSourcesToggled: workspace.toggleSources()
            onEpisodeListToggled: workspace.toggleList()
            onStatusRequested: {
                if (statusPopup.opened) statusPopup.close();
                else statusPopup.open();
            }
        }

        DesktopWorkspace {
            id: workspace
            objectName: "desktopWorkspace"
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
        objectName: "applicationStatusPopup"
        parent: root.contentItem
        x: Math.max(12, Math.min(libraryToolBar.x + libraryToolBar.statusButtonX, root.width - width - 12))
        y: 58
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
