import QtQuick
import QtQuick.Controls as QQC
import GeoControls 1.0
import QtQuick.Layouts

CustomDialog {
    id: root
    title: "Import"
    modal: true
    width: 620
    height: 430
    standardButtons: QQC.Dialog.NoButton

    property string selectedMode: "xiaoyuzhou"

    CustomFileDialog {
        id: localFileDialog
        title: "Local audio"
        onAccepted: localPath.text = selectedFile
    }

    ColumnLayout {
        objectName: "importDialogBody"
        anchors.fill: parent
        spacing: 12

        CustomTabBar {
            id: importTabs
            Layout.fillWidth: true
            onTargetIndexChanged: root.selectedMode = ["xiaoyuzhou", "local", "subscription"][targetIndex]
            CustomTabButton {
                text: "Xiaoyuzhou"
                tabBar: importTabs
                targetIndex: 0
            }
            CustomTabButton {
                objectName: "localImportTab"
                text: "Local File"
                tabBar: importTabs
                targetIndex: 1
            }
            CustomTabButton {
                objectName: "subscriptionImportTab"
                text: "Subscription"
                tabBar: importTabs
                targetIndex: 2
            }
        }

        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: root.selectedMode === "xiaoyuzhou" ? 0 : root.selectedMode === "local" ? 1 : 2

            ColumnLayout {
                spacing: 10
                CustomTextField {
                    id: episodeUrl
                    alignRightWhenFocused: false
                    placeholderText: "Episode URL"
                    Layout.fillWidth: true
                }
                CustomComboBox {
                    id: importGroup
                    editable: true
                    model: libraryController.groups
                    textRole: "title"
                    Layout.fillWidth: true
                }
                CustomCheckBox {
                    id: downloadAudio
                    text: "Download audio"
                    checked: true
                }
            }

            ColumnLayout {
                spacing: 10
                RowLayout {
                    Layout.fillWidth: true
                    CustomTextField {
                        id: localPath
                        alignRightWhenFocused: false
                        placeholderText: "Audio file"
                        Layout.fillWidth: true
                    }
                    CustomButton {
                        text: "Browse"
                        onClicked: localFileDialog.open()
                    }
                }
                CustomLabel {
                    text: "Local files are transcribed through the same atot service and published into the configured library."
                    color: Theme.placeholderTextColor
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                }
            }

            ColumnLayout {
                spacing: 10
                CustomTextField {
                    id: subscriptionUrl
                    alignRightWhenFocused: false
                    placeholderText: "RSS or podcast URL"
                    Layout.fillWidth: true
                }
                CustomComboBox {
                    id: subscriptionGroup
                    editable: true
                    model: libraryController.groups
                    textRole: "title"
                    Layout.fillWidth: true
                }
                CustomSpinBox {
                    id: subscriptionLimit
                    objectName: "importSubscriptionLimit"
                    decimals: 0
                    realFrom: 1
                    realTo: 500
                    realValue: 20
                    Layout.preferredWidth: 140
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            CustomButton {
                text: "List"
                visible: root.selectedMode === "subscription"
                onClicked: jobController.listSubscriptions()
            }
            CustomButton {
                text: "Refresh All"
                visible: root.selectedMode === "subscription"
                onClicked: jobController.refreshSubscriptions(true, "", subscriptionLimit.value)
            }
            Item {
                Layout.fillWidth: true
            }
            CustomButton {
                text: "Cancel"
                onClicked: root.close()
            }
            CustomButton {
                text: "Run"
                highlighted: true
                enabled: !jobController.running
                onClicked: {
                    if (root.selectedMode === "xiaoyuzhou") {
                        jobController.importXiaoyuzhou(episodeUrl.text, importGroup.editText || importGroup.currentText, downloadAudio.checked);
                    } else if (root.selectedMode === "local") {
                        jobController.transcribeAudio(localPath.text);
                    } else {
                        jobController.addSubscription(subscriptionUrl.text, subscriptionGroup.editText || subscriptionGroup.currentText, subscriptionLimit.value);
                    }
                    root.close();
                }
            }
        }
    }
}
