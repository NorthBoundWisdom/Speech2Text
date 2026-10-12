import SwiftUI
#if canImport(Audio2TextCore)
    import Audio2TextCore
#endif

extension ProcessSidebarView {
    @ViewBuilder
    var processingProgressHeader: some View {
        if !controller.sidebarModelProgressStatuses.isEmpty {
            modelProgressPanel
        } else if let batchProgress = controller.batchProgress {
            VStack(alignment: .leading, spacing: 8) {
                progressStrip(
                    title: "\(batchProgress.title) \(min(batchProgress.completed + 1, batchProgress.total))/\(batchProgress.total)",
                    detail: batchProgress.currentTitle,
                    fraction: batchProgress.fraction,
                    showsStopButton: true
                )
            }
        } else if controller.hasActiveSidebarModelProgress {
            modelProgressPanel
        } else if controller.stage.isRunning {
            progressStrip(
                title: controller.stage.title,
                detail: controller.message,
                fraction: controller.progressFraction
            )
        } else if let report = controller.processingReport {
            processingResultStrip(report)
        } else if !controller.sidebarModelProgressStatuses.isEmpty {
            modelProgressPanel
        } else if let status = store.cloudStartupStatus {
            progressStrip(
                title: status.title,
                detail: status.detail,
                fraction: status.fraction,
                state: status.state
            )
        } else if let detail = cloudAPIKeyWarningDetail {
            progressStrip(
                title: cloudAPIKeyWarningTitle,
                detail: detail,
                fraction: 1.0,
                state: .warning
            )
        }
    }

    var cloudAPIKeyWarningDetail: String? {
        guard store.settings.workflowDefaultCloudSummary && !store.settings.workflowLocalOnly else {
            return nil
        }
        if !store.settings.isCloudConfigured {
            return "Configure an API key before cloud summary."
        }
        if store.isCloudConnectionFailed(for: store.settings) {
            return "The last cloud API key check failed."
        }
        return nil
    }

    var cloudAPIKeyWarningTitle: String {
        store.settings.isCloudConfigured ? "Cloud API Key Check Failed" : "Cloud API Key Missing"
    }

    var modelProgressPanel: some View {
        let statuses = controller.sidebarModelProgressStatuses
        return Group {
            if !statuses.isEmpty {
                VStack(alignment: .leading, spacing: 0) {
                    ForEach(Array(statuses.enumerated()), id: \.element.id) { index, status in
                        progressStripContent(
                            title: status.title,
                            itemTitle: status.itemTitle,
                            detail: status.detail,
                            fraction: status.fraction,
                            state: status.state,
                            showsStopButton: controller.showsStopAfterCurrentTaskControl(for: status.kind, state: status.state),
                            report: processingReportForStatus(status)
                        )
                        .padding(.horizontal, 10)
                        .padding(.vertical, 8)

                        if index < statuses.count - 1 {
                            Divider()
                                .overlay(Color.secondary.opacity(0.16))
                                .padding(.horizontal, 10)
                        }
                    }
                }
                .background(
                    RoundedRectangle(cornerRadius: SidebarMetrics.rowCornerRadius)
                        .fill(Color.secondary.opacity(0.10))
                )
                .padding(.trailing, 12)
                .padding(.bottom, 8)
            }
        }
    }

