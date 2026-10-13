import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Pane {
    id: root
    objectName: "applicationStatusPanel"
    padding: 10
    implicitHeight: content.implicitHeight + topPadding + bottomPadding
    property bool running: false
    property string stage: "Idle"
    property string errorText: ""
    property int queuedCount: 0
    property string libraryMessage: ""
    property color textColor: "#272b2b"
    property color mutedColor: "#626963"
    property color accentColor: "#1677ff"
    property color errorColor: "#c53030"
    property color surfaceColor: "#f3f5f8"
    signal logsRequested()
    Accessible.name: "Application status"

    background: Rectangle { radius: 7; color: root.surfaceColor }

    ColumnLayout {
        id: content
        width: root.availableWidth
        spacing: 6
        RowLayout {
            Layout.fillWidth: true
            spacing: 6
            BusyIndicator {
                running: root.running
                visible: running
                Layout.preferredWidth: 18
                Layout.preferredHeight: 18
            }
            Label {
                objectName: "activityStatusTitle"
                text: root.running ? root.stage : (root.errorText.length > 0 ? "Task failed" : root.stage)
                color: root.errorText.length > 0 ? root.errorColor : root.textColor
                font.weight: Font.DemiBold
                wrapMode: Text.Wrap
                Layout.fillWidth: true
                Layout.minimumWidth: 0
            }
            ToolButton {
                text: "\u2261"
                Accessible.name: "View task log"
                ToolTip.visible: hovered
                ToolTip.text: Accessible.name
                Layout.preferredWidth: 26
                Layout.preferredHeight: 24
                onClicked: root.logsRequested()
            }
        }
        Label {
            objectName: "queuedStatus"
            visible: root.queuedCount > 0
            text: root.queuedCount + " queued"
            color: root.mutedColor
            wrapMode: Text.Wrap
            Layout.fillWidth: true
        }
        Label {
            objectName: "taskErrorStatus"
            visible: root.errorText.length > 0
            text: root.errorText
            textFormat: Text.PlainText
            color: root.errorColor
            wrapMode: Text.Wrap
            Layout.fillWidth: true
        }
        ProgressBar {
            visible: root.running
            indeterminate: root.running
            Layout.fillWidth: true
            Layout.preferredHeight: 5
        }
        Rectangle { visible: root.libraryMessage.length > 0; Layout.fillWidth: true; implicitHeight: 1; color: root.mutedColor; opacity: 0.2 }
        Label {
            visible: root.libraryMessage.length > 0
            text: "Library"
            color: root.textColor
            font.weight: Font.DemiBold
            Layout.fillWidth: true
        }
        Label {
            objectName: "libraryStatusDetail"
            visible: root.libraryMessage.length > 0
            text: root.libraryMessage
            textFormat: Text.PlainText
            color: root.mutedColor
            wrapMode: Text.Wrap
            Layout.fillWidth: true
        }
    }
}
