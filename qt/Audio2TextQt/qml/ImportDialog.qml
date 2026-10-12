import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts

Dialog {
    id: root
    title: "Import"
    modal: true
    width: 620
    height: 430
    standardButtons: Dialog.NoButton

    property string selectedMode: "xiaoyuzhou"

    FileDialog {
        id: localFileDialog
        title: "Local audio"
        onAccepted: localPath.text = selectedFile
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 12

        TabBar {
            Layout.fillWidth: true
            onCurrentIndexChanged: root.selectedMode = ["xiaoyuzhou", "local", "subscription"][currentIndex]
            TabButton { text: "Xiaoyuzhou" }
            TabButton { text: "Local File" }
            TabButton { text: "Subscription" }
        }

        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: root.selectedMode === "xiaoyuzhou" ? 0 : root.selectedMode === "local" ? 1 : 2

            ColumnLayout {
                spacing: 10
                TextField {
                    id: episodeUrl
                    placeholderText: "Episode URL"
                    Layout.fillWidth: true
                }
                ComboBox {
                    id: importGroup
                    editable: true
                    model: libraryController.groups
                    textRole: "title"
                    Layout.fillWidth: true
                }
                CheckBox {
                    id: downloadAudio
                    text: "Download audio"
                    checked: true
                }
            }

            ColumnLayout {
                spacing: 10
                RowLayout {
                    Layout.fillWidth: true
                    TextField {
                        id: localPath
                        placeholderText: "Audio file"
                        Layout.fillWidth: true
                    }
                    Button {
                        text: "Browse"
                        onClicked: localFileDialog.open()
                    }
                }
                Label {
                    text: "Local files are transcribed through the same atot service and published into the configured library."
                    color: themeController.muted
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                }
            }

            ColumnLayout {
                spacing: 10
                TextField {
                    id: subscriptionUrl
                    placeholderText: "RSS or podcast URL"
                    Layout.fillWidth: true
                }
                ComboBox {
                    id: subscriptionGroup
                    editable: true
                    model: libraryController.groups
                    textRole: "title"
                    Layout.fillWidth: true
                }
                SpinBox {
                    id: subscriptionLimit
                    from: 1
                    to: 500
                    value: 20
                    Layout.preferredWidth: 140
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Button {
                text: "List"
                visible: root.selectedMode === "subscription"
                onClicked: jobController.listSubscriptions()
            }
            Button {
                text: "Refresh All"
                visible: root.selectedMode === "subscription"
                onClicked: jobController.refreshSubscriptions(true, "", subscriptionLimit.value)
            }
            Item { Layout.fillWidth: true }
            Button {
                text: "Cancel"
                onClicked: root.close()
            }
            Button {
                text: "Run"
                highlighted: true
                enabled: !jobController.running
                onClicked: {
                    if (root.selectedMode === "xiaoyuzhou") {
                        jobController.importXiaoyuzhou(episodeUrl.text, importGroup.editText || importGroup.currentText, downloadAudio.checked)
                    } else if (root.selectedMode === "local") {
                        jobController.transcribeAudio(localPath.text)
                    } else {
                        jobController.addSubscription(subscriptionUrl.text, subscriptionGroup.editText || subscriptionGroup.currentText, subscriptionLimit.value)
                    }
                    root.close()
                }
            }
        }
    }
}

