@testable import Audio2TextApp
import Foundation
import XCTest

@MainActor
final class JobControllerSubscriptionProgressTests: XCTestCase {
    func testRefreshAllSubscriptionsPublishesSidebarProgressAndRunsEachSubscription() async throws {
        let root = URL(fileURLWithPath: NSTemporaryDirectory()).appendingPathComponent(UUID().uuidString)
        let libraryRoot = try configureLocalTestLibrary(dataRoot: root)
        try writeTestSubscription(
            id: "podcast-rss-a",
            title: "Alpha Show",
            to: libraryRoot.appendingPathComponent("subscriptions/podcast-rss-a.json")
        )
        try writeTestSubscription(
            id: "podcast-rss-b",
            title: "Beta Show",
            to: libraryRoot.appendingPathComponent("subscriptions/podcast-rss-b.json")
        )
        try writeLibraryManifest(root: libraryRoot)

        let runner = SubscriptionProgressProcessRunner()
        let runtime = RuntimeContext(
            dataRoot: root,
            workingDirectory: root.appendingPathComponent("cache"),
            cli: root.appendingPathComponent("Audio2TextCli"),
            environment: ["ATOT_TEST": "1"]
        )
        let controller = JobController(
            settingsStore: AppSettingsStore(dataRoot: root, credentials: MemoryCloudCredentials()),
            runner: runner,
            runtimeProvider: { runtime },
            loadsLibrarySynchronously: true
        )

        await controller.runRefreshSubscriptions(id: nil)

        XCTAssertEqual(
            runner.subscriptionArguments,
            [
                ["refresh", "--limit", "10", "--json", "--id", "podcast-rss-a"],
                ["refresh", "--limit", "10", "--json", "--id", "podcast-rss-b"],
            ]
        )
        XCTAssertEqual(controller.subscriptionRefreshTaskStatus?.id, "subscription-refresh")
        XCTAssertEqual(controller.subscriptionRefreshTaskStatus?.title, "刷新订阅")
        XCTAssertEqual(controller.subscriptionRefreshTaskStatus?.detail, "已刷新 2/2，同步完成")
        XCTAssertEqual(controller.subscriptionRefreshTaskStatus?.fraction, 1.0)
        XCTAssertEqual(controller.subscriptionRefreshTaskStatus?.state, .success)
        XCTAssertEqual(controller.sidebarProcessingTaskStatuses.map(\.id), ["subscription-refresh"])
    }

    func testSubscriptionRefreshProgressIsActiveSidebarProgress() {
        let controller = testJobController()
        controller.subscriptionRefreshTaskStatus = ProcessingTaskStatus(
            kind: .sync,
            id: "subscription-refresh",
            title: "刷新订阅",
            itemTitle: "Alpha Show",
            detail: "正在刷新 1/2",
            fraction: 0.5,
            state: .running
        )

        XCTAssertTrue(controller.hasActiveSidebarModelProgress)
        XCTAssertEqual(controller.sidebarProcessingTaskStatuses.first?.id, "subscription-refresh")
        XCTAssertEqual(controller.sidebarProcessingTaskStatuses.first?.itemTitle, "Alpha Show")
    }

    func testActiveSubscriptionRefreshOverridesOfflineLibraryBadgeStatus() {
        let controller = testJobController()
        controller.librarySyncStatus = .unavailable("Probe reported offline while files are changing.")
        controller.subscriptionRefreshTaskStatus = ProcessingTaskStatus(
            kind: .sync,
            id: "subscription-refresh",
            title: "抓取订阅历史",
            itemTitle: "Alpha Show",
            detail: "正在刷新 1/1",
            fraction: 0.25,
            state: .running
        )

        let status = controller.displayedLibrarySyncStatus

        XCTAssertEqual(status.state, .syncing)
        XCTAssertEqual(status.title, "同步中")
        XCTAssertEqual(status.detail, "正在刷新 1/1")
        XCTAssertEqual(status.progress, 0.25)
    }
}

private final class SubscriptionProgressProcessRunner: ProcessRunning {
    private(set) var subscriptionArguments: [[String]] = []

    func run(
        executable _: URL,
        arguments: [String],
        currentDirectory _: URL,
        environment _: [String: String]?,
        onOutput: @escaping @MainActor (String) -> Void
    ) async throws -> ProcessResult {
        subscriptionArguments.append(Self.subscriptionArguments(from: arguments))
        await onOutput("subscription refreshed\n")
        return ProcessResult(code: 0, output: #"{"results":[],"subscriptions":[]}"#)
    }

    private static func subscriptionArguments(from arguments: [String]) -> [String] {
        guard
            let index = arguments.firstIndex(of: "--request-json"),
            arguments.indices.contains(index + 1),
            let data = arguments[index + 1].data(using: .utf8),
            let request = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
            let params = request["params"] as? [String: Any],
            let subscriptionArguments = params["arguments"] as? [String]
        else {
            return []
        }
        return subscriptionArguments
    }
}

private func writeTestSubscription(id: String, title: String, to url: URL) throws {
    try writeJSON(
        [
            "id": id,
            "title": title,
            "source": "rss",
            "url": "https://example.com/\(id)",
            "feed_url": "https://example.com/\(id)/feed.xml",
            "group_name": "Default",
            "created_at": "2026-06-28T00:00:00Z",
            "last_checked_at": "2026-06-28T00:00:00Z",
        ],
        to: url
    )
}
