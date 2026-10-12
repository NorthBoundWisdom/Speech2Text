import Foundation
#if canImport(Audio2TextCore)
    import Audio2TextCore
#endif

@MainActor
extension JobController {
    func runSummaryGeneration(
        for item: ProcessLibraryItem,
        cloudSettings: CloudSettings
    ) async {
        stopWatching()
        selectLibraryItem(item)
        stage = .refreshing
        progressFraction = 0.05
        startWatching(outputDirectory: item.outputURL)
        setSummaryRequestStatus("Preparing cloud summary request", state: .inProgress, itemID: item.id)
        setCloudTaskStatus(
            itemTitle: compactProgressItemTitle(item.title),
            detail: "Preparing cloud summary request",
            fraction: 0.05,
            state: .queued
        )
        do {
            let runtime = try runtimeProvider()
            logStore.start(dataRoot: runtime.dataRoot)
            logStore.attach(outputDirectory: item.outputURL)
            persistentLogPath = logStore.outputURL?.path ?? logStore.fallbackURL?.path ?? ""
            progressFraction = 0.2
            logEvent(category: "summary", event: "summary_generation_started", message: "Summary generation started", fields: ["item_id": item.id])
            setSummaryRequestStatus("Preparing processing package", state: .inProgress, itemID: item.id)
            setCloudTaskStatus(
                itemTitle: compactProgressItemTitle(item.title),
                detail: "Preparing cloud processing package",
                fraction: 0.15,
                state: .queued
            )
            try await ensureCloudInputPackage(outputDirectory: item.outputURL, runtime: runtime) { [weak self] text in
                self?.appendLog(text)
                self?.refreshManualSummaryProgress(
                    for: item,
                    fallbackDetail: "Preparing cloud processing package",
                    fallbackFraction: 0.15,
                    fallbackState: .queued
                )
            }
            setSummaryRequestStatus("Requesting cloud summary", state: .inProgress, itemID: item.id)
            setCloudTaskStatus(
                itemTitle: compactProgressItemTitle(item.title),
                detail: "Requesting cloud summary",
                fraction: 0.25,
                state: .running
            )
            try await runSummaryCommand(
                outputDirectory: item.outputURL,
                runtime: runtime,
                cloudSettings: cloudSettings,
                ensureCloudInput: false
            ) { [weak self] text in
                self?.appendLog(text)
                self?.refreshManualSummaryProgress(
                    for: item,
                    fallbackDetail: "Requesting cloud summary",
                    fallbackFraction: 0.25
                )
            }
            snapshot = snapshotForOutputDirectory(item.outputURL)
            progressFraction = 1.0
            stage = .completed
            message = "Summary generated"
            setSummaryRequestStatus("Summary generated", state: .success, itemID: item.id, clearsAfterDelay: true)
            setCloudTaskStatus(
                itemTitle: compactProgressItemTitle(item.title),
                detail: "Summary generation completed",
                fraction: 1.0,
                state: .success
            )
            stopWatching()
            await refreshLibraryAndWait()
            logEvent(category: "summary", event: "summary_generation_completed", message: "Summary generated", fields: ["item_id": item.id])
            Task { [weak self] in
                await self?.refreshLibraryAfterProcessing(runtime: runtime)
            }
        } catch {
            stage = .failed
            message = error.localizedDescription
            let reason = shortStatusMessage(error.localizedDescription)
            setSummaryRequestStatus("Summary generation failed: \(reason)", state: .failure, itemID: item.id, clearsAfterDelay: true)
            setCloudTaskStatus(
                itemTitle: compactProgressItemTitle(item.title),
                detail: "Cloud task failed: \(reason)",
                fraction: max(progressFraction, snapshot.cloudProgressFraction, 0.10),
                state: .failure
            )
            appendLog("\nERROR: \(error.localizedDescription)\n")
            logError(category: "summary", event: "summary_generation_failed", error: error, fields: ["item_id": item.id])
            stopWatching()
            refresh()
        }
    }

    func runTitleGeneration(
        for item: ProcessLibraryItem,
        cloudSettings: CloudSettings
    ) async {
        stopWatching()
        selectLibraryItem(item)
        stage = .refreshing
        progressFraction = 0.2
        startWatching(outputDirectory: item.outputURL)
        setSummaryRequestStatus("Requesting cloud title", state: .inProgress, itemID: item.id)
        setCloudTaskStatus(
            itemTitle: compactProgressItemTitle(item.title),
            detail: "Requesting cloud title",
            fraction: 0.25,
            state: .running
        )
        do {
            let runtime = try runtimeProvider()
            logStore.start(dataRoot: runtime.dataRoot)
            logStore.attach(outputDirectory: item.outputURL)
            persistentLogPath = logStore.outputURL?.path ?? logStore.fallbackURL?.path ?? ""
            try await runTitleCommand(outputDirectory: item.outputURL, runtime: runtime, cloudSettings: cloudSettings) { [weak self] text in
                self?.appendLog(text)
                self?.setCloudTaskStatus(
                    itemTitle: self?.compactProgressItemTitle(item.title) ?? "",
                    detail: "Requesting cloud title",
                    fraction: 0.50,
                    state: .running
                )
            }
            snapshot = snapshotForOutputDirectory(item.outputURL)
            progressFraction = 1.0
            stage = .completed
            message = "Title regenerated"
            setSummaryRequestStatus("Title generated", state: .success, itemID: item.id, clearsAfterDelay: true)
            setCloudTaskStatus(
                itemTitle: compactProgressItemTitle(item.title),
                detail: "Title generation completed",
                fraction: 1.0,
                state: .success
            )
            stopWatching()
            await refreshLibraryAndWait()
            logEvent(category: "summary", event: "title_generation_completed", message: "Title regenerated", fields: ["item_id": item.id])
        } catch {
            stage = .failed
            message = error.localizedDescription
            let reason = shortStatusMessage(error.localizedDescription)
            setSummaryRequestStatus("Title generation failed: \(reason)", state: .failure, itemID: item.id, clearsAfterDelay: true)
            setCloudTaskStatus(
                itemTitle: compactProgressItemTitle(item.title),
                detail: "Cloud task failed: \(reason)",
                fraction: max(progressFraction, 0.10),
                state: .failure
            )
            appendLog("\nERROR: \(error.localizedDescription)\n")
            logError(category: "summary", event: "title_generation_failed", error: error, fields: ["item_id": item.id])
            stopWatching()
            refresh()
        }
    }

