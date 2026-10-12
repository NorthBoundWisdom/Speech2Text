import Foundation

@MainActor
extension JobController {
    func localProcessingReport(
        itemID: String,
        title: String,
        localState: ProcessingTaskState,
        reason: String,
        reprocess: Bool
    ) -> ProcessingReport {
        let reportTitle: String
        switch localState {
        case .warning:
            reportTitle = reprocess ? "本地重新转写完成，QA 需复查" : "本地转写完成，QA 需复查"
        case .failure:
            reportTitle = reprocess ? "本地重新转写失败" : "本地转写失败"
        default:
            reportTitle = reprocess ? "本地重新转写完成" : "本地转写完成"
        }
        return ProcessingReport(
            title: reportTitle,
            detail: reason,
            items: [
                ProcessingReportItem(
                    id: "\(itemID)-local",
                    title: "本地转写：\(title)",
                    state: reportState(for: localState),
                    reason: reason
                ),
            ]
        )
    }

    func combinedProcessingReport(
        itemID: String,
        title: String,
        localState: ProcessingTaskState,
        localReason: String,
        cloudState: ProcessingTaskState,
        cloudReason: String
    ) -> ProcessingReport {
        let reportTitle: String
        if cloudState == .failure {
            reportTitle = "处理部分完成"
        } else if localState == .warning || cloudState == .warning {
            reportTitle = "处理完成，需复查"
        } else {
            reportTitle = "处理完成"
        }
        return ProcessingReport(
            title: reportTitle,
            detail: "本地：\(localReason)；云：\(cloudReason)",
            items: [
                ProcessingReportItem(
                    id: "\(itemID)-local",
                    title: "本地转写：\(title)",
                    state: reportState(for: localState),
                    reason: localReason
                ),
                ProcessingReportItem(
                    id: "\(itemID)-cloud",
                    title: "云总结：\(title)",
                    state: reportState(for: cloudState),
                    reason: cloudReason
                ),
            ]
        )
    }

    private func reportState(for taskState: ProcessingTaskState) -> ProcessingReportState {
        taskState == .failure ? .failure : .success
    }

    func qaFailureSummary(for outputDirectory: URL) -> String {
        let qaURL = outputDirectory.appendingPathComponent("qa.json")
        guard
            let data = try? Data(contentsOf: qaURL),
            let object = try? JSONSerialization.jsonObject(with: data) as? [String: Any]
        else {
            return "QA failed; review QA or run repair"
        }
        let summary = object["summary"] as? [String: Any] ?? [:]
        let issueCount = integerValue(summary["issue_count"])
        let blockingCount = integerValue(summary["blocking_issue_count"])
        let repairWindowCount = integerValue(summary["repair_window_count"])
        var parts = ["QA failed"]
        if let issueCount {
            parts.append("\(issueCount) issues")
        }
        if let blockingCount {
            parts.append("\(blockingCount) blocking")
        }
        if let repairWindowCount, repairWindowCount > 0 {
            parts.append("\(repairWindowCount) repair windows")
        }
        return parts.joined(separator: ", ") + "."
    }

    private func integerValue(_ value: Any?) -> Int? {
        if let value = value as? Int {
            return value
        }
        if let value = value as? NSNumber {
            return value.intValue
        }
        if let value = value as? String {
            return Int(value)
        }
        return nil
    }
}
