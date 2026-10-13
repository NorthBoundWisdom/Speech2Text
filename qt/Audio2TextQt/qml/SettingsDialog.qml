import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts

Dialog {
    id: root
    title: "Settings"
    modal: true
    parent: Overlay.overlay
    x: Math.round((parent.width - width) / 2)
    y: Math.round((parent.height - height) / 2)
    width: 940
    height: 700
    standardButtons: Dialog.NoButton

    property int selectedPage: 0
    property bool apiKeyVisible: false
    property var tools: settingsController.detectTools()
    property color surface: "#fbfcfe"
    property color surfaceMuted: "#f6f8fb"
    property color softBorder: "#e1e7ef"
    property color cardColor: "#ffffff"
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
        cloudApiBaseDraft = settingsController.cloudApiBase
        cloudApiKeyDraft = settingsController.cloudApiKey
        cloudModelDraft = settingsController.cloudModel
        cloudTimeoutDraft = settingsController.cloudTimeout
        cloudTemperatureDraft = settingsController.cloudTemperature
        cloudMaxTokensDraft = settingsController.cloudMaxTokens
        cloudModelOptionsDraft = settingsController.cloudModelOptions
        summaryPromptDraft = settingsController.summaryPrompt
        titlePromptDraft = settingsController.titlePrompt
    }

    function saveCloudDrafts() {
        settingsController.cloudApiBase = cloudApiBaseDraft
        settingsController.cloudApiKey = cloudApiKeyDraft
        settingsController.cloudModel = cloudModelDraft
        settingsController.cloudTimeout = cloudTimeoutDraft
        settingsController.cloudTemperature = cloudTemperatureDraft
        settingsController.cloudMaxTokens = cloudMaxTokensDraft
        settingsController.cloudModelOptions = cloudModelOptionsDraft
        settingsController.summaryPrompt = summaryPromptDraft
        settingsController.titlePrompt = titlePromptDraft
        settingsController.saveCloudConfig()
        tools = settingsController.detectTools()
    }

    onOpened: {
        tools = settingsController.detectTools()
        loadCloudDrafts()
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

            Label {
                text: settingsController.dataRoot
                color: themeController.muted
                elide: Text.ElideMiddle
                Layout.fillWidth: true
            }
            Button {
                text: "Choose Data Folder"
                highlighted: true
                onClicked: dataRootDialog.open()
            }
            Button {
                text: "Close"
                Layout.preferredWidth: 96
                onClicked: root.close()
            }
        }
    }

    FolderDialog {
        id: dataRootDialog
        title: "Choose data folder"
        onAccepted: {
            settingsController.setDataRootUrl(selectedFolder)
            root.tools = settingsController.detectTools()
            root.loadCloudDrafts()
        }
    }

    FolderDialog {
        id: libraryRootDialog
        title: "Library root"
        onAccepted: {
            settingsController.setLibraryRootUrl(selectedFolder)
            root.tools = settingsController.detectTools()
        }
    }

    FolderDialog {
        id: vcpkgDialog
        title: "vcpkg root"
        onAccepted: {
            settingsController.vcpkgRoot = selectedFolder
            root.tools = settingsController.detectTools()
        }
    }

    FileDialog {
        id: atotDialog
        title: "atot executable"
        onAccepted: {
            settingsController.setAtotPathUrl(selectedFile)
            root.tools = settingsController.detectTools()
        }
    }

    RowLayout {
        anchors.fill: parent
        anchors.margins: 10
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
                    { title: "Overview", subtitle: "Readiness" },
                    { title: "Local ASR", subtitle: "Model and workflow" },
                    { title: "Cloud Model", subtitle: "API key and prompts" },
                    { title: "Library", subtitle: "Data locations" },
                    { title: "Runtime", subtitle: "Tools and CLI" }
                ]

                delegate: ItemDelegate {
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
                            color: themeController.accent
                            visible: highlighted
                            anchors.left: parent.left
                            anchors.leftMargin: 4
                            anchors.verticalCenter: parent.verticalCenter
                        }
                    }

                    contentItem: ColumnLayout {
                        spacing: 2
                        Label {
                            text: modelData.title
                            color: highlighted ? themeController.accent : themeController.text
                            font.weight: highlighted ? Font.DemiBold : Font.Normal
                            elide: Text.ElideRight
                            Layout.fillWidth: true
                        }
                        Label {
                            text: modelData.subtitle
                            color: themeController.muted
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

            ScrollView {
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
                            Label {
                                text: "Overview"
                                color: themeController.text
                                font.pixelSize: 22
                                font.weight: Font.DemiBold
                            }
                            Label {
                                text: settingsController.dataRoot
                                color: themeController.muted
                                elide: Text.ElideMiddle
                                Layout.fillWidth: true
                            }
                        }
                        Button {
                            text: "Choose Data Folder"
                            highlighted: true
                            onClicked: dataRootDialog.open()
                        }
                        Button {
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

                    TextArea {
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

            ScrollView {
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

                        Label { text: "Model"; color: themeController.text }
                        TextField {
                            text: settingsController.modelAlias
                            onEditingFinished: settingsController.modelAlias = text
                            Layout.fillWidth: true
                        }
                        Item {}

                        Label { text: "Cloud chunk"; color: themeController.text }
                        SpinBox {
                            from: 1
                            to: 120
                            value: settingsController.cloudChunkMinutes
                            onValueModified: settingsController.cloudChunkMinutes = value
                        }
                        Label { text: "minutes"; color: themeController.muted }

                        Label { text: "Workflow"; color: themeController.text }
                        Switch {
                            text: "Prefer local-only processing"
                            checked: settingsController.localOnly
                            onToggled: settingsController.localOnly = checked
                            Layout.columnSpan: 2
                        }
                    }

                    SectionHeader { title: "Transcription Languages"; subtitle: "No selection: auto. One: language hint. Multiple: auto with hints, preserving original languages. Hints do not restrict detection." }
                    GridLayout {
                        columns: 3
                        Layout.fillWidth: true
                        Repeater {
                            model: settingsController.languageOptions
                            CheckBox {
                                required property var modelData
                                text: modelData.label
                                checked: settingsController.transcriptionLanguages.indexOf(modelData.code) >= 0
                                onToggled: {
                                    let codes = settingsController.transcriptionLanguages.slice()
                                    let index = codes.indexOf(modelData.code)
                                    if (index >= 0) codes.splice(index, 1)
                                    if (checked) codes.push(modelData.code)
                                    settingsController.transcriptionLanguages = codes
                                }
                            }
                        }
                    }
                    Button { text: "Automatic Detection"; onClicked: settingsController.transcriptionLanguages = [] }
                    SectionHeader { title: "Summary Output Language"; subtitle: "Controls summaries, headings, short titles, and MCP instructions. Overrides conflicting custom prompt language requirements. No API key required to save." }
                    ComboBox {
                        model: settingsController.languageOptions
                        textRole: "label"
                        valueRole: "code"
                        currentIndex: {
                            for (let i = 0; i < model.length; i++)
                                if (model[i].code === settingsController.summaryLanguage) return i
                            return -1
                        }
                        onActivated: settingsController.summaryLanguage = currentValue
                        Layout.preferredWidth: 240
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        Button {
                            text: "Doctor"
                            onClicked: jobController.runDoctor()
                        }
                        Button {
                            text: "Library Status"
                            onClicked: jobController.runLibraryStatus()
                        }
                        Item { Layout.fillWidth: true }
                    }
                }
            }

            ScrollView {
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

                        Label { text: "API Base"; color: themeController.text }
                        TextField {
                            text: root.cloudApiBaseDraft
                            placeholderText: "https://.../v1"
                            onTextChanged: root.cloudApiBaseDraft = text
                            Layout.fillWidth: true
                        }
                        Item {}

                        Label { text: "API Key"; color: themeController.text }
                        TextField {
                            text: root.cloudApiKeyDraft
                            echoMode: root.apiKeyVisible ? TextInput.Normal : TextInput.Password
                            onTextChanged: root.cloudApiKeyDraft = text
                            Layout.fillWidth: true
                        }
                        Button {
                            text: root.apiKeyVisible ? "Hide" : "Show"
                            onClicked: root.apiKeyVisible = !root.apiKeyVisible
                        }

                        Label { text: "Model"; color: themeController.text }
                        TextField {
                            text: root.cloudModelDraft
                            onTextChanged: root.cloudModelDraft = text
                            Layout.fillWidth: true
                        }
                        Item {}

                        Label { text: "Timeout"; color: themeController.text }
                        TextField {
                            text: root.cloudTimeoutDraft
                            onTextChanged: root.cloudTimeoutDraft = text
                            Layout.fillWidth: true
                        }
                        Label { text: "seconds"; color: themeController.muted }

                        Label { text: "Temperature"; color: themeController.text }
                        TextField {
                            text: root.cloudTemperatureDraft
                            onTextChanged: root.cloudTemperatureDraft = text
                            Layout.fillWidth: true
                        }
                        Item {}

                        Label { text: "Max Tokens"; color: themeController.text }
                        TextField {
                            text: root.cloudMaxTokensDraft
                            onTextChanged: root.cloudMaxTokensDraft = text
                            Layout.fillWidth: true
                        }
                        Item {}

                        Label { text: "Model Options"; color: themeController.text }
                        TextField {
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
                        Label { text: "Config File"; color: themeController.muted }
                        Label { text: settingsController.configPath; color: themeController.text; elide: Text.ElideMiddle; Layout.fillWidth: true }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        Button {
                            text: "Save Cloud Config"
                            onClicked: root.saveCloudDrafts()
                        }
                        Button {
                            text: "Reload"
                            onClicked: {
                                settingsController.reloadCloudConfig()
                                root.loadCloudDrafts()
                                root.tools = settingsController.detectTools()
                            }
                        }
                        Button {
                            text: "Inspect"
                            onClicked: jobController.configInspect()
                        }
                        Item { Layout.fillWidth: true }
                    }
                }
            }

            ScrollView {
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

                        Label { text: "Data root"; color: themeController.text }
                        TextField {
                            text: settingsController.dataRoot
                            onEditingFinished: {
                                settingsController.dataRoot = text
                                root.tools = settingsController.detectTools()
                                root.loadCloudDrafts()
                            }
                            Layout.fillWidth: true
                        }
                        Button { text: "Choose Folder"; onClicked: dataRootDialog.open() }

                        Label { text: "Library root"; color: themeController.text }
                        TextField {
                            text: settingsController.libraryRootOverride
                            placeholderText: settingsController.resolvedLibraryRoot
                            onEditingFinished: settingsController.libraryRootOverride = text
                            Layout.fillWidth: true
                        }
                        Button { text: "Browse"; onClicked: libraryRootDialog.open() }

                        Label { text: "Resolved"; color: themeController.muted }
                        Label {
                            text: settingsController.resolvedLibraryRoot
                            color: themeController.text
                            elide: Text.ElideMiddle
                            Layout.fillWidth: true
                        }
                        Item {}
                    }
                }
            }

            ScrollView {
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

                        Label { text: "atot"; color: themeController.text }
                        TextField {
                            text: settingsController.atotPath
                            placeholderText: tools.atot || "PATH / data-root env"
                            onEditingFinished: {
                                settingsController.atotPath = text
                                root.tools = settingsController.detectTools()
                            }
                            Layout.fillWidth: true
                        }
                        Button { text: "Browse"; onClicked: atotDialog.open() }

                        Label { text: "vcpkg"; color: themeController.text }
                        TextField {
                            text: settingsController.vcpkgRoot
                            onEditingFinished: {
                                settingsController.vcpkgRoot = text
                                root.tools = settingsController.detectTools()
                            }
                            Layout.fillWidth: true
                        }
                        Button { text: "Browse"; onClicked: vcpkgDialog.open() }

                        Label { text: "ffmpeg"; color: themeController.muted }
                        Label { text: tools.ffmpeg || "missing"; color: tools.ffmpegReady ? themeController.success : themeController.danger; elide: Text.ElideMiddle; Layout.fillWidth: true }
                        Item {}

                        Label { text: "ffprobe"; color: themeController.muted }
                        Label { text: tools.ffprobe || "missing"; color: tools.ffprobeReady ? themeController.success : themeController.danger; elide: Text.ElideMiddle; Layout.fillWidth: true }
                        Item {}
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        Button {
                            text: "Detect"
                            onClicked: root.tools = settingsController.detectTools()
                        }
                        Button {
                            text: "Doctor"
                            onClicked: jobController.runDoctor()
                        }
                        Button {
                            text: "Config List"
                            onClicked: jobController.configList()
                        }
                        Button {
                            text: "Reset App Settings"
                            onClicked: {
                                settingsController.resetDefaults()
                                root.tools = settingsController.detectTools()
                                root.loadCloudDrafts()
                            }
                        }
                        Item { Layout.fillWidth: true }
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
        Label {
            text: parent.title
            color: themeController.text
            font.pixelSize: 20
            font.weight: Font.DemiBold
        }
        Label {
            text: parent.subtitle
            color: themeController.muted
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }
    }

    component StatusCard: Rectangle {
        property string title: ""
        property string detail: ""
        property bool ok: false
        property color stateColor: ok ? themeController.success : themeController.warning
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
                Label {
                    text: parent.parent.parent.title
                    color: themeController.text
                    font.weight: Font.DemiBold
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }
            }
            Label {
                text: parent.parent.detail
                color: themeController.muted
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
        Label {
            text: parent.title
            color: themeController.muted
            Layout.fillWidth: true
        }
        TextArea {
            id: editor
            wrapMode: TextEdit.Wrap
            selectByMouse: true
            Layout.fillWidth: true
            Layout.preferredHeight: 110
        }
    }
}
