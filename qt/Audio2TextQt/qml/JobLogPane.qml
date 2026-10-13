import QtQuick
import QtQuick.Controls as QQC
import GeoControls 1.0
import QtQuick.Layouts

CustomPane {
    id: root
    padding: 0

    property bool expanded: false

    background: Rectangle {
        color: Theme.alternateBaseColor
        border.color: Theme.dividerColor
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        RowLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: 34
            Layout.leftMargin: 10
            Layout.rightMargin: 10

            CustomLabel {
                text: "Task log"
                color: Theme.textColor
                font.weight: Font.DemiBold
                Layout.fillWidth: true
            }
            CustomButton {
                text: "Clear"
                visible: root.expanded
                onClicked: jobController.clearLog()
            }
        }

        CustomTextArea {
            visible: root.expanded
            readOnly: true
            selectByMouse: true
            wrapMode: TextEdit.NoWrap
            text: jobController.logText
            font.family: Qt.application.font.family
            font.pixelSize: 12
            color: Theme.textColor
            Layout.fillWidth: true
            Layout.fillHeight: true
            background: Rectangle {
                color: Theme.contentSurfaceColor
            }
        }
    }
}
