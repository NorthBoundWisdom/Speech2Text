import SwiftUI

struct SummaryPaneView: View {
    @ObservedObject var controller: JobController
    let readingStyle: ReadingStyleSettings
    @State private var isEditing = false
    @State private var summaryDraft = ""
    @State private var loadedSummaryURL: URL?
    @State private var isRegenerateConfirmationPresented = false

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            header
            Divider()
            content
        }
        .onAppear {
            loadDraft(force: true)
        }
        .onDisappear {
            Task { await controller.flushPendingSummarySave() }
        }
        .onChange(of: controller.snapshot.summaryURL) { _ in
            Task { await controller.flushPendingSummarySave() }
            loadDraft(force: true)
        }
        .onChange(of: controller.snapshot.summaryText) { _ in
            loadDraft(force: false)
        }
        .onChange(of: controller.summaryRequestStatus) { status in
            if status?.state == .inProgress {
                isEditing = false
            }
        }
        .alert("重新生成总结？", isPresented: $isRegenerateConfirmationPresented) {
            Button("重新生成", role: .destructive) {
                isEditing = false
                controller.flushPendingSummarySaveSynchronously()
                controller.regenerateSummaryDiscardingExisting()
            }
            Button("取消", role: .cancel) {}
        } message: {
            Text("旧的总结将被丢弃，并调用云 LLM 重新生成。")
        }
    }

    private var header: some View {
        HStack(spacing: 10) {
            if let requestStatus = controller.visibleSummaryRequestStatus(for: controller.selectedLibraryItem) {
                summaryRequestStatusView(requestStatus)
            } else if !controller.snapshot.summarySource.isEmpty {
                Text("Source: \(controller.snapshot.summarySource)")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .lineLimit(1)
            }
            Spacer()
            if let item = controller.selectedLibraryItem {
                summaryHeaderButton(
                    systemName: item.isRead ? "checkmark.circle.fill" : "checkmark.circle",
                    foregroundColor: item.isRead ? .accentColor : .secondary,
                    help: item.isRead ? "标记为未读" : "标记为已读"
                ) {
                    controller.markRead(!item.isRead, for: item)
                }
            }
            summaryHeaderButton(
                systemName: isEditing ? "eye" : "pencil",
                help: isEditing ? "Preview summary" : "Edit Markdown",
                disabled: controller.snapshot.summaryURL == nil || isSummaryRequestInProgress
            ) {
                if isEditing {
                    Task { await controller.flushPendingSummarySave() }
                }
                isEditing.toggle()
                if isEditing {
                    loadDraft(force: true)
                }
            }
            summaryHeaderButton(
                systemName: "arrow.clockwise",
                help: "使用云 API 重新生成总结",
                disabled: !controller.isCloudSummaryConfigured || !canRegenerateSummary || isSummaryRequestInProgress
            ) {
                if hasExistingSummary {
                    isRegenerateConfirmationPresented = true
                } else {
                    isEditing = false
                    controller.flushPendingSummarySaveSynchronously()
                    controller.regenerateSummaryDiscardingExisting()
                }
            }
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 8)
    }

    private func summaryHeaderButton(
        systemName: String,
        foregroundColor: Color = .secondary,
        help: String,
        disabled: Bool = false,
        action: @escaping () -> Void
    ) -> some View {
        Button(action: action) {
            Image(systemName: systemName)
                .font(.system(size: 15, weight: .medium))
                .frame(width: 54, height: 30)
        }
        .buttonStyle(SummaryHeaderIconButtonStyle(foregroundColor: foregroundColor))
        .disabled(disabled)
        .help(help)
        .accessibilityLabel(help)
    }

    private func summaryRequestStatusView(_ status: SummaryRequestStatus) -> some View {
        HStack(spacing: 6) {
            switch status.state {
            case .inProgress:
                ProgressView()
                    .controlSize(.small)
            case .success:
                Image(systemName: "checkmark.circle.fill")
                    .foregroundStyle(.green)
            case .failure:
                Image(systemName: "xmark.circle.fill")
                    .foregroundStyle(.red)
            }
            Text(status.message)
                .font(.caption)
                .foregroundStyle(status.state == .failure ? .red : .secondary)
                .lineLimit(1)
                .truncationMode(.tail)
        }
        .frame(minWidth: 0, maxWidth: 360, alignment: .leading)
    }

    @ViewBuilder
    private var content: some View {
        if isEditing && !isSummaryRequestInProgress {
            TextEditor(text: summaryDraftBinding)
                .font(.system(.body, design: .monospaced))
                .padding(8)
        } else {
            SimpleMarkdownView(text: previewText, style: readingStyle)
        }
    }

    private var previewText: String {
        controller.snapshot.summaryText
    }

    private var canRegenerateSummary: Bool {
        controller.canGenerateSummary(for: controller.selectedLibraryItem)
    }

    private var hasExistingSummary: Bool {
        !controller.snapshot.summaryText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
    }

    private var isSummaryRequestInProgress: Bool {
        controller.visibleSummaryRequestStatus(for: controller.selectedLibraryItem)?.state == .inProgress
    }

    private var summaryDraftBinding: Binding<String> {
        Binding(
            get: { summaryDraft },
            set: { newValue in
                guard newValue != summaryDraft else { return }
                summaryDraft = newValue
                controller.saveCurrentSummaryMarkdown(newValue)
            }
        )
    }

    private func loadDraft(force: Bool) {
        let summaryURL = controller.snapshot.summaryURL
        guard force || !isEditing else { return }
        guard force || loadedSummaryURL != summaryURL || summaryDraft != controller.snapshot.summaryText else { return }
        summaryDraft = controller.snapshot.summaryText
        loadedSummaryURL = summaryURL
        if summaryURL == nil {
            isEditing = false
        }
    }
}

private struct SummaryHeaderIconButtonStyle: ButtonStyle {
    let foregroundColor: Color

    @Environment(\.isEnabled) private var isEnabled

    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .foregroundStyle(isEnabled ? foregroundColor : Color.secondary.opacity(0.45))
            .background(backgroundColor(isPressed: configuration.isPressed), in: RoundedRectangle(cornerRadius: 8, style: .continuous))
            .contentShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
            .scaleEffect(configuration.isPressed ? 0.98 : 1)
            .animation(.easeOut(duration: 0.08), value: configuration.isPressed)
    }

    private func backgroundColor(isPressed: Bool) -> Color {
        if !isEnabled {
            return Color.secondary.opacity(0.06)
        }
        return isPressed ? Color.secondary.opacity(0.16) : Color.secondary.opacity(0.10)
    }
}
