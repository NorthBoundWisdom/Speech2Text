import AppKit
import SwiftUI

struct SettingsView: View {
    @ObservedObject var store: AppStore
    @Environment(\.dismiss) private var dismiss
    @State private var draft: AppSettings
    @State private var selectedTab: SettingsTab = .overview
    @State private var modelDownloadAlias: String?
    @State private var isAudioToolsPresented = false
    @State private var isDeleteLogsConfirmationPresented = false
    @State private var isAPIKeyVisible = false
    @FocusState private var isAPIKeyFocused: Bool

    init(store: AppStore) {
        self.store = store
        _draft = State(initialValue: store.settings)
    }

    var body: some View {
        VStack(spacing: 0) {
            HStack(spacing: 0) {
                SettingsSidebar(selection: $selectedTab)
                    .frame(width: 190)
                Divider()
                detailPane
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            }
            Divider()
            SettingsFooterBar(
                message: store.settingsMessage,
                recheck: {
                    store.reload()
                    store.refreshConfigInspection()
                    draft = store.settings
                },
                cancel: { dismiss() },
                save: {
                    if store.saveSettings(draft) {
                        dismiss()
                    }
                }
            )
        }
        .frame(minWidth: 820, minHeight: 620)
        .onAppear {
            store.refreshConfigInspection()
        }
        .confirmationDialog("Delete Historical Logs?", isPresented: $isDeleteLogsConfirmationPresented) {
            Button("Delete Logs", role: .destructive) {
                store.deleteHistoricalLogs()
            }
            Button("Cancel", role: .cancel) {}
        } message: {
            Text("This removes old app logs, job logs, and cached crash reports. The current app log is kept.")
        }
        .sheet(isPresented: modelDownloadsPresentedBinding) {
            ModelDownloadsView(selectedAlias: modelDownloadAlias ?? draft.localASRModel)
        }
        .sheet(isPresented: $isAudioToolsPresented) {
            AudioToolsSetupView(store: store)
        }
    }

