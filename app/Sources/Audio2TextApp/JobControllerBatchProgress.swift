import Foundation

extension JobController {
    func beginMarkedBatch(
        total: Int,
        title: String = "处理标记",
        taskKind: ProcessingTaskKind? = nil
    ) {
        processingReport = nil
        activeBatchTotal = total
        activeBatchCompleted = 0
        activeBatchCurrentTitle = ""
        activeBatchTaskKind = taskKind
        isBatchStopRequested = false
        batchProgress = BatchProcessingProgress(
            title: title,
            completed: 0,
            total: total,
            currentTitle: "",
            currentItemProgress: 0.0
        )
        syncBatchTaskStatus(state: .queued)
    }

    func endMarkedBatch() {
        activeBatchCompleted = 0
        activeBatchTotal = 0
        activeBatchCurrentTitle = ""
        activeBatchTaskKind = nil
        isBatchStopRequested = false
        batchProgress = nil
    }

    func updateBatchProgressFromCurrentItem() {
        guard activeBatchTotal > 0 else { return }
        batchProgress = BatchProcessingProgress(
            title: batchProgress?.title ?? "处理标记",
            completed: min(activeBatchCompleted, activeBatchTotal),
            total: activeBatchTotal,
            currentTitle: activeBatchCurrentTitle,
            currentItemProgress: progressFraction
        )
        syncBatchTaskStatus(state: .running)
    }

    private func syncBatchTaskStatus(state: ProcessingTaskState) {
        guard let activeBatchTaskKind, let batchProgress else { return }
        let visibleCompleted = min(activeBatchCompleted + (activeBatchCompleted < activeBatchTotal ? 1 : 0), activeBatchTotal)
        let compactTitle = compactProgressItemTitle(activeBatchCurrentTitle)
        let detail = compactTitle.isEmpty
            ? "\(batchProgress.title) \(visibleCompleted)/\(activeBatchTotal)"
            : "\(batchProgress.title) \(visibleCompleted)/\(activeBatchTotal)：\(compactTitle)"
        switch activeBatchTaskKind {
        case .processing:
            setProcessingTaskStatus(detail: detail, fraction: batchProgress.fraction, state: state, itemTitle: "")
        case .cloud:
            setCloudTaskStatus(itemTitle: "", detail: detail, fraction: batchProgress.fraction, state: state)
        case .sync:
            break
        }
    }
}
