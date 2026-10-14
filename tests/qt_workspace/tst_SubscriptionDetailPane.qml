import QtQuick
import QtTest
import GeoControls 1.0
import "../../qt/Audio2TextQt/qml" as App

Rectangle {
    id: fixture
    width: 1100
    height: 720
    color: Theme.baseColor
    QtObject {
        id: mockLibrary
        property var selectedSubscription: ({
            id: "feed", title: "A long podcast channel title for responsive layout",
            count: 9, unprocessedCount: 6, processedCount: 3, source: "podcast_rss",
            groupName: "Default", feedURL: "https://example.org/podcasts/feed.xml",
            createdAt: "2026-01-01", lastCheckedAt: "2026-10-14"
        })
        property var subscriptions: [selectedSubscription]
        property var selectedSubscriptionItems: {
            let items = [];
            for (let i = 0; i < 9; ++i) items.push({
                id: "episode-" + i, title: "A detailed episode title that can use the full reading pane width",
                hasProcessed: i < 3, isRead: false, status: "QA pass", queueStatus: "unread",
                modifiedAt: "2026-10-14", sourceURL: "https://example.org/podcasts/episodes/" + i
            });
            return items;
        }
        property string selectedSource: "subscriptions"
        property string openedId: ""
        function selectItem(id) { openedId = id; }
    }
    QtObject {
        id: mockJobs
        property bool running: false
    }
    App.SubscriptionDetailPane {
        id: pane
        anchors.fill: parent
        library: mockLibrary
        jobs: mockJobs
    }

    TestCase {
        name: "SubscriptionDetailPane"
        when: windowShown
        function initTestCase() { failOnWarning(/.*/); }
        function cleanup() { settingsController.appearanceMode = "system"; }
        function test_content_uses_viewport_width_data() {
            return [
                { tag: "narrow", width: 320 },
                { tag: "medium", width: 700 },
                { tag: "wide", width: 1100 }
            ];
        }
        function test_content_uses_viewport_width(data) {
            fixture.width = data.width;
            settingsController.appearanceMode = "dark";
            let scroll = findChild(pane, "subscriptionScroll");
            let content = findChild(pane, "subscriptionContent");
            let stats = findChild(pane, "subscriptionStats");
            let episode = findChild(pane, "subscriptionEpisode_episode-0");
            tryCompare(content, "width", scroll.availableWidth);
            fuzzyCompare(stats.width, content.width, 1);
            fuzzyCompare(episode.width, content.width, 1);
            fuzzyCompare(scroll.contentWidth, scroll.availableWidth, 1);
            verify(scroll.contentHeight > scroll.availableHeight);
            let refreshAll = findChild(pane, "refreshAllSubscriptions");
            tryVerify(function() {
                return refreshAll.mapToItem(pane, refreshAll.width, refreshAll.height).x <= pane.width - 17;
            });
            verify(refreshAll.mapToItem(pane, 0, refreshAll.height).y <= scroll.y);
            let form = findChild(pane, "addSubscriptionForm");
            let add = findChild(pane, "addSubscriptionButton");
            fuzzyCompare(form.width, content.width, 1);
            verify(add.mapToItem(content, add.width, 0).x <= content.width);
            if (captureDirectory.length > 0) {
                wait(150); // Let control color transitions settle before capturing.
                let saved = false;
                verify(pane.grabToImage(function(result) {
                    saved = result.saveToFile(captureDirectory + "/subscription-" + data.tag + ".png");
                }));
                tryVerify(function() { return saved; });
            }
        }
        function test_open_episode_preserves_navigation() {
            let scroll = findChild(pane, "subscriptionScroll");
            scroll.contentItem.contentY = 0;
            let open = findChild(pane, "openSubscriptionEpisode_episode-0");
            mouseClick(open);
            compare(mockLibrary.selectedSource, "library");
            compare(mockLibrary.openedId, "episode-0");
        }
    }
}
