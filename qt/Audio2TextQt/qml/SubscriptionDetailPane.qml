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

    property var subscription: libraryController.selectedSubscription
    property var episodes: libraryController.selectedSubscriptionItems
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

        RowLayout {
            Layout.fillWidth: true
            Layout.margins: 18
            spacing: 10

            ColumnLayout {
                spacing: 2
                Layout.fillWidth: true
                CustomLabel {
                    text: root.hasSubscription ? root.subscription.title : "Subscriptions"
                    color: Theme.textColor
                    font.pixelSize: 20
                    font.weight: Font.DemiBold
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }
                CustomLabel {
                    text: root.hasSubscription ? root.subscription.count + " episodes · " + root.subscription.unprocessedCount + " unprocessed" : (libraryController.subscriptions.length === 0 ? "No subscriptions yet" : libraryController.subscriptions.length + " subscriptions")
                    color: Theme.placeholderTextColor
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }
            }

            CustomButton {
                text: "Refresh"
                enabled: root.hasSubscription && !jobController.running
                onClicked: jobController.refreshSubscriptions(false, root.subscription.id, 20)
            }
            CustomButton {
                text: "History"
                enabled: root.hasSubscription && !jobController.running
                onClicked: jobController.refreshSubscriptions(false, root.subscription.id, 0)
            }
            CustomButton {
                text: "Remove"
                enabled: root.hasSubscription && !jobController.running
                onClicked: jobController.removeSubscription(root.subscription.id)
            }
            CustomButton {
                text: "Refresh All"
                enabled: libraryController.subscriptions.length > 0 && !jobController.running
                onClicked: jobController.refreshSubscriptions(true, "", 20)
            }
        }

        Rectangle {
            Layout.fillWidth: true
            height: 1
            color: Theme.dividerColor
        }

        CustomScrollView {
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
                            }
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
                            CustomLabel {
                                text: root.subscription.unprocessedCount
                                color: Theme.highlightColor
                                font.pixelSize: 24
                                font.weight: Font.DemiBold
                            }
                            CustomLabel {
                                text: "Unprocessed"
                                color: Theme.placeholderTextColor
                                font.pixelSize: 12
                            }
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
                            radius: 8
                            color: "#f7f8fa"
                            border.color: Theme.dividerColor
                            Layout.fillWidth: true
                            height: 78

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
                                    text: "Open"
                                    onClicked: {
                                        libraryController.selectedSource = "library";
                                        libraryController.selectItem(modelData.id);
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

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8
                        CustomTextField {
                            id: subscriptionUrl
                            alignRightWhenFocused: false
                            placeholderText: "Xiaoyuzhou, Apple Podcast, or RSS URL"
                            Layout.fillWidth: true
                        }
                        CustomTextField {
                            id: subscriptionGroup
                            alignRightWhenFocused: false
                            text: root.hasSubscription ? root.subscription.groupName : "Default"
                            placeholderText: "Group"
                            Layout.preferredWidth: 130
                        }
                        CustomSpinBox {
                            id: subscriptionLimit
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
