@testable import Audio2TextApp
import Audio2TextCore
import XCTest

final class JobControllerSummaryTitleTests: XCTestCase {
    @MainActor
    func testSummaryEditUpdatesSnapshotAndFlushesWithoutFullSnapshotRead() async throws {
        let root = URL(fileURLWithPath: NSTemporaryDirectory())
            .appendingPathComponent(UUID().uuidString)
        let output = root.appendingPathComponent("work/summary-edit", isDirectory: true)
        let documents = root.appendingPathComponent("Audio2TextLibrary/episodes/summary-edit/documents", isDirectory: true)
        try FileManager.default.createDirectory(at: output, withIntermediateDirectories: true)
        try FileManager.default.createDirectory(at: documents, withIntermediateDirectories: true)
        let summaryURL = documents.appendingPathComponent("summary.md")
        try "old summary".write(to: summaryURL, atomically: true, encoding: .utf8)
        let controller = JobController(
            settingsStore: AppSettingsStore(dataRoot: root, credentials: MemoryCloudCredentials()),
            loadsLibrarySynchronously: true
        )
        controller.snapshot = OutputSnapshot(
            outputDirectory: output,
            summaryText: "old summary",
            summarySource: "summary.md",
            summaryURL: summaryURL
        )
        var jsonReadURLs: [URL] = []
        OutputWatcher.jsonReadObserver = { jsonReadURLs.append($0) }
        defer { OutputWatcher.jsonReadObserver = nil }

        controller.saveCurrentSummaryMarkdown("draft summary")

        XCTAssertEqual(controller.snapshot.summaryText, "draft summary")
        XCTAssertEqual(try readText(summaryURL), "old summary")
        XCTAssertTrue(jsonReadURLs.isEmpty)

        await controller.flushPendingSummarySave()

        XCTAssertEqual(try readText(summaryURL), "draft summary")
        XCTAssertTrue(jsonReadURLs.isEmpty)
    }

    @MainActor
    func testPendingSummaryEditSurvivesLibraryRefreshSnapshot() async throws {
        let root = URL(fileURLWithPath: NSTemporaryDirectory())
            .appendingPathComponent(UUID().uuidString)
        let dataRoot = root.appendingPathComponent("data")
        let episode = try writeTestLibraryEpisode(
            dataRoot: dataRoot,
            id: "summary-refresh",
            title: "Summary Refresh",
            documents: ["summary.md": "old library summary", "transcript.md": "transcript"]
        )
        let settingsStore = AppSettingsStore(dataRoot: dataRoot, credentials: MemoryCloudCredentials())
        let controller = JobController(settingsStore: settingsStore, loadsLibrarySynchronously: true)
        let item = try XCTUnwrap(controller.libraryItems.first(where: { $0.id == episode.id }))
        controller.selectLibraryItem(item)

        controller.saveCurrentSummaryMarkdown("draft library summary")
        await controller.refreshLibraryAndWait()

        XCTAssertEqual(controller.snapshot.summaryText, "draft library summary")

        await controller.flushPendingSummarySave()

        XCTAssertEqual(
            try readText(episode.documentsRoot.appendingPathComponent("summary.md")),
            "draft library summary"
        )
    }

    @MainActor
    func testCanGenerateSummaryUsesTranscriptEvenWhenSummaryIsEmpty() throws {
        let root = URL(fileURLWithPath: NSTemporaryDirectory())
            .appendingPathComponent(UUID().uuidString)
        let audio = try writeAudioFile(root.appendingPathComponent("episode.m4a"))
        let item = testLibraryItem(
            id: "empty-summary-\(UUID().uuidString)",
            title: "Empty Summary",
            groupName: "Default",
            audioURL: audio,
            status: "QA pass",
            hasTranscript: false,
            hasOutput: true,
            runStatus: "done",
            modifiedAt: Date()
        )
        try FileManager.default.createDirectory(at: item.outputURL, withIntermediateDirectories: true)
        let documents = root.appendingPathComponent("Audio2TextLibrary/episodes/\(item.id)/documents")
        try FileManager.default.createDirectory(at: documents, withIntermediateDirectories: true)
        try "".write(to: documents.appendingPathComponent("summary.md"), atomically: true, encoding: .utf8)
        try "transcript body".write(
            to: documents.appendingPathComponent("transcript.md"),
            atomically: true,
            encoding: .utf8
        )
        let itemWithDocuments = item.withDocumentsURL(documents)

        let controller = testJobController()
        controller.libraryItems = [itemWithDocuments]

        XCTAssertTrue(controller.canGenerateSummary(for: itemWithDocuments))
    }

