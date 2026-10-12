import Foundation

struct BatchProcessingProgress: Equatable {
    let title: String
    let completed: Int
    let total: Int
    let currentTitle: String
    let currentItemProgress: Double

    var fraction: Double {
        guard total > 0 else { return 0 }
        let boundedCurrent = min(1.0, max(0.0, currentItemProgress))
        return min(1.0, max(0.0, (Double(completed) + boundedCurrent) / Double(total)))
    }
}

enum ProcessingWorkflow: Equatable {
    case localOnly
    case transcribeAndSummarize

    var requiresCloudSummary: Bool {
        self == .transcribeAndSummarize
    }

    func actionTitle(reprocess: Bool = false, isCloudConfigured: Bool = true) -> String {
        switch (self, reprocess) {
        case (.localOnly, true):
            return "Retranscribe locally only"
        case (.localOnly, false):
            return "Transcribe locally only"
        case (.transcribeAndSummarize, true):
            return isCloudConfigured ? "Retranscribe and summarize" : "Retranscribe and summarize (not configured)"
        case (.transcribeAndSummarize, false):
            return isCloudConfigured ? "Transcribe and summarize" : "Transcribe and summarize (not configured)"
        }
    }

    func batchTitle(reprocess: Bool = false) -> String {
        switch (self, reprocess) {
        case (.localOnly, true): return "Retranscribe locally only"
        case (.localOnly, false): return "Transcribe locally only"
        case (.transcribeAndSummarize, true): return "Retranscribe and summarize"
        case (.transcribeAndSummarize, false): return "Transcribe and summarize"
        }
    }
}

enum ProcessingTaskKind: String, Equatable {
    case processing
    case cloud
    case sync
}

enum ProcessingTaskState: Equatable {
    case queued
    case running
    case success
    case warning
    case failure

    var isActive: Bool {
        switch self {
        case .queued, .running:
            return true
        case .success, .warning, .failure:
            return false
        }
    }
}

struct ProcessingTaskStatus: Equatable, Identifiable {
    let kind: ProcessingTaskKind
    let id: String
    let title: String
    let itemTitle: String
    let detail: String
    let fraction: Double
    let state: ProcessingTaskState

    init(
        kind: ProcessingTaskKind,
        id: String? = nil,
        title: String,
        itemTitle: String,
        detail: String,
        fraction: Double,
        state: ProcessingTaskState = .running
    ) {
        self.kind = kind
        self.id = id ?? kind.rawValue
        self.title = title
        self.itemTitle = itemTitle
        self.detail = detail
        self.fraction = min(1.0, max(0.0, fraction))
        self.state = state
    }
}

typealias ModelProgressStatus = ProcessingTaskStatus

enum SummaryRequestState: Equatable {
    case inProgress
    case success
    case failure
}

struct SummaryRequestStatus: Equatable {
    let itemID: String
    let state: SummaryRequestState
    let message: String
}

enum ProcessingReportState: Equatable {
    case success
    case failure
}

struct ProcessingReportItem: Identifiable, Equatable {
    let id: String
    let title: String
    let state: ProcessingReportState
    let reason: String
}

struct ProcessingReport: Identifiable, Equatable {
    let id = UUID()
    let title: String
    let detail: String
    let items: [ProcessingReportItem]

    var successCount: Int {
        items.filter { $0.state == .success }.count
    }

    var failureCount: Int {
        items.filter { $0.state == .failure }.count
    }

    var hasFailures: Bool {
        failureCount > 0
    }
}
