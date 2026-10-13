import QtQuick
import QtTest
import "../../qt/Audio2TextQt/qml"

Item {
    width: 1320
    height: 680
    DesktopWorkspace {
        id: workspace
        anchors.fill: parent
        sourceContent: Component { Rectangle { color: "#eeeeee" } }
        listContent: Component { Rectangle { color: "#fafafa" } }
        detailContent: Component { Rectangle { color: "#ffffff" } }
    }

    TestCase {
        name: "DesktopWorkspace"
        when: windowShown

        function settle() { waitForRendering(workspace) }
        function init() {
            if (workspace.sourceCollapsed) workspace.toggleSources()
            if (workspace.listCollapsed) workspace.toggleList()
            settle()
        }
        function test_collapsing_both_columns_and_restoring_widths() {
            var sourceWidth = workspace.sourceActualWidth
            var listWidth = workspace.listActualWidth
            workspace.toggleSources()
            settle()
            compare(workspace.sourceActualWidth, 0)
            verify(workspace.detailActualWidth >= 320)
            workspace.toggleList()
            settle()
            compare(workspace.listActualWidth, 0)
            fuzzyCompare(workspace.detailActualWidth, workspace.width, 1)
            workspace.toggleSources()
            workspace.toggleList()
            settle()
            fuzzyCompare(workspace.sourceActualWidth, sourceWidth, 1)
            fuzzyCompare(workspace.listActualWidth, listWidth, 1)
        }
        function test_divider_drags_resize_both_columns() {
            var beforeSource = workspace.sourceActualWidth
            mouseDrag(workspace, beforeSource, 180, 40, 0)
            settle()
            verify(workspace.sourceActualWidth > beforeSource + 20)
            var beforeList = workspace.listActualWidth
            mouseDrag(workspace, workspace.sourceActualWidth + beforeList + 1, 180, 45, 0)
            settle()
            verify(workspace.listActualWidth > beforeList + 20)
            fuzzyCompare(workspace.sourceWidth, workspace.sourceActualWidth, 1)
            fuzzyCompare(workspace.listWidth, workspace.listActualWidth, 1)
        }
        function test_narrow_window_keeps_reader_inside_viewport() {
            parent.width = 980
            settle()
            verify(workspace.detailActualWidth >= 320)
            verify(workspace.sourceActualWidth + workspace.listActualWidth + workspace.detailActualWidth <= 980)
            parent.width = 1320
            settle()
        }
    }
}
