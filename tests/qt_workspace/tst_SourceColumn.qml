import QtQuick
import QtTest
import GeoControls 1.0
import "../../qt/Audio2TextQt/qml" as App

Rectangle {
    id: fixture
    width: 270
    height: 740
    color: Theme.pageSurfaceColor
    QtObject {
        id: library
        property var items: []
        property string selectedSource: "library"
        property string statusMessage: "42 episodes, 3 groups, 2 subscriptions"
        property var sources: [
            { id: "library", title: "Library", kind: "root", count: 42 },
            { id: "subscriptions", title: "Subscriptions", kind: "root", count: 2 },
            { id: "smart:today", title: "Today", kind: "smart", count: 0 },
            { id: "smart:unprocessed", title: "Unprocessed", kind: "smart", count: 31 },
            { id: "smart:processed", title: "Processed", kind: "smart", count: 11 },
            { id: "smart:starred", title: "Starred", kind: "smart", count: 1 },
            { id: "smart:archive", title: "Archive", kind: "smart", count: 0 },
            { id: "group:Default", title: "Default", kind: "group", count: 42 },
            { id: "group:Research", title: "Research", kind: "group", count: 0 },
            { id: "group:Travel", title: "Travel", kind: "group", count: 0 }
        ]
    }
    QtObject {
        id: jobs
        property bool running: false
        property string stage: "Idle"
        property string lastError: ""
        property int queuedJobCount: 0
    }
    App.SourceColumn {
        id: sidebar
        anchors.fill: parent
        library: library
        jobs: jobs
    }

    TestCase {
        name: "SourceColumn"
        when: windowShown
        function initTestCase() { failOnWarning(/.*/); }
        function cleanup() {
            settingsController.appearanceMode = "system";
            library.selectedSource = "library";
            fixture.width = 270;
        }
        function test_compact_sidebar_data() {
            return [{ tag: "light", mode: "light" }, { tag: "dark", mode: "dark" }];
        }
        function test_compact_sidebar(data) {
            settingsController.appearanceMode = data.mode;
            let selected = findChild(sidebar, "sourceRow_library");
            let subscriptions = findChild(sidebar, "sourceRow_subscriptions");
            let emptyFolder = findChild(sidebar, "sidebarTitle_group:Research");
            let lastFolder = findChild(sidebar, "sourceRow_group:Travel");
            verify(selected && subscriptions && emptyFolder && lastFolder);
            compare(selected.height, 32);
            verify(subscriptions.y < selected.y);
            compare(findChild(sidebar, "sidebarTitle_library").color, Theme.highlightedTextColor);
            compare(selected.background.color, Theme.highlightColor);
            compare(emptyFolder.color, Theme.textColor);
            compare(emptyFolder.opacity, 1);
            verify(lastFolder.mapToItem(sidebar, 0, lastFolder.height).y <= sidebar.height);
            if (captureDirectory.length > 0) {
                let saved = false;
                verify(sidebar.grabToImage(function(result) {
                    saved = result.saveToFile(captureDirectory + "/sidebar-" + data.mode + ".png");
                }));
                tryVerify(function() { return saved; });
            }
        }
        function test_narrow_sidebar_keeps_counts_and_labels_separate() {
            fixture.width = 180;
            let title = findChild(sidebar, "sidebarTitle_smart:unprocessed");
            let count = findChild(sidebar, "sidebarCount_smart:unprocessed");
            tryVerify(function() { return title.width > 30; });
            verify(title.mapToItem(sidebar, title.width, 0).x < count.mapToItem(sidebar, 0, 0).x);
            verify(count.mapToItem(sidebar, count.width, 0).x <= sidebar.width - 10);
        }
        function test_mouse_and_keyboard_select_sources() {
            let subscriptions = findChild(sidebar, "sourceRow_subscriptions");
            mouseClick(subscriptions);
            compare(library.selectedSource, "subscriptions");
            let research = findChild(sidebar, "sourceRow_group:Research");
            research.forceActiveFocus();
            keyClick(Qt.Key_Space);
            compare(library.selectedSource, "group:Research");
        }
    }
}
