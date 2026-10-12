import Foundation

extension JobController {
    func runLibraryLocalProcessingForBatch(for item: ProcessLibraryItem, runtime: RuntimeContext) async -> BatchLocalProcessingOutcome {
        stopWatching()
        selectLibraryItem(item)
        stage = .idle
        message = ""
        logText = ""
        snapshot = OutputSnapshot()
        progressFraction = 0.0
        persistentLogPath = ""

        do {
            let processingItem = try await restoreAudioForBatchIfNeeded(item)
            logStore.start(dataRoot: runtime.dataRoot)
            logStore.attach(outputDirectory: processingItem.outputURL)
            persistentLogPath = logStore.outputURL?.path ?? logStore.fallbackURL?.path ?? ""
            logEvent(event: "library_batch_local_processing_started", message: "Batch local processing started", fields: ["item_id": processingItem.id])
            let processingResult = try await processAudio(
                processingItem.audioURL,
                outputDirectory: processingItem.outputURL,
                runtime: runtime,
                skipExisting: true
            )
            stage = .refreshing
            updateProgress(defaultValue: 0.95)
            refresh()
            stage = .completed
            progressFraction = 1.0
            message = processingResult.qaPassed ? "Local transcript ready" : "QA needs review"
            stopWatching()
            await refreshLibraryAndWait()
            logEvent(event: "library_batch_local_processing_completed", message: message, fields: ["item_id": processingItem.id])
            if processingResult.qaPassed {
                return BatchLocalProcessingOutcome(succeeded: true, shouldQueueSummary: true, reason: "Local transcript ready", taskState: .success)
            }
            return BatchLocalProcessingOutcome(succeeded: true, shouldQueueSummary: true, reason: qaFailureSummary(for: processingItem.outputURL), taskState: .warning)
        } catch {
            stage = .failed
            let reason = conciseFailureReason(error)
            message = reason
            appendLog("\nERROR: \(error.localizedDescription)\n")
            logError(event: "library_batch_local_processing_failed", error: error, fields: ["item_id": item.id])
            stopWatching()
            await refreshLibraryAndWait()
            return BatchLocalProcessingOutcome(succeeded: false, shouldQueueSummary: false, reason: reason, taskState: .failure)
        }
    }

    func runLibraryReprocessingForBatch(for item: ProcessLibraryItem, runtime: RuntimeContext) async -> BatchLocalProcessingOutcome {
        guard canProcessLibraryItem(item, reprocess: true) else {
            return BatchLocalProcessingOutcome(
                succeeded: false,
                shouldQueueSummary: false,
                reason: "Audio is missing",
                taskState: .failure
            )
        }
        stopWatching()
        selectLibraryItem(item)
        stage = .idle
        message = ""
        logText = ""
        snapshot = OutputSnapshot()
        progressFraction = 0.0
        persistentLogPath = ""

        do {
            logStore.start(dataRoot: runtime.dataRoot)
            logStore.attach(outputDirectory: item.outputURL)
            persistentLogPath = logStore.outputURL?.path ?? logStore.fallbackURL?.path ?? ""
            logEvent(event: "library_batch_reprocessing_started", message: "Batch reprocessing started", fields: ["item_id": item.id])
            if FileManager.default.fileExists(atPath: item.outputURL.path) {
                try FileManager.default.removeItem(at: item.outputURL)
            }
            let processingResult = try await processAudio(
                item.audioURL,
                outputDirectory: item.outputURL,
                runtime: runtime,
                skipExisting: false
            )
            stage = .refreshing
            updateProgress(defaultValue: 0.95)
            refresh()
            stage = .completed
            progressFraction = 1.0
            stopWatching()
            await refreshLibraryAndWait()
            let resultReason = processingResult.qaPassed ? "Reprocessed" : qaFailureSummary(for: item.outputURL)
            logEvent(event: "library_batch_reprocessing_completed", message: resultReason, fields: ["item_id": item.id])
            return BatchLocalProcessingOutcome(
                succeeded: true,
                shouldQueueSummary: true,
                reason: resultReason,
                taskState: processingResult.taskState
            )
        } catch {
            stage = .failed
            let reason = conciseFailureReason(error)
            message = reason
            appendLog("\nERROR: \(error.localizedDescription)\n")
            logError(event: "library_batch_reprocessing_failed", error: error, fields: ["item_id": item.id])
            stopWatching()
            await refreshLibraryAndWait()
            return BatchLocalProcessingOutcome(succeeded: false, shouldQueueSummary: false, reason: reason, taskState: .failure)
        }
    }

