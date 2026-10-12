import AppKit
import SwiftUI
#if canImport(Audio2TextCore)
    import Audio2TextCore
#endif

struct ProcessingReportDialog: View {
    @Environment(\.dismiss) private var dismiss

    let report: ProcessingReport

    private var successItems: [ProcessingReportItem] {
        report.items.filter { $0.state == .success }
    }

    private var failureItems: [ProcessingReportItem] {
        report.items.filter { $0.state == .failure }
    }

    private var allVisibleItems: [ProcessingReportItem] {
        failureItems + successItems
    }

    private var clipboardText: String {
        let itemText = allVisibleItems
            .map { item in
                let state = item.state == .failure ? "失败" : "成功"
                return "[\(state)] \(item.title)\n\(item.reason)"
            }
            .joined(separator: "\n\n")
        return "\(report.title)\n\(report.detail)\n\n\(itemText)"
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            header
            Divider()
            ScrollView {
                LazyVStack(alignment: .leading, spacing: 14) {
                    if !failureItems.isEmpty {
                        reportSection(title: "失败", color: .red, items: failureItems)
                    }
                    if !successItems.isEmpty {
                        reportSection(title: "成功", color: .green, items: successItems)
                    }
                }
                .padding(16)
            }
        }
    }

    private var header: some View {
        HStack(spacing: 10) {
            Image(systemName: report.hasFailures ? "xmark.circle.fill" : "checkmark.circle.fill")
                .font(.system(size: 18, weight: .semibold))
                .foregroundStyle(report.hasFailures ? Color.red : Color.green)
            VStack(alignment: .leading, spacing: 3) {
                Text(report.hasFailures ? "失败详情" : "处理结果")
                    .font(.headline)
                Text(report.detail)
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .textSelection(.enabled)
            }
            Spacer()
            HStack(spacing: 8) {
                resultBadge(title: "成功", count: report.successCount, color: .green)
                resultBadge(title: "失败", count: report.failureCount, color: .red)
                Button {
                    NSPasteboard.general.clearContents()
                    NSPasteboard.general.setString(clipboardText, forType: .string)
                } label: {
                    Image(systemName: "doc.on.doc")
                        .font(.system(size: 12, weight: .semibold))
                        .frame(width: 24, height: 22)
                }
                .buttonStyle(.plain)
                .foregroundStyle(.secondary)
                .help(report.hasFailures ? "复制失败信息" : "复制处理结果")
                Button {
                    dismiss()
                } label: {
                    Image(systemName: "xmark")
                        .font(.system(size: 12, weight: .bold))
                        .frame(width: 24, height: 22)
                }
                .buttonStyle(.plain)
                .foregroundStyle(.secondary)
                .keyboardShortcut(.cancelAction)
                .help("关闭")
                .accessibilityLabel("关闭")
            }
        }
        .padding(16)
    }

    private func reportSection(title: String, color: Color, items: [ProcessingReportItem]) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(spacing: 6) {
                Circle()
                    .fill(color)
                    .frame(width: 7, height: 7)
                Text("\(title) \(items.count)")
                    .font(.system(size: 12, weight: .semibold))
                    .foregroundStyle(.secondary)
            }
            VStack(alignment: .leading, spacing: 0) {
                ForEach(items) { item in
                    HStack(alignment: .top, spacing: 10) {
                        Image(systemName: item.state == .success ? "checkmark.circle" : "xmark.circle")
                            .foregroundStyle(item.state == .success ? Color.green : Color.red)
                            .frame(width: 16, height: 16)
                        VStack(alignment: .leading, spacing: 3) {
                            Text(item.title)
                                .font(.system(size: 13, weight: .medium))
                                .lineLimit(2)
                            Text(item.reason)
                                .font(.system(size: 12))
                                .foregroundStyle(.secondary)
                                .fixedSize(horizontal: false, vertical: true)
                                .textSelection(.enabled)
                        }
                        Spacer(minLength: 0)
                    }
                    .padding(.vertical, 8)
                    if item.id != items.last?.id {
                        Divider()
                            .padding(.leading, 26)
                    }
                }
            }
        }
    }

    private func resultBadge(title: String, count: Int, color: Color) -> some View {
        HStack(spacing: 4) {
            Circle()
                .fill(color)
                .frame(width: 6, height: 6)
            Text("\(title) \(count)")
                .font(.system(size: 11, weight: .medium, design: .rounded).monospacedDigit())
                .foregroundStyle(.secondary)
        }
    }
}
