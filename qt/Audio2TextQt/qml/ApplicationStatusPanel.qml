import QtQuick
import QtQuick.Controls as QQC
import GeoControls 1.0
import QtQuick.Layouts

CustomPane {
    id: root
    objectName: "applicationStatusPanel"
    padding: 10
    implicitHeight: content.implicitHeight + topPadding + bottomPadding
    property bool running: false
    property string stage: "Idle"
    property string errorText: ""
    property int queuedCount: 0
    property string libraryMessage: ""
    property color textColor: Theme.textColor
    property color mutedColor: Theme.placeholderTextColor
    property color accentColor: Theme.highlightColor
    property color errorColor: Theme.errorColor
    property color surfaceColor: Theme.alternateBaseColor
    signal logsRequested
    Accessible.name: "Application status"

    background: Rectangle {
        radius: 7
        color: root.surfaceColor
    }

    ColumnLayout {
        id: content
        width: root.availableWidth
        spacing: 6
        RowLayout {
            Layout.fillWidth: true
            spacing: 6
            CustomBusyIndicator {
                running: root.running
                visible: running
                Layout.preferredWidth: 18
                Layout.preferredHeight: 18
            }
            CustomLabel {
                objectName: "activityStatusTitle"
                text: root.running ? root.stage : (root.errorText.length > 0 ? "Task failed" : root.stage)
                color: root.errorText.length > 0 ? root.errorColor : root.textColor
                font.weight: Font.DemiBold
                wrapMode: Text.Wrap
                Layout.fillWidth: true
                Layout.minimumWidth: 0
            }
            CustomToolButton {
                display: QQC.AbstractButton.TextOnly
                focusPolicy: Qt.StrongFocus
                text: "\u2261"
                Accessible.name: "View task log"
                tooltip: "View task log"
                Layout.preferredWidth: 26
                Layout.preferredHeight: 24
                onClicked: root.logsRequested()
            }
        }
        CustomLabel {
            objectName: "queuedStatus"
            visible: root.queuedCount > 0
            text: root.queuedCount + " queued"
            color: root.mutedColor
            wrapMode: Text.Wrap
            Layout.fillWidth: true
        }
        CustomLabel {
            objectName: "taskErrorStatus"
            visible: root.errorText.length > 0
            text: root.errorText
            textFormat: Text.PlainText
            color: root.errorColor
            wrapMode: Text.Wrap
            Layout.fillWidth: true
        }
        CustomProgressBar {
            visible: root.running
            indeterminate: root.running
            Layout.fillWidth: true
            Layout.preferredHeight: 5
        }
        Rectangle {
            visible: root.libraryMessage.length > 0
            Layout.fillWidth: true
            implicitHeight: 1
            color: root.mutedColor
            opacity: 0.2
        }
        CustomLabel {
            visible: root.libraryMessage.length > 0
            text: "Library"
            color: root.textColor
            font.weight: Font.DemiBold
            Layout.fillWidth: true
        }
        CustomLabel {
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