    func runSummaryCommand(
        outputDirectory: URL,
        runtime: RuntimeContext,
        cloudSettings: CloudSettings,
        ensureCloudInput: Bool = true,
        onOutput: (@MainActor (String) -> Void)? = nil
    ) async throws {
        let outputHandler = onOutput ?? appendLog
        if ensureCloudInput {
            try await ensureCloudInputPackage(outputDirectory: outputDirectory, runtime: runtime, onOutput: outputHandler)
        }
        let promptFile = try writeSummaryPromptFile(cloudSettings.summaryPrompt, runtime: runtime)
        let arguments = AtotServiceClient.cloudSummarize(
            outputDirectory: outputDirectory,
            promptFile: promptFile
        )
        outputHandler("\n$ \(runtime.cli.path) \(arguments.joined(separator: " "))\n")
        outputHandler("Cloud model: \(cloudSettings.redactedDescription)\n")
        logEvent(
            category: "summary",
            event: "summary_command_started",
            message: "Cloud summary command started",
            fields: ["model": cloudSettings.model, "api_base": cloudSettings.apiBase, "mode": "chunked"]
        )
        do {
            let result = try await runner.run(
                executable: runtime.cli,
                arguments: arguments,
                currentDirectory: runtime.workingDirectory,
                environment: runtime.environment,
                onOutput: outputHandler
            )
            try validateCloudCommandResult(
                result,
                outputDirectory: outputDirectory,
                requiredArtifact: "cloud/summary.md",
                missingArtifactMessage: "Cloud summary command completed without writing cloud/summary.md.",
                includeChunkFailures: true
            )
            try publishTitleIfPresent(outputDirectory: outputDirectory, dataRoot: runtime.dataRoot)
        } catch let AppError.processFailed(_, _, output) {
            throw AppError.cloudSummaryFailed(cloudSummaryFailureMessage(from: output, outputDirectory: outputDirectory, includeChunkFailures: true))
        }
    }

    func runTitleCommand(
        outputDirectory: URL,
        runtime: RuntimeContext,
        cloudSettings: CloudSettings,
        onOutput: (@MainActor (String) -> Void)? = nil
    ) async throws {
        let outputHandler = onOutput ?? appendLog
        let promptFile = try writeTitlePromptFile(cloudSettings.titlePrompt, runtime: runtime)
        let arguments = AtotServiceClient.cloudTitle(
            outputDirectory: outputDirectory,
            promptFile: promptFile
        )
        outputHandler("\n$ \(runtime.cli.path) \(arguments.joined(separator: " "))\n")
        outputHandler("Cloud model: \(cloudSettings.redactedDescription)\n")
        logEvent(
            category: "summary",
            event: "title_command_started",
            message: "Cloud title command started",
            fields: ["model": cloudSettings.model, "api_base": cloudSettings.apiBase]
        )
        do {
            let result = try await runner.run(
                executable: runtime.cli,
                arguments: arguments,
                currentDirectory: runtime.workingDirectory,
                environment: runtime.environment,
                onOutput: outputHandler
            )
            try validateCloudCommandResult(
                result,
                outputDirectory: outputDirectory,
                requiredArtifact: "cloud/short_title.txt",
                missingArtifactMessage: "Cloud title command completed without writing cloud/short_title.txt."
            )
            try publishTitleIfPresent(outputDirectory: outputDirectory, dataRoot: runtime.dataRoot)
        } catch let AppError.processFailed(_, _, output) {
            throw AppError.cloudTitleFailed(cloudSummaryFailureMessage(from: output))
        }
    }

    func validateCloudSummarySettings(
        environment: [String: String] = ProcessInfo.processInfo.environment
    ) throws -> CloudSettings {
        let cloudSettings = settingsStore.cloudSettings(environment: environment)
        if !cloudSettings.configurationError.isEmpty {
            throw AppError.invalidImportOutput(cloudSettings.configurationError)
        }
        guard cloudSettings.isConfigured else {
            throw AppError.missingCloudAPIKey
        }
        return cloudSettings
    }
}
