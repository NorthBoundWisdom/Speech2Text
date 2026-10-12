import Foundation

@MainActor
extension JobController {
    func canGenerateSummary(for item: ProcessLibraryItem?) -> Bool {
        guard let item, !stage.isRunning else { return false }
        if item.hasTranscript {
            return true
        }
        let itemSnapshot = snapshotForOutputDirectory(item.outputURL)
        return !itemSnapshot.transcriptText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
    }

    var isCloudSummaryConfigured: Bool {
        settingsStore.cloudSettings().isConfigured
    }

    func canProcessLibraryItem(
        _ item: ProcessLibraryItem?,
        reprocess: Bool = false,
        workflow: ProcessingWorkflow
    ) -> Bool {
        guard canProcessLibraryItem(item, reprocess: reprocess) else { return false }
        return workflow == .localOnly || isCloudSummaryConfigured
    }

    func canRegenerateTitle(for item: ProcessLibraryItem?) -> Bool {
        guard let item, !stage.isRunning else { return false }
        return !summaryTextForTitleGeneration(for: item).trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
    }

    func visibleSummaryRequestStatus(for item: ProcessLibraryItem?) -> SummaryRequestStatus? {
        guard let item, let summaryRequestStatus, summaryRequestStatus.itemID == item.id else { return nil }
        return summaryRequestStatus
    }

    func beginCloudOnlyTask(
        itemTitle: String,
        detail: String,
        fraction: Double = 0.05,
        state: ProcessingTaskState = .queued
    ) {
        processingTaskStatus = nil
        backgroundSummaryQueue.resetProgress()
        setCloudTaskStatus(itemTitle: itemTitle, detail: detail, fraction: fraction, state: state)
    }

    func summaryQueueFraction(currentFraction: Double) -> Double {
        backgroundSummaryQueue.snapshot.overallFraction(currentFraction: currentFraction)
    }

    func summaryQueueDetail(
        currentTitle: String = "",
        completed: Bool = false
    ) -> String {
        backgroundSummaryQueue.snapshot.progressDetail(
            currentTitle: currentTitle,
            currentItemCompleted: completed,
            titleFormatter: compactProgressItemTitle
        )
    }

    func generateSummary(for item: ProcessLibraryItem) {
        guard !stage.isRunning else {
            setSummaryRequestStatus("The current task is still running", state: .failure, itemID: item.id, clearsAfterDelay: true)
            return
        }
        guard canGenerateSummary(for: item) else {
            message = "Transcript is missing"
            setSummaryRequestStatus("Cannot generate a summary without a transcript", state: .failure, itemID: item.id, clearsAfterDelay: true)
            return
        }
        setSummaryRequestStatus("Preparing cloud summary request", state: .inProgress, itemID: item.id)
        beginCloudOnlyTask(itemTitle: compactProgressItemTitle(item.title), detail: "Preparing cloud summary request")
        let cloudSettings: CloudSettings
        do {
            cloudSettings = try validateCloudSummarySettings()
        } catch {
            message = error.localizedDescription
            setSummaryRequestStatus(error.localizedDescription, state: .failure, itemID: item.id, clearsAfterDelay: true)
            setCloudTaskStatus(
                itemTitle: compactProgressItemTitle(item.title),
                detail: "Cloud task failed: \(shortStatusMessage(error.localizedDescription))",
                fraction: 1.0,
                state: .failure
            )
            logError(category: "summary", event: "summary_generation_preflight_failed", error: error, fields: ["item_id": item.id])
            return
        }
        beginSummaryGeneration(for: item, cloudSettings: cloudSettings)
    }

    func saveCurrentSummaryMarkdown(_ text: String) {
        guard let summaryURL = snapshot.summaryURL else {
            message = "Summary file is missing"
            return
        }
        pendingSummarySaveURL = summaryURL
        pendingSummarySaveText = text
        var updatedSnapshot = snapshot
        updatedSnapshot.summaryText = text
        snapshot = updatedSnapshot
        schedulePendingSummarySave(summaryURL: summaryURL, text: text)
    }

