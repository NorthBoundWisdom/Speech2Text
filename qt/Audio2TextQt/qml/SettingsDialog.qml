import QtQuick
import QtQuick.Controls as QQC
import GeoControls 1.0
import QtQuick.Layouts

CustomDialog {
    id: root
    title: "Settings"
    modal: true
    parent: QQC.Overlay.overlay
    x: Math.round((parent.width - width) / 2)
    y: Math.round((parent.height - height) / 2)
    width: 940
    height: 700
    standardButtons: QQC.Dialog.NoButton

    property int selectedPage: 0
    property bool apiKeyVisible: false
    property var tools: settingsController.detectTools()
    property color surface: Theme.pageSurfaceColor
    property color surfaceMuted: Theme.railSurfaceColor
    property color softBorder: Theme.dividerColor
    property color cardColor: Theme.contentSurfaceColor
    property string cloudApiBaseDraft: ""
    property string cloudApiKeyDraft: ""
    property string cloudModelDraft: ""
    property string cloudTimeoutDraft: ""
    property string cloudTemperatureDraft: ""
    property string cloudMaxTokensDraft: ""
    property string cloudModelOptionsDraft: ""
    property string summaryPromptDraft: ""
    property string titlePromptDraft: ""

    function loadCloudDrafts() {
        cloudApiBaseDraft = settingsController.cloudApiBase;
        cloudApiKeyDraft = settingsController.cloudApiKey;
        cloudModelDraft = settingsController.cloudModel;
        cloudTimeoutDraft = settingsController.cloudTimeout;
        cloudTemperatureDraft = settingsController.cloudTemperature;
        cloudMaxTokensDraft = settingsController.cloudMaxTokens;
        cloudModelOptionsDraft = settingsController.cloudModelOptions;
        summaryPromptDraft = settingsController.summaryPrompt;
        titlePromptDraft = settingsController.titlePrompt;
    }

    function saveCloudDrafts() {
        settingsController.cloudApiBase = cloudApiBaseDraft;
        settingsController.cloudApiKey = cloudApiKeyDraft;
        settingsController.cloudModel = cloudModelDraft;
        settingsController.cloudTimeout = cloudTimeoutDraft;
        settingsController.cloudTemperature = cloudTemperatureDraft;
        settingsController.cloudMaxTokens = cloudMaxTokensDraft;
        settingsController.cloudModelOptions = cloudModelOptionsDraft;
        settingsController.summaryPrompt = summaryPromptDraft;
        settingsController.titlePrompt = titlePromptDraft;
        settingsController.saveCloudConfig();
        tools = settingsController.detectTools();
    }

    onOpened: {
        tools = settingsController.detectTools();
        loadCloudDrafts();
    }

    Component.onCompleted: loadCloudDrafts()

    background: Rectangle {
        color: root.surface
        radius: 10
        border.color: root.softBorder
    }

    footer: Rectangle {
        implicitHeight: 58
        color: root.surface

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 18
            anchors.rightMargin: 18
            spacing: 10

            CustomLabel {
                text: settingsController.dataRoot
                color: Theme.placeholderTextColor
                elide: Text.ElideMiddle
                Layout.fillWidth: true
            }
            CustomButton {
                text: "Choose Data Folder"
                highlighted: true
                onClicked: dataRootDialog.open()
            }
            CustomButton {
                text: "Close"
                Layout.preferredWidth: 96
                onClicked: root.close()
            }
        }
    }

    CustomFolderDialog {
        id: dataRootDialog
        title: "Choose data folder"
        onAccepted: {
            settingsController.setDataRootUrl(selectedFolder);
            root.tools = settingsController.detectTools();
            root.loadCloudDrafts();
        }
    }

    CustomFolderDialog {
        id: libraryRootDialog
        title: "Library root"
        onAccepted: {
            settingsController.setLibraryRootUrl(selectedFolder);
            root.tools = settingsController.detectTools();
        }
    }

    CustomFolderDialog {
        id: vcpkgDialog
        title: "vcpkg root"
        onAccepted: {
            settingsController.vcpkgRoot = selectedFolder;
            root.tools = settingsController.detectTools();
        }
    }

    CustomFileDialog {
        id: atotDialog
        title: "atot executable"
        onAccepted: {
            settingsController.setAtotPathUrl(selectedFile);
            root.tools = settingsController.detectTools();
        }
    }

    RowLayout {
        anchors.fill: parent
        anchors.margins: 10
        objectName: "settingsDialogBody"
        spacing: 12

        Rectangle {
            Layout.preferredWidth: 196
            Layout.fillHeight: true
            radius: 10
            color: root.surfaceMuted
            border.color: root.softBorder

            ListView {
                id: settingsPages
                anchors.fill: parent
                anchors.margins: 8
                clip: true
                model: [
                    {
                        title: "Overview",
                        subtitle: "Readiness"
                    },
                    {
                        title: "Local ASR",
                        subtitle: "Model and workflow"
                    },
                    {
                        title: "Cloud Model",
                        subtitle: "API key and prompts"
                    },
                    {
                        title: "Library",
                        subtitle: "Data locations"
                    },
                    {
                        title: "Runtime",
                        subtitle: "Tools and CLI"
                    }
                ]

                delegate: CustomItemDelegate {
                    width: settingsPages.width
                    height: 58
                    leftPadding: 14
                    rightPadding: 12
                    highlighted: root.selectedPage === index
                    onClicked: root.selectedPage = index

                    background: Rectangle {
                        radius: 8
                        color: highlighted ? "#eaf2ff" : (hovered ? "#ffffff" : "transparent")
                        border.color: highlighted ? "#cfe0ff" : "transparent"

                        Rectangle {
                            width: 3
                            height: 24
                            radius: 2
                            color: Theme.highlightColor
                            visible: highlighted
                            anchors.left: parent.left
                            anchors.leftMargin: 4
                            anchors.verticalCenter: parent.verticalCenter
                        }
                    }

                    contentItem: ColumnLayout {
                        spacing: 2
                        CustomLabel {
                            text: modelData.title
                            color: highlighted ? Theme.highlightColor : Theme.textColor
                            font.weight: highlighted ? Font.DemiBold : Font.Normal
                            elide: Text.ElideRight
                            Layout.fillWidth: true
                        }
                        CustomLabel {
                            text: modelData.subtitle
                            color: Theme.placeholderTextColor
                            font.pixelSize: 11
                            elide: Text.ElideRight
                            Layout.fillWidth: true
                        }
                    }
                }
            }
        }

        StackLayout {
            currentIndex: root.selectedPage
            Layout.fillWidth: true
            Layout.fillHeight: true

            CustomScrollView {
                padding: 18
                contentWidth: availableWidth
                ColumnLayout {
                    width: parent.width
                    spacing: 14

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 12

                        ColumnLayout {
                            spacing: 2
                            Layout.fillWidth: true
                            CustomLabel {
                                text: "Overview"
                                color: Theme.textColor
                                font.pixelSize: 22
                                font.weight: Font.DemiBold
                            }
                            CustomLabel {
                                text: settingsController.dataRoot
                                color: Theme.placeholderTextColor
                                elide: Text.ElideMiddle
                                Layout.fillWidth: true
                            }
                        }
                        CustomButton {
                            text: "Choose Data Folder"
                            highlighted: true
                            onClicked: dataRootDialog.open()
                        }
                        CustomButton {
                            text: "Detect"
                            onClicked: root.tools = settingsController.detectTools()
                        }
                    }

                    GridLayout {
                        columns: 2
                        columnSpacing: 10
                        rowSpacing: 10
                        Layout.fillWidth: true

                        StatusCard {
                            title: "Library"
                            detail: settingsController.resolvedLibraryRoot
                            ok: libraryController.items.length > 0
                            Layout.fillWidth: true
                        }
                        StatusCard {
                            title: "Cloud Summary"
                            detail: settingsController.cloudConfigured ? settingsController.cloudModel + " @ " + settingsController.cloudApiBase : "API Base and API Key are not configured."
                            ok: settingsController.cloudConfigured
                            Layout.fillWidth: true
                        }
                        StatusCard {
                            title: "atot"
                            detail: tools.atot || "missing"
                            ok: tools.atotReady
                            Layout.fillWidth: true
                        }
                        StatusCard {
                            title: "ffmpeg"
                            detail: tools.ffmpeg || "missing"
                            ok: tools.ffmpegReady
                            Layout.fillWidth: true
                        }
                    }

                    CustomTextArea {
                        readOnly: true
                        wrapMode: TextEdit.Wrap
                        text: jobController.lastResult || jobController.lastError
                        visible: text.length > 0
                        Layout.fillWidth: true
                        Layout.preferredHeight: visible ? 150 : 0
                        selectByMouse: true
                        background: Rectangle {
                            color: "#f8fafc"
                            radius: 8
                            border.color: root.softBorder
                        }
                    }
                }
            }

            CustomScrollView {
                padding: 18
                contentWidth: availableWidth
                ColumnLayout {
                    width: parent.width
                    spacing: 14

                    SectionHeader {
                        title: "Local ASR"
                        subtitle: "Choose the local transcription model and default processing behavior."
                    }

                    GridLayout {
                        columns: 3
                        columnSpacing: 8
                        rowSpacing: 10
                        Layout.fillWidth: true

                        CustomLabel {
                            text: "Model"
                            color: Theme.textColor
                        }
                        CustomTextField {
                            alignRightWhenFocused: false
                            text: settingsController.modelAlias
                            onEditingFinished: settingsController.modelAlias = text
                            Layout.fillWidth: true
                        }
                        Item {}

                        CustomLabel {
                            text: "Cloud chunk"
                            color: Theme.textColor
                        }
                        CustomSpinBox {
                            objectName: "cloudChunkMinutes"
                            decimals: 0
                            realFrom: 1
                            realTo: 120
                            realValue: settingsController.cloudChunkMinutes
                            onEditingCommitted: function (minutes) {
                                settingsController.cloudChunkMinutes = minutes;
                            }
                        }
                        CustomLabel {
                            text: "minutes"
                            color: Theme.placeholderTextColor
                        }

                        CustomLabel {
                            text: "Workflow"
                            color: Theme.textColor
                        }
                        CustomSwitch {
                            objectName: "processingWorkflow"
                            model: ["Local only", "Cloud enabled"]
                            currentIndex: settingsController.localOnly ? 0 : 1
                            onActivated: function (index) {
                                settingsController.localOnly = index === 0;
                            }
                            Accessible.name: "Processing workflow"
                            Layout.columnSpan: 2
                        }
                    }

                    SectionHeader {
                        title: "Transcription Languages"
                        subtitle: "No selection: auto. One: language hint. Multiple: auto with hints, preserving original languages. Hints do not restrict detection."
                    }
                    GridLayout {
                        columns: 3
                        Layout.fillWidth: true
                        Repeater {
                            model: settingsController.languageOptions
                            CustomCheckBox {
                                required property var modelData
                                objectName: "transcriptionLanguage_" + modelData.code
                                text: modelData.label
                                checked: settingsController.transcriptionLanguages.indexOf(modelData.code) >= 0
                                onClicked: {
                                    let codes = settingsController.transcriptionLanguages.slice();
                                    let index = codes.indexOf(modelData.code);
                                    if (index >= 0)
                                        codes.splice(index, 1);
                                    if (checked)
                                        codes.push(modelData.code);
                                    settingsController.transcriptionLanguages = codes;
                                }
                            }
                        }
                    }
                    CustomButton {
                        text: "Automatic Detection"
                        onClicked: settingsController.transcriptionLanguages = []
                    }
                    SectionHeader {
                        title: "Summary Output Language"
                        subtitle: "Controls summaries, headings, short titles, and MCP instructions. Overrides conflicting custom prompt language requirements. No API key required to save."
                    }
                    CustomComboBox {
                        objectName: "summaryOutputLanguage"
                        model: settingsController.languageOptions
                        textRole: "label"
                        valueRole: "code"
                        currentIndex: {
                            for (let i = 0; i < model.length; i++)
                                if (model[i].code === settingsController.summaryLanguage)
                                    return i;
                            return -1;
                        }
                        onActivated: settingsController.summaryLanguage = currentValue
                        Layout.preferredWidth: 240
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        CustomButton {
                            text: "Doctor"
                            onClicked: jobController.runDoctor()
                        }
                        CustomButton {
                            text: "Library Status"
                            onClicked: jobController.runLibraryStatus()
                        }
                        Item {
                            Layout.fillWidth: true
                        }
                    }
                }
            }

            CustomScrollView {
                padding: 18
                contentWidth: availableWidth
                ColumnLayout {
                    width: parent.width
                    spacing: 14

                    SectionHeader {
                        title: "Cloud Model"
                        subtitle: "Configure summary and title generation. Values are written to config.toml under the selected data root."
                    }

                    GridLayout {
                        columns: 3
                        columnSpacing: 8
                        rowSpacing: 10
                        Layout.fillWidth: true

                        CustomLabel {
                            text: "API Base"
                            color: Theme.textColor
                        }
                        CustomTextField {
                            alignRightWhenFocused: false
                            text: root.cloudApiBaseDraft
                            placeholderText: "https://.../v1"
                            onTextChanged: root.cloudApiBaseDraft = text
                            Layout.fillWidth: true
                        }
                        Item {}

                        CustomLabel {
                            text: "API Key"
                            color: Theme.textColor
                        }
                        CustomTextField {
                            alignRightWhenFocused: false
                            text: root.cloudApiKeyDraft
                            echoMode: root.apiKeyVisible ? TextInput.Normal : TextInput.Password
                            onTextChanged: root.cloudApiKeyDraft = text
                            Layout.fillWidth: true
                        }
                        CustomButton {
                            text: root.apiKeyVisible ? "Hide" : "Show"
                            onClicked: root.apiKeyVisible = !root.apiKeyVisible
                        }

                        CustomLabel {
                            text: "Model"
                            color: Theme.textColor
                        }
                        CustomTextField {
                            alignRightWhenFocused: false
                            text: root.cloudModelDraft
                            onTextChanged: root.cloudModelDraft = text
                            Layout.fillWidth: true
                        }
                        Item {}

                        CustomLabel {
                            text: "Timeout"
                            color: Theme.textColor
                        }
                        CustomTextField {
                            alignRightWhenFocused: false
                            text: root.cloudTimeoutDraft
                            onTextChanged: root.cloudTimeoutDraft = text
                            Layout.fillWidth: true
                        }
                        CustomLabel {
                            text: "seconds"
                            color: Theme.placeholderTextColor
                        }

                        CustomLabel {
                            text: "Temperature"
                            color: Theme.textColor
                        }
                        CustomTextField {
                            alignRightWhenFocused: false
                            text: root.cloudTemperatureDraft
                            onTextChanged: root.cloudTemperatureDraft = text
                            Layout.fillWidth: true
                        }
                        Item {}

                        CustomLabel {
                            text: "Max Tokens"
                            color: Theme.textColor
                        }
                        CustomTextField {
                            alignRightWhenFocused: false
                            text: root.cloudMaxTokensDraft
                            onTextChanged: root.cloudMaxTokensDraft = text
                            Layout.fillWidth: true
                        }
                        Item {}

                        CustomLabel {
                            text: "Model Options"
                            color: Theme.textColor
                        }
                        CustomTextField {
                            alignRightWhenFocused: false
                            text: root.cloudModelOptionsDraft
                            placeholderText: "gpt-5.4-mini, gpt-5.4, gpt-5.5, gpt-5.6-sol, gpt-5.6-terra, gpt-5.6-luna"
                            onTextChanged: root.cloudModelOptionsDraft = text
                            Layout.fillWidth: true
                        }
                        Item {}
                    }

                    PromptEditor {
                        title: "Summary Prompt"
                        textValue: root.summaryPromptDraft
                        onTextValueChanged: root.summaryPromptDraft = textValue
                        Layout.fillWidth: true
                    }

                    PromptEditor {
                        title: "Title Prompt"
                        textValue: root.titlePromptDraft
                        onTextValueChanged: root.titlePromptDraft = textValue
                        Layout.fillWidth: true
                    }

                    GridLayout {
                        columns: 2
                        columnSpacing: 12
                        rowSpacing: 6
                        Layout.fillWidth: true
                        CustomLabel {
                            text: "Config File"
                            color: Theme.placeholderTextColor
                        }
                        CustomLabel {
                            text: settingsController.configPath
                            color: Theme.textColor
                            elide: Text.ElideMiddle
                            Layout.fillWidth: true
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        CustomButton {
                            text: "Save Cloud Config"
                            onClicked: root.saveCloudDrafts()
                        }
                        CustomButton {
                            text: "Reload"
                            onClicked: {
                                settingsController.reloadCloudConfig();
                                root.loadCloudDrafts();
                                root.tools = settingsController.detectTools();
                            }
                        }
                        CustomButton {
                            text: "Inspect"
                            onClicked: jobController.configInspect()
                        }
                        Item {
                            Layout.fillWidth: true
                        }
                    }
                }
            }

            CustomScrollView {
                padding: 18
                contentWidth: availableWidth
                ColumnLayout {
                    width: parent.width
                    spacing: 14

                    SectionHeader {
                        title: "Library"
                        subtitle: "Choose the authoritative SonaFolio library and data locations."
                    }

                    GridLayout {
                        columns: 3
                        columnSpacing: 8
                        rowSpacing: 10
                        Layout.fillWidth: true

                        CustomLabel {
                            text: "Data root"
                            color: Theme.textColor
                        }
                        CustomTextField {
                            alignRightWhenFocused: false
                            text: settingsController.dataRoot
                            onEditingFinished: {
                                settingsController.dataRoot = text;
                                root.tools = settingsController.detectTools();
                                root.loadCloudDrafts();
                            }
                            Layout.fillWidth: true
                        }
                        CustomButton {
                            text: "Choose Folder"
                            onClicked: dataRootDialog.open()
                        }

                        CustomLabel {
                            text: "Library root"
                            color: Theme.textColor
                        }
                        CustomTextField {
                            alignRightWhenFocused: false
                            text: settingsController.libraryRootOverride
                            placeholderText: settingsController.resolvedLibraryRoot
                            onEditingFinished: settingsController.libraryRootOverride = text
                            Layout.fillWidth: true
                        }
                        CustomButton {
                            text: "Browse"
                            onClicked: libraryRootDialog.open()
                        }

                        CustomLabel {
                            text: "Resolved"
                            color: Theme.placeholderTextColor
                        }
                        CustomLabel {
                            text: settingsController.resolvedLibraryRoot
                            color: Theme.textColor
                            elide: Text.ElideMiddle
                            Layout.fillWidth: true
                        }
                        Item {}
                    }
                }
            }

            CustomScrollView {
                padding: 18
                contentWidth: availableWidth
                ColumnLayout {
                    width: parent.width
                    spacing: 14

                    SectionHeader {
                        title: "Runtime"
                        subtitle: "Locate atot, bundled ffmpeg/ffprobe, and optional vcpkg tools."
                    }

                    GridLayout {
                        columns: 3
                        columnSpacing: 8
                        rowSpacing: 10
                        Layout.fillWidth: true

                        CustomLabel {
                            text: "atot"
                            color: Theme.textColor
                        }
                        CustomTextField {
                            alignRightWhenFocused: false
                            text: settingsController.atotPath
                            placeholderText: tools.atot || "PATH / data-root env"
                            onEditingFinished: {
                                settingsController.atotPath = text;
                                root.tools = settingsController.detectTools();
                            }
                            Layout.fillWidth: true
                        }
                        CustomButton {
                            text: "Browse"
                            onClicked: atotDialog.open()
                        }

                        CustomLabel {
                            text: "vcpkg"
                            color: Theme.textColor
                        }
                        CustomTextField {
                            alignRightWhenFocused: false
                            text: settingsController.vcpkgRoot
                            onEditingFinished: {
                                settingsController.vcpkgRoot = text;
                                root.tools = settingsController.detectTools();
                            }
                            Layout.fillWidth: true
                        }
                        CustomButton {
                            text: "Browse"
                            onClicked: vcpkgDialog.open()
                        }

                        CustomLabel {
                            text: "ffmpeg"
                            color: Theme.placeholderTextColor
                        }
                        CustomLabel {
                            text: tools.ffmpeg || "missing"
                            color: tools.ffmpegReady ? Theme.successColor : Theme.errorColor
                            elide: Text.ElideMiddle
                            Layout.fillWidth: true
                        }
                        Item {}

                        CustomLabel {
                            text: "ffprobe"
                            color: Theme.placeholderTextColor
                        }
                        CustomLabel {
                            text: tools.ffprobe || "missing"
                            color: tools.ffprobeReady ? Theme.successColor : Theme.errorColor
                            elide: Text.ElideMiddle
                            Layout.fillWidth: true
                        }
                        Item {}
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        CustomButton {
                            text: "Detect"
                            onClicked: root.tools = settingsController.detectTools()
                        }
                        CustomButton {
                            text: "Doctor"
                            onClicked: jobController.runDoctor()
                        }
                        CustomButton {
                            text: "Config List"
                            onClicked: jobController.configList()
                        }
                        CustomButton {
                            text: "Reset App Settings"
                            onClicked: {
                                settingsController.resetDefaults();
                                root.tools = settingsController.detectTools();
                                root.loadCloudDrafts();
                            }
                        }
                        Item {
                            Layout.fillWidth: true
                        }
                    }
                }
            }
        }
    }

    component SectionHeader: ColumnLayout {
        property string title: ""
        property string subtitle: ""
        Layout.fillWidth: true
        spacing: 4
        CustomLabel {
            text: parent.title
            color: Theme.textColor
            font.pixelSize: 20
            font.weight: Font.DemiBold
        }
        CustomLabel {
            text: parent.subtitle
            color: Theme.placeholderTextColor
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }
    }

    component StatusCard: Rectangle {
        property string title: ""
        property string detail: ""
        property bool ok: false
        property color stateColor: ok ? Theme.successColor : Theme.warningColor
        radius: 10
        color: root.cardColor
        border.color: root.softBorder
        Layout.preferredHeight: 112

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 14
            spacing: 8

            RowLayout {
                Layout.fillWidth: true
                spacing: 8
                Rectangle {
                    width: 8
                    height: 8
                    radius: 4
                    color: parent.parent.parent.stateColor
                    Layout.alignment: Qt.AlignVCenter
                }
                CustomLabel {
                    text: parent.parent.parent.title
                    color: Theme.textColor
                    font.weight: Font.DemiBold
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }
            }
            CustomLabel {
                text: parent.parent.detail
                color: Theme.placeholderTextColor
                wrapMode: Text.WordWrap
                maximumLineCount: 3
                elide: Text.ElideMiddle
                Layout.fillWidth: true
            }
        }
    }

    component PromptEditor: ColumnLayout {
        property alias textValue: editor.text
        property string title: ""
        spacing: 6
        CustomLabel {
            text: parent.title
            color: Theme.placeholderTextColor
            Layout.fillWidth: true
        }
        CustomTextArea {
            id: editor
            wrapMode: TextEdit.Wrap
            selectByMouse: true
            Layout.fillWidth: true
            Layout.preferredHeight: 110
        }
    }
}