    private var detailPane: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 14) {
                switch selectedTab {
                case .overview:
                    overviewPane
                case .local:
                    localPane
                case .cloud:
                    cloudPane
                case .translation:
                    translationPane
                case .workflow:
                    workflowPane
                case .library:
                    libraryPane
                case .reading:
                    readingPane
                case .runtime:
                    runtimePane
                case .sources:
                    ConfigSourcesPane(
                        payload: store.configInspection,
                        isLoading: store.isLoadingConfigInspection,
                        openConfig: store.openCloudConfig,
                        refresh: store.refreshConfigInspection
                    )
                }
            }
            .padding(18)
            .frame(maxWidth: .infinity, alignment: .leading)
        }
    }

    private var rowDivider: some View {
        Divider()
    }

    private var overviewPane: some View {
        SettingsOverviewPane(
            cards: [
                statusCard(for: store.diagnostics.item("model-\(draft.localASRModel)") ?? store.diagnostics.item("model-\(store.settings.localASRModel)")),
                statusCard(for: store.diagnostics.item("cli")),
                statusCard(for: store.diagnostics.item("ffmpeg")),
                SettingsStatusCard(
                    title: "Cloud Summary",
                    detail: draft.isCloudConfigured ? "\(draft.cloudModel) @ \(draft.apiBase)" : "Optional; endpoint and API key are not configured.",
                    severity: draft.isCloudConfigured ? .ok : .warning,
                    icon: draft.isCloudConfigured ? "checkmark.circle.fill" : "cloud"
                ),
                statusCard(for: store.diagnostics.item("logs")),
            ].compactMap { $0 }
        )
    }

    private var localPane: some View {
        SettingsSectionPane(
            title: "Local ASR",
            subtitle: "Choose the local transcription model and decoding profile."
        ) {
            settingsGroup {
                modelSetupRow(
                    item: store.diagnostics.item("model-\(draft.localASRModel)"),
                    selection: $draft.localASRModel,
                    disabled: store.diagnostics.item("model-\(draft.localASRModel)")?.severity == .ok,
                    action: { modelDownloadAlias = draft.localASRModel }
                )
                rowDivider
                labeledField("ASR Profile") {
                    Picker("ASR Profile", selection: $draft.localASRProfile) {
                        ForEach(LocalASRProfile.all) { profile in
                            Text(profile.title).tag(profile.name)
                        }
                    }
                    .labelsHidden()
                    .frame(width: 220)
                }
            }
        }
    }

    private var cloudPane: some View {
        SettingsSectionPane(
            title: "Cloud Model",
            subtitle: "Configure summary and title generation."
        ) {
            settingsGroup {
                labeledField("API Base") {
                    apiBaseControl
                }
                rowDivider
                labeledField("API Key") {
                    apiKeyControl
                }
                rowDivider
                labeledField("Model") {
                    EditableComboBox(text: $draft.cloudModel, options: draft.cloudModelOptions)
                        .frame(width: 240, height: 28)
                }
                rowDivider
                numericCloudFields
                rowDivider
                promptEditor("Summary Prompt", text: $draft.summaryPrompt)
                rowDivider
                promptEditor("Title Prompt", text: $draft.titlePrompt)
                rowDivider
                configFileRow
            }
        }
    }

    private var translationPane: some View {
        SettingsSectionPane(
            title: "Translation",
            subtitle: "Control SRT translation output."
        ) {
            settingsGroup {
                Toggle("Translate generated SRT subtitles to Chinese", isOn: $draft.translation.enabled)
                    .frame(maxWidth: .infinity, minHeight: 44, alignment: .leading)
                rowDivider
                labeledField("Backend") {
                    Picker("Translation Backend", selection: translationBackendBinding) {
                        Text("Cloud").tag(TranslationBackend.cloud)
                        Text("Local").tag(TranslationBackend.local)
                    }
                    .pickerStyle(.segmented)
                    .labelsHidden()
                    .frame(width: 170)
                }
                rowDivider
                labeledField("Target") {
                    Text("Simplified Chinese (zh)")
                        .foregroundStyle(.secondary)
                }
                rowDivider
                if draft.translation.backend == .cloud {
                    cloudTranslationRow
                } else {
                    translationModelRow
                }
            }
        }
    }

    private var workflowPane: some View {
        SettingsSectionPane(
            title: "Workflow",
            subtitle: "Set default processing behavior for future jobs."
        ) {
            settingsGroup {
                Toggle("Queue cloud summary by default", isOn: $draft.workflowDefaultCloudSummary)
                    .frame(maxWidth: .infinity, minHeight: 40, alignment: .leading)
                rowDivider
                Toggle("Prefer local-only processing", isOn: $draft.workflowLocalOnly)
                    .frame(maxWidth: .infinity, minHeight: 40, alignment: .leading)
                rowDivider
                labeledField("Chunking") {
                    Picker("Chunking", selection: $draft.workflowChunking) {
                        Text("Auto").tag("auto")
                        Text("Fixed").tag("fixed")
                        Text("Smart").tag("smart")
                    }
                    .pickerStyle(.segmented)
                    .labelsHidden()
                    .frame(width: 230)
                }
                rowDivider
                labeledField("Chunk Length") {
                    TextField("", text: $draft.workflowChunkLength)
                        .multilineTextAlignment(.trailing)
                        .frame(width: 110)
                    Text("sec").foregroundStyle(.secondary)
                }
                rowDivider
                labeledField("Overlap") {
                    TextField("", text: $draft.workflowOverlap)
                        .multilineTextAlignment(.trailing)
                        .frame(width: 110)
                    Text("sec").foregroundStyle(.secondary)
                }
            }
        }
    }

    private var readingPane: some View {
        SettingsSectionPane(
            title: "Reading",
            subtitle: "Tune the detail pane text used for transcripts, summaries, logs, and previews."
        ) {
            settingsGroup {
                labeledField("Text Size") {
                    Picker("Text Size", selection: readingTextSizeBinding) {
                        ForEach(ReadingTextSize.allCases) { size in
                            Text(size.title).tag(size)
                        }
                    }
                    .labelsHidden()
                    .frame(width: 210)
                }
                rowDivider
                labeledField("Line Spacing") {
                    Picker("Line Spacing", selection: readingLineSpacingBinding) {
                        ForEach(ReadingLineSpacing.allCases) { spacing in
                            Text(spacing.title).tag(spacing)
                        }
                    }
                    .pickerStyle(.segmented)
                    .labelsHidden()
                    .frame(width: 300)
                }
                rowDivider
                labeledField("Content Width") {
                    Picker("Content Width", selection: readingContentWidthBinding) {
                        ForEach(ReadingContentWidth.allCases) { width in
                            Text(width.title).tag(width)
                        }
                    }
                    .pickerStyle(.segmented)
                    .labelsHidden()
                    .frame(width: 360)
                }
                rowDivider
                labeledField("Font") {
                    Picker("Font", selection: readingFontDesignBinding) {
                        ForEach(ReadingFontDesign.allCases) { design in
                            Text(design.title).tag(design)
                        }
                    }
                    .pickerStyle(.segmented)
                    .labelsHidden()
                    .frame(width: 260)
                }
            }
            readingPreview
        }
    }

    private var libraryPane: some View {
        SettingsSectionPane(
            title: "Library",
            subtitle: "Choose the authoritative SonaFolio library location."
        ) {
            settingsGroup {
                libraryLocationRow
                rowDivider
                libraryActionsRow
            }
        }
    }

    private var libraryLocationRow: some View {
        HStack(alignment: .center, spacing: 12) {
            VStack(alignment: .leading, spacing: 3) {
                Text("Library Folder")
                    .fontWeight(.medium)
                Text(libraryModeDescription)
                    .font(.caption)
                    .foregroundStyle(.secondary)
                Text(draft.resolvedLibraryRoot.path)
                    .font(.caption2.monospaced())
                    .foregroundStyle(.secondary)
                    .lineLimit(2)
                    .truncationMode(.middle)
            }
            Spacer(minLength: 12)
            Button {
                chooseLibraryFolder()
            } label: {
                Label("Choose", systemImage: "folder")
                    .frame(minWidth: 104)
            }
        }
        .frame(maxWidth: .infinity, minHeight: 66, alignment: .leading)
    }

    private var libraryActionsRow: some View {
        HStack(spacing: 10) {
            Button {
                draft.libraryStorage = "icloud"
                draft.libraryICloudRoot = ""
            } label: {
                Label("Use iCloud", systemImage: "icloud")
            }
            .disabled(draft.libraryStorage == "icloud" && draft.libraryICloudRoot.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)

            Button {
                draft.libraryStorage = "local"
            } label: {
                Label("Use Local", systemImage: "externaldrive")
            }
            .disabled(draft.libraryStorage == "local")

            Button {
                revealLibraryFolder()
            } label: {
                Label("Open Folder", systemImage: "arrow.up.right.square")
            }

            Spacer()
        }
        .frame(maxWidth: .infinity, minHeight: 50, alignment: .leading)
    }

    private var libraryModeDescription: String {
        draft.libraryStorage == "local"
            ? "Local-only library"
            : "iCloud Drive library"
    }

    private var runtimePane: some View {
        SettingsSectionPane(
            title: "Runtime",
            subtitle: "Check local dependencies and maintenance actions."
        ) {
            settingsGroup {
                setupRow(
                    item: store.diagnostics.item("cli"),
                    actionTitle: "Install",
                    actionIcon: "shippingbox",
                    disabled: store.isInstallingRuntime
                        || store.diagnostics.item("cli")?.severity == .ok
                        || AppPaths.isAppStoreDistribution(),
                    action: store.installRuntime
                )
                rowDivider
                setupRow(
                    item: store.diagnostics.item("ffmpeg"),
                    actionTitle: "Install",
                    actionIcon: "waveform",
                    disabled: store.diagnostics.item("ffmpeg")?.severity == .ok
                        || AppPaths.isAppStoreDistribution(),
                    action: { isAudioToolsPresented = true }
                )
                rowDivider
                setupRow(
                    item: store.diagnostics.item("logs"),
                    actionTitle: "Reveal",
                    actionIcon: "doc.text.magnifyingglass",
                    disabled: false,
                    action: store.revealLogs
                )
                rowDivider
                deleteLogsRow
            }
        }
    }

    private func settingsGroup<Content: View>(@ViewBuilder content: () -> Content) -> some View {
        VStack(alignment: .leading, spacing: 0) {
            content()
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 4)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color.secondary.opacity(0.08))
        .clipShape(RoundedRectangle(cornerRadius: 8))
    }

    private var modelDownloadsPresentedBinding: Binding<Bool> {
        Binding(
            get: { modelDownloadAlias != nil },
            set: { isPresented in
                if !isPresented {
                    modelDownloadAlias = nil
                }
            }
        )
    }

    private var translationBackendBinding: Binding<TranslationBackend> {
        Binding(
            get: { draft.translation.backend },
            set: { draft.translation.backend = $0 }
        )
    }

    private var readingTextSizeBinding: Binding<ReadingTextSize> {
        Binding(
            get: { draft.readingStyle.textSize },
            set: { draft.readingStyle.textSize = $0 }
        )
    }

    private var readingLineSpacingBinding: Binding<ReadingLineSpacing> {
        Binding(
            get: { draft.readingStyle.lineSpacing },
            set: { draft.readingStyle.lineSpacing = $0 }
        )
    }

    private var readingContentWidthBinding: Binding<ReadingContentWidth> {
        Binding(
            get: { draft.readingStyle.contentWidth },
            set: { draft.readingStyle.contentWidth = $0 }
        )
    }

    private var readingFontDesignBinding: Binding<ReadingFontDesign> {
        Binding(
            get: { draft.readingStyle.fontDesign },
            set: { draft.readingStyle.fontDesign = $0 }
        )
    }

    private var numericCloudFields: some View {
        HStack(spacing: 16) {
            compactTextField("Timeout", text: $draft.cloudTimeout)
            compactTextField("Temperature", text: $draft.cloudTemperature)
            compactTextField("Max Tokens", text: $draft.cloudMaxTokens)
        }
        .frame(maxWidth: .infinity, minHeight: 54, alignment: .leading)
    }

    private var configFileRow: some View {
        HStack(alignment: .center, spacing: 12) {
            VStack(alignment: .leading, spacing: 3) {
                Text("Config File")
                    .fontWeight(.medium)
                Text("Open config.toml for direct edits.")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            Spacer()
            Button {
                store.openCloudConfig()
            } label: {
                Label("Open", systemImage: "doc.text")
                    .frame(minWidth: 96)
            }
        }
        .frame(maxWidth: .infinity, minHeight: 54, alignment: .leading)
    }

    private var readingPreview: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Preview")
                .foregroundStyle(.secondary)
            SimpleMarkdownView(text: readingPreviewMarkdown, style: draft.readingStyle)
                .frame(height: 260)
                .background(Color.secondary.opacity(0.06))
                .clipShape(RoundedRectangle(cornerRadius: 8))
                .overlay(
                    RoundedRectangle(cornerRadius: 8)
                        .stroke(Color.secondary.opacity(0.12), lineWidth: 1)
                )
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    private var readingPreviewMarkdown: String {
        """
        # A conversation worth keeping

        ## Main ideas

        This illustrative transcript discusses learning from conversations and preserving context.

        - Keep the original transcript available when reviewing a summary.
        - Use timestamps to return to important passages.

        ```text
        Stage: summary
        Progress: 100%
        ```

        | Document | State |
        | --- | --- |
        | Summary | Generated |
        | Transcript | Readable |
        """
    }

    private var cloudTranslationRow: some View {
        HStack(alignment: .center, spacing: 12) {
            Image(systemName: draft.isCloudConfigured ? "checkmark.circle.fill" : "exclamationmark.triangle.fill")
                .foregroundStyle(draft.isCloudConfigured ? .green : .orange)
                .frame(width: 18)
            VStack(alignment: .leading, spacing: 3) {
                Text("Cloud Translation")
                    .fontWeight(.medium)
                Text(draft.isCloudConfigured ? "Uses \(draft.cloudModel) from Cloud Model settings." : "Configure Cloud Model API Key before using cloud translation.")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .lineLimit(1)
                    .truncationMode(.middle)
            }
            Spacer()
        }
        .frame(maxWidth: .infinity, minHeight: 48, alignment: .leading)
    }

    private var translationModelRow: some View {
        let model = LocalASRModel.anyModel(for: draft.translation.localModelAlias)
        let present = localModelFilesArePresent(model)
        return HStack(alignment: .center, spacing: 12) {
            Image(systemName: present ? "checkmark.circle.fill" : "exclamationmark.triangle.fill")
                .foregroundStyle(present ? .green : .orange)
                .frame(width: 18)
            VStack(alignment: .leading, spacing: 3) {
                Text(model.title)
                    .fontWeight(.medium)
                Text(present ? "Local translation model files are present." : model.note)
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .lineLimit(1)
                    .truncationMode(.middle)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            Spacer()
            Button {
                modelDownloadAlias = model.alias
            } label: {
                Label("Download", systemImage: "arrow.down.circle")
                    .frame(minWidth: 88)
            }
            .disabled(present)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(.vertical, 4)
    }

    private var deleteLogsRow: some View {
        HStack(alignment: .center, spacing: 12) {
            Image(systemName: "trash")
                .foregroundStyle(.red)
                .frame(width: 18)
            VStack(alignment: .leading, spacing: 3) {
                Text("Historical Logs")
                    .fontWeight(.medium)
                Text("Delete old app logs, job logs, and cached crash reports.")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .lineLimit(1)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            Spacer()
            Button(role: .destructive) {
                isDeleteLogsConfirmationPresented = true
            } label: {
                Label("Delete", systemImage: "trash")
                    .frame(minWidth: 96)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(.vertical, 4)
    }

    private var apiBaseControl: some View {
        HStack(spacing: 8) {
            TextField("", text: $draft.apiBase)
                .labelsHidden()
                .multilineTextAlignment(.trailing)
            pasteButton {
                if let text = clipboardString() {
                    draft.apiBase = text
                }
            }
        }
    }

    private var apiKeyControl: some View {
        HStack(spacing: 8) {
            apiKeyPreviewField
            Button {
                isAPIKeyVisible.toggle()
            } label: {
                Image(systemName: isAPIKeyVisible ? "eye.slash" : "eye")
                    .frame(width: 18, height: 18)
            }
            .buttonStyle(.bordered)
            .help(isAPIKeyVisible ? "Hide API key" : "Show API key")

            pasteButton {
                if let text = clipboardString() {
                    draft.apiKey = text
                }
            }

            checkKeyButton
        }
    }

    @ViewBuilder
    private var apiKeyPreviewField: some View {
        if isAPIKeyVisible {
            TextField("", text: $draft.apiKey)
                .labelsHidden()
                .focused($isAPIKeyFocused)
                .font(.system(.body, design: .monospaced))
                .multilineTextAlignment(.trailing)
        } else {
            SecureField("", text: $draft.apiKey)
                .labelsHidden()
                .focused($isAPIKeyFocused)
                .font(.system(.body, design: .monospaced))
                .multilineTextAlignment(.trailing)
        }
    }

    private func pasteButton(action: @escaping () -> Void) -> some View {
        Button(action: action) {
            Image(systemName: "doc.on.clipboard")
                .frame(width: 18, height: 18)
        }
        .buttonStyle(.bordered)
        .help("Paste from Clipboard")
    }

    private func clipboardString() -> String? {
        let text = NSPasteboard.general.string(forType: .string)?
            .trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
        return text.isEmpty ? nil : text
    }

    @ViewBuilder
    private var checkKeyButton: some View {
        if store.isCloudConnectionVerified(for: draft) {
            Button {
                store.testCloudConnection(draft)
            } label: {
                Image(systemName: "network")
                    .frame(width: 18, height: 18)
            }
            .buttonStyle(.borderedProminent)
            .tint(.green)
            .disabled(store.isTestingCloud)
            .help("Check API key")
        } else if store.isCloudConnectionFailed(for: draft) {
            Button {
                store.testCloudConnection(draft)
            } label: {
                Image(systemName: "network")
                    .frame(width: 18, height: 18)
            }
            .buttonStyle(.borderedProminent)
            .tint(.red)
            .disabled(store.isTestingCloud)
            .help("Check API key")
        } else {
            Button {
                store.testCloudConnection(draft)
            } label: {
                Image(systemName: "network")
                    .frame(width: 18, height: 18)
            }
            .disabled(store.isTestingCloud)
            .help("Check API key")
        }
    }

    private func icon(for severity: DiagnosticSeverity) -> String {
        switch severity {
        case .ok: return "checkmark.circle.fill"
        case .warning: return "exclamationmark.triangle.fill"
        case .error: return "xmark.octagon.fill"
        }
    }

    private func color(for severity: DiagnosticSeverity) -> Color {
        switch severity {
        case .ok: return .green
        case .warning: return .orange
        case .error: return .red
        }
    }

    private func localModelFilesArePresent(_ model: LocalASRModel) -> Bool {
        let root = AppPaths.modelRoot(dataRoot: AppPaths.dataRoot())
        return model.files.allSatisfy { file in
            FileManager.default.fileExists(atPath: root.appendingPathComponent(file.pathUnderModelRoot).path)
        }
    }

    private func setupRow(
        item: DiagnosticItem?,
        actionTitle: String,
        actionIcon: String,
        disabled: Bool,
        action: @escaping () -> Void
    ) -> some View {
        HStack(alignment: .center, spacing: 12) {
            Image(systemName: icon(for: item?.severity ?? .warning))
                .foregroundStyle(color(for: item?.severity ?? .warning))
                .frame(width: 18)
            VStack(alignment: .leading, spacing: 3) {
                Text(item?.title ?? "Check")
                    .fontWeight(.medium)
                Text(item?.detail ?? "Status is unavailable.")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .lineLimit(1)
                    .truncationMode(.middle)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            Spacer()
            Button {
                action()
            } label: {
                Label(actionTitle, systemImage: actionIcon)
                    .frame(minWidth: 96)
            }
            .disabled(disabled)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(.vertical, 4)
    }

    private func modelSetupRow(
        item: DiagnosticItem?,
        selection: Binding<String>,
        disabled: Bool,
        action: @escaping () -> Void
    ) -> some View {
        HStack(alignment: .center, spacing: 12) {
            Image(systemName: icon(for: item?.severity ?? .warning))
                .foregroundStyle(color(for: item?.severity ?? .warning))
                .frame(width: 18)
            Text(item?.title ?? "ASR Model")
                .fontWeight(.medium)
                .frame(width: 210, alignment: .leading)
            Spacer()
            Picker("ASR Model", selection: selection) {
                ForEach(LocalASRModel.all) { model in
                    Text(model.title).tag(model.alias)
                }
            }
            .labelsHidden()
            .frame(width: 170, alignment: .trailing)
            Button {
                action()
            } label: {
                Label("Download", systemImage: "arrow.down.circle")
                    .frame(minWidth: 88)
            }
            .disabled(disabled)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(.vertical, 4)
    }

    private func labeledField<Content: View>(_ title: String, @ViewBuilder content: () -> Content) -> some View {
        HStack(alignment: .center, spacing: 12) {
            Text(title)
                .lineLimit(1)
                .frame(width: 132, alignment: .leading)
                .foregroundStyle(.secondary)
            Spacer(minLength: 24)
            content()
                .frame(minWidth: 0, alignment: .trailing)
        }
        .frame(maxWidth: .infinity, minHeight: 54)
    }

    private func compactTextField(_ title: String, text: Binding<String>) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(title)
                .font(.caption)
                .foregroundStyle(.secondary)
            TextField("", text: text)
                .textFieldStyle(.roundedBorder)
        }
    }

    private func promptEditor(_ title: String, text: Binding<String>) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(title)
                .foregroundStyle(.secondary)
            TextEditor(text: text)
                .font(.body)
                .frame(minHeight: 74)
                .scrollContentBackground(.hidden)
                .background(Color(nsColor: .textBackgroundColor).opacity(0.65))
                .clipShape(RoundedRectangle(cornerRadius: 6))
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(.vertical, 8)
    }

    private func chooseLibraryFolder() {
        let panel = NSOpenPanel()
        panel.title = "Choose SonaFolio Library Folder"
        panel.canChooseFiles = false
        panel.canChooseDirectories = true
        panel.canCreateDirectories = true
        panel.allowsMultipleSelection = false
        panel.directoryURL = draft.resolvedLibraryRoot
        if panel.runModal() == .OK, let url = panel.url {
            let path = AppPaths.normalizedLibraryRoot(url.standardizedFileURL).path
            if draft.libraryStorage == "local" {
                draft.libraryLocalRoot = path
            } else {
                draft.libraryICloudRoot = path
            }
        }
    }

    private func revealLibraryFolder() {
        let url = draft.resolvedLibraryRoot
        try? FileManager.default.createDirectory(at: url, withIntermediateDirectories: true)
        NSWorkspace.shared.open(url)
    }

    private func statusCard(for item: DiagnosticItem?) -> SettingsStatusCard? {
        guard let item else { return nil }
        return SettingsStatusCard(
            title: item.title,
            detail: item.detail,
            severity: item.severity,
            icon: icon(for: item.severity)
        )
    }
}

private enum SettingsTab: String, CaseIterable, Identifiable {
    case overview
    case local
    case cloud
    case translation
    case workflow
    case library
    case reading
    case runtime
    case sources

    var id: String {
        rawValue
    }

    var title: String {
        switch self {
        case .overview: return "Overview"
        case .local: return "Local ASR"
        case .cloud: return "Cloud Model"
        case .translation: return "Translation"
        case .workflow: return "Workflow"
        case .library: return "Library"
        case .reading: return "Reading"
        case .runtime: return "Runtime"
        case .sources: return "Config Sources"
        }
    }

    var icon: String {
        switch self {
        case .overview: return "gauge"
        case .local: return "waveform"
        case .cloud: return "cloud"
        case .translation: return "character.bubble"
        case .workflow: return "slider.horizontal.3"
        case .library: return "arrow.triangle.2.circlepath"
        case .reading: return "textformat.size"
        case .runtime: return "shippingbox"
        case .sources: return "list.bullet.rectangle"
        }
    }
}

private struct SettingsSidebar: View {
    @Binding var selection: SettingsTab

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Settings")
                .font(.title3)
                .fontWeight(.semibold)
                .padding(.horizontal, 12)
                .padding(.top, 14)
            VStack(spacing: 2) {
                ForEach(SettingsTab.allCases) { tab in
                    Button {
                        selection = tab
                    } label: {
                        Label(tab.title, systemImage: tab.icon)
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .padding(.horizontal, 10)
                            .padding(.vertical, 7)
                            .background(selection == tab ? Color.accentColor.opacity(0.16) : Color.clear)
                            .clipShape(RoundedRectangle(cornerRadius: 6))
                            .contentShape(Rectangle())
                    }
                    .buttonStyle(.plain)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .contentShape(Rectangle())
                    .foregroundStyle(selection == tab ? .primary : .secondary)
                }
            }
            .padding(.horizontal, 8)
            .frame(maxWidth: .infinity, alignment: .leading)
            Spacer()
        }
        .background(Color(nsColor: .windowBackgroundColor))
    }
}

private struct SettingsSectionPane<Content: View>: View {
    let title: String
    let subtitle: String
    @ViewBuilder let content: Content

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            VStack(alignment: .leading, spacing: 3) {
                Text(title)
                    .font(.title3)
                    .fontWeight(.semibold)
                Text(subtitle)
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            content
        }
    }
}

private struct SettingsStatusCard: Identifiable {
    let id = UUID()
    let title: String
    let detail: String
    let severity: DiagnosticSeverity
    let icon: String
}

private struct SettingsOverviewPane: View {
    let cards: [SettingsStatusCard]

    var body: some View {
        SettingsSectionPane(
            title: "Overview",
            subtitle: "Current readiness and configuration state."
        ) {
            LazyVGrid(columns: [GridItem(.adaptive(minimum: 230), spacing: 10)], spacing: 10) {
                ForEach(cards) { card in
                    HStack(alignment: .top, spacing: 10) {
                        Image(systemName: card.icon)
                            .foregroundStyle(color(for: card.severity))
                            .frame(width: 18)
                        VStack(alignment: .leading, spacing: 4) {
                            Text(card.title)
                                .fontWeight(.medium)
                            Text(card.detail)
                                .font(.caption)
                                .foregroundStyle(.secondary)
                                .lineLimit(3)
                        }
                        Spacer(minLength: 0)
                    }
                    .padding(12)
                    .frame(minHeight: 94, alignment: .topLeading)
                    .background(Color.secondary.opacity(0.08))
                    .clipShape(RoundedRectangle(cornerRadius: 8))
                }
            }
        }
    }

    private func color(for severity: DiagnosticSeverity) -> Color {
        switch severity {
        case .ok: return .green
        case .warning: return .orange
        case .error: return .red
        }
    }
}

private struct ConfigSourcesPane: View {
    let payload: ConfigInspectionPayload?
    let isLoading: Bool
    let openConfig: () -> Void
    let refresh: () -> Void

    var body: some View {
        SettingsSectionPane(
            title: "Config Sources",
            subtitle: "Effective values, source layers, and preferred editable keys."
        ) {
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text(payload?.path ?? "config.toml")
                        .font(.system(.caption, design: .monospaced))
                        .foregroundStyle(.secondary)
                        .lineLimit(1)
                        .truncationMode(.middle)
                    layerSummary
                }
                Spacer()
                Button(action: refresh) {
                    Label(isLoading ? "Loading" : "Refresh", systemImage: "arrow.clockwise")
                }
                .disabled(isLoading)
                Button(action: openConfig) {
                    Label("Open", systemImage: "doc.text")
                }
            }
            .padding(12)
            .background(Color.secondary.opacity(0.08))
            .clipShape(RoundedRectangle(cornerRadius: 8))

            VStack(spacing: 0) {
                HStack {
                    Text("Key").frame(width: 190, alignment: .leading)
                    Text("Value").frame(maxWidth: .infinity, alignment: .leading)
                    Text("Source").frame(width: 132, alignment: .leading)
                    Text("Raw Key").frame(width: 190, alignment: .leading)
                }
                .font(.caption)
                .foregroundStyle(.secondary)
                .padding(.horizontal, 10)
                .padding(.vertical, 8)

                Divider()

                if let payload {
                    ForEach(payload.entries) { entry in
                        HStack(alignment: .firstTextBaseline, spacing: 10) {
                            Text(entry.key)
                                .font(.system(.caption, design: .monospaced))
                                .frame(width: 190, alignment: .leading)
                            Text(entry.value.displayString)
                                .font(.caption)
                                .lineLimit(2)
                                .truncationMode(.middle)
                                .frame(maxWidth: .infinity, alignment: .leading)
                            sourceBadge(entry.source, isDefault: entry.isDefault)
                                .frame(width: 132, alignment: .leading)
                            Text(entry.rawKey)
                                .font(.system(.caption, design: .monospaced))
                                .foregroundStyle(.secondary)
                                .lineLimit(1)
                                .truncationMode(.middle)
                                .frame(width: 190, alignment: .leading)
                        }
                        .padding(.horizontal, 10)
                        .padding(.vertical, 7)
                        Divider()
                    }
                } else {
                    Text(isLoading ? "Loading config sources..." : "Config source data is unavailable.")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .frame(maxWidth: .infinity, minHeight: 96)
                }
            }
            .background(Color.secondary.opacity(0.06))
            .clipShape(RoundedRectangle(cornerRadius: 8))
        }
    }

    private var layerSummary: some View {
        let user = payload?.layers.userConfig.enabled == true ? "user config loaded" : "using defaults"
        return Text(user)
            .font(.caption)
            .foregroundStyle(.secondary)
    }

    private func sourceBadge(_ source: String, isDefault: Bool) -> some View {
        let text = isDefault ? "default" : source.replacingOccurrences(of: "_", with: " ")
        let color: Color = source == "user_config" ? .blue : .secondary
        return Text(text)
            .font(.caption2)
            .padding(.horizontal, 7)
            .padding(.vertical, 3)
            .background(color.opacity(0.14))
            .foregroundStyle(color)
            .clipShape(RoundedRectangle(cornerRadius: 6))
    }
}

