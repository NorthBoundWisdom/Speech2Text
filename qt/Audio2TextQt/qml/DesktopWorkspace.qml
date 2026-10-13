import QtQuick
import QtQuick.Controls as QQC
import GeoControls 1.0

CustomSplitView {
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
            sourceWidth = sourcePane.width;
        if (!listCollapsed && listPane.width >= 240)
            listWidth = listPane.width;
    }

    function toggleSources() {
        rememberWidths();
        sourceCollapsed = !sourceCollapsed;
        if (!sourceCollapsed)
            sourcePane.QQC.SplitView.preferredWidth = sourceWidth;
    }

    function toggleList() {
        rememberWidths();
        listCollapsed = !listCollapsed;
        if (!listCollapsed)
            listPane.QQC.SplitView.preferredWidth = listWidth;
    }

    onResizingChanged: {
        if (!resizing)
            rememberWidths();
    }

    Loader {
        id: sourcePane
        visible: !root.sourceCollapsed
        sourceComponent: root.sourceContent
        QQC.SplitView.preferredWidth: root.sourceWidth
        QQC.SplitView.minimumWidth: 180
        QQC.SplitView.maximumWidth: 460
    }
    Loader {
        id: listPane
        visible: !root.listCollapsed
        sourceComponent: root.listContent
        QQC.SplitView.preferredWidth: root.listWidth
        QQC.SplitView.minimumWidth: 240
        QQC.SplitView.maximumWidth: 700
    }
    Loader {
        id: detailPane
        sourceComponent: root.detailContent
        QQC.SplitView.fillWidth: true
        QQC.SplitView.minimumWidth: 320
    }
}
