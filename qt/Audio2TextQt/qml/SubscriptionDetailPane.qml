import QtQuick
import QtQuick.Controls as QQC
import GeoControls 1.0
import QtQuick.Layouts

CustomPane {
    id: root
    padding: 0
    property var library: libraryController
    property var jobs: jobController
    readonly property bool narrow: width < 700
    readonly property bool stackedStats: width < 420
    background: Rectangle {
        color: Theme.baseColor
    }

    property var subscription: library.selectedSubscription
    property var episodes: library.selectedSubscriptionItems
    property bool hasSubscription: subscription && subscription.id !== undefined && subscription.id !== ""

    function displayUrl(sub) {
        if (!sub)
            return "No URL";
        if (sub.feedURL && sub.feedURL.length > 0)
            return sub.feedURL;
        if (sub.url && sub.url.length > 0)
            return sub.url;
        return "No URL";
    }

    function emptyAware(value) {
        return value && value.length > 0 ? value : "None";
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        GridLayout {
            columns: root.narrow ? 1 : 2
            Layout.fillWidth: true
            Layout.margins: 18
            columnSpacing: 10
            rowSpacing: 10

            ColumnLayout {
                spacing: 2
                Layout.fillWidth: true
                Layout.minimumWidth: 0
                CustomLabel {
                    text: root.hasSubscription ? root.subscription.title : "Subscriptions"
                    color: Theme.textColor
                    font.pixelSize: 20
                    font.weight: Font.DemiBold
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }
                CustomLabel {
                    text: root.hasSubscription ? root.subscription.count + " episodes · " + root.subscription.unprocessedCount + " unprocessed" : (root.library.subscriptions.length === 0 ? "No subscriptions yet" : root.library.subscriptions.length + " subscriptions")
                    color: Theme.placeholderTextColor
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }
            }

            Flow {
                spacing: 8
                Layout.fillWidth: root.narrow
                Layout.minimumWidth: 0
                Layout.preferredWidth: refreshButton.implicitWidth + historyButton.implicitWidth
                    + removeButton.implicitWidth + refreshAllButton.implicitWidth + spacing * 3
                CustomButton {
                    id: refreshButton
                    objectName: "refreshSubscription"
                    text: "Refresh"
                    enabled: root.hasSubscription && !root.jobs.running
                    onClicked: root.jobs.refreshSubscriptions(false, root.subscription.id, 20)
                }
                CustomButton {
                    id: historyButton
                    text: "History"
                    enabled: root.hasSubscription && !root.jobs.running
                    onClicked: root.jobs.refreshSubscriptions(false, root.subscription.id, 0)
                }
                CustomButton {
                    id: removeButton
                    text: "Remove"
                    enabled: root.hasSubscription && !root.jobs.running
                    onClicked: root.jobs.removeSubscription(root.subscription.id)
                }
                CustomButton {
                    id: refreshAllButton
                    objectName: "refreshAllSubscriptions"
                    text: "Refresh All"
                    enabled: root.library.subscriptions.length > 0 && !root.jobs.running
                    onClicked: root.jobs.refreshSubscriptions(true, "", 20)
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            height: 1
            color: Theme.dividerColor
        }

        CustomScrollView {
            id: subscriptionScroll
            objectName: "subscriptionScroll"
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            padding: 22
            contentWidth: availableWidth
            contentHeight: subscriptionContent.implicitHeight

            ColumnLayout {
                id: subscriptionContent
                objectName: "subscriptionContent"
                width: subscriptionScroll.availableWidth
                height: implicitHeight
                spacing: 18

                GridLayout {
                    objectName: "subscriptionStats"
                    columns: root.stackedStats ? 1 : 3
                    visible: root.hasSubscription
                    Layout.fillWidth: true
                    columnSpacing: 12
                    rowSpacing: 12

                    Rectangle {
                        radius: 8
                        color: Theme.railSurfaceColor
                        Layout.fillWidth: true
                        Layout.minimumWidth: 0
                        Layout.preferredWidth: 1
                        Layout.preferredHeight: root.stackedStats ? 64 : 84
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: root.stackedStats ? 8 : 12
                            CustomLabel {
                                text: root.subscription.count
                                color: Theme.textColor
                                font.pixelSize: 24
                                font.weight: Font.DemiBold
                            }
                            CustomLabel {
                                text: "Episodes"
                                color: Theme.placeholderTextColor
                                font.pixelSize: 12
                                Layout.fillWidth: true
                                Layout.minimumWidth: 0
                                wrapMode: Text.Wrap
                            }
                        }
                    }
                    Rectangle {
                        radius: 8
                        color: Theme.actionButtonHoveredColor
                        Layout.fillWidth: true
                        Layout.minimumWidth: 0
                        Layout.preferredWidth: 1
                        Layout.preferredHeight: root.stackedStats ? 64 : 84
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: root.stackedStats ? 8 : 12
                            CustomLabel {
                                text: root.subscription.unprocessedCount
                                color: Theme.accentColor
                                font.pixelSize: 24
                                font.weight: Font.DemiBold
                            }
                            CustomLabel {
                                text: "Unprocessed"
                                color: Theme.placeholderTextColor
                                font.pixelSize: 12
                                Layout.fillWidth: true
                                Layout.minimumWidth: 0
                                wrapMode: Text.Wrap
                            }
                        }
                    }
                    Rectangle {
                        radius: 8
                        color: Theme.railSurfaceColor
                        Layout.fillWidth: true
                        Layout.minimumWidth: 0
                        Layout.preferredWidth: 1
                        Layout.preferredHeight: root.stackedStats ? 64 : 84
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: root.stackedStats ? 8 : 12
                            CustomLabel {
                                text: root.subscription.processedCount
                                color: Theme.successColor
                                font.pixelSize: 24
                                font.weight: Font.DemiBold
                            }
                            CustomLabel {
                                text: "Processed"
                                color: Theme.placeholderTextColor
                                font.pixelSize: 12
                                Layout.fillWidth: true
                                Layout.minimumWidth: 0
                                wrapMode: Text.Wrap
                            }
                        }
                    }
                }

                ColumnLayout {
                    visible: root.hasSubscription
                    Layout.fillWidth: true
                    spacing: 10

                    CustomLabel {
                        text: "Current Episodes"
                        color: Theme.textColor
                        font.pixelSize: 15
                        font.weight: Font.DemiBold
                    }

                    Repeater {
                        model: root.episodes

                        delegate: Rectangle {
                            objectName: "subscriptionEpisode_" + modelData.id
                            radius: 8
                            color: Theme.railSurfaceColor
                            border.color: Theme.dividerColor
                            Layout.fillWidth: true
                            Layout.preferredHeight: 78
                            Layout.minimumWidth: 0

                            RowLayout {
                                anchors.fill: parent
                                anchors.margins: 10
                                spacing: 10

                                CustomLabel {
                                    text: modelData.hasProcessed ? "OK" : "NEW"
                                    color: modelData.hasProcessed ? Theme.successColor : Theme.highlightColor
                                    font.pixelSize: 11
                                    font.weight: Font.DemiBold
                                    Layout.preferredWidth: 32
                                }

                                ColumnLayout {
                                    spacing: 3
                                    Layout.fillWidth: true
                                    Layout.minimumWidth: 0
                                    CustomLabel {
                                        text: modelData.title
                                        color: Theme.textColor
                                        font.weight: modelData.isRead ? Font.Normal : Font.DemiBold
                                        elide: Text.ElideRight
                                        Layout.fillWidth: true
                                    }
                                    CustomLabel {
                                        text: modelData.status + " · " + modelData.queueStatus + (modelData.modifiedAt ? " · " + modelData.modifiedAt : "")
                                        color: Theme.placeholderTextColor
                                        font.pixelSize: 12
                                        elide: Text.ElideRight
                                        Layout.fillWidth: true
                                    }
                                    CustomLabel {
                                        text: modelData.sourceURL || modelData.mediaURL || ""
                                        color: Theme.placeholderTextColor
                                        font.pixelSize: 11
                                        elide: Text.ElideMiddle
                                        Layout.fillWidth: true
                                    }
                                }

                                CustomButton {
                                    objectName: "openSubscriptionEpisode_" + modelData.id
                                    text: "Open"
                                    onClicked: {
                                        root.library.selectedSource = "library";
                                        root.library.selectItem(modelData.id);
                                    }
                                }
                            }
                        }
                    }

                    CustomLabel {
                        visible: root.episodes.length === 0
                        text: "No episodes imported for this subscription yet."
                        color: Theme.placeholderTextColor
                        Layout.fillWidth: true
                        wrapMode: Text.Wrap
                    }
                }

                ColumnLayout {
                    visible: root.hasSubscription
                    Layout.fillWidth: true
                    spacing: 10

                    CustomLabel {
                        text: "Channel Metadata"
                        color: Theme.textColor
                        font.pixelSize: 15
                        font.weight: Font.DemiBold
                    }

                    GridLayout {
                        columns: 2
                        columnSpacing: 12
                        rowSpacing: 8
                        Layout.fillWidth: true

                        CustomLabel {
                            text: "Source"
                            color: Theme.placeholderTextColor
                        }
                        CustomLabel {
                            text: root.emptyAware(root.subscription.source)
                            color: Theme.textColor
                            elide: Text.ElideRight
                            Layout.fillWidth: true
                        }
                        CustomLabel {
                            text: "Group"
                            color: Theme.placeholderTextColor
                        }
                        CustomLabel {
                            text: root.emptyAware(root.subscription.groupName)
                            color: Theme.textColor
                            elide: Text.ElideRight
                            Layout.fillWidth: true
                        }
                        CustomLabel {
                            text: "Feed"
                            color: Theme.placeholderTextColor
                        }
                        CustomLabel {
                            text: root.displayUrl(root.subscription)
                            color: Theme.textColor
                            elide: Text.ElideMiddle
                            Layout.fillWidth: true
                        }
                        CustomLabel {
                            text: "Created"
                            color: Theme.placeholderTextColor
                        }
                        CustomLabel {
                            text: root.emptyAware(root.subscription.createdAt)
                            color: Theme.textColor
                            elide: Text.ElideRight
                            Layout.fillWidth: true
                        }
                        CustomLabel {
                            text: "Last Checked"
                            color: Theme.placeholderTextColor
                        }
                        CustomLabel {
                            text: root.emptyAware(root.subscription.lastCheckedAt)
                            color: Theme.textColor
                            elide: Text.ElideRight
                            Layout.fillWidth: true
                        }
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 10

                    CustomLabel {
                        text: "Add Subscription"
                        color: Theme.textColor
                        font.pixelSize: 15
                        font.weight: Font.DemiBold
                    }

                    GridLayout {
                        objectName: "addSubscriptionForm"
                        columns: root.narrow ? 2 : 4
                        Layout.fillWidth: true
                        columnSpacing: 8
                        rowSpacing: 8
                        CustomTextField {
                            id: subscriptionUrl
                            alignRightWhenFocused: false
                            placeholderText: "Xiaoyuzhou, Apple Podcast, or RSS URL"
                            Layout.fillWidth: true
                            Layout.minimumWidth: 0
                            Layout.columnSpan: root.narrow ? 2 : 1
                        }
                        CustomTextField {
                            id: subscriptionGroup
                            alignRightWhenFocused: false
                            text: root.hasSubscription ? root.subscription.groupName : "Default"
                            placeholderText: "Group"
                            Layout.preferredWidth: 130
                            Layout.fillWidth: root.narrow
                            Layout.minimumWidth: 0
                        }
                        CustomSpinBox {
                            id: subscriptionLimit
                            Layout.preferredWidth: 110
                            decimals: 0
                            realFrom: 0
                            realTo: 500
                            realValue: 20
                            CustomToolTip {
                                visible: parent.hovered
                                text: "0 means no explicit limit"
                            }
                        }
                        CustomButton {
                            text: "Add"
                            objectName: "addSubscriptionButton"
                            Layout.columnSpan: root.narrow ? 2 : 1
                            Layout.alignment: Qt.AlignRight
                            enabled: subscriptionUrl.text.trim().length > 0 && !root.jobs.running
                            onClicked: root.jobs.addSubscription(subscriptionUrl.text, subscriptionGroup.text, subscriptionLimit.value)
                        }
                    }
                }

                Item {
                    Layout.fillWidth: true
                    height: 10
                }
            }
        }
    }
}