private struct SettingsFooterBar: View {
    let message: String
    let recheck: () -> Void
    let cancel: () -> Void
    let save: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                Button(action: recheck) {
                    Label("Recheck", systemImage: "arrow.clockwise")
                }
                Spacer()
                Button("Cancel", action: cancel)
                Button(action: save) {
                    Label("Save", systemImage: "checkmark.seal")
                }
                .buttonStyle(.borderedProminent)
            }
            if !message.isEmpty {
                Text(message)
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .lineLimit(2)
            }
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 10)
    }
}

struct EditableComboBox: NSViewRepresentable {
    @Binding var text: String
    let options: [String]

    func makeCoordinator() -> Coordinator {
        Coordinator(text: $text)
    }

    func makeNSView(context: Context) -> NSComboBox {
        let comboBox = NSComboBox()
        comboBox.usesDataSource = false
        comboBox.isEditable = true
        comboBox.completes = false
        comboBox.delegate = context.coordinator
        comboBox.target = context.coordinator
        comboBox.action = #selector(Coordinator.comboBoxAction(_:))
        comboBox.addItems(withObjectValues: options)
        comboBox.stringValue = text
        return comboBox
    }

    func updateNSView(_ nsView: NSComboBox, context _: Context) {
        let currentItems = nsView.objectValues.compactMap { $0 as? String }
        if currentItems != options {
            nsView.removeAllItems()
            nsView.addItems(withObjectValues: options)
        }
        if nsView.stringValue != text {
            nsView.stringValue = text
        }
    }

