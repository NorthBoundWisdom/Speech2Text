import QtQuick
import QtQuick.Controls as QQC
import QtTest
import "../../qt/Audio2TextQt/qml" as App

Item {
    id: fixture
    width: 1320
    height: 680

    Rectangle {
        anchors.fill: view
        color: "white"
    }

    App.MarkdownView {
        id: view
        width: 640
        height: 500
        markdown: "# A long episode title that should wrap within the reading area\n\n"
            + ("A paragraph near the right edge with a long link https://example.org/"
               + "averylongunbrokentextsegment".repeat(8) + "\n\n").repeat(20)
    }

    TestCase {
        name: "MarkdownView"
        when: windowShown

        function initTestCase() {
            failOnWarning(/.*/);
        }

        function test_reader_keeps_both_margins_data() {
            return [
                { tag: "narrow", width: 320 },
                { tag: "default", width: 690 },
                { tag: "wide", width: 1320 }
            ];
        }

        function test_reader_keeps_both_margins(data) {
            view.width = data.width;
            verify(waitForRendering(view));
            let reader = findChild(view, "markdownReader");
            verify(reader);
            let left = reader.mapToItem(view, 0, 0).x;
            let right = reader.mapToItem(view, reader.width, 0).x;
            verify(left >= 24, "Missing left reading margin: " + left);
            verify(right <= view.width - 24, "Text extends into the right margin: " + right);
            verify(reader.width <= view.contentMaxWidth);
            fuzzyCompare(left, view.width - right, 1);
            verify(view.contentHeight > view.height);
            fuzzyCompare(view.contentWidth, view.availableWidth, 1);
            compare(view.QQC.ScrollBar.horizontal.policy, QQC.ScrollBar.AlwaysOff);
            if (captureDirectory.length > 0) {
                let saved = false;
                verify(view.grabToImage(function (result) {
                    saved = result.saveToFile(captureDirectory + "/markdown-" + data.tag + ".png");
                }));
                tryVerify(function () { return saved; });
            }
        }

        function test_resize_preserves_vertical_scrolling() {
            view.width = 690;
            verify(waitForRendering(view));
            let reader = findChild(view, "markdownReader");
            let wideHeight = reader.height;
            view.width = 320;
            verify(waitForRendering(view));
            verify(reader.height > wideHeight);
            view.contentItem.contentY = 100;
            view.markdown = "# Another episode\n\nNew content.";
            tryCompare(view.contentItem, "contentY", 0);
        }
    }
}
