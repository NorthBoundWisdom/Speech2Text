import QtQuick
import QtQuick.Controls as QQC
import GeoControls 1.0
import QtQuick.Layouts

CustomPane {
    id: root
    padding: 0
    property var library: libraryController
    property var jobs: jobController
    background: Rectangle {
        color: Theme.pageSurfaceColor
    }

    signal importRequested
    signal settingsRequested
    signal logsRequested

    function sourceById(sourceId) {
        for (var i = 0; i < root.library.sources.length; ++i) {
            var source = root.library.sources[i];
            if (source.id === sourceId)
                return source;
        }
        return null;
    }

    function groupSources() {
        var groups = [];
        for (var i = 0; i < root.library.sources.length; ++i) {
            var source = root.library.sources[i];
            if (source.kind === "group")
                groups.push(source);
        }
        return groups;
    }

    function isSelected(source) {
        return source && root.library.selectedSource === source.id;
    }

    function selectSource(source) {
        if (source)
            root.library.selectedSource = source.id;
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        RowLayout {
            Layout.fillWidth: true
            Layout.leftMargin: 12
            Layout.rightMargin: 10
            Layout.topMargin: 8
            Layout.bottomMargin: 8
            spacing: 8

            CustomToolButton {
                display: QQC.AbstractButton.TextOnly
                focusPolicy: Qt.StrongFocus
                text: "+"
                CustomToolTip {
                    visible: parent.hovered
                    text: "Import"
                }
                onClicked: root.importRequested()
                Layout.preferredWidth: 30
                Layout.preferredHeight: 28
            }

            ColumnLayout {
                spacing: 1
                Layout.fillWidth: true
                CustomLabel {
                    text: "SonaFolio"
                    font.pixelSize: 15
                    font.weight: Font.DemiBold
                    color: Theme.textColor
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }
                CustomLabel {
                    text: root.library.items.length + " episodes"
                    font.pixelSize: 11
                    color: Theme.placeholderTextColor
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }
            }

            CustomToolButton {
                display: QQC.AbstractButton.TextOnly
                focusPolicy: Qt.StrongFocus
                text: "\u2699"
                font.pixelSize: 17
                CustomToolTip {
                    visible: parent.hovered
                    text: "Settings"
                }
                onClicked: root.settingsRequested()
                Layout.preferredWidth: 32
                Layout.preferredHeight: 28
            }
        }

        CustomScrollView {
            id: statusArea
            Layout.fillWidth: true
            Layout.leftMargin: 10
            Layout.rightMargin: 10
            Layout.bottomMargin: 10
            Layout.preferredHeight: Math.min(sourceStatus.implicitHeight, Math.max(120, root.height * 0.45))
            contentWidth: availableWidth
            clip: true
            ApplicationStatusPanel {
                id: sourceStatus
                width: statusArea.availableWidth
                running: root.jobs.running
                stage: root.jobs.stage
                errorText: root.jobs.lastError
                queuedCount: root.jobs.queuedJobCount
                libraryMessage: root.library.statusMessage
                textColor: Theme.textColor
                mutedColor: Theme.placeholderTextColor
                errorColor: Theme.errorColor
                accentColor: Theme.highlightColor
                surfaceColor: Theme.alternateBaseColor
                onLogsRequested: root.logsRequested()
            }
        }

        Rectangle {
            Layout.fillWidth: true
            height: 1
            color: Theme.dividerColor
        }

        CustomScrollView {
            id: sourceScroll
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            contentWidth: availableWidth

            ColumnLayout {
                width: sourceScroll.availableWidth
                spacing: 2

                Item { Layout.fillWidth: true; implicitHeight: 10 }
                SourceRow {
                    source: root.sourceById("subscriptions")
                    symbol: "subscriptions"
                    tint: Theme.appearance === 1 ? "#da82f5" : "#a226cf"
                }
                SourceRow {
                    source: root.sourceById("smart:today")
                    symbol: "today"
                    tint: Theme.appearance === 1 ? "#ffb54f" : "#ba6500"
                }
                SourceRow {
                    source: root.sourceById("smart:unprocessed")
                    symbol: "unprocessed"
                    tint: Theme.appearance === 1 ? "#40b6ff" : "#0077c8"
                }
                SourceRow {
                    source: root.sourceById("smart:processed")
                    symbol: "processed"
                    tint: Theme.successColor
                }
                SourceRow {
                    source: root.sourceById("smart:starred")
                    symbol: "starred"
                    tint: Theme.appearance === 1 ? "#ffd84a" : "#b57900"
                }
                SourceRow {
                    source: root.sourceById("smart:archive")
                    symbol: "archive"
                }

                CustomLabel {
                    text: "Folders"
                    color: Theme.placeholderTextColor
                    font.pixelSize: 12
                    font.weight: Font.DemiBold
                    Layout.fillWidth: true
                    Layout.leftMargin: 16
                    Layout.rightMargin: 16
                    Layout.topMargin: 14
                    Layout.bottomMargin: 4
                }
                SourceRow {
                    source: root.sourceById("library")
                    symbol: "library"
                }
                Repeater {
                    model: root.groupSources()
                    delegate: SourceRow {
                        source: modelData
                        symbol: "folder"
                    }
                }
                Item { Layout.fillWidth: true; implicitHeight: 10 }
            }
        }
    }

    component SourceRow: CustomItemDelegate {
        id: row
        property var source
        property string symbol: "folder"
        property color tint: Theme.placeholderTextColor
        readonly property bool selected: root.isSelected(source)
        objectName: "sourceRow_" + (source ? source.id : "")
        visible: source !== null
        Layout.fillWidth: true
        Layout.leftMargin: 10
        Layout.rightMargin: 10
        Layout.preferredHeight: visible ? 32 : 0
        implicitHeight: visible ? 32 : 0
        leftPadding: 8
        rightPadding: 10
        topPadding: 0
        bottomPadding: 0
        focusPolicy: Qt.StrongFocus
        Accessible.name: source ? source.title : ""
        Accessible.selected: selected
        onClicked: root.selectSource(source)

        background: Rectangle {
            radius: 8
            color: row.selected ? Theme.highlightColor : row.down
                ? Theme.buttonPressedColor : row.hovered ? Theme.alternateBaseColor : "transparent"
            border.width: row.visualFocus ? 2 : 0
            border.color: Theme.accentColor
        }

        contentItem: RowLayout {
            spacing: 10
            SidebarIcon {
                objectName: "sidebarIcon_" + row.symbol
                symbol: row.symbol
                color: row.selected ? Theme.highlightedTextColor : row.tint
                Layout.preferredWidth: 24
                Layout.preferredHeight: 24
                Layout.alignment: Qt.AlignVCenter
            }
            CustomLabel {
                objectName: "sidebarTitle_" + (row.source ? row.source.id : "")
                text: row.source ? row.source.title : ""
                color: row.selected ? Theme.highlightedTextColor : Theme.textColor
                font.pixelSize: 14
                font.weight: row.selected ? Font.DemiBold : Font.Medium
                elide: Text.ElideRight
                verticalAlignment: Text.AlignVCenter
                Layout.fillWidth: true
                Layout.minimumWidth: 0
            }
            CustomLabel {
                objectName: "sidebarCount_" + (row.source ? row.source.id : "")
                text: row.source && row.source.count > 0 ? row.source.count : ""
                visible: text.length > 0
                color: row.selected ? Theme.highlightedTextColor : Theme.placeholderTextColor
                font.pixelSize: 13
                font.weight: Font.DemiBold
                horizontalAlignment: Text.AlignRight
                verticalAlignment: Text.AlignVCenter
            }
        }
    }
}
