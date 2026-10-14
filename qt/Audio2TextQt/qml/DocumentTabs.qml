import QtQuick
import QtQuick.Controls as QQC
import GeoControls 1.0

CustomPane {
    id: root
    property var tabs: []
    property string currentTab: "metadata"
    signal tabSelected(string tabId)
    padding: 4
    background: Rectangle {
        radius: 12
        color: Theme.alternateBaseColor
    }

    contentItem: Flow {
        spacing: 4
        Repeater {
            model: root.tabs
            delegate: CustomButton {
                id: tab
                objectName: "documentTab_" + modelData.id
                readonly property bool selected: root.currentTab === modelData.id
                text: modelData.title
                defaultHeight: 32
                defaultPadding: 12
                width: Math.min(implicitWidth, root.availableWidth)
                font.pixelSize: 13
                font.weight: selected ? Font.DemiBold : Font.Normal
                Accessible.role: Accessible.PageTab
                Accessible.name: text
                Accessible.selected: selected
                onClicked: root.tabSelected(modelData.id)
                contentItem: Text {
                    text: tab.text
                    font: tab.font
                    color: tab.selected || tab.hovered ? Theme.textColor : Theme.placeholderTextColor
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    elide: Text.ElideRight
                }
                background: Rectangle {
                    radius: 8
                    color: tab.down ? Theme.buttonPressedColor : tab.selected
                        ? Theme.contentSurfaceColor : tab.hovered ? Theme.buttonHoveredColor : "transparent"
                    border.width: tab.visualFocus ? 2 : 0
                    border.color: Theme.accentColor
                    Behavior on color { ColorAnimation { duration: 120 } }
                }
            }
        }
    }
}
