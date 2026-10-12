import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Pane {
    id: root
    padding: 0
    background: Rectangle {
        color: themeController.panel
    }

    property var subscription: libraryController.selectedSubscription
    property var episodes: libraryController.selectedSubscriptionItems
    property bool hasSubscription: subscription && subscription.id !== undefined && subscription.id !== ""

    function displayUrl(sub) {
        if (!sub)
            return "No URL"
        if (sub.feedURL && sub.feedURL.length > 0)
            return sub.feedURL
        if (sub.url && sub.url.length > 0)
            return sub.url
        return "No URL"
    }

    function emptyAware(value) {
        return value && value.length > 0 ? value : "None"
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        RowLayout {
            Layout.fillWidth: true
            Layout.margins: 18
            spacing: 10

            ColumnLayout {
                spacing: 2
                Layout.fillWidth: true
                Label {
                    text: root.hasSubscription ? root.subscription.title : "Subscriptions"
                    color: themeController.text
                    font.pixelSize: 20
                    font.weight: Font.DemiBold
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }
                Label {
                    text: root.hasSubscription
                        ? root.subscription.count + " episodes · " + root.subscription.unprocessedCount + " unprocessed"
                        : (libraryController.subscriptions.length === 0 ? "No subscriptions yet" : libraryController.subscriptions.length + " subscriptions")
                    color: themeController.muted
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }
            }

            Button {
                text: "Refresh"
                enabled: root.hasSubscription && !jobController.running
                onClicked: jobController.refreshSubscriptions(false, root.subscription.id, 20)
            }
            Button {
                text: "History"
                enabled: root.hasSubscription && !jobController.running
                onClicked: jobController.refreshSubscriptions(false, root.subscription.id, 0)
            }
            Button {
                text: "Remove"
                enabled: root.hasSubscription && !jobController.running
                onClicked: jobController.removeSubscription(root.subscription.id)
            }
            Button {
                text: "Refresh All"
                enabled: libraryController.subscriptions.length > 0 && !jobController.running
                onClicked: jobController.refreshSubscriptions(true, "", 20)
            }
        }

        Rectangle {
            Layout.fillWidth: true
            height: 1
            color: themeController.border
        }

        ScrollView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            padding: 22

            ColumnLayout {
                width: parent.width
                spacing: 18

                RowLayout {
                    visible: root.hasSubscription
                    Layout.fillWidth: true
                    spacing: 12

                    Rectangle {
                        radius: 8
                        color: "#f1f4f8"
                        Layout.fillWidth: true
                        Layout.preferredHeight: 84
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 12
                            Label { text: root.subscription.count; color: themeController.text; font.pixelSize: 24; font.weight: Font.DemiBold }
                            Label { text: "Episodes"; color: themeController.muted; font.pixelSize: 12 }
                        }
                    }
                    Rectangle {
                        radius: 8
                        color: "#eef5ff"
                        Layout.fillWidth: true
                        Layout.preferredHeight: 84
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 12
                            Label { text: root.subscription.unprocessedCount; color: themeController.accent; font.pixelSize: 24; font.weight: Font.DemiBold }
                            Label { text: "Unprocessed"; color: themeController.muted; font.pixelSize: 12 }
                        }
                    }
                    Rectangle {
                        radius: 8
                        color: "#eef8f1"
                        Layout.fillWidth: true
                        Layout.preferredHeight: 84
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 12
                            Label { text: root.subscription.processedCount; color: themeController.success; font.pixelSize: 24; font.weight: Font.DemiBold }
                            Label { text: "Processed"; color: themeController.muted; font.pixelSize: 12 }
                        }
                    }
                }

                ColumnLayout {
                    visible: root.hasSubscription
                    Layout.fillWidth: true
                    spacing: 10

                    Label {
                        text: "Current Episodes"
                        color: themeController.text
                        font.pixelSize: 15
                        font.weight: Font.DemiBold
                    }

                    Repeater {
                        model: root.episodes

                        delegate: Rectangle {
                            radius: 8
                            color: "#f7f8fa"
                            border.color: themeController.border
                            Layout.fillWidth: true
                            height: 78

                            RowLayout {
                                anchors.fill: parent
                                anchors.margins: 10
                                spacing: 10

                                Label {
                                    text: modelData.hasProcessed ? "OK" : "NEW"
                                    color: modelData.hasProcessed ? themeController.success : themeController.accent
                                    font.pixelSize: 11
                                    font.weight: Font.DemiBold
                                    Layout.preferredWidth: 32
                                }

                                ColumnLayout {
                                    spacing: 3
                                    Layout.fillWidth: true
                                    Label {
                                        text: modelData.title
                                        color: themeController.text
                                        font.weight: modelData.isRead ? Font.Normal : Font.DemiBold
                                        elide: Text.ElideRight
                                        Layout.fillWidth: true
                                    }
                                    Label {
                                        text: modelData.status + " · " + modelData.queueStatus + (modelData.modifiedAt ? " · " + modelData.modifiedAt : "")
                                        color: themeController.muted
                                        font.pixelSize: 12
                                        elide: Text.ElideRight
                                        Layout.fillWidth: true
                                    }
                                    Label {
                                        text: modelData.sourceURL || modelData.mediaURL || ""
                                        color: themeController.muted
                                        font.pixelSize: 11
                                        elide: Text.ElideMiddle
                                        Layout.fillWidth: true
                                    }
                                }

                                Button {
                                    text: "Open"
                                    onClicked: {
                                        libraryController.selectedSource = "library"
                                        libraryController.selectItem(modelData.id)
                                    }
                                }
                            }
                        }
                    }

                    Label {
                        visible: root.episodes.length === 0
                        text: "No episodes imported for this subscription yet."
                        color: themeController.muted
                        Layout.fillWidth: true
                    }
                }

                ColumnLayout {
                    visible: root.hasSubscription
                    Layout.fillWidth: true
                    spacing: 10

                    Label {
                        text: "Channel Metadata"
                        color: themeController.text
                        font.pixelSize: 15
                        font.weight: Font.DemiBold
                    }

                    GridLayout {
                        columns: 2
                        columnSpacing: 12
                        rowSpacing: 8
                        Layout.fillWidth: true

                        Label { text: "Source"; color: themeController.muted }
                        Label { text: root.emptyAware(root.subscription.source); color: themeController.text; elide: Text.ElideRight; Layout.fillWidth: true }
                        Label { text: "Group"; color: themeController.muted }
                        Label { text: root.emptyAware(root.subscription.groupName); color: themeController.text; elide: Text.ElideRight; Layout.fillWidth: true }
                        Label { text: "Feed"; color: themeController.muted }
                        Label { text: root.displayUrl(root.subscription); color: themeController.text; elide: Text.ElideMiddle; Layout.fillWidth: true }
                        Label { text: "Created"; color: themeController.muted }
                        Label { text: root.emptyAware(root.subscription.createdAt); color: themeController.text; elide: Text.ElideRight; Layout.fillWidth: true }
                        Label { text: "Last Checked"; color: themeController.muted }
                        Label { text: root.emptyAware(root.subscription.lastCheckedAt); color: themeController.text; elide: Text.ElideRight; Layout.fillWidth: true }
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 10

                    Label {
                        text: "Add Subscription"
                        color: themeController.text
                        font.pixelSize: 15
                        font.weight: Font.DemiBold
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8
                        TextField {
                            id: subscriptionUrl
                            placeholderText: "Xiaoyuzhou, Apple Podcast, or RSS URL"
                            Layout.fillWidth: true
                        }
                        TextField {
                            id: subscriptionGroup
                            text: root.hasSubscription ? root.subscription.groupName : "Default"
                            placeholderText: "Group"
                            Layout.preferredWidth: 130
                        }
                        SpinBox {
                            id: subscriptionLimit
                            from: 0
                            to: 500
                            value: 20
                            ToolTip.visible: hovered
                            ToolTip.text: "0 means no explicit limit"
                        }
                        Button {
                            text: "Add"
                            enabled: subscriptionUrl.text.trim().length > 0 && !jobController.running
                            onClicked: jobController.addSubscription(subscriptionUrl.text, subscriptionGroup.text, subscriptionLimit.value)
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
