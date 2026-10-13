import QtQuick
import QtQuick.Controls as QQC
import GeoControls 1.0
import QtQuick.Layouts

CustomPane {
    id: root
    padding: 0
    background: Rectangle {
        color: "#fafbfc"
    }

    function isUnprocessedItem(item) {
        return item && !item.hasProcessed;
    }

    function queueStatusLabel(status) {
        if (status === "to_process")
            return "Process";
        if (status === "process_later")
            return "Later";
        if (status === "delete")
            return "Delete";
        return "Unread";
    }

    function queueStatusGlyph(status) {
        if (status === "to_process")
            return "\u25B6";
        if (status === "process_later")
            return "\u25F7";
        if (status === "delete")
            return "\u2715";
        return "\u25CB";
    }

    function queueStatusColor(status) {
        if (status === "to_process")
            return Theme.highlightColor;
        if (status === "process_later")
            return Theme.warningColor;
        if (status === "delete")
            return Theme.errorColor;
        return Theme.placeholderTextColor;
    }

    function statusColor(status) {
        if (status === "Failed" || status === "QA fail")
            return Theme.errorColor;
        if (status === "Processed" || status === "QA pass")
            return Theme.successColor;
        return Theme.warningColor;
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        ColumnLayout {
            Layout.fillWidth: true
            Layout.margins: 10
            spacing: 8

            CustomTextField {
                id: searchField
                alignRightWhenFocused: false
                visible: !libraryController.showingSubscriptions
                placeholderText: "Search"
                text: libraryController.searchText
                onTextChanged: libraryController.searchText = text
                Layout.fillWidth: true
            }

            RowLayout {
                Layout.fillWidth: true
                CustomLabel {
                    text: libraryController.showingSubscriptions ? libraryController.subscriptions.length + " subscriptions" : libraryController.filteredItems.length + " " + libraryController.selectedSourceTitle
                    color: Theme.placeholderTextColor
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }
                CustomCheckBox {
                    visible: !libraryController.showingSubscriptions
                    text: "Archive"
                    checked: libraryController.showArchived
                    onClicked: libraryController.showArchived = checked
                }
                CustomButton {
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

            delegate: CustomItemDelegate {
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
                            item.itemData = itemData;
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

            CustomLabel {
                text: root.queueStatusGlyph(itemData.queueStatus)
                color: root.queueStatusColor(itemData.queueStatus)
                font.pixelSize: 12
                font.weight: Font.DemiBold
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
                Layout.preferredWidth: 18
            }
            CustomLabel {
                text: itemData.title
                color: itemData.isRead ? Theme.placeholderTextColor : Theme.textColor
                font.pixelSize: 13
                font.weight: itemData.isRead ? Font.Normal : Font.DemiBold
                elide: Text.ElideRight
                maximumLineCount: 1
                Layout.fillWidth: true
            }
            CustomLabel {
                visible: itemData.isStarred
                text: "*"
                color: Theme.warningColor
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

                        CustomLabel {
                            anchors.centerIn: parent
                            text: "A"
                            color: Theme.placeholderTextColor
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

                        CustomLabel {
                            anchors.centerIn: parent
                            text: "T"
                            color: Theme.placeholderTextColor
                            font.pixelSize: 7
                            font.weight: Font.DemiBold
                        }
                    }
                }

                CustomLabel {
                    text: itemData.title
                    color: itemData.isRead ? Theme.placeholderTextColor : Theme.textColor
                    font.pixelSize: 13
                    font.weight: itemData.isRead ? Font.Normal : Font.DemiBold
                    elide: Text.ElideRight
                    maximumLineCount: 1
                    Layout.fillWidth: true
                }
                CustomLabel {
                    text: itemData.isStarred ? "*" : ""
                    color: Theme.warningColor
                    Layout.preferredWidth: 12
                }
            }

            CustomLabel {
                text: itemData.seriesName || itemData.source || itemData.groupName
                color: Theme.placeholderTextColor
                font.pixelSize: 12
                elide: Text.ElideRight
                Layout.fillWidth: true
            }

            RowLayout {
                Layout.fillWidth: true
                CustomLabel {
                    text: itemData.status
                    color: root.statusColor(itemData.status)
                    font.pixelSize: 12
                }
                CustomLabel {
                    text: itemData.detail
                    color: Theme.placeholderTextColor
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

            delegate: CustomItemDelegate {
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
                        CustomLabel {
                            text: modelData.source === "xiaoyuzhou" ? "XYZ" : "RSS"
                            color: Theme.highlightColor
                            font.pixelSize: 10
                            font.weight: Font.DemiBold
                            Layout.preferredWidth: 30
                        }
                        CustomLabel {
                            text: modelData.title
                            color: Theme.textColor
                            font.pixelSize: 13
                            font.weight: subscriptionRow.highlighted ? Font.DemiBold : Font.Normal
                            elide: Text.ElideRight
                            Layout.fillWidth: true
                        }
                        CustomLabel {
                            text: modelData.unprocessedCount + "/" + modelData.count
                            color: modelData.unprocessedCount > 0 ? Theme.highlightColor : Theme.placeholderTextColor
                            font.pixelSize: 12
                        }
                    }

                    CustomLabel {
                        text: modelData.groupName + (modelData.lastCheckedAt ? " · " + modelData.lastCheckedAt : "")
                        color: Theme.placeholderTextColor
                        font.pixelSize: 11
                        elide: Text.ElideRight
                        Layout.fillWidth: true
                    }

                    CustomLabel {
                        text: modelData.feedURL || modelData.url || "No URL"
                        color: Theme.placeholderTextColor
                        font.pixelSize: 11
                        elide: Text.ElideMiddle
                        Layout.fillWidth: true
                    }
                }
            }

            CustomLabel {
                anchors.centerIn: parent
                visible: subscriptionList.count === 0
                text: "No subscriptions"
                color: Theme.placeholderTextColor
            }
        }
    }
}
