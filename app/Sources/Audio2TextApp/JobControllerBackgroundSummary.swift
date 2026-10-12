import Foundation

@MainActor
extension JobController {
    @discardableResult
    func enqueueBackgroundSummary(
        for item: ProcessLibraryItem,
        runtime: RuntimeContext,
        localState: ProcessingTaskState = .success,
        localReason: String = "Local transcript ready"
    ) -> Bool {
        enqueueBackgroundSummary(
            itemID: item.id,
            title: item.title,
            outputDirectory: item.outputURL,
            runtime: runtime,
            localState: localState,
            localReason: localReason
        )
    }

    @discardableResult
    func enqueueBackgroundSummary(
        itemID: String,
        title: String,
        outputDirectory: URL,
        runtime: RuntimeContext,
        localState: ProcessingTaskState,
        localReason: String
    ) -> Bool {
        guard !isBatchStopRequested else {
            appendLog("Cloud summary skipped for \(title): stop requested.\n")
            logEvent(
                category: "summary",
                event: "batch_summary_skipped_stop_requested",
                message: "Batch cloud summary skipped because stopping after current task was requested",
                fields: ["item_id": itemID]
            )
            return false
        }
        let cloudSettings = settingsStore.cloudSettings(environment: runtime.environment)
        guard cloudSettings.isConfigured else {
            appendLog("Cloud summary skipped for \(title): cloud summary is not configured.\n")
            setCloudTaskStatus(
                itemTitle: compactProgressItemTitle(title),
                detail: "Cloud task failed: cloud summaries are not configured",
                fraction: 1.0,
                state: .failure
            )
            processingReport = combinedProcessingReport(
                itemID: itemID,
                title: title,
                localState: localState,
                localReason: localReason,
                cloudState: .failure,
                cloudReason: "Cloud summary is not configured"
            )
            logEvent(
                .warning,
                category: "summary",
                event: "batch_summary_skipped_unconfigured",
                message: "Batch cloud summary skipped because cloud settings are incomplete",
                fields: ["item_id": itemID]
            )
            return false
        }
        backgroundSummaryQueue.enqueue(
            BackgroundSummaryJob(
                itemID: itemID,
                title: title,
                outputDirectory: outputDirectory,
                runtime: runtime,
                cloudSettings: cloudSettings,
                localState: localState,
                localReason: localReason
            )
        )
        return true
    }

    func runBackgroundSummaryCommand(
        _ job: BackgroundSummaryJob,
        onOutput: @escaping @MainActor (String) -> Void
    ) async throws {
        appendBackgroundSummaryLog("\nStarting cloud summary for \(job.title).\n", outputDirectory: job.outputDirectory)
        logEvent(category: "summary", event: "batch_summary_started", message: "Batch cloud summary started", fields: ["item_id": job.itemID])
        try await runSummaryCommand(
            outputDirectory: job.outputDirectory,
            runtime: job.runtime,
            cloudSettings: job.cloudSettings,
            onOutput: onOutput
        )
    }

    func handleBackgroundSummaryQueueEvent(_ event: BackgroundSummaryQueueEvent) {
        switch event {
        case let .queued(job, _):
            appendBackgroundSummaryLog("Queued cloud summary for \(job.title).\n", outputDirectory: job.outputDirectory)
            logEvent(category: "summary", event: "batch_summary_queued", message: "Batch cloud summary queued", fields: ["item_id": job.itemID])
            setBackgroundSummaryProgress(itemTitle: compactProgressItemTitle(job.title), detail: summaryQueueDetail(), fraction: summaryQueueFraction(currentFraction: 0.05), state: .queued)
        case let .started(job, _):
            setBackgroundSummaryProgress(for: job, detail: summaryQueueDetail(currentTitle: job.title), fraction: summaryQueueFraction(currentFraction: 0.08), state: .running)
        case let .output(job, text, _):
            appendBackgroundSummaryLog(text, outputDirectory: job.outputDirectory)
            refreshBackgroundSummaryProgress(for: job)
        case let .completed(job, _):
            appendBackgroundSummaryLog("Cloud summary completed.\n", outputDirectory: job.outputDirectory)
            setBackgroundSummaryProgress(for: job, detail: summaryQueueDetail(currentTitle: job.title, completed: true), fraction: summaryQueueFraction(currentFraction: 1.0), state: .success)
            if selectedLibraryItem?.outputURL.standardizedFileURL.path == job.outputDirectory.standardizedFileURL.path {
                snapshot = snapshotForOutputDirectory(job.outputDirectory)
            }
            refreshLibraryInBackground()
            processingReport = combinedProcessingReport(
                itemID: job.itemID,
                title: job.title,
                localState: job.localState,
                localReason: job.localReason,
                cloudState: .success,
                cloudReason: "Cloud summary completed"
            )
            Task { [weak self] in
                await self?.refreshLibraryAfterProcessing(runtime: job.runtime)
            }
            logEvent(category: "summary", event: "batch_summary_completed", message: "Batch cloud summary completed", fields: ["item_id": job.itemID])
        case let .failed(job, error, _):
            appendBackgroundSummaryLog("\nERROR: \(error.localizedDescription)\n", outputDirectory: job.outputDirectory)
            let reason = shortStatusMessage(error.localizedDescription)
            setBackgroundSummaryProgress(for: job, detail: "Cloud task failed: \(reason)", fraction: summaryQueueFraction(currentFraction: 1.0), state: .failure)
            message = reason
            processingReport = combinedProcessingReport(
                itemID: job.itemID,
                title: job.title,
                localState: job.localState,
                localReason: job.localReason,
                cloudState: .failure,
                cloudReason: reason
            )
            logError(category: "summary", event: "batch_summary_failed", error: error, fields: ["item_id": job.itemID])
        case .idle:
            if batchProgress == nil {
                isBatchStopRequested = false
            }
        }
    }

