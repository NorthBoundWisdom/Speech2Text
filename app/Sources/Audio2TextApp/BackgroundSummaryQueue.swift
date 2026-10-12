import Foundation

struct BackgroundSummaryJob: Equatable {
    let itemID: String
    let title: String
    let outputDirectory: URL
    let runtime: RuntimeContext
    let cloudSettings: CloudSettings
    let localState: ProcessingTaskState
    let localReason: String
}

struct BackgroundSummaryQueueSnapshot: Equatable {
    let total: Int
    let completed: Int
    let pending: Int
    let isRunning: Bool

    func overallFraction(currentFraction: Double) -> Double {
        guard total > 0 else { return currentFraction }
        let boundedCurrent = min(1.0, max(0.0, currentFraction))
        return min(1.0, max(0.0, (Double(completed) + boundedCurrent) / Double(total)))
    }

    func progressDetail(
        currentTitle: String = "",
        currentItemCompleted: Bool = false,
        titleFormatter: (String) -> String = { $0 }
    ) -> String {
        if total > 1 {
            let visibleCompleted = currentItemCompleted ? completed : min(completed + 1, total)
            let prefix = currentItemCompleted ? "Cloud summary completed" : "Generating cloud summary"
            let item = titleFormatter(currentTitle)
            return item.isEmpty
                ? "\(prefix) \(visibleCompleted)/\(total)"
                : "\(prefix) \(visibleCompleted)/\(total): \(item)"
        }
        return currentItemCompleted ? "Cloud summary completed" : "Generating cloud summary"
    }
}

enum BackgroundSummaryQueueEvent {
    case queued(job: BackgroundSummaryJob, snapshot: BackgroundSummaryQueueSnapshot)
    case started(job: BackgroundSummaryJob, snapshot: BackgroundSummaryQueueSnapshot)
    case output(job: BackgroundSummaryJob, text: String, snapshot: BackgroundSummaryQueueSnapshot)
    case completed(job: BackgroundSummaryJob, snapshot: BackgroundSummaryQueueSnapshot)
    case failed(job: BackgroundSummaryJob, error: Error, snapshot: BackgroundSummaryQueueSnapshot)
    case idle(snapshot: BackgroundSummaryQueueSnapshot)
}

@MainActor
final class BackgroundSummaryQueue {
    typealias Runner = @MainActor (
        BackgroundSummaryJob,
        @escaping @MainActor (String) -> Void
    ) async throws -> Void
    typealias EventHandler = @MainActor (BackgroundSummaryQueueEvent) -> Void

    private let runner: Runner
    private let eventHandler: EventHandler
    private var jobs: [BackgroundSummaryJob] = []
    private var task: Task<Void, Never>?
    private(set) var currentJob: BackgroundSummaryJob?
    private var total = 0
    private var completed = 0

    init(
        runner: @escaping Runner,
        eventHandler: @escaping EventHandler
    ) {
        self.runner = runner
        self.eventHandler = eventHandler
    }

    var snapshot: BackgroundSummaryQueueSnapshot {
        BackgroundSummaryQueueSnapshot(
            total: total,
            completed: completed,
            pending: jobs.count,
            isRunning: task != nil
        )
    }

    var pendingCount: Int {
        jobs.count
    }

    func resetProgress() {
        total = 0
        completed = 0
        currentJob = nil
    }

    @discardableResult
    func cancelPendingJobs() -> Int {
        let cancelledCount = jobs.count
        guard cancelledCount > 0 else { return 0 }
        jobs.removeAll()
        total = completed + (currentJob == nil ? 0 : 1)
        return cancelledCount
    }

    func enqueue(_ job: BackgroundSummaryJob) {
        jobs.append(job)
        total += 1
        eventHandler(.queued(job: job, snapshot: snapshot))
        startIfNeeded()
    }

    private func startIfNeeded() {
        guard task == nil else { return }
        task = Task { [weak self] in
            await self?.drain()
        }
    }

    private func drain() async {
        while !Task.isCancelled, !jobs.isEmpty {
            let job = jobs.removeFirst()
            currentJob = job
            eventHandler(.started(job: job, snapshot: snapshot))
            do {
                try await runner(job) { [weak self] text in
                    guard let self else { return }
                    self.eventHandler(.output(job: job, text: text, snapshot: self.snapshot))
                }
                completeCurrentItem()
                currentJob = nil
                eventHandler(.completed(job: job, snapshot: snapshot))
            } catch {
                completeCurrentItem()
                currentJob = nil
                eventHandler(.failed(job: job, error: error, snapshot: snapshot))
            }
        }
        task = nil
        eventHandler(.idle(snapshot: snapshot))
    }

    private func completeCurrentItem() {
        completed = min(completed + 1, max(total, 1))
    }
}