    func processingResultStrip(_ report: ProcessingReport) -> some View {
        let tint = report.hasFailures ? Color.red : Color.green
        return VStack(alignment: .leading, spacing: 6) {
            HStack(spacing: 8) {
                Image(systemName: report.hasFailures ? "xmark.circle.fill" : "checkmark.circle.fill")
                    .font(.system(size: 13, weight: .semibold))
                    .foregroundStyle(tint)
                    .frame(width: 14, height: 14)
                Text(report.title)
                    .font(.system(size: 12, weight: .semibold))
                    .lineLimit(1)
                Spacer(minLength: 8)
                Button {
                    presentedProcessingReport = report
                } label: {
                    Image(systemName: "list.bullet.rectangle")
                        .font(.system(size: 11, weight: .semibold))
                        .frame(width: 18, height: 18)
                }
                .buttonStyle(.plain)
                .foregroundStyle(.secondary)
                .help("查看处理结果")
                .accessibilityLabel("查看处理结果")
                Button {
                    controller.dismissProcessingReport()
                } label: {
                    Image(systemName: "xmark")
                        .font(.system(size: 10, weight: .semibold))
                        .frame(width: 18, height: 18)
                }
                .buttonStyle(.plain)
                .foregroundStyle(.secondary)
                .help("关闭状态提示")
                .accessibilityLabel("关闭状态提示")
            }
            Text(report.detail)
                .font(.system(size: 11, weight: .regular))
                .foregroundStyle(report.hasFailures ? Color.red : Color.secondary)
                .lineLimit(2)
                .truncationMode(.tail)
            HStack(spacing: 8) {
                resultCountPill(title: "成功", count: report.successCount, color: .green)
                resultCountPill(title: "失败", count: report.failureCount, color: .red)
            }
        }
        .padding(.horizontal, 10)
        .padding(.vertical, 8)
        .background(
            RoundedRectangle(cornerRadius: SidebarMetrics.rowCornerRadius)
                .fill(tint.opacity(0.10))
        )
        .overlay(
            RoundedRectangle(cornerRadius: SidebarMetrics.rowCornerRadius)
                .stroke(tint.opacity(0.24), lineWidth: 1)
        )
        .padding(.trailing, 12)
        .padding(.bottom, 8)
    }

    func processingReportForStatus(_ status: ProcessingTaskStatus) -> ProcessingReport? {
        guard !status.state.isActive else { return nil }
        guard let report = controller.processingReport else { return fallbackProcessingReport(for: status) }
        if report.hasFailures || status.state == .failure || status.state == .warning {
            return report
        }
        return nil
    }

    func fallbackProcessingReport(for status: ProcessingTaskStatus) -> ProcessingReport? {
        guard status.state == .failure || status.state == .warning else { return nil }
        let reason = status.detail.trimmingCharacters(in: .whitespacesAndNewlines)
        let title = status.itemTitle.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
            ? status.title
            : status.itemTitle
        return ProcessingReport(
            title: status.state == .failure ? "\(status.title)失败" : "\(status.title)需复查",
            detail: reason.isEmpty ? "未提供失败详情" : reason,
            items: [
                ProcessingReportItem(
                    id: status.id,
                    title: title,
                    state: .failure,
                    reason: reason.isEmpty ? "未提供失败详情" : reason
                ),
            ]
        )
    }

    func resultCountPill(title: String, count: Int, color: Color) -> some View {
        HStack(spacing: 4) {
            Circle()
                .fill(color)
                .frame(width: 6, height: 6)
            Text("\(title) \(count)")
                .font(.system(size: 10, weight: .medium, design: .rounded).monospacedDigit())
                .foregroundStyle(.secondary)
                .lineLimit(1)
        }
        .padding(.horizontal, 7)
        .padding(.vertical, 3)
        .background(
            Capsule()
                .fill(Color.secondary.opacity(0.10))
        )
    }

    func progressStrip(
        title: String,
        detail: String,
        fraction: Double,
        state: ProcessingTaskState = .running,
        showsStopButton: Bool = false
    ) -> some View {
        progressStripContent(
            title: title,
            itemTitle: "",
            detail: detail,
            fraction: fraction,
            state: state,
            showsStopButton: showsStopButton
        )
        .padding(.horizontal, 10)
        .padding(.vertical, 8)
        .background(
            RoundedRectangle(cornerRadius: SidebarMetrics.rowCornerRadius)
                .fill(taskStateColor(state).opacity(state.isActive ? 0.10 : 0.08))
        )
        .overlay(
            RoundedRectangle(cornerRadius: SidebarMetrics.rowCornerRadius)
                .stroke(taskStateColor(state).opacity(state.isActive ? 0.0 : 0.24), lineWidth: 1)
        )
        .padding(.trailing, 12)
        .padding(.bottom, 8)
    }

