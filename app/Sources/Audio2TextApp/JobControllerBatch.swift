import Foundation

extension JobController {
    func processAllMarkedToProcess(workflow: ProcessingWorkflow = .localOnly) {
        guard !stage.isRunning else { return }
        let items = markedToProcessItems()
        guard !items.isEmpty else {
            message = "No marked items to process"
            return
        }
        guard workflow == .localOnly || isCloudSummaryConfigured else {
            message = "Cloud summary is not configured"
            return
        }
        dismissProcessingReport()
        clearProcessingTaskStatuses()
        logEvent(category: "library", event: "process_all_marked_requested", message: "Batch processing requested", fields: ["count": "\(items.count)", "workflow": "\(workflow)"])
        currentTask?.cancel()
        currentTask = Task { await runMarkedProcessing(items, workflow: workflow) }
    }

    func processLibraryItems(
        _ selectedItems: [ProcessLibraryItem],
        workflow: ProcessingWorkflow = .localOnly
    ) {
        guard !stage.isRunning else { return }
        let items = unprocessedItems(from: selectedItems)
        guard !items.isEmpty else {
            message = "No selected items can be processed"
            return
        }
        guard workflow == .localOnly || isCloudSummaryConfigured else {
            message = "Cloud summary is not configured"
            return
        }
        dismissProcessingReport()
        clearProcessingTaskStatuses()
        logEvent(
            category: "library",
            event: "process_selected_unprocessed_requested",
            message: "Selected unprocessed batch requested",
            fields: ["count": "\(items.count)", "workflow": "\(workflow)"]
        )
        currentTask?.cancel()
        currentTask = Task { await runMarkedProcessing(items, workflow: workflow) }
    }

    func reprocessLibraryItems(
        _ selectedItems: [ProcessLibraryItem],
        workflow: ProcessingWorkflow = .localOnly
    ) {
        guard !stage.isRunning else { return }
        let items = uniqueItems(from: selectedItems).filter(\.isProcessed)
        guard !items.isEmpty else {
            message = "No selected items can be reprocessed"
            return
        }
        guard workflow == .localOnly || isCloudSummaryConfigured else {
            message = "Cloud summary is not configured"
            return
        }
        dismissProcessingReport()
        clearProcessingTaskStatuses()
        logEvent(
            category: "library",
            event: "reprocess_selected_requested",
            message: "Selected processed batch reprocess requested",
            fields: ["count": "\(items.count)", "workflow": "\(workflow)"]
        )
        currentTask?.cancel()
        currentTask = Task { await runBatchReprocessing(items, workflow: workflow) }
    }

    func stopBatchAfterCurrentItem() {
        stopAfterCurrentTask()
    }

    func stopAfterCurrentTask() {
        guard !isBatchStopRequested else { return }
        let hasActiveBatch = batchProgress != nil
        let cancelledCloudJobs = backgroundSummaryQueue.cancelPendingJobs()
        guard hasActiveBatch || cancelledCloudJobs > 0 else { return }
        isBatchStopRequested = true
        message = cancelledCloudJobs > 0
            ? "Will stop after current task; canceled \(cancelledCloudJobs) queued cloud task\(cancelledCloudJobs == 1 ? "" : "s")"
            : "Will stop after current task"
        logEvent(
            category: "library",
            event: "stop_after_current_requested",
            message: "Will stop after the current task and cancel queued tasks",
            fields: ["cancelled_cloud_jobs": "\(cancelledCloudJobs)"]
        )
        updateBatchProgressFromCurrentItem()
        refreshCloudStopProgress()
    }

    func showsStopAfterCurrentTaskControl(for kind: ProcessingTaskKind, state: ProcessingTaskState) -> Bool {
        guard state.isActive else { return false }
        return isBatchStopRequested || canStopAfterCurrentTask(for: kind)
    }

    func canStopAfterCurrentTask(for kind: ProcessingTaskKind) -> Bool {
        switch kind {
        case .processing:
            return batchProgress != nil
        case .cloud:
            return batchProgress != nil || backgroundSummaryQueue.pendingCount > 0
        case .sync:
            return false
        }
    }

    private func refreshCloudStopProgress() {
        guard let cloudProcessingTaskStatus, cloudProcessingTaskStatus.state.isActive else { return }
        let currentTitle = backgroundSummaryQueue.currentJob?.title ?? cloudProcessingTaskStatus.itemTitle
        let fraction = backgroundSummaryQueue.currentJob == nil
            ? cloudProcessingTaskStatus.fraction
            : summaryQueueFraction(currentFraction: cloudProcessingTaskStatus.fraction)
        setCloudTaskStatus(
            itemTitle: cloudProcessingTaskStatus.itemTitle,
            detail: summaryQueueDetail(currentTitle: currentTitle),
            fraction: fraction,
            state: cloudProcessingTaskStatus.state
        )
    }

    func dismissProcessingReport() {
        processingReport = nil
    }
}