    @MainActor
    func testRegenerateSummaryKeepsExistingSummaryWhenCloudKeyMissing() throws {
        let root = URL(fileURLWithPath: NSTemporaryDirectory())
            .appendingPathComponent(UUID().uuidString)
        let audio = try writeAudioFile(root.appendingPathComponent("episode.m4a"))
        let item = testLibraryItem(
            id: "missing-key-\(UUID().uuidString)",
            title: "Missing Key",
            groupName: "Default",
            audioURL: audio,
            status: "QA pass",
            hasTranscript: true,
            hasOutput: true,
            runStatus: "done",
            modifiedAt: Date()
        )
        try FileManager.default.createDirectory(at: item.outputURL, withIntermediateDirectories: true)
        let documents = root.appendingPathComponent("Audio2TextLibrary/episodes/\(item.id)/documents")
        try FileManager.default.createDirectory(at: documents, withIntermediateDirectories: true)
        let summaryURL = documents.appendingPathComponent("summary.md")
        try "existing summary".write(to: summaryURL, atomically: true, encoding: .utf8)
        try "transcript body".write(
            to: documents.appendingPathComponent("transcript.md"),
            atomically: true,
            encoding: .utf8
        )
        let itemWithDocuments = item.withDocumentsURL(documents)

        let settingsStore = AppSettingsStore(dataRoot: root, credentials: MemoryCloudCredentials())
        let controller = JobController(settingsStore: settingsStore, loadsLibrarySynchronously: true)
        controller.libraryItems = [itemWithDocuments]
        controller.selectedLibraryItemID = itemWithDocuments.id
        controller.snapshot = controller.snapshot(for: itemWithDocuments)

        controller.regenerateSummaryDiscardingExisting()

        XCTAssertEqual(try readText(summaryURL), "existing summary")
        XCTAssertTrue(controller.message.contains("API key"))
        XCTAssertEqual(controller.visibleSummaryRequestStatus(for: item)?.state, .failure)
        XCTAssertTrue(controller.visibleSummaryRequestStatus(for: item)?.message.contains("API key") == true)
        XCTAssertEqual(controller.sidebarProcessingTaskStatuses.map(\.kind), [.cloud])
        XCTAssertEqual(controller.sidebarProcessingTaskStatuses.map(\.title), ["Cloud task"])
        XCTAssertEqual(controller.sidebarProcessingTaskStatuses.first?.state, .failure)
        XCTAssertTrue(controller.sidebarProcessingTaskStatuses.first?.detail.contains("API key") == true)
        XCTAssertNil(controller.processingTaskStatus)
    }

    @MainActor
    func testCanRegenerateTitleRequiresCloudSummary() throws {
        let root = URL(fileURLWithPath: NSTemporaryDirectory())
            .appendingPathComponent(UUID().uuidString)
        let audio = try writeAudioFile(root.appendingPathComponent("episode.m4a"))
        let item = testLibraryItem(
            id: "title-\(UUID().uuidString)",
            title: "Title",
            groupName: "Default",
            audioURL: audio,
            status: "QA pass",
            hasTranscript: true,
            hasOutput: true,
            runStatus: "done",
            modifiedAt: Date()
        )
        try FileManager.default.createDirectory(at: item.outputURL, withIntermediateDirectories: true)
        try "root summary".write(to: item.outputURL.appendingPathComponent("summary.md"), atomically: true, encoding: .utf8)
        let controller = testJobController()

        XCTAssertFalse(controller.canRegenerateTitle(for: item))

        try FileManager.default.createDirectory(at: item.outputURL.appendingPathComponent("cloud"), withIntermediateDirectories: true)
        try "cloud summary".write(to: item.outputURL.appendingPathComponent("cloud/summary.md"), atomically: true, encoding: .utf8)

        XCTAssertTrue(controller.canRegenerateTitle(for: item))
    }

