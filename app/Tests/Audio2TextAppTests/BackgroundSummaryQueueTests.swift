@testable import Audio2TextApp
import XCTest

@MainActor
final class BackgroundSummaryQueueTests: XCTestCase {
    func testQueueRunsMultipleItemsInOrderAndContinuesAfterFailure() async throws {
        var runnerOrder: [String] = []
        var events: [String] = []
        var finalSnapshot: BackgroundSummaryQueueSnapshot?
        let failingItemID = "one"
        let queue = BackgroundSummaryQueue(
            runner: { job, output in
                runnerOrder.append(job.itemID)
                output("output-\(job.itemID)")
                if job.itemID == failingItemID {
                    throw AppError.cloudSummaryFailed("boom")
                }
            },
            eventHandler: { event in
                switch event {
                case let .queued(job, snapshot):
                    events.append("queued:\(job.itemID):\(snapshot.total):\(snapshot.completed):\(snapshot.pending)")
                case let .started(job, snapshot):
                    events.append("started:\(job.itemID):\(snapshot.total):\(snapshot.completed):\(snapshot.pending)")
                case let .output(job, text, _):
                    events.append("output:\(job.itemID):\(text)")
                case let .completed(job, snapshot):
                    events.append("completed:\(job.itemID):\(snapshot.total):\(snapshot.completed):\(snapshot.pending)")
                case let .failed(job, _, snapshot):
                    events.append("failed:\(job.itemID):\(snapshot.total):\(snapshot.completed):\(snapshot.pending)")
                case let .idle(snapshot):
                    events.append("idle:\(snapshot.total):\(snapshot.completed):\(snapshot.pending):\(snapshot.isRunning)")
                    finalSnapshot = snapshot
                }
            }
        )

        queue.enqueue(testBackgroundSummaryJob(itemID: "one", title: "First"))
        queue.enqueue(testBackgroundSummaryJob(itemID: "two", title: "Second"))

        for _ in 0 ..< 100 where !(finalSnapshot?.isRunning == false && finalSnapshot?.completed == 2) {
            try await Task.sleep(nanoseconds: 10_000_000)
        }

        XCTAssertEqual(runnerOrder, ["one", "two"])
        XCTAssertEqual(
            events,
            [
                "queued:one:1:0:1",
                "queued:two:2:0:2",
                "started:one:2:0:1",
                "output:one:output-one",
                "failed:one:2:1:1",
                "started:two:2:1:0",
                "output:two:output-two",
                "completed:two:2:2:0",
                "idle:2:2:0:false",
            ]
        )
        XCTAssertEqual(finalSnapshot, BackgroundSummaryQueueSnapshot(total: 2, completed: 2, pending: 0, isRunning: false))
    }

    func testQueueSnapshotFormatsBatchProgress() {
        let snapshot = BackgroundSummaryQueueSnapshot(total: 3, completed: 1, pending: 1, isRunning: true)

        XCTAssertEqual(snapshot.overallFraction(currentFraction: 0.5), 0.5, accuracy: 0.001)
        XCTAssertEqual(
            snapshot.progressDetail(currentTitle: "A Long Episode Title", titleFormatter: { String($0.prefix(6)) }),
            "Generating cloud summary 2/3: A Long"
        )
        XCTAssertEqual(
            snapshot.progressDetail(currentTitle: "Done", currentItemCompleted: true),
            "Cloud summary completed 1/3: Done"
        )
    }

    func testCancelPendingJobsLetsCurrentJobFinishAndDropsRest() async throws {
        var startedIDs: [String] = []
        var completedIDs: [String] = []
        var finalSnapshot: BackgroundSummaryQueueSnapshot?
        var releaseFirstJob: CheckedContinuation<Void, Never>?
        let queue = BackgroundSummaryQueue(
            runner: { job, _ in
                startedIDs.append(job.itemID)
                if job.itemID == "one" {
                    await withCheckedContinuation { continuation in
                        releaseFirstJob = continuation
                    }
                }
            },
            eventHandler: { event in
                switch event {
                case let .completed(job, _):
                    completedIDs.append(job.itemID)
                case let .idle(snapshot):
                    finalSnapshot = snapshot
                case .queued, .started, .output, .failed:
                    break
                }
            }
        )

        queue.enqueue(testBackgroundSummaryJob(itemID: "one", title: "First"))
        queue.enqueue(testBackgroundSummaryJob(itemID: "two", title: "Second"))
        queue.enqueue(testBackgroundSummaryJob(itemID: "three", title: "Third"))

        for _ in 0 ..< 100 where releaseFirstJob == nil {
            try await Task.sleep(nanoseconds: 10_000_000)
        }

        XCTAssertEqual(startedIDs, ["one"])
        XCTAssertEqual(queue.cancelPendingJobs(), 2)
        XCTAssertEqual(queue.snapshot, BackgroundSummaryQueueSnapshot(total: 1, completed: 0, pending: 0, isRunning: true))

        releaseFirstJob?.resume()
        for _ in 0 ..< 100 where !(finalSnapshot?.isRunning == false) {
            try await Task.sleep(nanoseconds: 10_000_000)
        }

        XCTAssertEqual(startedIDs, ["one"])
        XCTAssertEqual(completedIDs, ["one"])
        XCTAssertEqual(finalSnapshot, BackgroundSummaryQueueSnapshot(total: 1, completed: 1, pending: 0, isRunning: false))
    }
}

private func testBackgroundSummaryJob(itemID: String, title: String) -> BackgroundSummaryJob {
    let root = URL(fileURLWithPath: NSTemporaryDirectory()).appendingPathComponent(UUID().uuidString)
    var cloudSettings = CloudSettings.load(environment: [:])
    cloudSettings.apiKey = "test-key"
    return BackgroundSummaryJob(
        itemID: itemID,
        title: title,
        outputDirectory: root.appendingPathComponent("work/\(itemID)"),
        runtime: RuntimeContext(
            dataRoot: root,
            workingDirectory: root,
            cli: root.appendingPathComponent("Audio2TextCli"),
            environment: [:]
        ),
        cloudSettings: cloudSettings,
        localState: .success,
        localReason: "Local transcript ready"
    )
}
