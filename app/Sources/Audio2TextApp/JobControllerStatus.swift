import Foundation
#if canImport(Audio2TextCore)
    import Audio2TextCore
#endif

@MainActor
extension JobController {
    var librarySidebarState: LibrarySidebarState {
        refreshLibrarySidebarDerivedStateIfNeeded()
        return cachedLibrarySidebarState
    }

    var currentProcessingItemTitle: String {
        let rawTitle: String
        if !activeBatchCurrentTitle.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            rawTitle = activeBatchCurrentTitle
        } else if let item = selectedLibraryItem {
            rawTitle = item.title
        } else if let selectedFile {
            rawTitle = selectedFile.deletingPathExtension().lastPathComponent
        } else {
            rawTitle = ""
        }
        return compactProgressItemTitle(rawTitle)
    }

    func compactProgressItemTitle(_ rawTitle: String) -> String {
        let trimmed = rawTitle.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return "" }
        let prefix = String(trimmed.prefix(12))
        return trimmed.count > 12 ? "\(prefix)..." : prefix
    }

    var sidebarProcessingTaskStatuses: [ProcessingTaskStatus] {
        var statuses: [ProcessingTaskStatus] = []
        if let processingStatus = currentProcessingTaskStatus {
            statuses.append(processingStatus)
        }
        if let cloudStatus = cloudTaskStatus {
            statuses.append(cloudStatus)
        }
        if let subscriptionStatus = subscriptionRefreshTaskStatus {
            statuses.append(subscriptionStatus)
        }
        if let refreshStatus = libraryRefreshTaskStatus {
            statuses.append(refreshStatus)
        }
        return statuses
    }

    var sidebarModelProgressStatuses: [ProcessingTaskStatus] {
        sidebarProcessingTaskStatuses
    }

    var displayedLibrarySyncStatus: LibrarySyncStatus {
        guard
            let syncStatus = sidebarProcessingTaskStatuses.first(where: { $0.kind == .sync && $0.state.isActive })
        else {
            return librarySyncStatus
        }
        let detail = syncStatus.detail.trimmingCharacters(in: .whitespacesAndNewlines)
        return .syncing(
            detail.isEmpty ? "Library changes are syncing." : detail,
            checkedAt: librarySyncStatus.checkedAt,
            progress: syncStatus.fraction
        )
    }

    var hasActiveSidebarProcessingTasks: Bool {
        sidebarProcessingTaskStatuses.contains { $0.state.isActive }
            || processingTaskStatus != nil
            || cloudProcessingTaskStatus != nil
            || isRefreshingLibrary
            || snapshot.runStatus == "running"
            || snapshot.cloudStatus == "running"
    }

    var hasActiveSidebarModelProgress: Bool {
        hasActiveSidebarProcessingTasks
    }

    var sidebarBatchTaskKind: ProcessingTaskKind? {
        activeBatchTaskKind
    }

    var currentProcessingTaskStatus: ProcessingTaskStatus? {
        if let processingTaskStatus {
            return processingTaskStatus
        }
        return processingProgressStatusFromSnapshot()
    }

    var cloudTaskStatus: ProcessingTaskStatus? {
        if let cloudProcessingTaskStatus {
            return cloudProcessingTaskStatus
        }
        return cloudModelProgressStatus
    }

    var libraryRefreshTaskStatus: ProcessingTaskStatus? {
        guard isRefreshingLibrary || !libraryRefreshMessage.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
            return nil
        }
        return ProcessingTaskStatus(
            kind: .sync,
            title: "Library",
            itemTitle: "",
            detail: libraryRefreshMessage.isEmpty ? "Refreshing" : libraryRefreshMessage,
            fraction: isRefreshingLibrary ? 0.5 : 1.0,
            state: isRefreshingLibrary ? .running : .success
        )
    }

    var localModelProgressStatus: ProcessingTaskStatus? {
        processingProgressStatusFromSnapshot()
    }

    var cloudModelProgressStatus: ProcessingTaskStatus? {
        let processContextActive = stage.isRunning || batchProgress != nil
        return cloudProgressStatus(
            from: snapshot,
            itemTitle: currentProcessingItemTitle,
            processContextActive: processContextActive,
            prefersSummaryStageFloor: stage == .summarizing,
            allowsUnknownSummaryProgress: stage == .summarizing
        )
    }

    func processingProgressStatusFromSnapshot() -> ProcessingTaskStatus? {
        let processContextActive = stage.isRunning || batchProgress != nil
        let localFraction = max(snapshot.progressFraction, stage.isRunning ? progressFraction : 0.0)
        let hasLocalActivity = snapshot.runStatus == "running"
            || stage == .transcribing
            || stage == .qa
            || (processContextActive && stage == .summarizing && snapshot.runStatus == "done")
        guard hasLocalActivity else { return nil }

        let detail: String
        let fraction: Double
        let state: ProcessingTaskState
        if stage == .transcribing, snapshot.runStatus != "running" {
            detail = "Transcribing locally"
            fraction = max(localFraction, 0.15)
            state = .running
        } else if snapshot.runStatus == "running", stage != .qa {
            detail = snapshot.totalChunks > 0 ? "Chunks \(snapshot.chunkProgress)" : "Transcribing locally"
            fraction = max(localFraction, 0.10)
            state = .running
        } else if stage == .qa {
            detail = "Checking QA"
            fraction = max(localFraction, 0.86)
            state = .running
        } else if processContextActive, stage == .summarizing, snapshot.runStatus == "done" {
            detail = snapshot.qaStatus == "fail" ? "Transcription completed; review QA" : "Transcription completed"
            fraction = 1.0
            state = snapshot.qaStatus == "fail" ? .warning : .success
        } else {
            return nil
        }

        return ProcessingTaskStatus(
            kind: .processing,
            title: "Process",
            itemTitle: currentProcessingItemTitle,
            detail: detail,
            fraction: fraction,
            state: state
        )
    }

    func cloudProgressStatus(
        from source: OutputSnapshot,
        itemTitle: String,
        processContextActive: Bool,
        prefersSummaryStageFloor: Bool,
        allowsUnknownSummaryProgress: Bool
    ) -> ProcessingTaskStatus? {
        let status = source.cloudStatus
        let cloudFraction = source.cloudProgressFraction
        let hasCloudActivity = status == "running"
            || status == "prepared"
            || (processContextActive && allowsUnknownSummaryProgress)
            || (processContextActive && status == "complete")
            || (processContextActive && status == "partial")
            || (processContextActive && status == "failed")
        guard hasCloudActivity else { return nil }

        let detail: String
        let fraction: Double
        let state: ProcessingTaskState
        switch status {
        case "prepared":
            detail = processContextActive ? "Preparing cloud processing package" : "Cloud processing package is ready"
            fraction = max(cloudFraction, 0.05)
            state = .queued
        case "running":
            if source.cloudStage == "chunk_summaries" {
                detail = source.cloudTotalChunks > 0 ? "Chunk summaries \(source.cloudChunkProgress)" : "Summarizing chunks"
            } else if source.cloudStage == "episode_summary" {
                detail = "Summarizing episode"
            } else if source.cloudStage == "prepare" {
                detail = "Preparing cloud processing package"
            } else {
                detail = "Generating cloud summary"
            }
            fraction = max(cloudFraction, prefersSummaryStageFloor ? 0.92 : 0.08)
            state = .running
        case "partial":
            guard processContextActive else { return nil }
            detail = source.cloudFailedChunks > 0
                ? "Cloud summary partially completed; \(source.cloudFailedChunks) failed"
                : "Cloud summary partially completed"
            fraction = 1.0
            state = .warning
        case "complete":
            guard processContextActive else { return nil }
            detail = "Cloud summary completed"
            fraction = 1.0
            state = .success
        case "failed":
            guard processContextActive else { return nil }
            detail = source.cloudMessage.isEmpty ? "Cloud task failed" : "Cloud task failed: \(source.cloudMessage)"
            fraction = max(cloudFraction, 0.10)
            state = .failure
        default:
            guard processContextActive, allowsUnknownSummaryProgress else { return nil }
            detail = "Generating cloud summary"
            fraction = max(cloudFraction, 0.92)
            state = .running
        }

        return ProcessingTaskStatus(
            kind: .cloud,
            title: "Cloud task",
            itemTitle: itemTitle,
            detail: detail,
            fraction: fraction,
            state: state
        )
    }
}