    func flushPendingSummarySave() async {
        summarySaveTask?.cancel()
        summarySaveTask = nil
        guard let summaryURL = pendingSummarySaveURL, let text = pendingSummarySaveText else {
            return
        }
        do {
            try await Task.detached(priority: .utility) {
                try Self.writeSummaryMarkdown(text, to: summaryURL)
            }.value
            clearPendingSummarySaveIfCurrent(summaryURL: summaryURL, text: text)
        } catch {
            message = error.localizedDescription
            logError(category: "summary", event: "summary_save_failed", error: error)
        }
    }

    func flushPendingSummarySaveSynchronously() {
        summarySaveTask?.cancel()
        summarySaveTask = nil
        guard let summaryURL = pendingSummarySaveURL, let text = pendingSummarySaveText else {
            return
        }
        do {
            try Self.writeSummaryMarkdown(text, to: summaryURL)
            clearPendingSummarySaveIfCurrent(summaryURL: summaryURL, text: text)
        } catch {
            message = error.localizedDescription
            logError(category: "summary", event: "summary_save_failed", error: error)
        }
    }

    func snapshotApplyingPendingSummary(_ outputSnapshot: OutputSnapshot) -> OutputSnapshot {
        guard
            let pendingSummarySaveURL,
            let pendingSummarySaveText,
            outputSnapshot.summaryURL?.standardizedFileURL.path == pendingSummarySaveURL.standardizedFileURL.path
        else {
            return outputSnapshot
        }
        var mergedSnapshot = outputSnapshot
        mergedSnapshot.summaryText = pendingSummarySaveText
        return mergedSnapshot
    }

    private func schedulePendingSummarySave(summaryURL: URL, text: String) {
        summarySaveTask?.cancel()
        summarySaveTask = Task { [weak self] in
            do {
                try await Task.sleep(nanoseconds: 400_000_000)
                try await Task.detached(priority: .utility) {
                    try Self.writeSummaryMarkdown(text, to: summaryURL)
                }.value
                await MainActor.run {
                    self?.clearPendingSummarySaveIfCurrent(summaryURL: summaryURL, text: text)
                }
            } catch is CancellationError {
                return
            } catch {
                await MainActor.run {
                    self?.message = error.localizedDescription
                    self?.logError(category: "summary", event: "summary_save_failed", error: error)
                }
            }
        }
    }

    private func clearPendingSummarySaveIfCurrent(summaryURL: URL, text: String) {
        guard
            pendingSummarySaveURL?.standardizedFileURL.path == summaryURL.standardizedFileURL.path,
            pendingSummarySaveText == text
        else {
            return
        }
        pendingSummarySaveURL = nil
        pendingSummarySaveText = nil
        summarySaveTask = nil
    }

    private nonisolated static func writeSummaryMarkdown(_ text: String, to summaryURL: URL) throws {
        try FileManager.default.createDirectory(
            at: summaryURL.deletingLastPathComponent(),
            withIntermediateDirectories: true
        )
        try text.write(to: summaryURL, atomically: true, encoding: .utf8)
    }

    func regenerateSummaryDiscardingExisting() {
        guard !stage.isRunning else { return }
        guard let item = selectedLibraryItem else {
            message = "No library item is selected"
            return
        }
        regenerateSummaryDiscardingExisting(for: item)
    }

