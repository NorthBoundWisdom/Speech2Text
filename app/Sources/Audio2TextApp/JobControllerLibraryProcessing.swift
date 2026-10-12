import Foundation
#if canImport(Audio2TextCore)
    import Audio2TextCore
#endif

@MainActor
extension JobController {
    func canRunRepair(for item: ProcessLibraryItem?) -> Bool {
        guard let item, !stage.isRunning else { return false }
        let qaURL = item.outputURL.appendingPathComponent("qa.json")
        let preparedURL = item.outputURL.appendingPathComponent("prepared.wav")
        return FileManager.default.fileExists(atPath: qaURL.path)
            && FileManager.default.fileExists(atPath: preparedURL.path)
    }

    func runRepairForSelectedItem() {
        guard let item = selectedLibraryItem, canRunRepair(for: item) else {
            message = "Repair requires QA and prepared audio"
            return
        }
        currentTask?.cancel()
        currentTask = Task { await runRepair(for: item) }
    }

    func processLibraryItem(
        _ item: ProcessLibraryItem,
        reprocess: Bool = false,
        workflow: ProcessingWorkflow = .localOnly
    ) {
        guard !stage.isRunning else { return }
        guard canProcessLibraryItem(item, reprocess: reprocess, workflow: workflow) else {
            message = workflow.requiresCloudSummary && !isCloudSummaryConfigured
                ? "Cloud summary is not configured"
                : "Audio is missing"
            return
        }
        dismissProcessingReport()
        logEvent(
            event: "library_processing_requested",
            message: reprocess ? "Library reprocess requested" : "Library processing requested",
            fields: ["item_id": item.id, "reprocess": "\(reprocess)", "workflow": "\(workflow)"]
        )
        clearProcessingTaskStatuses()
        currentTask?.cancel()
        currentTask = Task { await runLibraryProcessing(for: item, reprocess: reprocess, workflow: workflow) }
    }

    func canProcessLibraryItem(_ item: ProcessLibraryItem?, reprocess: Bool = false) -> Bool {
        guard let item, !stage.isRunning else { return false }
        if item.isAudioPresent {
            return true
        }
        if item.canRestoreAudio {
            return !reprocess || item.isProcessed || item.needsReanalysis
        }
        return false
    }

    func canDownloadAudio(for item: ProcessLibraryItem?) -> Bool {
        guard let item, !stage.isRunning else { return false }
        return item.canDownloadAudio
    }

    func restoreAudio(for item: ProcessLibraryItem) {
        guard !stage.isRunning else { return }
        guard item.canRestoreAudio else {
            message = "No recoverable audio source is available"
            return
        }
        logEvent(category: "import", event: "audio_restore_requested", message: "Audio restore requested", fields: ["item_id": item.id, "source": item.source])
        currentTask?.cancel()
        currentTask = Task { await runAudioRestore(for: item) }
    }

    func downloadAudio(for item: ProcessLibraryItem) {
        guard !stage.isRunning else { return }
        guard item.canDownloadAudio else {
            message = "No downloadable audio source is available"
            return
        }
        logEvent(category: "import", event: "audio_download_requested", message: "Audio download requested", fields: ["item_id": item.id, "source": item.source])
        currentTask?.cancel()
        currentTask = Task { await runAudioDownload(for: item) }
    }

    func downloadAudio(for selectedItems: [ProcessLibraryItem]) {
        guard !stage.isRunning else { return }
        let items = unprocessedItems(from: selectedItems).filter(\.canDownloadAudio)
        guard !items.isEmpty else {
            message = "No selected items can download audio"
            return
        }
        logEvent(
            category: "import",
            event: "audio_download_batch_requested",
            message: "Batch audio download requested",
            fields: ["count": "\(items.count)"]
        )
        currentTask?.cancel()
        currentTask = Task { await runAudioDownloadBatch(items) }
    }

