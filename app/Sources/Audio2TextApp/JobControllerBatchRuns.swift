import Foundation

extension JobController {
    func runMarkedProcessing(
        _ items: [ProcessLibraryItem],
        workflow: ProcessingWorkflow
    ) async {
        let runtime: RuntimeContext
        do {
            runtime = try runtimeProvider()
        } catch {
            let reason = conciseFailureReason(error)
            message = reason
            processingReport = ProcessingReport(
                title: "批量处理失败",
                detail: reason,
                items: [
                    ProcessingReportItem(
                        id: "runtime",
                        title: "运行环境",
                        state: .failure,
                        reason: reason
                    ),
                ]
            )
            logError(event: "process_all_marked_runtime_failed", error: error)
            return
        }
        clearProcessingTaskStatuses()
        beginMarkedBatch(total: items.count, title: workflow.batchTitle(), taskKind: .processing)
        var reportItems: [ProcessingReportItem] = []
        var warningCount = 0
        for (index, item) in items.enumerated() where !Task.isCancelled {
            activeBatchCompleted = index
            activeBatchCurrentTitle = item.title
            progressFraction = 0.0
            updateBatchProgressFromCurrentItem()
            let outcome = await runLibraryLocalProcessingForBatch(for: item, runtime: runtime)
            reportItems.append(
                ProcessingReportItem(
                    id: item.id,
                    title: item.title,
                    state: outcome.succeeded ? .success : .failure,
                    reason: outcome.reason
                )
            )
            if outcome.taskState == .warning {
                warningCount += 1
            }
            if outcome.succeeded {
                if workflow.requiresCloudSummary, outcome.shouldQueueSummary, enqueueBackgroundSummary(
                    for: item,
                    runtime: runtime,
                    localState: outcome.taskState,
                    localReason: outcome.reason
                ) {
                    message = "Local transcript ready; summary queued"
                } else if workflow.requiresCloudSummary, outcome.shouldQueueSummary {
                    message = "Local transcript ready; cloud summary skipped"
                } else {
                    message = outcome.reason
                }
            } else {
                message = "Skipped failed item: \(item.title)"
            }
            activeBatchCompleted = index + 1
            activeBatchCurrentTitle = item.title
            progressFraction = 1.0
            updateBatchProgressFromCurrentItem()
            if isBatchStopRequested {
                logEvent(
                    category: "library",
                    event: "batch_stopped_after_current",
                    message: "Batch stopped after current item",
                    fields: ["completed": "\(activeBatchCompleted)", "total": "\(items.count)"]
                )
                break
            }
        }
        let successCount = reportItems.filter { $0.state == .success }.count
        let failureCount = reportItems.filter { $0.state == .failure }.count
        let localBatchState: ProcessingTaskState = failureCount > 0 ? .failure : (warningCount > 0 ? .warning : .success)
        let detail: String
        if isBatchStopRequested {
            detail = "Stopped after current item. Success \(successCount), failed \(failureCount)."
        } else {
            detail = "Success \(successCount), failed \(failureCount)."
        }
        if !workflow.requiresCloudSummary || failureCount > 0 {
            processingReport = ProcessingReport(
                title: failureCount > 0 ? "\(workflow.batchTitle())完成，有失败" : "\(workflow.batchTitle())完成",
                detail: detail,
                items: reportItems
            )
        }
        setProcessingTaskStatus(
            detail: failureCount > 0 ? "本地批量完成，有失败" : (warningCount > 0 ? "本地批量完成，QA 需复查" : "本地批量完成"),
            fraction: 1.0,
            state: localBatchState,
            itemTitle: ""
        )
        stage = failureCount > 0 ? .failed : .completed
        message = detail
        endMarkedBatch()
        await refreshLibraryAndWait()
    }

