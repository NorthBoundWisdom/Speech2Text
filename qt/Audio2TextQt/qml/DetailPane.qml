import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts

Pane {
    id: root
    padding: 0
    background: Rectangle {
        color: themeController.panel
    }

    property var item: libraryController.selectedItem
    property var snapshot: libraryController.selectedSnapshot
    property string currentTab: "metadata"
    property bool srtOverwriteValue: false
    property bool hasSelection: item && item.id !== undefined && item.id !== ""
    property bool isProcessed: hasSelection && item.hasProcessed
    property var processedTabs: [
        { id: "metadata", title: "简介" },
        { id: "summary", title: "摘要" },
        { id: "transcript", title: "转写" },
        { id: "repair", title: "Repair" },
        { id: "glossary", title: "Glossary" },
        { id: "log", title: "Log" }
    ]
    property var unprocessedTabs: [
        { id: "metadata", title: "简介" }
    ]
    property var availableTabs: isProcessed ? processedTabs : unprocessedTabs

    function tabExists(tabId) {
        for (var i = 0; i < availableTabs.length; ++i) {
            if (availableTabs[i].id === tabId)
                return true
        }
        return false
    }

    function selectDefaultTab() {
        if (!hasSelection) {
            currentTab = "metadata"
            return
        }
        if (!isProcessed) {
            currentTab = "metadata"
            return
        }
        if (snapshot.summaryText && snapshot.summaryText.trim().length > 0) {
            currentTab = "summary"
        } else if (snapshot.transcriptText && snapshot.transcriptText.trim().length > 0) {
            currentTab = "transcript"
        } else {
            currentTab = "metadata"
        }
    }

    function bodyTextForTab(tabId) {
        if (!hasSelection)
            return "# Audio2Text\n\nSelect an item from the list."
        if (!snapshot)
            return "Metadata is not available."
        var text = ""
        if (tabId === "metadata")
            text = snapshot.metadataText
        else if (tabId === "summary")
            text = snapshot.summaryText
        else if (tabId === "transcript")
            text = snapshot.transcriptText
        else if (tabId === "repair")
            text = snapshot.repairText
        else if (tabId === "glossary")
            text = snapshot.glossaryText
        else if (tabId === "log")
            text = snapshot.logText
        if (text && text.trim().length > 0)
            return text
        if (tabId === "summary")
            return "Summary is not available yet."
        if (tabId === "transcript")
            return "Transcript is not available yet."
        if (tabId === "repair")
            return "No repair artifacts are available."
        if (tabId === "glossary")
            return "No glossary artifacts are available."
        if (tabId === "log")
            return "No log artifacts are available."
        return "Metadata is not available."
    }

    function hasVisibleChunkProgress() {
        if (!hasSelection || !isProcessed || !snapshot)
            return false
        var progress = snapshot.chunkProgress
        if (progress === undefined || progress === null)
            return false
        progress = String(progress)
        return progress.length > 0 && progress !== "0/0"
    }

    function queueStatusTitle(status) {
        if (status === "to_process")
            return "Process"
        if (status === "process_later")
            return "Later"
        if (status === "delete")
            return "Delete"
        return "Unread"
    }

    function canDownloadAudio() {
        return hasSelection && !isProcessed && !item.hasFile && item.source !== "local" && item.mediaURL
    }

    Connections {
        target: libraryController
        function onSelectedItemChanged() {
            root.selectDefaultTab()
        }
    }

    onAvailableTabsChanged: {
        if (!tabExists(currentTab))
            selectDefaultTab()
    }

    FileDialog {
        id: srtInputDialog
        title: "SRT Input"
        onAccepted: jobController.exportSrtForFile(selectedFile, root.srtOverwriteValue)
    }

    Loader {
        anchors.fill: parent
        sourceComponent: libraryController.showingSubscriptions ? subscriptionDetailComponent : episodeDetailComponent
    }

    Component {
        id: subscriptionDetailComponent
        SubscriptionDetailPane {}
    }

    Component {
        id: episodeDetailComponent

        Loader {
            anchors.fill: parent
            sourceComponent: root.isProcessed ? processedEpisodeComponent : unprocessedEpisodeComponent
        }
    }

    Component {
        id: unprocessedEpisodeComponent

        ColumnLayout {
            spacing: 0

            Rectangle {
                Layout.fillWidth: true
                height: 1
                color: themeController.border
            }

            ColumnLayout {
                Layout.fillWidth: true
                Layout.margins: 14
                spacing: 8

                Label {
                    text: root.hasSelection ? root.item.title : "No episode selected"
                    color: themeController.text
                    font.pixelSize: 20
                    font.weight: Font.DemiBold
                    elide: Text.ElideRight
                    maximumLineCount: 2
                    Layout.fillWidth: true
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8

                    Label {
                        text: root.hasSelection ? root.item.status + " · " + root.queueStatusTitle(root.item.queueStatus) : ""
                        color: themeController.muted
                        elide: Text.ElideRight
                        Layout.fillWidth: true
                    }

                    RowLayout {
                        spacing: 6

                        Repeater {
                            model: [
                                { title: "Unread", value: "unread" },
                                { title: "Process", value: "to_process" },
                                { title: "Later", value: "process_later" },
                                { title: "Delete", value: "delete" }
                            ]

                            delegate: SegmentButton {
                                text: modelData.title
                                selected: root.item.queueStatus === modelData.value
                                implicitWidth: Math.max(72, contentItem.implicitWidth + 22)
                                implicitHeight: 32
                                onClicked: libraryController.setSelectedQueueStatus(modelData.value)
                            }
                        }
                    }

                    Label {
                        visible: root.hasSelection
                        text: root.canDownloadAudio() ? "Remote audio" : (root.item.hasFile ? "Audio ready" : "Audio pending")
                        color: themeController.muted
                        elide: Text.ElideRight
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                height: 1
                color: themeController.border
            }

            MarkdownView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                markdown: root.bodyTextForTab("metadata")
            }
        }
    }

    Component {
        id: processedEpisodeComponent

        ColumnLayout {
            spacing: 0

            Rectangle {
                Layout.fillWidth: true
                height: 1
                color: themeController.border
            }

            ColumnLayout {
                Layout.fillWidth: true
                Layout.margins: 14
                spacing: 8

                Label {
                    text: root.hasSelection ? root.item.title : "No episode selected"
                    color: themeController.text
                    font.pixelSize: 20
                    font.weight: Font.DemiBold
                    elide: Text.ElideRight
                    maximumLineCount: 2
                    Layout.fillWidth: true
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8

                    Label {
                        text: root.hasSelection ? root.item.status + " · " + root.item.groupName : ""
                        color: themeController.muted
                        elide: Text.ElideRight
                        Layout.fillWidth: true
                    }

                    Button {
                        text: "Actions"
                        enabled: root.hasSelection || libraryController.filteredItems.length > 0
                        onClicked: episodeActions.open()

                        Menu {
                            id: episodeActions
                            y: parent.height + 6
                            padding: 8
                            overlap: 0

                            background: Rectangle {
                                radius: 10
                                color: "#fbfcfe"
                                border.color: "#d9e2ec"
                            }

                            ActionMenuItem {
                                text: root.item.isRead ? "Mark Unread" : "Mark Read"
                                enabled: root.hasSelection
                                onTriggered: libraryController.setSelectedRead(!root.item.isRead)
                            }
                            ActionMenuItem {
                                text: root.item.isStarred ? "Unstar" : "Star"
                                enabled: root.hasSelection
                                onTriggered: libraryController.toggleSelectedStar()
                            }
                            ActionMenuItem {
                                text: root.item.isArchived ? "Unarchive" : "Archive"
                                enabled: root.hasSelection
                                onTriggered: libraryController.archiveSelected(!root.item.isArchived)
                            }

                            ActionMenuSeparator {}

                            ActionMenuItem {
                                text: "QA"
                                enabled: root.hasSelection && !jobController.running
                                onTriggered: jobController.qaSelected(root.item)
                            }
                            ActionMenuItem {
                                text: "Repair"
                                enabled: root.hasSelection && !jobController.running
                                onTriggered: jobController.repairSelected(root.item, false)
                            }
                            ActionMenuItem {
                                text: "Prepare Cloud Chunks"
                                enabled: root.hasSelection && !jobController.running
                                onTriggered: jobController.cloudPrepareSelected(root.item)
                            }
                            ActionMenuItem {
                                text: "Cloud Summary"
                                enabled: root.hasSelection && !jobController.running
                                onTriggered: jobController.cloudSummarizeSelected(root.item)
                            }
                            ActionMenuItem {
                                text: "Generate Title"
                                enabled: root.hasSelection && !jobController.running
                                onTriggered: jobController.cloudTitleSelected(root.item)
                            }
                            ActionMenuItem {
                                text: "Glossary Review"
                                enabled: root.hasSelection && !jobController.running
                                onTriggered: jobController.cloudGlossaryReviewSelected(root.item)
                            }
                            ActionMenuItem {
                                text: "Polish"
                                enabled: root.hasSelection && !jobController.running
                                onTriggered: jobController.cloudPolishSelected(root.item)
                            }

                            ActionMenuSeparator {}

                            ActionMenuItem {
                                text: "Overwrite SRT"
                                checkable: true
                                checked: root.srtOverwriteValue
                                onTriggered: root.srtOverwriteValue = checked
                            }
                            ActionMenuItem {
                                text: "Export SRT"
                                enabled: root.hasSelection && !jobController.running
                                onTriggered: jobController.exportSrtForSelected(root.item, root.srtOverwriteValue)
                            }
                            ActionMenuItem {
                                text: "Export SRT From File..."
                                enabled: !jobController.running
                                onTriggered: srtInputDialog.open()
                            }
                        }
                    }
                }

                Label {
                    visible: root.hasVisibleChunkProgress()
                    text: "Chunks " + root.snapshot.chunkProgress + " · Cloud " + root.snapshot.cloudStatus
                    color: themeController.muted
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }
            }

            Rectangle {
                Layout.fillWidth: true
                height: 1
                color: themeController.border
            }

            RowLayout {
                Layout.fillWidth: true
                Layout.margins: 10
                spacing: 6

                Repeater {
                    model: root.availableTabs
                    delegate: SegmentButton {
                        text: modelData.title
                        selected: root.currentTab === modelData.id
                        onClicked: root.currentTab = modelData.id
                    }
                }

                Item { Layout.fillWidth: true }
            }

            MarkdownView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                markdown: root.bodyTextForTab(root.currentTab)
            }
        }
    }

    component SegmentButton: Button {
        id: segment
        property bool selected: false
        checkable: true
        checked: selected
        implicitWidth: Math.max(74, contentItem.implicitWidth + 28)
        implicitHeight: 34

        contentItem: Text {
            text: segment.text
            color: segment.enabled
                ? (segment.selected ? "#ffffff" : themeController.text)
                : themeController.muted
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            font.pixelSize: 14
            font.weight: segment.selected ? Font.DemiBold : Font.Normal
            elide: Text.ElideRight
        }

        background: Rectangle {
            radius: 6
            color: segment.selected
                ? themeController.accent
                : (segment.hovered ? "#eef5ff" : themeController.panelAlt)
            border.color: segment.selected ? themeController.accent : themeController.border
        }
    }

    component ActionMenuItem: MenuItem {
        id: actionItem
        implicitWidth: Math.max(240, implicitContentWidth + leftPadding + rightPadding)
        implicitHeight: visible ? 38 : 0
        leftPadding: 14
        rightPadding: 14
        topPadding: 8
        bottomPadding: 8

        contentItem: RowLayout {
            spacing: 10

            Label {
                text: actionItem.text
                color: actionItem.enabled
                    ? (actionItem.highlighted ? "#0f3d7a" : themeController.text)
                    : "#95a1af"
                font.pixelSize: 14
                font.weight: actionItem.checkable && actionItem.checked ? Font.DemiBold : Font.Normal
                elide: Text.ElideRight
                Layout.fillWidth: true
            }

            Label {
                visible: actionItem.checkable
                text: actionItem.checked ? "✓" : ""
                color: themeController.accent
                font.pixelSize: 13
                font.weight: Font.DemiBold
                horizontalAlignment: Text.AlignRight
                Layout.preferredWidth: 12
            }
        }

        background: Rectangle {
            radius: 8
            color: actionItem.highlighted
                ? "#eaf2ff"
                : (actionItem.hovered ? "#f4f8fc" : "transparent")
            border.color: actionItem.highlighted ? "#d7e5fb" : "transparent"
        }
    }

    component ActionMenuSeparator: MenuSeparator {
        implicitWidth: 240
        topPadding: 6
        bottomPadding: 6
        leftPadding: 0
        rightPadding: 0

        contentItem: Rectangle {
            implicitHeight: 1
            color: "#e4ebf2"
        }
    }
}