    private func setBackgroundSummaryProgress(
        for job: BackgroundSummaryJob,
        detail: String,
        fraction: Double,
        state: ProcessingTaskState
    ) {
        setBackgroundSummaryProgress(itemTitle: compactProgressItemTitle(job.title), detail: detail, fraction: fraction, state: state)
    }

    private func setBackgroundSummaryProgress(
        itemTitle: String,
        detail: String,
        fraction: Double,
        state: ProcessingTaskState
    ) {
        setCloudTaskStatus(
            itemTitle: itemTitle,
            detail: detail,
            fraction: fraction,
            state: state
        )
    }

    private func refreshBackgroundSummaryProgress(for job: BackgroundSummaryJob) {
        let summarySnapshot = snapshotForOutputDirectory(job.outputDirectory)
        if selectedLibraryItem?.outputURL.standardizedFileURL.path == job.outputDirectory.standardizedFileURL.path {
            snapshot = summarySnapshot
        }
        let status = cloudProgressStatus(
            from: summarySnapshot,
            itemTitle: compactProgressItemTitle(job.title),
            processContextActive: true,
            prefersSummaryStageFloor: false,
            allowsUnknownSummaryProgress: true
        )
        let visibleStatus = status?.state == .failure ? nil : status
        cloudProcessingTaskStatus = visibleStatus.map { status in
            ProcessingTaskStatus(
                kind: .cloud,
                title: status.title,
                itemTitle: status.itemTitle,
                detail: status.detail,
                fraction: summaryQueueFraction(currentFraction: status.fraction),
                state: status.state
            )
        } ?? ProcessingTaskStatus(
            kind: .cloud,
            title: "Cloud task",
            itemTitle: compactProgressItemTitle(job.title),
            detail: summaryQueueDetail(currentTitle: job.title),
            fraction: summaryQueueFraction(currentFraction: 0.08),
            state: .running
        )
    }

    func refreshManualSummaryProgress(
        for item: ProcessLibraryItem,
        fallbackDetail: String,
        fallbackFraction: Double,
        fallbackState: ProcessingTaskState = .running
    ) {
        let summarySnapshot = snapshotForOutputDirectory(item.outputURL)
        if selectedLibraryItem?.outputURL.standardizedFileURL.path == item.outputURL.standardizedFileURL.path {
            snapshot = summarySnapshot
        }
        if let status = cloudProgressStatus(
            from: summarySnapshot,
            itemTitle: compactProgressItemTitle(item.title),
            processContextActive: true,
            prefersSummaryStageFloor: false,
            allowsUnknownSummaryProgress: true
        ), !(fallbackState.isActive && status.state == .failure) {
            cloudProcessingTaskStatus = status
            return
        }
        setCloudTaskStatus(
            itemTitle: compactProgressItemTitle(item.title),
            detail: fallbackDetail,
            fraction: fallbackFraction,
            state: fallbackState
        )
    }

    func appendBackgroundSummaryLog(_ text: String, outputDirectory: URL) {
        let logURL = outputDirectory.appendingPathComponent("app.log")
        try? FileManager.default.createDirectory(at: logURL.deletingLastPathComponent(), withIntermediateDirectories: true)
        if
            let data = text.data(using: .utf8),
            FileManager.default.fileExists(atPath: logURL.path),
            let handle = try? FileHandle(forWritingTo: logURL)
        {
            _ = try? handle.seekToEnd()
            try? handle.write(contentsOf: data)
            try? handle.close()
        } else {
            try? text.write(to: logURL, atomically: true, encoding: .utf8)
        }
        if snapshot.outputDirectory?.standardizedFileURL.path == outputDirectory.standardizedFileURL.path {
            logText.append(text)
        }
    }
}
