import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Pane {
    id: root
    padding: 0
    background: Rectangle {
        color: themeController.panel
    }

    signal importRequested()
    signal settingsRequested()
    signal logsRequested()

    function sourceById(sourceId) {
        for (var i = 0; i < libraryController.sources.length; ++i) {
            var source = libraryController.sources[i]
            if (source.id === sourceId)
                return source
        }
        return null
    }

    function groupSources() {
        var groups = []
        for (var i = 0; i < libraryController.sources.length; ++i) {
            var source = libraryController.sources[i]
            if (source.kind === "group")
                groups.push(source)
        }
        return groups
    }

    function isSelected(source) {
        return source && libraryController.selectedSource === source.id
    }

    function selectSource(source) {
        if (source)
            libraryController.selectedSource = source.id
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        RowLayout {
            Layout.fillWidth: true
            Layout.leftMargin: 12
            Layout.rightMargin: 10
            Layout.topMargin: 12
            Layout.bottomMargin: 12
            spacing: 8

            ToolButton {
                text: "+"
                ToolTip.visible: hovered
                ToolTip.text: "Import"
                onClicked: root.importRequested()
                Layout.preferredWidth: 30
                Layout.preferredHeight: 28
            }

            ColumnLayout {
                spacing: 1
                Layout.fillWidth: true
                Label {
                    text: "SonaFolio"
                    font.pixelSize: 15
                    font.weight: Font.DemiBold
                    color: themeController.text
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }
                Label {
                    text: libraryController.items.length + " episodes"
                    font.pixelSize: 11
                    color: themeController.muted
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }
            }

            ToolButton {
                text: "\u2699"
                font.pixelSize: 17
                ToolTip.visible: hovered
                ToolTip.text: "Settings"
                onClicked: root.settingsRequested()
                Layout.preferredWidth: 32
                Layout.preferredHeight: 28
            }
        }

        ScrollView {
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
                running: jobController.running
                stage: jobController.stage
                errorText: jobController.lastError
                queuedCount: jobController.queuedJobCount
                libraryMessage: libraryController.statusMessage
                textColor: themeController.text
                mutedColor: themeController.muted
                errorColor: themeController.danger
                accentColor: themeController.accent
                surfaceColor: themeController.panelAlt
                onLogsRequested: root.logsRequested()
            }
        }

        Rectangle {
            Layout.fillWidth: true
            height: 1
            color: themeController.border
        }

        ScrollView {
            id: sourceScroll
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            contentWidth: availableWidth

            ColumnLayout {
                width: sourceScroll.availableWidth
                spacing: 14

                Item {
                    Layout.fillWidth: true
                    height: 6
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 4

                    SectionHeader { title: "Library" }
                    SourceRow { source: root.sourceById("library"); badge: "LIB"; tint: themeController.muted }
                    SourceRow { source: root.sourceById("subscriptions"); badge: "RSS"; tint: "#7c3aed" }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 4

                    SectionHeader { title: "Smart Feeds" }
                    SourceRow { source: root.sourceById("smart:today"); badge: "DAY"; tint: "#c26a00" }
                    SourceRow { source: root.sourceById("smart:unprocessed"); badge: "NEW"; tint: themeController.accent }
                    SourceRow { source: root.sourceById("smart:processed"); badge: "OK"; tint: themeController.success }
                    SourceRow { source: root.sourceById("smart:starred"); badge: "*"; tint: "#b77900" }
                    SourceRow { source: root.sourceById("smart:archive"); badge: "ARC"; tint: themeController.muted }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 4

                    SectionHeader { title: "Folders" }
                    Repeater {
                        model: root.groupSources()
                        delegate: SourceRow {
                            source: modelData
                            badge: "#"
                            tint: themeController.muted
                            dimWhenEmpty: true
                        }
                    }
                }

                Item {
                    Layout.fillWidth: true
                    height: 14
                }
            }
        }
    }

    component SectionHeader: Label {
        property string title: ""
        text: title
        color: themeController.muted
        font.pixelSize: 11
        font.weight: Font.DemiBold
        Layout.fillWidth: true
        Layout.leftMargin: 14
        Layout.rightMargin: 12
        Layout.topMargin: 6
        Layout.bottomMargin: 4
    }

    component SourceRow: Item {
        id: row
        property var source
        property string badge: ""
        property color tint: themeController.muted
        property bool dimWhenEmpty: false
        property bool selected: root.isSelected(source)
        property bool empty: source && source.count === 0
        property bool hovered: mouse.containsMouse

        visible: source !== null
        Layout.fillWidth: true
        Layout.preferredHeight: visible ? 34 : 0
        implicitHeight: visible ? 34 : 0

        Rectangle {
            id: rowBackground
            color: row.selected ? "#eaf2ff" : (row.hovered ? "#f7faff" : "transparent")
            radius: 8
            anchors.fill: parent
            anchors.leftMargin: 10
            anchors.rightMargin: 12
            anchors.topMargin: 2
            anchors.bottomMargin: 2

            Rectangle {
                visible: row.selected
                width: 3
                radius: 2
                color: themeController.accent
                anchors.left: parent.left
                anchors.top: parent.top
                anchors.bottom: parent.bottom
                anchors.topMargin: 6
                anchors.bottomMargin: 6
            }
        }

        Label {
            id: badgeLabel
            text: row.badge
            color: row.selected ? themeController.accent : row.tint
            opacity: row.dimWhenEmpty && row.empty && !row.selected ? 0.58 : 1.0
            font.pixelSize: row.badge.length > 1 ? 9 : 13
            font.weight: Font.DemiBold
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            anchors.left: parent.left
            anchors.leftMargin: 18
            anchors.verticalCenter: parent.verticalCenter
            width: 36
            height: 24
        }

        Label {
            id: titleLabel
            text: row.source ? row.source.title : ""
            color: row.selected ? themeController.accent : themeController.text
            opacity: row.dimWhenEmpty && row.empty && !row.selected ? 0.62 : 1.0
            font.pixelSize: 14
            font.weight: row.selected ? Font.DemiBold : Font.Normal
            elide: Text.ElideRight
            verticalAlignment: Text.AlignVCenter
            anchors.left: badgeLabel.right
            anchors.leftMargin: 12
            anchors.right: countLabel.left
            anchors.rightMargin: 14
            anchors.verticalCenter: parent.verticalCenter
            height: 24
        }

        Label {
            id: countLabel
            text: row.source && row.source.count > 0 ? row.source.count : ""
            color: row.selected ? themeController.accent : themeController.muted
            font.pixelSize: 13
            font.weight: row.selected ? Font.DemiBold : Font.Normal
            horizontalAlignment: Text.AlignRight
            verticalAlignment: Text.AlignVCenter
            anchors.right: parent.right
            anchors.rightMargin: 18
            anchors.verticalCenter: parent.verticalCenter
            width: 64
            height: 24
        }

        MouseArea {
            id: mouse
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: root.selectSource(row.source)
        }
    }
}