    func runBatchReprocessing(_ items: [ProcessLibraryItem], workflow: ProcessingWorkflow) async {
        let runtime: RuntimeContext
        do {
            runtime = try runtimeProvider()
        } catch {
            let reason = conciseFailureReason(error)
            message = reason
            processingReport = ProcessingReport(
                title: "批量重新处理失败",
                detail: reason,
                items: [
                    ProcessingReportItem(
                        id: "runtime",
                        title: "运行环境",
                        state: .failure,
                        reason: reason
                    ),
                ]
            )
            logError(event: "reprocess_selected_runtime_failed", error: error)
            return
        }

        clearProcessingTaskStatuses()
        beginMarkedBatch(total: items.count, title: workflow.batchTitle(reprocess: true), taskKind: .processing)
        var reportItems: [ProcessingReportItem] = []
        var warningCount = 0
        for (index, item) in items.enumerated() where !Task.isCancelled {
            activeBatchCompleted = index
            activeBatchCurrentTitle = item.title
            progressFraction = 0.0
            updateBatchProgressFromCurrentItem()
            let outcome = await runLibraryReprocessingForBatch(for: item, runtime: runtime)
            reportItems.append(
                ProcessingReportItem(
                    id: item.id,
                    title: item.title,
                    state: outcome.succeeded ? .success : .failure,
                    reason: outcome.reason
                )
            )
            if outcome.taskState == .warning {
                warningCount += 1
            }
            if workflow.requiresCloudSummary, outcome.succeeded, outcome.shouldQueueSummary {
                _ = enqueueBackgroundSummary(
                    for: item,
                    runtime: runtime,
                    localState: outcome.taskState,
                    localReason: outcome.reason
                )
            }
            message = outcome.reason
            activeBatchCompleted = index + 1
            activeBatchCurrentTitle = item.title
            progressFraction = 1.0
            updateBatchProgressFromCurrentItem()
            if isBatchStopRequested {
                logEvent(
                    category: "library",
                    event: "reprocess_batch_stopped_after_current",
                    message: "Reprocess batch stopped after current item",
                    fields: ["completed": "\(activeBatchCompleted)", "total": "\(items.count)"]
                )
                break
            }
        }

        let successCount = reportItems.filter { $0.state == .success }.count
        let failureCount = reportItems.filter { $0.state == .failure }.count
        let localBatchState: ProcessingTaskState = failureCount > 0 ? .failure : (warningCount > 0 ? .warning : .success)
        let detail = isBatchStopRequested
            ? "Stopped after current item. Success \(successCount), failed \(failureCount)."
            : "Success \(successCount), failed \(failureCount)."
        if !workflow.requiresCloudSummary || failureCount > 0 {
            processingReport = ProcessingReport(
                title: failureCount > 0 ? "\(workflow.batchTitle(reprocess: true))完成，有失败" : "\(workflow.batchTitle(reprocess: true))完成",
                detail: detail,
                items: reportItems
            )
        }
        setProcessingTaskStatus(
            detail: failureCount > 0 ? "本地批量完成，有失败" : (warningCount > 0 ? "本地批量完成，QA 需复查" : "本地批量完成"),
            fraction: 1.0,
            state: localBatchState,
            itemTitle: ""
        )
        stage = failureCount > 0 ? .failed : .completed
        message = detail
        endMarkedBatch()
        await refreshLibraryAndWait()
    }

    func runBatchTitleGeneration(_ items: [ProcessLibraryItem], cloudSettings: CloudSettings) async {
        clearProcessingTaskStatus()
        beginMarkedBatch(total: items.count, title: "生成标题", taskKind: .cloud)
        var reportItems: [ProcessingReportItem] = []
        for (index, item) in items.enumerated() where !Task.isCancelled {
            activeBatchCompleted = index
            activeBatchCurrentTitle = item.title
            progressFraction = 0.0
            updateBatchProgressFromCurrentItem()
            let outcome = await runTitleGenerationForBatch(for: item, cloudSettings: cloudSettings)
            reportItems.append(
                ProcessingReportItem(
                    id: item.id,
                    title: item.title,
                    state: outcome.succeeded ? .success : .failure,
                    reason: outcome.reason
                )
            )
            message = outcome.reason
            activeBatchCompleted = index + 1
            activeBatchCurrentTitle = item.title
            progressFraction = 1.0
            updateBatchProgressFromCurrentItem()
            if isBatchStopRequested {
                logEvent(
                    category: "summary",
                    event: "title_batch_stopped_after_current",
                    message: "Title batch stopped after current item",
                    fields: ["completed": "\(activeBatchCompleted)", "total": "\(items.count)"]
                )
                break
            }
        }

        let successCount = reportItems.filter { $0.state == .success }.count
        let failureCount = reportItems.filter { $0.state == .failure }.count
        let detail = isBatchStopRequested
            ? "Stopped after current item. Success \(successCount), failed \(failureCount)."
            : "Success \(successCount), failed \(failureCount)."
        processingReport = ProcessingReport(
            title: failureCount > 0 ? "批量标题生成完成，有失败" : "批量标题生成完成",
            detail: detail,
            items: reportItems
        )
        let taskState: ProcessingTaskState = failureCount > 0 ? .failure : (isBatchStopRequested ? .warning : .success)
        setCloudTaskStatus(
            itemTitle: "",
            detail: failureCount > 0 ? "生成标题完成，有失败" : (isBatchStopRequested ? "生成标题已停止" : "生成标题完成"),
            fraction: 1.0,
            state: taskState
        )
        stage = failureCount > 0 ? .failed : .completed
        message = detail
        endMarkedBatch()
        await refreshLibraryAndWait()
    }
}
