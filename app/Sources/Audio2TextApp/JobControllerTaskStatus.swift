import Foundation
#if canImport(Audio2TextCore)
    import Audio2TextCore
#endif

@MainActor
extension JobController {
    func setProcessingTaskStatus(
        detail: String,
        fraction: Double,
        state: ProcessingTaskState,
        itemTitle: String? = nil
    ) {
        processingTaskStatus = ProcessingTaskStatus(
            kind: .processing,
            title: "Process",
            itemTitle: itemTitle ?? currentProcessingItemTitle,
            detail: detail,
            fraction: fraction,
            state: state
        )
    }

    func setCloudTaskStatus(
        itemTitle: String,
        detail: String,
        fraction: Double,
        state: ProcessingTaskState
    ) {
        cloudProcessingTaskStatus = ProcessingTaskStatus(
            kind: .cloud,
            title: "Cloud task",
            itemTitle: itemTitle,
            detail: detail,
            fraction: fraction,
            state: state
        )
    }

    func clearProcessingTaskStatus() {
        processingTaskStatus = nil
    }

    func clearProcessingTaskStatuses() {
        processingTaskStatus = nil
        cloudProcessingTaskStatus = nil
        backgroundSummaryQueue.resetProgress()
    }
}
