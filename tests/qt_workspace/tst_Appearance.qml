import QtQuick
import QtTest
import GeoControls 1.0
import "../../qt/Audio2TextQt/qml" as App

Rectangle {
    id: fixture
    width: 720
    height: 520
    color: Theme.baseColor

    App.DocumentTabs {
        id: tabs
        x: 16
        y: 12
        width: fixture.width - 32
        tabs: [
            { id: "metadata", title: "Overview" },
            { id: "summary", title: "Summary" },
            { id: "transcript", title: "Transcript" },
            { id: "repair", title: "Repair" },
            { id: "glossary", title: "Glossary" },
            { id: "log", title: "Log" }
        ]
        currentTab: "transcript"
        onTabSelected: function(tabId) { currentTab = tabId; }
    }
    App.MarkdownView {
        id: readerView
        x: 0
        y: tabs.y + tabs.height + 8
        width: fixture.width
        height: fixture.height - y
        markdown: "# A quieter reading space\n\n"
            + "Clear type, softer tabs, and comfortable contrast for long podcast transcripts.\n\n"
            + "## Episode highlights\n\n- A shared library across desktop frontends.\n"
            + "- Appearance changes immediately and is remembered.\n\n"
            + "> Follow System adapts when the system appearance changes.\n\n"
            + "Visit the [episode page](https://example.org) or copy `a short quote`.\n\n"
            + "```text\nA code sample stays readable in both appearances.\n```"
    }

    TestCase {
        name: "Appearance"
        when: windowShown
        function initTestCase() { failOnWarning(/.*/); }
        function cleanup() {
            Theme.helper.systemColorScheme = Qt.binding(function () { return Qt.styleHints.colorScheme; });
            settingsController.appearanceMode = "system";
            fixture.width = 720;
        }
        function luminance(color) {
            function channel(value) {
                return value <= 0.04045 ? value / 12.92 : Math.pow((value + 0.055) / 1.055, 2.4);
            }
            return 0.2126 * channel(color.r) + 0.7152 * channel(color.g) + 0.0722 * channel(color.b);
        }
        function contrast(a, b) {
            let first = luminance(a), second = luminance(b);
            return (Math.max(first, second) + 0.05) / (Math.min(first, second) + 0.05);
        }
        function capture(name) {
            if (captureDirectory.length === 0) return;
            let saved = false;
            verify(fixture.grabToImage(function(result) {
                saved = result.saveToFile(captureDirectory + "/" + name + ".png");
            }));
            tryVerify(function() { return saved; });
        }
        function test_light_and_dark_text_remain_readable_data() {
            return [{ tag: "light", mode: "light", appearance: 0 }, { tag: "dark", mode: "dark", appearance: 1 }];
        }
        function test_light_and_dark_text_remain_readable(data) {
            settingsController.appearanceMode = data.mode;
            compare(Theme.appearance, data.appearance);
            verify(contrast(Theme.textColor, Theme.baseColor) >= 7);
            verify(contrast(Theme.placeholderTextColor, Theme.baseColor) >= 4.5);
            verify(contrast(Theme.helper.linkColor, Theme.baseColor) >= 4.5);
            let selectedTab = findChild(tabs, "documentTab_" + tabs.currentTab);
            tryCompare(selectedTab.background, "color", Theme.contentSurfaceColor);
            verify(contrast(selectedTab.contentItem.color, selectedTab.background.color) >= 7);
            let reader = findChild(readerView, "markdownReader");
            verify(reader.text.indexOf(Theme.textColor.toString()) >= 0);
            verify(reader.text.indexOf(Theme.helper.linkColor.toString()) >= 0);
            capture("reading-" + data.mode);
        }
        function test_system_changes_and_explicit_override() {
            settingsController.appearanceMode = "system";
            Theme.helper.systemColorScheme = Qt.Light;
            compare(Theme.appearance, 0);
            Theme.helper.systemColorScheme = Qt.Dark;
            compare(Theme.appearance, 1);
            settingsController.appearanceMode = "light";
            compare(Theme.appearance, 0);
            settingsController.appearanceMode = "dark";
            Theme.helper.systemColorScheme = Qt.Light;
            compare(Theme.appearance, 1);
        }
        function test_tabs_wrap_and_support_keyboard_selection() {
            fixture.width = 320;
            verify(waitForRendering(fixture));
            let logTab = findChild(tabs, "documentTab_log");
            verify(logTab.mapToItem(tabs, logTab.width, 0).x <= tabs.width);
            verify(tabs.height > 40);
            mouseClick(logTab);
            compare(tabs.currentTab, "log");
            let summaryTab = findChild(tabs, "documentTab_summary");
            summaryTab.forceActiveFocus();
            keyClick(Qt.Key_Space);
            compare(tabs.currentTab, "summary");
        }
    }
}
