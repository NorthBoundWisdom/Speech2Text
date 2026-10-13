import QtQuick
import QtQuick.Controls

SplitView {
    id: root
    orientation: Qt.Horizontal
    property real sourceWidth: 270
    property real listWidth: 360
    property bool sourceCollapsed: false
    property bool listCollapsed: false
    property Component sourceContent
    property Component listContent
    property Component detailContent
    readonly property real sourceActualWidth: sourcePane.visible ? sourcePane.width : 0
    readonly property real listActualWidth: listPane.visible ? listPane.width : 0
    readonly property real detailActualWidth: detailPane.width

    function rememberWidths() {
        if (!sourceCollapsed && sourcePane.width >= 180)
            sourceWidth = sourcePane.width
        if (!listCollapsed && listPane.width >= 240)
            listWidth = listPane.width
    }

    function toggleSources() {
        rememberWidths()
        sourceCollapsed = !sourceCollapsed
        if (!sourceCollapsed)
            sourcePane.SplitView.preferredWidth = sourceWidth
    }

    function toggleList() {
        rememberWidths()
        listCollapsed = !listCollapsed
        if (!listCollapsed)
            listPane.SplitView.preferredWidth = listWidth
    }

    onResizingChanged: {
        if (!resizing)
            rememberWidths()
    }

    handle: Rectangle {
        id: divider
        implicitWidth: 1
        implicitHeight: 1
        color: SplitHandle.pressed || SplitHandle.hovered ? palette.highlight : palette.mid
        // Keep the divider visually thin while making it easy to grab.
        containmentMask: Item {
            x: (divider.width - width) / 2
            width: 12
            height: root.height
        }
    }

    Loader {
        id: sourcePane
        visible: !root.sourceCollapsed
        sourceComponent: root.sourceContent
        SplitView.preferredWidth: root.sourceWidth
        SplitView.minimumWidth: 180
        SplitView.maximumWidth: 460
    }
    Loader {
        id: listPane
        visible: !root.listCollapsed
        sourceComponent: root.listContent
        SplitView.preferredWidth: root.listWidth
        SplitView.minimumWidth: 240
        SplitView.maximumWidth: 700
    }
    Loader {
        id: detailPane
        sourceComponent: root.detailContent
        SplitView.fillWidth: true
        SplitView.minimumWidth: 320
    }
}
