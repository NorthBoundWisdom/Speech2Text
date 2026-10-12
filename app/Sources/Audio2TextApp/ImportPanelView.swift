import SwiftUI
import UniformTypeIdentifiers

struct ImportPanelView: View {
    @ObservedObject var controller: JobController
    @Binding var isPresented: Bool

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            Picker("", selection: inputModeBinding) {
                ForEach(InputMode.allCases) { mode in
                    Text(mode.title).tag(mode)
                }
            }
            .pickerStyle(.segmented)

            if controller.inputMode == .xiaoyuzhou {
                linkImportFields
            } else {
                fileImportFields
            }

            if shouldShowGroupPicker {
                groupPicker
            }

            importActionBar
        }
        .frame(width: 360)
    }

    private var linkImportFields: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Link")
                .font(.caption)
                .foregroundStyle(.secondary)
            HStack(spacing: 8) {
                TextField("https://www.xiaoyuzhoufm.com/episode/...", text: urlTextBinding)
                    .textFieldStyle(.roundedBorder)
                Button {
                    controller.checkLink()
                } label: {
                    if case .checking = controller.linkCheckStatus {
                        ProgressView()
                            .controlSize(.small)
                    } else {
                        Text("Check")
                    }
                }
                .disabled(controller.urlText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || controller.stage.isRunning)
            }
            linkStatusView
        }
    }

    private var linkStatusView: some View {
        Group {
            switch controller.linkCheckStatus {
            case .idle:
                EmptyView()
            case .checking:
                Text("Checking...")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            case let .valid(_, title):
                Label(title.isEmpty ? "Link is valid" : "Link is valid: \(title)", systemImage: "checkmark.circle.fill")
                    .font(.caption)
                    .foregroundStyle(.green)
                    .lineLimit(2)
            case let .invalid(message):
                Label(message, systemImage: "xmark.circle.fill")
                    .font(.caption)
                    .foregroundStyle(.red)
                    .lineLimit(2)
            }
        }
    }

    private var fileImportFields: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Audio / Video File")
                .font(.caption)
                .foregroundStyle(.secondary)
            HStack(spacing: 8) {
                TextField("Choose an audio or video file", text: selectedFilePathBinding)
                    .textFieldStyle(.roundedBorder)
                    .disabled(true)
                Button("Select") {
                    chooseAudioFile()
                }
            }
            Picker("", selection: localImportModeBinding) {
                ForEach(LocalImportMode.allCases) { mode in
                    Text(mode.title).tag(mode)
                }
            }
            .pickerStyle(.segmented)
            .labelsHidden()
        }
    }

    private var groupPicker: some View {
        VStack(alignment: .leading, spacing: 5) {
            Text("Group")
                .font(.caption)
                .foregroundStyle(.secondary)
            HStack(spacing: 8) {
                TextField("Default", text: selectedGroupNameBinding)
                    .textFieldStyle(.roundedBorder)
                Menu {
                    ForEach(controller.availableGroupNames, id: \.self) { groupName in
                        Button(groupName) {
                            controller.selectedGroupName = groupName
                        }
                    }
                } label: {
                    Image(systemName: "chevron.down")
                }
                .menuStyle(.borderlessButton)
                .fixedSize()
                .help("Choose existing group")
            }
        }
    }

    private var importActionBar: some View {
        HStack(spacing: 10) {
            Button {
                controller.resetImportDraft()
                isPresented = false
            } label: {
                Text("Cancel")
                    .frame(maxWidth: .infinity)
            }
            .buttonStyle(.bordered)

            Button {
                controller.importOnly()
                isPresented = false
            } label: {
                Label("Confirm", systemImage: "checkmark")
                    .frame(maxWidth: .infinity)
            }
            .buttonStyle(.borderedProminent)
            .disabled(!controller.canConfirmImport)
        }
    }

    private var shouldShowGroupPicker: Bool {
        switch controller.inputMode {
        case .xiaoyuzhou:
            return controller.isLinkValidForCurrentURL
        case .localFile:
            return controller.selectedFile != nil
        }
    }

    private var inputModeBinding: Binding<InputMode> {
        Binding(
            get: { controller.inputMode },
            set: {
                controller.inputMode = $0
                controller.resetImportDraft()
            }
        )
    }

    private var urlTextBinding: Binding<String> {
        Binding(
            get: { controller.urlText },
            set: { controller.urlText = $0 }
        )
    }

    private var selectedGroupNameBinding: Binding<String> {
        Binding(
            get: { controller.selectedGroupName },
            set: { controller.selectedGroupName = $0 }
        )
    }

    private var selectedFilePathBinding: Binding<String> {
        Binding(
            get: { controller.selectedFile?.path ?? "" },
            set: { _ in }
        )
    }

    private var localImportModeBinding: Binding<LocalImportMode> {
        Binding(
            get: { controller.localImportMode },
            set: { controller.localImportMode = $0 }
        )
    }

    private func chooseAudioFile() {
        let panel = NSOpenPanel()
        panel.canChooseFiles = true
        panel.canChooseDirectories = false
        panel.allowsMultipleSelection = false
        panel.allowedContentTypes = [.audio, .movie, .video]
        if panel.runModal() == .OK {
            controller.selectedFile = panel.url
        }
    }
}
