import QtQuick
import QtQuick.Controls as QQC
import QtQuick.Layouts
import GeoControls 1.0

CustomToolBar {
    id: root
    objectName: "libraryToolBar"
    property bool sourcesVisible: true
    property bool episodeListVisible: true
    property bool statusOpen: false
    readonly property real statusButtonX: statusButton.x + leftPadding
    signal sourcesToggled()
    signal episodeListToggled()
    signal statusRequested()

    implicitHeight: 54
    leftPadding: 12
    rightPadding: 12
    topPadding: 8
    bottomPadding: 9
    background: Rectangle {
        color: Theme.windowColor
        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            height: 1
            color: Theme.dividerColor
            opacity: 0.6
        }
    }

    contentItem: RowLayout {
        spacing: 6
        ToolbarButton {
            objectName: "toggleSourcesButton"
            iconSource: "../resources/icons/sidebar.svg"
            checkable: true
            checked: root.sourcesVisible
            tooltip: root.sourcesVisible ? "Hide Sources" : "Show Sources"
            shortcutSequence: "Ctrl+Shift+S"
            onClicked: root.sourcesToggled()
        }
        ToolbarButton {
            objectName: "toggleEpisodeListButton"
            iconSource: "../resources/icons/episode-list.svg"
            checkable: true
            checked: root.episodeListVisible
            tooltip: root.episodeListVisible ? "Hide Episode List" : "Show Episode List"
            shortcutSequence: "Ctrl+Shift+L"
            onClicked: root.episodeListToggled()
        }
        CustomLabel {
            objectName: "toolbarTitle"
            text: "SonaFolio"
            color: Theme.textColor
            font.pixelSize: 16
            font.weight: Font.DemiBold
            Layout.leftMargin: 6
            Layout.rightMargin: 4
            Layout.alignment: Qt.AlignVCenter
        }
        ToolbarButton {
            id: statusButton
            objectName: "applicationStatusButton"
            iconSource: "../resources/icons/info.svg"
            checked: root.statusOpen
            tooltip: "Library and Processing Status"
            onClicked: root.statusRequested()
        }
        Item { Layout.fillWidth: true }
    }

    component ToolbarButton: CustomToolButton {
        id: button
        display: QQC.AbstractButton.IconOnly
        defaultHeight: 36
        implicitWidth: 38
        defaultPadding: 7
        iconSize: 22
        focusPolicy: Qt.StrongFocus
        handleInCpp: false
        Accessible.name: tooltip
        icon.color: !enabled ? Theme.disabledTextColor : hovered || checked ? Theme.textColor : Theme.placeholderTextColor
        background: Rectangle {
            radius: 7
            color: button.down ? Theme.buttonPressedColor : button.hovered
                ? Theme.buttonHoveredColor : button.checked ? Theme.alternateBaseColor : "transparent"
            border.width: button.visualFocus ? 2 : 0
            border.color: Theme.highlightColor
        }
    }
}
