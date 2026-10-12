import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Pane {
    id: root
    padding: 0
    background: Rectangle {
        color: "#fafbfc"
    }

    function isUnprocessedItem(item) {
        return item && !item.hasProcessed
    }

    function queueStatusLabel(status) {
        if (status === "to_process")
            return "Process"
        if (status === "process_later")
            return "Later"
        if (status === "delete")
            return "Delete"
        return "Unread"
    }

    function queueStatusGlyph(status) {
        if (status === "to_process")
            return "\u25B6"
        if (status === "process_later")
            return "\u25F7"
        if (status === "delete")
            return "\u2715"
        return "\u25CB"
    }

    function queueStatusColor(status) {
        if (status === "to_process")
            return themeController.accent
        if (status === "process_later")
            return themeController.warning
        if (status === "delete")
            return themeController.danger
        return themeController.muted
    }

    function statusColor(status) {
        if (status === "Failed" || status === "QA fail")
            return themeController.danger
        if (status === "Processed" || status === "QA pass")
            return themeController.success
        return themeController.warning
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        ColumnLayout {
            Layout.fillWidth: true
            Layout.margins: 10
            spacing: 8

            TextField {
                id: searchField
                visible: !libraryController.showingSubscriptions
                placeholderText: "Search"
                text: libraryController.searchText
                onTextChanged: libraryController.searchText = text
                Layout.fillWidth: true
            }

            RowLayout {
                Layout.fillWidth: true
                Label {
                    text: libraryController.showingSubscriptions
                        ? libraryController.subscriptions.length + " subscriptions"
                        : libraryController.filteredItems.length + " " + libraryController.selectedSourceTitle
                    color: themeController.muted
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }
                CheckBox {
                    visible: !libraryController.showingSubscriptions
                    text: "Archive"
                    checked: libraryController.showArchived
                    onToggled: libraryController.showArchived = checked
                }
                Button {
                    visible: libraryController.showingSubscriptions
                    text: "Refresh"
                    enabled: libraryController.subscriptions.length > 0 && !jobController.running
                    onClicked: jobController.refreshSubscriptions(true, "", 0)
                }
            }
        }

        Loader {
            Layout.fillWidth: true
            Layout.fillHeight: true
            sourceComponent: libraryController.showingSubscriptions ? subscriptionsComponent : itemsComponent
        }
    }

    Component {
        id: itemsComponent

        ListView {
            id: itemList
            clip: true
            model: libraryController.filteredItems

            delegate: ItemDelegate {
                id: row
                width: itemList.width
                height: root.isUnprocessedItem(modelData) ? 38 : 82
                leftPadding: 14
                rightPadding: 18
                topPadding: root.isUnprocessedItem(modelData) ? 5 : 8
                bottomPadding: root.isUnprocessedItem(modelData) ? 5 : 8
                highlighted: libraryController.selectedItem.id === modelData.id
                onClicked: libraryController.selectItem(modelData.id)

                background: Rectangle {
                    color: row.highlighted ? "#eaf2ff" : (row.hovered ? "#f0f3f7" : "transparent")
                }

                contentItem: Loader {
                    id: contentLoader
                    property var itemData: modelData
                    sourceComponent: root.isUnprocessedItem(modelData) ? unprocessedItemContent : processedItemContent
                    onLoaded: {
                        if (item && Object.prototype.hasOwnProperty.call(item, "itemData"))
                            item.itemData = itemData
                    }
                }
            }
        }
    }

    Component {
        id: unprocessedItemContent

        RowLayout {
            property var itemData
            spacing: 8

            Label {
                text: root.queueStatusGlyph(itemData.queueStatus)
                color: root.queueStatusColor(itemData.queueStatus)
                font.pixelSize: 12
                font.weight: Font.DemiBold
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
                Layout.preferredWidth: 18
            }
            Label {
                text: itemData.title
                color: itemData.isRead ? themeController.muted : themeController.text
                font.pixelSize: 13
                font.weight: itemData.isRead ? Font.Normal : Font.DemiBold
                elide: Text.ElideRight
                maximumLineCount: 1
                Layout.fillWidth: true
            }
            Label {
                visible: itemData.isStarred
                text: "*"
                color: themeController.warning
                Layout.preferredWidth: visible ? 12 : 0
            }
        }
    }

    Component {
        id: processedItemContent

        ColumnLayout {
            property var itemData
            spacing: 4

            RowLayout {
                Layout.fillWidth: true
                RowLayout {
                    spacing: 3
                    Layout.preferredWidth: 28

                    Rectangle {
                        visible: itemData.hasFile
                        width: visible ? 10 : 0
                        height: 10
                        radius: 5
                        color: "#dfe7f2"
                        border.color: "#c8d4e3"
                        Layout.alignment: Qt.AlignVCenter

                        Label {
                            anchors.centerIn: parent
                            text: "A"
                            color: themeController.muted
                            font.pixelSize: 7
                            font.weight: Font.DemiBold
                        }
                    }

                    Rectangle {
                        visible: itemData.hasTranscript
                        width: visible ? 10 : 0
                        height: 10
                        radius: 5
                        color: "#dfe7f2"
                        border.color: "#c8d4e3"
                        Layout.alignment: Qt.AlignVCenter

                        Label {
                            anchors.centerIn: parent
                            text: "T"
                            color: themeController.muted
                            font.pixelSize: 7
                            font.weight: Font.DemiBold
                        }
                    }
                }

                Label {
                    text: itemData.title
                    color: itemData.isRead ? themeController.muted : themeController.text
                    font.pixelSize: 13
                    font.weight: itemData.isRead ? Font.Normal : Font.DemiBold
                    elide: Text.ElideRight
                    maximumLineCount: 1
                    Layout.fillWidth: true
                }
                Label {
                    text: itemData.isStarred ? "*" : ""
                    color: themeController.warning
                    Layout.preferredWidth: 12
                }
            }

            Label {
                text: itemData.seriesName || itemData.source || itemData.groupName
                color: themeController.muted
                font.pixelSize: 12
                elide: Text.ElideRight
                Layout.fillWidth: true
            }

            RowLayout {
                Layout.fillWidth: true
                Label {
                    text: itemData.status
                    color: root.statusColor(itemData.status)
                    font.pixelSize: 12
                }
                Label {
                    text: itemData.detail
                    color: themeController.muted
                    font.pixelSize: 12
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }
            }
        }
    }

    Component {
        id: subscriptionsComponent

        ListView {
            id: subscriptionList
            clip: true
            model: libraryController.subscriptions

            delegate: ItemDelegate {
                id: subscriptionRow
                width: subscriptionList.width
                height: 84
                leftPadding: 14
                rightPadding: 18
                topPadding: 8
                bottomPadding: 8
                highlighted: libraryController.selectedSubscriptionId === modelData.id
                onClicked: libraryController.selectSubscription(modelData.id)

                background: Rectangle {
                    color: subscriptionRow.highlighted ? "#eaf2ff" : (subscriptionRow.hovered ? "#f0f3f7" : "transparent")
                }

                contentItem: ColumnLayout {
                    spacing: 4

                    RowLayout {
                        Layout.fillWidth: true
                        Label {
                            text: modelData.source === "xiaoyuzhou" ? "XYZ" : "RSS"
                            color: themeController.accent
                            font.pixelSize: 10
                            font.weight: Font.DemiBold
                            Layout.preferredWidth: 30
                        }
                        Label {
                            text: modelData.title
                            color: themeController.text
                            font.pixelSize: 13
                            font.weight: subscriptionRow.highlighted ? Font.DemiBold : Font.Normal
                            elide: Text.ElideRight
                            Layout.fillWidth: true
                        }
                        Label {
                            text: modelData.unprocessedCount + "/" + modelData.count
                            color: modelData.unprocessedCount > 0 ? themeController.accent : themeController.muted
                            font.pixelSize: 12
                        }
                    }

                    Label {
                        text: modelData.groupName + (modelData.lastCheckedAt ? " · " + modelData.lastCheckedAt : "")
                        color: themeController.muted
                        font.pixelSize: 11
                        elide: Text.ElideRight
                        Layout.fillWidth: true
                    }

                    Label {
                        text: modelData.feedURL || modelData.url || "No URL"
                        color: themeController.muted
                        font.pixelSize: 11
                        elide: Text.ElideMiddle
                        Layout.fillWidth: true
                    }
                }
            }

            Label {
                anchors.centerIn: parent
                visible: subscriptionList.count === 0
                text: "No subscriptions"
                color: themeController.muted
            }
        }
    }
}
