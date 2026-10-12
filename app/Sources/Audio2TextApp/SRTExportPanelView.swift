import SwiftUI

struct SRTExportPanelView: View {
    @ObservedObject var controller: SRTExportController
    @Binding var isPresented: Bool

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack {
                Text("Generate SRT")
                    .font(.title3)
                    .fontWeight(.semibold)
                Spacer()
                Button("Done") {
                    isPresented = false
                }
            }

            filePickerRow
            Toggle("Overwrite existing subtitle file", isOn: $controller.overwrite)
                .disabled(controller.state.isRunning)

            statusView

            TextEditor(text: logBinding)
                .font(.system(.caption, design: .monospaced))
                .frame(height: 180)
                .scrollContentBackground(.hidden)
                .background(Color.secondary.opacity(0.08))
                .clipShape(RoundedRectangle(cornerRadius: 6))

            HStack {
                if controller.successURL != nil {
                    Button {
                        controller.revealOutput()
                    } label: {
                        Label("Reveal", systemImage: "folder")
                    }
                }
                Spacer()
                Button("Cancel") {
                    isPresented = false
                }
                Button {
                    controller.export()
                } label: {
                    Label("Generate", systemImage: "captions.bubble")
                }
                .buttonStyle(.borderedProminent)
                .disabled(!controller.canExport)
            }
        }
        .padding(20)
        .frame(width: 620, height: 430)
    }

    private var filePickerRow: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Audio / Video File")
                .font(.caption)
                .foregroundStyle(.secondary)
            HStack(spacing: 8) {
                TextField("Choose an audio or video file", text: selectedFilePathBinding)
                    .textFieldStyle(.roundedBorder)
                    .disabled(true)
                Button("Choose") {
                    controller.chooseFile()
                }
                .disabled(controller.state.isRunning)
            }
        }
    }

    @ViewBuilder
    private var statusView: some View {
        switch controller.state {
        case .idle:
            Text("Source language: auto. Output: SRT beside the selected file.")
                .font(.caption)
                .foregroundStyle(.secondary)
        case .running:
            HStack(spacing: 8) {
                ProgressView()
                    .controlSize(.small)
                Text("Generating subtitles...")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        case let .success(url):
            Label(url.path, systemImage: "checkmark.circle.fill")
                .font(.caption)
                .foregroundStyle(.green)
                .lineLimit(2)
                .truncationMode(.middle)
        case let .failure(message):
            Label(message, systemImage: "xmark.octagon.fill")
                .font(.caption)
                .foregroundStyle(.red)
                .lineLimit(3)
        }
    }

    private var selectedFilePathBinding: Binding<String> {
        Binding(
            get: { controller.selectedFile?.path ?? "" },
            set: { _ in }
        )
    }

    private var logBinding: Binding<String> {
        Binding(
            get: { controller.logText },
            set: { _ in }
        )
    }
}
