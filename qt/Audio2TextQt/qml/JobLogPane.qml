import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Pane {
    id: root
    padding: 0

    property bool expanded: false

    background: Rectangle {
        color: themeController.panelAlt
        border.color: themeController.border
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        RowLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: 34
            Layout.leftMargin: 10
            Layout.rightMargin: 10

            Label {
                text: "Task log"
                color: themeController.text
                font.weight: Font.DemiBold
                Layout.fillWidth: true
            }
            Button {
                text: "Clear"
                visible: root.expanded
                onClicked: jobController.clearLog()
            }
        }

        TextArea {
            visible: root.expanded
            readOnly: true
            selectByMouse: true
            wrapMode: TextEdit.NoWrap
            text: jobController.logText
            font.family: Qt.application.font.family
            font.pixelSize: 12
            color: themeController.text
            Layout.fillWidth: true
            Layout.fillHeight: true
            background: Rectangle {
                color: "#f8fafc"
            }
        }
    }
}