    @MainActor
    func testCanRegenerateTitleUsesLibrarySummaryWhenAudioIsMissing() throws {
        let root = URL(fileURLWithPath: NSTemporaryDirectory())
            .appendingPathComponent(UUID().uuidString)
        let audio = root.appendingPathComponent("missing-audio.m4a")
        let item = testLibraryItem(
            id: "title-docs-\(UUID().uuidString)",
            title: "Title From Documents",
            groupName: "Default",
            audioURL: audio,
            status: "QA pass",
            hasFile: false,
            hasProcessed: true,
            hasTranscript: true,
            hasOutput: true,
            runStatus: "done",
            modifiedAt: Date()
        )
        let documents = root.appendingPathComponent("Audio2TextLibrary/episodes/\(item.id)/documents")
        try FileManager.default.createDirectory(at: documents, withIntermediateDirectories: true)
        try "library summary for title".write(to: documents.appendingPathComponent("summary.md"), atomically: true, encoding: .utf8)
        let itemWithDocuments = item.withDocumentsURL(documents)
        let controller = testJobController()
        controller.libraryItems = [itemWithDocuments]

        XCTAssertFalse(ProcessLibrary.isExistingNonEmptyFile(audio))
        XCTAssertTrue(controller.canRegenerateTitle(for: itemWithDocuments))

        try controller.prepareSummaryForTitleGeneration(for: itemWithDocuments)

        XCTAssertEqual(
            try readText(itemWithDocuments.outputURL.appendingPathComponent("cloud/summary.md")),
            "library summary for title"
        )
    }

    @MainActor
    func testRegenerateTitleUsesCloudTaskStatusWhenCloudKeyMissing() throws {
        let root = URL(fileURLWithPath: NSTemporaryDirectory())
            .appendingPathComponent(UUID().uuidString)
        let audio = try writeAudioFile(root.appendingPathComponent("episode.m4a"))
        let item = testLibraryItem(
            id: "title-cloud-task-\(UUID().uuidString)",
            title: "Title Cloud Task",
            groupName: "Default",
            audioURL: audio,
            status: "QA pass",
            hasTranscript: true,
            hasOutput: true,
            runStatus: "done",
            modifiedAt: Date()
        )
        try FileManager.default.createDirectory(at: item.outputURL.appendingPathComponent("cloud"), withIntermediateDirectories: true)
        try "cloud summary".write(to: item.outputURL.appendingPathComponent("cloud/summary.md"), atomically: true, encoding: .utf8)
        let settingsStore = AppSettingsStore(dataRoot: root, credentials: MemoryCloudCredentials())
        let controller = JobController(settingsStore: settingsStore, loadsLibrarySynchronously: true)

        controller.regenerateTitle(for: item)

        XCTAssertNil(controller.processingTaskStatus)
        XCTAssertEqual(controller.sidebarProcessingTaskStatuses.map(\.kind), [.cloud])
        XCTAssertEqual(controller.sidebarProcessingTaskStatuses.first?.title, "Cloud task")
        XCTAssertEqual(controller.sidebarProcessingTaskStatuses.first?.state, .failure)
        XCTAssertTrue(controller.sidebarProcessingTaskStatuses.first?.detail.contains("API key") == true)
    }

