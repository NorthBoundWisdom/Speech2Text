import Foundation
#if canImport(Audio2TextCore)
    import Audio2TextCore
#endif

@MainActor
extension JobController {
    func start(workflow: ProcessingWorkflow = .localOnly) {
        guard canStart else { return }
        dismissProcessingReport()
        logEvent(
            event: "job_start_requested",
            message: "Processing job requested",
            fields: ["input_mode": "\(inputMode)", "group": selectedGroupName]
        )
        currentTask?.cancel()
        currentTask = Task { await runJob(workflow: workflow) }
    }

    func checkLink() {
        guard !stage.isRunning else { return }
        let url = urlText.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !url.isEmpty else {
            linkCheckStatus = .invalid("请输入链接")
            return
        }
        guard url.contains("xiaoyuzhoufm.com/episode/") else {
            linkCheckStatus = .invalid("目前只支持小宇宙单集链接")
            return
        }
        logEvent(event: "link_check_requested", message: "Link check requested", fields: ["host": URL(string: url)?.host ?? ""])
        currentTask?.cancel()
        linkCheckStatus = .checking
        currentTask = Task { await runLinkCheck(url: url) }
    }

    func importOnly() {
        guard canConfirmImport else { return }
        logEvent(event: "import_only_requested", message: "Import-only job requested", fields: ["input_mode": "\(inputMode)"])
        currentTask?.cancel()
        currentTask = Task { await runImportOnly() }
    }

    func resetImportDraft() {
        linkCheckStatus = .idle
        selectedFile = nil
        localImportMode = .copy
    }

    private func runJob(workflow: ProcessingWorkflow) async {
        stage = .idle
        message = ""
        logText = ""
        snapshot = OutputSnapshot()
        progressFraction = 0.0
        persistentLogPath = ""
        clearProcessingTaskStatuses()

        do {
            let runtime = try runtimeProvider()
            let dataRoot = runtime.dataRoot
            logStore.start(dataRoot: dataRoot)
            persistentLogPath = logStore.fallbackURL?.path ?? ""
            logEvent(event: "job_started", message: "Processing job started", fields: ["fallback_log": persistentLogPath])
            let audioURL: URL
            switch inputMode {
            case .xiaoyuzhou:
                audioURL = try await importXiaoyuzhou(runtime: runtime, download: true)
            case .localFile:
                audioURL = try importLocal(dataRoot: dataRoot)
            }
            let outputDirectory = OutputWatcher.outputDirectory(forAudio: audioURL, dataRoot: dataRoot)
            logStore.attach(outputDirectory: outputDirectory)
            persistentLogPath = logStore.outputURL?.path ?? persistentLogPath
            logEvent(event: "job_output_directory", message: "Job output directory selected", fields: ["output_directory": outputDirectory.path])
            let processingResult = try await processAudio(
                audioURL,
                outputDirectory: outputDirectory,
                runtime: runtime,
                skipExisting: true
            )
            let resultTitle = audioURL.deletingPathExtension().lastPathComponent
            let resultReason = processingResult.qaPassed ? "Completed" : qaFailureSummary(for: outputDirectory)
            if workflow.requiresCloudSummary {
                _ = enqueueBackgroundSummary(
                    itemID: audioURL.path,
                    title: resultTitle,
                    outputDirectory: outputDirectory,
                    runtime: runtime,
                    localState: processingResult.taskState,
                    localReason: resultReason
                )
            }

            stage = .refreshing
            updateProgress(defaultValue: 0.95)
            refresh()
            stage = .completed
            progressFraction = 1.0
            message = resultReason
            stopWatching()
            await refreshLibraryAndWait()
            logEvent(event: "job_completed", message: "Processing job completed", fields: ["output_log": persistentLogPath])
            Task { [weak self] in
                await self?.refreshLibraryAfterProcessing(runtime: runtime)
            }
        } catch {
            stage = .failed
            let reason = conciseFailureReason(error)
            message = reason
            setProcessingTaskStatus(detail: reason, fraction: max(progressFraction, 0.10), state: .failure)
            processingReport = ProcessingReport(
                title: "处理失败",
                detail: reason,
                items: [
                    ProcessingReportItem(
                        id: selectedFile?.path ?? urlText,
                        title: selectedFile?.deletingPathExtension().lastPathComponent ?? "当前任务",
                        state: .failure,
                        reason: reason
                    ),
                ]
            )
            appendLog("\nERROR: \(error.localizedDescription)\n")
            logError(event: "job_failed", error: error)
            stopWatching()
            await refreshLibraryAndWait()
        }
    }
}
