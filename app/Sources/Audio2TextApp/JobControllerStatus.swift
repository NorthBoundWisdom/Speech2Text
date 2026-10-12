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
            detail.isEmpty ? "资料正在同步。" : detail,
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
            detail: libraryRefreshMessage.isEmpty ? "刷新中" : libraryRefreshMessage,
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
            detail = "本地转写中"
            fraction = max(localFraction, 0.15)
            state = .running
        } else if snapshot.runStatus == "running", stage != .qa {
            detail = snapshot.totalChunks > 0 ? "分块 \(snapshot.chunkProgress)" : "本地转写中"
            fraction = max(localFraction, 0.10)
            state = .running
        } else if stage == .qa {
            detail = "QA 检查中"
            fraction = max(localFraction, 0.86)
            state = .running
        } else if processContextActive, stage == .summarizing, snapshot.runStatus == "done" {
            detail = snapshot.qaStatus == "fail" ? "转写完成，QA 待复查" : "转写完成"
            fraction = 1.0
            state = snapshot.qaStatus == "fail" ? .warning : .success
        } else {
            return nil
        }

        return ProcessingTaskStatus(
            kind: .processing,
            title: "处理",
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
            detail = processContextActive ? "准备云端处理包" : "云端处理包已就绪"
            fraction = max(cloudFraction, 0.05)
            state = .queued
        case "running":
            if source.cloudStage == "chunk_summaries" {
                detail = source.cloudTotalChunks > 0 ? "分块总结 \(source.cloudChunkProgress)" : "分块总结中"
            } else if source.cloudStage == "episode_summary" {
                detail = "整集总结中"
            } else if source.cloudStage == "prepare" {
                detail = "准备云端处理包"
            } else {
                detail = "云总结处理中"
            }
            fraction = max(cloudFraction, prefersSummaryStageFloor ? 0.92 : 0.08)
            state = .running
        case "partial":
            guard processContextActive else { return nil }
            detail = source.cloudFailedChunks > 0
                ? "云总结部分完成，失败 \(source.cloudFailedChunks)"
                : "云总结部分完成"
            fraction = 1.0
            state = .warning
        case "complete":
            guard processContextActive else { return nil }
            detail = "云总结完成"
            fraction = 1.0
            state = .success
        case "failed":
            guard processContextActive else { return nil }
            detail = source.cloudMessage.isEmpty ? "云任务失败" : "云任务失败：\(source.cloudMessage)"
            fraction = max(cloudFraction, 0.10)
            state = .failure
        default:
            guard processContextActive, allowsUnknownSummaryProgress else { return nil }
            detail = "云总结处理中"
            fraction = max(cloudFraction, 0.92)
            state = .running
        }

        return ProcessingTaskStatus(
            kind: .cloud,
            title: "云任务",
            itemTitle: itemTitle,
            detail: detail,
            fraction: fraction,
            state: state
        )
    }
}