    private func runLibraryProcessing(
        for item: ProcessLibraryItem,
        reprocess: Bool,
        workflow: ProcessingWorkflow
    ) async {
        stopWatching()
        selectLibraryItem(item)
        stage = .idle
        message = ""
        logText = ""
        snapshot = OutputSnapshot()
        progressFraction = 0.0
        persistentLogPath = ""
        clearProcessingTaskStatuses()

        do {
            let runtime = try runtimeProvider()
            let processingItem: ProcessLibraryItem
            if item.isAudioPresent {
                processingItem = item
            } else {
                processingItem = try await restoreAudioForBatchIfNeeded(item)
            }
            if reprocess, FileManager.default.fileExists(atPath: processingItem.outputURL.path) {
                try FileManager.default.removeItem(at: processingItem.outputURL)
            }
            logStore.start(dataRoot: runtime.dataRoot)
            logStore.attach(outputDirectory: processingItem.outputURL)
            persistentLogPath = logStore.outputURL?.path ?? logStore.fallbackURL?.path ?? ""
            logEvent(event: "library_processing_started", message: "Library processing started", fields: ["item_id": processingItem.id, "reprocess": "\(reprocess)"])
            let processingResult = try await processAudio(
                processingItem.audioURL,
                outputDirectory: processingItem.outputURL,
                runtime: runtime,
                skipExisting: !reprocess
            )
            let resultReason = processingResult.qaPassed ? (reprocess ? "Reprocessed" : "Completed") : qaFailureSummary(for: processingItem.outputURL)

            stage = .refreshing
            updateProgress(defaultValue: 0.95)
            refresh()
            setProcessingTaskStatus(
                detail: processingResult.qaPassed ? (reprocess ? "Retranscription completed" : "Local transcription completed") : "Local transcription completed; review QA",
                fraction: 1.0,
                state: processingResult.taskState,
                itemTitle: compactProgressItemTitle(processingItem.title)
            )
            if workflow.requiresCloudSummary {
                _ = enqueueBackgroundSummary(
                    for: processingItem,
                    runtime: runtime,
                    localState: processingResult.taskState,
                    localReason: resultReason
                )
            }
            stage = .completed
            progressFraction = 1.0
            message = resultReason
            if !workflow.requiresCloudSummary {
                processingReport = localProcessingReport(
                    itemID: processingItem.id,
                    title: processingItem.title,
                    localState: processingResult.taskState,
                    reason: resultReason,
                    reprocess: reprocess
                )
            }
            stopWatching()
            await refreshLibraryAndWait()
            logEvent(event: "library_processing_completed", message: message, fields: ["item_id": item.id])
            Task { [weak self] in
                await self?.refreshLibraryAfterProcessing(runtime: runtime)
            }
        } catch {
            stage = .failed
            let reason = conciseFailureReason(error)
            message = reason
            setProcessingTaskStatus(detail: reason, fraction: max(progressFraction, 0.10), state: .failure)
            processingReport = ProcessingReport(
                title: "Processing failed",
                detail: reason,
                items: [
                    ProcessingReportItem(
                        id: item.id,
                        title: item.title,
                        state: .failure,
                        reason: reason
                    ),
                ]
            )
            appendLog("\nERROR: \(error.localizedDescription)\n")
            logError(event: "library_processing_failed", error: error, fields: ["item_id": item.id])
            stopWatching()
            await refreshLibraryAndWait()
        }
    }

    private func runRepair(for item: ProcessLibraryItem) async {
        stopWatching()
        selectLibraryItem(item)
        stage = .qa
        message = "Running repair"
        progressFraction = 0.86
        do {
            let runtime = try runtimeProvider()
            logStore.start(dataRoot: runtime.dataRoot)
            logStore.attach(outputDirectory: item.outputURL)
            persistentLogPath = logStore.outputURL?.path ?? logStore.fallbackURL?.path ?? ""
            startWatching(outputDirectory: item.outputURL)
            let arguments = AtotServiceClient.repair(outputDirectory: item.outputURL)
            appendLog("\n$ \(runtime.cli.path) \(arguments.joined(separator: " "))\n")
            _ = try await runner.run(
                executable: runtime.cli,
                arguments: arguments,
                currentDirectory: runtime.workingDirectory,
                environment: runtime.environment,
                onOutput: appendLog
            )
            snapshot = snapshotForOutputDirectory(item.outputURL)
            progressFraction = 1.0
            stage = .completed
            message = "Repair completed"
            stopWatching()
            await refreshLibraryAndWait()
            logEvent(category: "repair", event: "repair_completed", message: "Repair completed", fields: ["item_id": item.id])
        } catch {
            stage = .failed
            message = error.localizedDescription
            appendLog("\nERROR: \(error.localizedDescription)\n")
            logError(category: "repair", event: "repair_failed", error: error, fields: ["item_id": item.id])
            stopWatching()
            await refreshLibraryAndWait()
        }
    }