    @MainActor
    func testBatchRegenerateTitlesUsesCloudTaskStatusWhenCloudKeyMissing() throws {
        let root = URL(fileURLWithPath: NSTemporaryDirectory())
            .appendingPathComponent(UUID().uuidString)
        let audio = try writeAudioFile(root.appendingPathComponent("episode.m4a"))
        let item = testLibraryItem(
            id: "batch-title-cloud-task-\(UUID().uuidString)",
            title: "Batch Title Cloud Task",
            groupName: "Default",
            audioURL: audio,
            status: "QA pass",
            hasTranscript: true,
            hasOutput: true,
            runStatus: "done",
            modifiedAt: Date()
        )
        let settingsStore = AppSettingsStore(dataRoot: root, credentials: MemoryCloudCredentials())
        let controller = JobController(settingsStore: settingsStore, loadsLibrarySynchronously: true)

        controller.regenerateTitles(for: [item])

        XCTAssertNil(controller.processingTaskStatus)
        XCTAssertEqual(controller.sidebarProcessingTaskStatuses.map(\.kind), [.cloud])
        XCTAssertEqual(controller.sidebarProcessingTaskStatuses.first?.title, "Cloud task")
        XCTAssertEqual(controller.sidebarProcessingTaskStatuses.first?.state, .failure)
        XCTAssertTrue(controller.sidebarProcessingTaskStatuses.first?.detail.contains("API key") == true)
    }

    @MainActor
    func testSidebarProgressTreatsRunningCloudSummaryAsActiveAfterLocalCompletion() {
        let controller = testJobController()
        controller.stage = .summarizing
        controller.snapshot.runStatus = "done"
        controller.snapshot.qaStatus = "pass"
        controller.snapshot.cloudStatus = "running"
        controller.snapshot.cloudStage = "episode_summary"
        controller.snapshot.cloudProgressFraction = 0.7

        XCTAssertTrue(controller.hasActiveSidebarModelProgress)
        XCTAssertEqual(controller.sidebarProcessingTaskStatuses.map(\.title), ["Process", "Cloud task"])
        XCTAssertEqual(controller.sidebarProcessingTaskStatuses.map(\.kind), [.processing, .cloud])
        XCTAssertEqual(controller.sidebarProcessingTaskStatuses.map(\.state), [.success, .running])
        XCTAssertEqual(controller.sidebarProcessingTaskStatuses.last?.detail, "Summarizing episode")
    }

    @MainActor
    func testSidebarProgressKeepsLocalWarningWhenCloudSummaryRunsAfterQAFailure() {
        let controller = testJobController()
        controller.stage = .summarizing
        controller.snapshot.runStatus = "done"
        controller.snapshot.qaStatus = "fail"
        controller.snapshot.cloudStatus = "running"
        controller.snapshot.cloudStage = "episode_summary"
        controller.snapshot.cloudProgressFraction = 0.7

        XCTAssertEqual(controller.sidebarProcessingTaskStatuses.map(\.title), ["Process", "Cloud task"])
        XCTAssertEqual(controller.sidebarProcessingTaskStatuses.map(\.kind), [.processing, .cloud])
        XCTAssertEqual(controller.sidebarProcessingTaskStatuses.map(\.state), [.warning, .running])
        XCTAssertEqual(controller.sidebarProcessingTaskStatuses.first?.detail, "Transcription completed; review QA")
    }

    @MainActor
    func testProcessingWorkflowCapabilityRequiresCloudOnlyForSummary() throws {
        let root = URL(fileURLWithPath: NSTemporaryDirectory()).appendingPathComponent(UUID().uuidString)

        let settingsStore = AppSettingsStore(dataRoot: root, credentials: MemoryCloudCredentials())
        let controller = JobController(settingsStore: settingsStore, loadsLibrarySynchronously: true)
        let item = try testLibraryItem(
            id: "workflow-\(UUID().uuidString)",
            title: "Workflow",
            groupName: "Default",
            audioURL: writeAudioFile(root.appendingPathComponent("workflow.m4a")),
            status: "Not processed",
            modifiedAt: Date()
        )

        XCTAssertFalse(controller.isCloudSummaryConfigured)
        XCTAssertTrue(controller.canProcessLibraryItem(item, workflow: .localOnly))
        XCTAssertFalse(controller.canProcessLibraryItem(item, workflow: .transcribeAndSummarize))

        var settings = AppSettings()
        settings.apiBase = "https://api.example/v1"
        settings.apiKey = "test-key"
        try settingsStore.save(settings, environment: [:])

        XCTAssertTrue(controller.isCloudSummaryConfigured)
        XCTAssertTrue(controller.canProcessLibraryItem(item, workflow: .localOnly))
        XCTAssertTrue(controller.canProcessLibraryItem(item, workflow: .transcribeAndSummarize))
    }
}