    func regenerateSummaryDiscardingExisting(for item: ProcessLibraryItem) {
        guard !stage.isRunning else { return }
        flushPendingSummarySaveSynchronously()
        let itemSnapshot = snapshot(for: item)
        guard item.hasTranscript || !itemSnapshot.transcriptText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
            message = "Transcript is missing"
            setSummaryRequestStatus("Cannot generate a summary without a transcript", state: .failure, itemID: item.id, clearsAfterDelay: true)
            return
        }
        setSummaryRequestStatus("Preparing cloud summary request", state: .inProgress, itemID: item.id)
        beginCloudOnlyTask(itemTitle: compactProgressItemTitle(item.title), detail: "Preparing cloud summary request")
        do {
            let cloudSettings = try validateCloudSummarySettings()
            if let summaryURL = itemSnapshot.summaryURL, FileManager.default.fileExists(atPath: summaryURL.path) {
                try FileManager.default.removeItem(at: summaryURL)
            }
            snapshot = snapshotForOutputDirectory(item.outputURL)
            logEvent(category: "summary", event: "summary_discarded_for_regeneration", message: "Existing summary discarded", fields: ["item_id": item.id])
            beginSummaryGeneration(for: item, cloudSettings: cloudSettings)
        } catch {
            message = error.localizedDescription
            setSummaryRequestStatus(error.localizedDescription, state: .failure, itemID: item.id, clearsAfterDelay: true)
            setCloudTaskStatus(
                itemTitle: compactProgressItemTitle(item.title),
                detail: "Cloud task failed: \(shortStatusMessage(error.localizedDescription))",
                fraction: 1.0,
                state: .failure
            )
            logError(category: "summary", event: "summary_discard_failed", error: error, fields: ["item_id": item.id])
        }
    }

    func regenerateSummaries(for selectedItems: [ProcessLibraryItem]) {
        guard !stage.isRunning else { return }
        let items = uniqueItems(from: selectedItems).filter { canGenerateSummary(for: $0) }
        guard !items.isEmpty else {
            message = "No selected items can regenerate summary"
            return
        }
        dismissProcessingReport()
        beginCloudOnlyTask(itemTitle: "", detail: "Preparing batch summaries")
        do {
            _ = try validateCloudSummarySettings()
            let runtime = try runtimeProvider()
            for item in items {
                let itemSnapshot = snapshot(for: item)
                if let summaryURL = itemSnapshot.summaryURL, FileManager.default.fileExists(atPath: summaryURL.path) {
                    try FileManager.default.removeItem(at: summaryURL)
                }
                logEvent(category: "summary", event: "summary_discarded_for_regeneration", message: "Existing summary discarded", fields: ["item_id": item.id])
                _ = enqueueBackgroundSummary(
                    for: item,
                    runtime: runtime,
                    localState: .success,
                    localReason: "Summary regeneration requested"
                )
            }
        } catch {
            message = error.localizedDescription
            setCloudTaskStatus(
                itemTitle: "",
                detail: "Cloud task failed: \(shortStatusMessage(error.localizedDescription))",
                fraction: 1.0,
                state: .failure
            )
            logError(category: "summary", event: "summary_generation_batch_preflight_failed", error: error, fields: ["count": "\(items.count)"])
        }
    }

    func regenerateTitle(for item: ProcessLibraryItem) {
        guard !stage.isRunning else {
            setSummaryRequestStatus("The current task is still running", state: .failure, itemID: item.id, clearsAfterDelay: true)
            return
        }
        guard canRegenerateTitle(for: item) else {
            message = "Summary is missing"
            setSummaryRequestStatus("Cannot generate a title without a summary", state: .failure, itemID: item.id, clearsAfterDelay: true)
            return
        }
        setSummaryRequestStatus("Preparing title regeneration", state: .inProgress, itemID: item.id)
        beginCloudOnlyTask(itemTitle: compactProgressItemTitle(item.title), detail: "Preparing cloud title request")
        do {
            let cloudSettings = try validateCloudSummarySettings()
            try prepareSummaryForTitleGeneration(for: item)
            currentTask?.cancel()
            currentTask = Task { await runTitleGeneration(for: item, cloudSettings: cloudSettings) }
        } catch {
            message = error.localizedDescription
            setSummaryRequestStatus(error.localizedDescription, state: .failure, itemID: item.id, clearsAfterDelay: true)
            setCloudTaskStatus(
                itemTitle: compactProgressItemTitle(item.title),
                detail: "Cloud task failed: \(shortStatusMessage(error.localizedDescription))",
                fraction: 1.0,
                state: .failure
            )
            logError(category: "summary", event: "title_generation_preflight_failed", error: error, fields: ["item_id": item.id])
        }
    }

    func regenerateTitles(for selectedItems: [ProcessLibraryItem]) {
        guard !stage.isRunning else { return }
        let items = uniqueItems(from: selectedItems)
        guard !items.isEmpty else {
            message = "No selected items can regenerate title"
            return
        }
        dismissProcessingReport()
        beginCloudOnlyTask(itemTitle: "", detail: "Preparing batch titles")
        do {
            let cloudSettings = try validateCloudSummarySettings()
            logEvent(
                category: "summary",
                event: "title_generation_batch_requested",
                message: "Batch title generation requested",
                fields: ["count": "\(items.count)"]
            )
            currentTask?.cancel()
            currentTask = Task { await runBatchTitleGeneration(items, cloudSettings: cloudSettings) }
        } catch {
            message = error.localizedDescription
            setCloudTaskStatus(
                itemTitle: "",
                detail: "Cloud task failed: \(shortStatusMessage(error.localizedDescription))",
                fraction: 1.0,
                state: .failure
            )
            logError(category: "summary", event: "title_generation_batch_preflight_failed", error: error, fields: ["count": "\(items.count)"])
        }
    }

    func beginSummaryGeneration(for item: ProcessLibraryItem, cloudSettings: CloudSettings) {
        setSummaryRequestStatus("Preparing cloud summary request", state: .inProgress, itemID: item.id)
        beginCloudOnlyTask(itemTitle: compactProgressItemTitle(item.title), detail: "Preparing cloud summary request")
        logEvent(category: "summary", event: "summary_requested", message: "Summary generation requested", fields: ["item_id": item.id])
        currentTask?.cancel()
        currentTask = Task { await runSummaryGeneration(for: item, cloudSettings: cloudSettings) }
    }

    func summaryTextForTitleGeneration(for item: ProcessLibraryItem) -> String {
        let cloudSummaryURL = item.outputURL.appendingPathComponent("cloud/summary.md")
        if
            let cloudText = try? String(contentsOf: cloudSummaryURL, encoding: .utf8),
            !cloudText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
        {
            return cloudText
        }
        return snapshot(for: item).summaryText
    }

    func prepareSummaryForTitleGeneration(for item: ProcessLibraryItem) throws {
        let cloudSummaryURL = item.outputURL.appendingPathComponent("cloud/summary.md")
        if
            let cloudText = try? String(contentsOf: cloudSummaryURL, encoding: .utf8),
            !cloudText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
        {
            return
        }
        let sourceSummary = summaryTextForTitleGeneration(for: item).trimmingCharacters(in: .whitespacesAndNewlines)
        guard !sourceSummary.isEmpty else {
            throw AppError.cloudTitleFailed("Cannot generate a title without a summary")
        }
        try FileManager.default.createDirectory(at: cloudSummaryURL.deletingLastPathComponent(), withIntermediateDirectories: true)
        try sourceSummary.write(to: cloudSummaryURL, atomically: true, encoding: .utf8)
    }

    func setSummaryRequestStatus(
        _ message: String,
        state: SummaryRequestState,
        itemID: String,
        clearsAfterDelay: Bool = false
    ) {
        summaryRequestStatusGeneration += 1
        let generation = summaryRequestStatusGeneration
        summaryRequestStatusClearTask?.cancel()
        summaryRequestStatus = SummaryRequestStatus(
            itemID: itemID,
            state: state,
            message: shortStatusMessage(message)
        )
        guard clearsAfterDelay else { return }
        summaryRequestStatusClearTask = Task { [weak self] in
            try? await Task.sleep(nanoseconds: 3_000_000_000)
            await MainActor.run {
                guard self?.summaryRequestStatusGeneration == generation else { return }
                self?.summaryRequestStatus = nil
                self?.summaryRequestStatusClearTask = nil
            }
        }
    }

    func shortStatusMessage(_ value: String) -> String {
        let trimmed = value.trimmingCharacters(in: .whitespacesAndNewlines)
        guard trimmed.count > 120 else { return trimmed }
        return String(trimmed.prefix(120)) + "..."
    }
}