    final class Coordinator: NSObject, NSComboBoxDelegate, NSControlTextEditingDelegate {
        @Binding private var text: String

        init(text: Binding<String>) {
            _text = text
        }

        @objc func comboBoxAction(_ sender: NSComboBox) {
            commit(sender, preferSelection: true)
        }

        func controlTextDidChange(_ notification: Notification) {
            guard let comboBox = notification.object as? NSComboBox else { return }
            commit(comboBox, preferSelection: false)
        }

        func controlTextDidEndEditing(_ notification: Notification) {
            guard let comboBox = notification.object as? NSComboBox else { return }
            commit(comboBox, preferSelection: false)
        }

        func comboBoxSelectionIsChanging(_ notification: Notification) {
            guard let comboBox = notification.object as? NSComboBox else { return }
            commit(comboBox, preferSelection: true)
        }

        func comboBoxSelectionDidChange(_ notification: Notification) {
            guard let comboBox = notification.object as? NSComboBox else { return }
            commit(comboBox, preferSelection: true)
        }

        func comboBoxWillDismiss(_ notification: Notification) {
            guard let comboBox = notification.object as? NSComboBox else { return }
            commit(comboBox, preferSelection: true)
        }

        private func commit(_ comboBox: NSComboBox, preferSelection: Bool) {
            if preferSelection, let selectedText = Self.selectedText(from: comboBox) {
                text = selectedText
                return
            }
            text = comboBox.stringValue
        }