    func runTitleGenerationForBatch(
        for item: ProcessLibraryItem,
        cloudSettings: CloudSettings
    ) async -> BatchLocalProcessingOutcome {
        guard canRegenerateTitle(for: item) else {
            return BatchLocalProcessingOutcome(
                succeeded: false,
                shouldQueueSummary: false,
                reason: "Missing cloud summary",
                taskState: .failure
            )
        }
        stopWatching()
        selectLibraryItem(item)
        stage = .refreshing
        message = ""
        logText = ""
        snapshot = OutputSnapshot()
        progressFraction = 0.2
        persistentLogPath = ""

        do {
            try prepareSummaryForTitleGeneration(for: item)
            startWatching(outputDirectory: item.outputURL)
            let runtime = try runtimeProvider()
            logStore.start(dataRoot: runtime.dataRoot)
            logStore.attach(outputDirectory: item.outputURL)
            persistentLogPath = logStore.outputURL?.path ?? logStore.fallbackURL?.path ?? ""
            try await runTitleCommand(outputDirectory: item.outputURL, runtime: runtime, cloudSettings: cloudSettings)
            snapshot = snapshotForOutputDirectory(item.outputURL)
            progressFraction = 1.0
            stage = .completed
            stopWatching()
            await refreshLibraryAndWait()
            let resultReason = "Title regenerated"
            logEvent(category: "summary", event: "title_generation_batch_completed", message: resultReason, fields: ["item_id": item.id])
            return BatchLocalProcessingOutcome(succeeded: true, shouldQueueSummary: false, reason: resultReason, taskState: .success)
        } catch {
            stage = .failed
            let reason = conciseFailureReason(error)
            message = reason
            appendLog("\nERROR: \(error.localizedDescription)\n")
            logError(category: "summary", event: "title_generation_batch_failed", error: error, fields: ["item_id": item.id])
            stopWatching()
            refresh()
            return BatchLocalProcessingOutcome(succeeded: false, shouldQueueSummary: false, reason: reason, taskState: .failure)
        }
    }

    func runAudioDownloadBatch(_ items: [ProcessLibraryItem]) async {
        beginMarkedBatch(total: items.count, title: "Download audio")
        var reportItems: [ProcessingReportItem] = []
        for (index, item) in items.enumerated() where !Task.isCancelled {
            activeBatchCompleted = index
            activeBatchCurrentTitle = item.title
            progressFraction = 0.05
            updateBatchProgressFromCurrentItem()
            let outcome = await runAudioDownloadForBatch(for: item)
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
                    category: "import",
                    event: "audio_download_batch_stopped_after_current",
                    message: "Audio download batch stopped after current item",
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
            title: failureCount > 0 ? "Batch audio download completed with failures" : "Batch audio download completed",
            detail: detail,
            items: reportItems
        )
        stage = failureCount > 0 ? .failed : .completed
        message = detail
        endMarkedBatch()
        await refreshLibraryAndWait()
    }

    private func runAudioDownloadForBatch(for item: ProcessLibraryItem) async -> BatchLocalProcessingOutcome {
        stopWatching()
        selectLibraryItem(item)
        stage = .importing
        message = "Downloading audio"
        do {
            try await restoreAudioFile(for: item)
            progressFraction = 1.0
            stage = .completed
            message = "Audio downloaded"
            await refreshLibraryAndWait()
            logEvent(category: "import", event: "audio_download_batch_item_completed", message: "Audio downloaded", fields: ["item_id": item.id])
            return BatchLocalProcessingOutcome(succeeded: true, shouldQueueSummary: false, reason: "Audio downloaded", taskState: .success)
        } catch {
            stage = .failed
            let reason = conciseFailureReason(error)
            message = reason
            appendLog("\nERROR: \(error.localizedDescription)\n")
            logError(category: "import", event: "audio_download_batch_item_failed", error: error, fields: ["item_id": item.id])
            await refreshLibraryAndWait()
            return BatchLocalProcessingOutcome(succeeded: false, shouldQueueSummary: false, reason: reason, taskState: .failure)
        }
    }

    func restoreAudioForBatchIfNeeded(_ item: ProcessLibraryItem) async throws -> ProcessLibraryItem {
        guard !item.isAudioPresent else { return item }
        guard item.canRestoreAudio else {
            throw AppError.fileCopyFailed("Audio is missing and no recoverable source is available.")
        }
        stage = .importing
        progressFraction = 0.05
        message = "Restoring audio for \(item.title)"
        logEvent(category: "import", event: "batch_audio_restore_started", message: "Batch audio restore started", fields: ["item_id": item.id])
        try await restoreAudioFile(for: item)
        await refreshLibraryAndWait()
        guard let restored = libraryItems.first(where: { $0.id == item.id }), restored.isAudioPresent else {
            throw AppError.fileCopyFailed("Audio restore did not produce a readable media file.")
        }
        selectLibraryItem(restored)
        logEvent(category: "import", event: "batch_audio_restore_completed", message: "Batch audio restore completed", fields: ["item_id": item.id])
        return restored
    }
}