    @discardableResult
    func processAudio(
        _ audioURL: URL,
        outputDirectory: URL,
        runtime: RuntimeContext,
        skipExisting: Bool
    ) async throws -> LocalProcessingResult {
        snapshot = snapshotForOutputDirectory(outputDirectory)
        updateProgress(defaultValue: 0.12)
        setProcessingTaskStatus(detail: "Preparing local transcription", fraction: max(progressFraction, 0.05), state: .queued)
        if skipExisting, isAlreadyProcessed(snapshot) {
            stage = .completed
            progressFraction = 1.0
            message = "Already processed; showing existing output"
            setProcessingTaskStatus(detail: "Local transcript already exists", fraction: 1.0, state: .success)
            appendLog("Existing output detected; skipped transcription.\n")
            logEvent(event: "transcription_skipped_existing", message: "Existing output detected; skipped transcription", fields: ["output_directory": outputDirectory.path])
            await refreshLibraryAndWait()
            return LocalProcessingResult(qaPassed: true, didTranscribe: false)
        }
        startWatching(outputDirectory: outputDirectory)

        let processor = LocalAudioProcessor(runner: runner)
        let processingResult = try await processor.run(
            audioURL: audioURL,
            outputDirectory: outputDirectory,
            runtime: runtime,
            onOutput: appendLog
        ) { event in
            switch event {
            case let .willTranscribe(arguments):
                stage = .transcribing
                updateProgress(defaultValue: 0.15)
                message = "Transcribing \(audioURL.lastPathComponent)"
                setProcessingTaskStatus(detail: "Transcribing locally", fraction: max(progressFraction, 0.15), state: .running)
                logEvent(event: "stage_changed", message: "Transcribing", fields: ["stage": "transcribing", "audio": audioURL.lastPathComponent])
                appendLog("\n$ \(runtime.cli.path) \(arguments.joined(separator: " "))\n")
            case let .willRunQA(arguments):
                stage = .qa
                progressFraction = 0.86
                message = "Running QA"
                setProcessingTaskStatus(detail: "Checking QA", fraction: 0.86, state: .running)
                logEvent(event: "stage_changed", message: "Running QA", fields: ["stage": "qa", "output_directory": outputDirectory.path])
                appendLog("\n$ \(runtime.cli.path) \(arguments.joined(separator: " "))\n")
            case let .qaFailed(code, output):
                appendLog("\nQA exited with \(code); local transcript needs review.\n\(output)\n")
                logEvent(
                    .warning,
                    event: "qa_failed_needs_review",
                    message: "QA failed; local transcript needs review",
                    fields: ["exit_code": "\(code)", "summary": AppLogger.redacted(output)]
                )
            }
        }

        snapshot = snapshotForOutputDirectory(outputDirectory)
        progressFraction = 1.0
        message = processingResult.qaPassed ? "Local transcript ready" : "Local transcript ready; QA needs review"
        setProcessingTaskStatus(
            detail: processingResult.qaPassed ? "Local transcription completed" : "Local transcription completed; review QA",
            fraction: 1.0,
            state: processingResult.taskState
        )
        logEvent(event: "stage_changed", message: "Local processing finished", fields: ["stage": "local_completed", "output_directory": outputDirectory.path])
        return processingResult
    }

    private func isAlreadyProcessed(_ snapshot: OutputSnapshot) -> Bool {
        snapshot.runStatus == "done" && !snapshot.transcriptText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
    }
}