    func progressStripContent(
        title: String,
        itemTitle: String,
        detail: String,
        fraction: Double,
        state: ProcessingTaskState = .running,
        showsStopButton: Bool = false,
        report: ProcessingReport? = nil
    ) -> some View {
        let boundedFraction = min(1.0, max(0.0, fraction))
        return VStack(alignment: .leading, spacing: 5) {
            HStack(spacing: 8) {
                taskStateIndicator(state)
                Text(title)
                    .font(.system(size: 12, weight: .semibold))
                    .lineLimit(1)
                Spacer(minLength: 8)
                if state.isActive {
                    Text("\(Int((boundedFraction * 100).rounded()))%")
                        .font(.system(size: 11, weight: .medium, design: .rounded).monospacedDigit())
                        .foregroundStyle(.secondary)
                }
                if showsStopButton {
                    Button {
                        controller.stopAfterCurrentTask()
                    } label: {
                        Image(systemName: controller.isBatchStopRequested ? "checkmark" : "stop.fill")
                            .font(.system(size: 10, weight: .semibold))
                            .frame(width: 18, height: 18)
                    }
                    .buttonStyle(.plain)
                    .foregroundStyle(controller.isBatchStopRequested ? Color.secondary : Color.red)
                    .help(controller.isBatchStopRequested ? "当前任务完成后停止" : "停止后续任务")
                    .disabled(controller.isBatchStopRequested)
                    .accessibilityLabel(controller.isBatchStopRequested ? "已请求停止后续任务" : "停止后续任务")
                }
                if let report {
                    Button {
                        presentedProcessingReport = report
                    } label: {
                        Image(systemName: "list.bullet.rectangle")
                            .font(.system(size: 10, weight: .semibold))
                            .frame(width: 18, height: 18)
                    }
                    .buttonStyle(.plain)
                    .foregroundStyle(report.hasFailures ? Color.red : Color.secondary)
                    .help(report.hasFailures ? "查看失败详情" : "查看处理结果")
                    .accessibilityLabel(report.hasFailures ? "查看失败详情" : "查看处理结果")
                }
            }
            if !itemTitle.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                Text("当前: \(itemTitle)")
                    .font(.system(size: 11, weight: .regular))
                    .foregroundStyle(.secondary)
                    .lineLimit(1)
                    .truncationMode(.tail)
            }
            if !detail.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                Text(detail)
                    .font(.system(size: 11, weight: .regular))
                    .foregroundStyle(.secondary)
                    .lineLimit(1)
                    .truncationMode(.tail)
            }
            GeometryReader { geometry in
                ZStack(alignment: .leading) {
                    Capsule()
                        .fill(Color.secondary.opacity(0.16))
                    Capsule()
                        .fill(taskStateColor(state))
                        .frame(width: max(4, geometry.size.width * boundedFraction))
                }
            }
            .frame(height: 4)
        }
    }

    @ViewBuilder
    func taskStateIndicator(_ state: ProcessingTaskState) -> some View {
        switch state {
        case .queued, .running:
            ProgressView()
                .controlSize(.small)
                .scaleEffect(0.72)
                .frame(width: 14, height: 14)
        case .success:
            Image(systemName: "checkmark.circle.fill")
                .font(.system(size: 13, weight: .semibold))
                .foregroundStyle(Color.green)
                .frame(width: 14, height: 14)
        case .warning:
            Image(systemName: "exclamationmark.triangle.fill")
                .font(.system(size: 12, weight: .semibold))
                .foregroundStyle(Color.orange)
                .frame(width: 14, height: 14)
        case .failure:
            Image(systemName: "xmark.circle.fill")
                .font(.system(size: 13, weight: .semibold))
                .foregroundStyle(Color.red)
                .frame(width: 14, height: 14)
        }
    }

    func taskStateColor(_ state: ProcessingTaskState) -> Color {
        switch state {
        case .queued, .running:
            return .accentColor
        case .success:
            return .green
        case .warning:
            return .orange
        case .failure:
            return .red
        }
    }
}
