import QtQuick
import QtQuick.Controls as QQC
import GeoControls 1.0
import QtQuick.Layouts

CustomPane {
    id: root
    padding: 0
    background: Rectangle {
        color: Theme.baseColor
    }

    property var item: libraryController.selectedItem
    property var snapshot: libraryController.selectedSnapshot
    property string currentTab: "metadata"
    property bool srtOverwriteValue: false
    property bool hasSelection: item && item.id !== undefined && item.id !== ""
    property bool isProcessed: hasSelection && item.hasProcessed
    property var processedTabs: [
        {
            id: "metadata",
            title: "Overview"
        },
        {
            id: "summary",
            title: "Summary"
        },
        {
            id: "transcript",
            title: "Transcript"
        },
        {
            id: "repair",
            title: "Repair"
        },
        {
            id: "glossary",
            title: "Glossary"
        },
        {
            id: "log",
            title: "Log"
        }
    ]
    property var unprocessedTabs: [
        {
            id: "metadata",
            title: "Overview"
        }
    ]
    property var availableTabs: isProcessed ? processedTabs : unprocessedTabs

    function tabExists(tabId) {
        for (var i = 0; i < availableTabs.length; ++i) {
            if (availableTabs[i].id === tabId)
                return true;
        }
        return false;
    }

    function selectDefaultTab() {
        if (!hasSelection) {
            currentTab = "metadata";
            return;
        }
        if (!isProcessed) {
            currentTab = "metadata";
            return;
        }
        if (snapshot.summaryText && snapshot.summaryText.trim().length > 0) {
            currentTab = "summary";
        } else if (snapshot.transcriptText && snapshot.transcriptText.trim().length > 0) {
            currentTab = "transcript";
        } else {
            currentTab = "metadata";
        }
    }

    function bodyTextForTab(tabId) {
        if (!hasSelection)
            return "# SonaFolio\n\nSelect an item from the list.";
        if (!snapshot)
            return "Metadata is not available.";
        var text = "";
        if (tabId === "metadata")
            text = snapshot.metadataText;
        else if (tabId === "summary")
            text = snapshot.summaryText;
        else if (tabId === "transcript")
            text = snapshot.transcriptText;
        else if (tabId === "repair")
            text = snapshot.repairText;
        else if (tabId === "glossary")
            text = snapshot.glossaryText;
        else if (tabId === "log")
            text = snapshot.logText;
        if (text && text.trim().length > 0)
            return text;
        if (tabId === "summary")
            return "Summary is not available yet.";
        if (tabId === "transcript")
            return "Transcript is not available yet.";
        if (tabId === "repair")
            return "No repair artifacts are available.";
        if (tabId === "glossary")
            return "No glossary artifacts are available.";
        if (tabId === "log")
            return "No log artifacts are available.";
        return "Metadata is not available.";
    }

    function hasVisibleChunkProgress() {
        if (!hasSelection || !isProcessed || !snapshot)
            return false;
        var progress = snapshot.chunkProgress;
        if (progress === undefined || progress === null)
            return false;
        progress = String(progress);
        return progress.length > 0 && progress !== "0/0";
    }

    function queueStatusTitle(status) {
        if (status === "to_process")
            return "Process";
        if (status === "process_later")
            return "Later";
        if (status === "delete")
            return "Delete";
        return "Unread";
    }

    function canDownloadAudio() {
        return hasSelection && !isProcessed && !item.hasFile && item.source !== "local" && item.mediaURL;
    }

    Connections {
        target: libraryController
        function onSelectedItemChanged() {
            root.selectDefaultTab();
        }
    }

    onAvailableTabsChanged: {
        if (!tabExists(currentTab))
            selectDefaultTab();
    }

    CustomFileDialog {
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
                color: Theme.dividerColor
            }

            ColumnLayout {
                Layout.fillWidth: true
                Layout.margins: 14
                spacing: 8

                CustomLabel {
                    text: root.hasSelection ? root.item.title : "No episode selected"
                    color: Theme.textColor
                    font.pixelSize: 20
                    font.weight: Font.DemiBold
                    elide: Text.ElideRight
                    maximumLineCount: 2
                    Layout.fillWidth: true
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8

                    CustomLabel {
                        text: root.hasSelection ? root.item.status + " · " + root.queueStatusTitle(root.item.queueStatus) : ""
                        color: Theme.placeholderTextColor
                        elide: Text.ElideRight
                        Layout.fillWidth: true
                    }

                    RowLayout {
                        spacing: 6

                        Repeater {
                            model: [
                                {
                                    title: "Unread",
                                    value: "unread"
                                },
                                {
                                    title: "Process",
                                    value: "to_process"
                                },
                                {
                                    title: "Later",
                                    value: "process_later"
                                },
                                {
                                    title: "Delete",
                                    value: "delete"
                                }
                            ]

                    delegate: QueueStatusButton {
                                text: modelData.title
                                selected: root.item.queueStatus === modelData.value
                                implicitWidth: Math.max(72, contentItem.implicitWidth + 22)
                                implicitHeight: 32
                                onClicked: libraryController.setSelectedQueueStatus(modelData.value)
                            }
                        }
                    }

                    CustomLabel {
                        visible: root.hasSelection
                        text: root.canDownloadAudio() ? "Remote audio" : (root.item.hasFile ? "Audio ready" : "Audio pending")
                        color: Theme.placeholderTextColor
                        elide: Text.ElideRight
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                height: 1
                color: Theme.dividerColor
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
                color: Theme.dividerColor
            }

            ColumnLayout {
                Layout.fillWidth: true
                Layout.margins: 14
                spacing: 8

                CustomLabel {
                    text: root.hasSelection ? root.item.title : "No episode selected"
                    color: Theme.textColor
                    font.pixelSize: 20
                    font.weight: Font.DemiBold
                    elide: Text.ElideRight
                    maximumLineCount: 2
                    Layout.fillWidth: true
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8

                    CustomLabel {
                        text: root.hasSelection ? root.item.status + " · " + root.item.groupName : ""
                        color: Theme.placeholderTextColor
                        elide: Text.ElideRight
                        Layout.fillWidth: true
                    }

                    CustomButton {
                        text: "Actions"
                        enabled: root.hasSelection || libraryController.filteredItems.length > 0
                        onClicked: episodeActions.open()

                        CustomMenu {
                            id: episodeActions
                            y: parent.height + 6
                            padding: 8
                            menuWidth: 260

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

                CustomLabel {
                    visible: root.hasVisibleChunkProgress()
                    text: "Chunks " + root.snapshot.chunkProgress + " · Cloud " + root.snapshot.cloudStatus
                    color: Theme.placeholderTextColor
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }
            }

            Rectangle {
                Layout.fillWidth: true
                height: 1
                color: Theme.dividerColor
            }

            DocumentTabs {
                Layout.fillWidth: true
                Layout.margins: 10
                tabs: root.availableTabs
                currentTab: root.currentTab
                onTabSelected: function(tabId) { root.currentTab = tabId; }
            }

            MarkdownView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                markdown: root.bodyTextForTab(root.currentTab)
            }
        }
    }

    component QueueStatusButton: CustomButton {
        property bool selected: false
        checkable: true
        checked: selected
        defaultHeight: 32
        defaultPadding: 12
        defaultRadius: 8
        borderWidth: 0
        font.pixelSize: 13
        buttonTextColor: Theme.textColor
        highlightColor: Theme.actionButtonHoveredColor
    }

    component ActionMenuItem: CustomMenuItem {
        implicitHeight: visible ? Math.max(38, Fonts.listItemHeight) : 0
    }

    component ActionMenuSeparator: CustomMenuSeparator {}
}