        static func selectedText(from comboBox: NSComboBox) -> String? {
            guard let selected = comboBox.objectValueOfSelectedItem as? String else {
                return nil
            }
            let trimmed = selected.trimmingCharacters(in: .whitespacesAndNewlines)
            return trimmed.isEmpty ? nil : selected
        }
    }
}

struct ModelDownloadsView: View {
    let selectedAlias: String
    @Environment(\.dismiss) private var dismiss

    private var dataRoot: URL {
        AppPaths.dataRoot()
    }

    private var modelRoot: URL {
        AppPaths.modelRoot(dataRoot: dataRoot)
    }

    private var selectedModel: LocalASRModel {
        LocalASRModel.anyModel(for: selectedAlias)
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            HStack {
                Text("Model Downloads")
                    .font(.title3)
                    .fontWeight(.semibold)
                Spacer()
                Button("Done") {
                    dismiss()
                }
            }

            Text("Selected model: \(selectedModel.title) (\(selectedModel.alias))")
                .font(.headline)
            Text(selectedModel.note)
                .font(.caption)
                .foregroundStyle(.secondary)

            VStack(alignment: .leading, spacing: 8) {
                Text("Place downloaded files under:")
                    .fontWeight(.medium)
                Text(modelRoot.path)
                    .font(.system(.caption, design: .monospaced))
                    .textSelection(.enabled)
                    .padding(8)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .background(Color.secondary.opacity(0.12))
                    .clipShape(RoundedRectangle(cornerRadius: 6))
                HStack {
                    Button {
                        try? FileManager.default.createDirectory(at: modelRoot, withIntermediateDirectories: true)
                        NSWorkspace.shared.open(modelRoot)
                    } label: {
                        Label("Open Folder", systemImage: "folder")
                    }
                    Button {
                        NSPasteboard.general.clearContents()
                        NSPasteboard.general.setString(modelRoot.path, forType: .string)
                    } label: {
                        Label("Copy Path", systemImage: "doc.on.doc")
                    }
                }
            }

            Divider()

            ForEach(selectedModel.files) { file in
                VStack(alignment: .leading, spacing: 6) {
                    HStack {
                        Text(file.name)
                            .fontWeight(.semibold)
                        Spacer()
                        if let url = URL(string: file.url) {
                            Link("Download", destination: url)
                        }
                    }
                    Text(modelRoot.appendingPathComponent(file.pathUnderModelRoot).path)
                        .font(.system(.caption, design: .monospaced))
                        .textSelection(.enabled)
                        .foregroundStyle(.secondary)
                }
                .padding(10)
                .background(Color.secondary.opacity(0.10))
                .clipShape(RoundedRectangle(cornerRadius: 8))
            }

            Spacer(minLength: 0)
        }
        .padding(20)
        .frame(width: 680, height: 460)
    }
}

struct AudioToolsSetupView: View {
    @ObservedObject var store: AppStore
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        HStack(spacing: 16) {
            Link("Homebrew Formula", destination: URL(string: "https://formulae.brew.sh/formula/ffmpeg")!)

            Button {
                store.reload()
                dismiss()
            } label: {
                Label("Refresh", systemImage: "arrow.clockwise")
            }
            .buttonStyle(.borderedProminent)
        }
        .padding(20)
        .frame(width: 360, height: 96)
    }
}
