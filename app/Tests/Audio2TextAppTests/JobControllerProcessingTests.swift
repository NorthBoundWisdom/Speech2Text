@testable import Audio2TextApp
import Audio2TextCore
import XCTest

@MainActor
final class JobControllerProcessingTests: XCTestCase {
    func testDefaultProcessingWithoutAPIKeyNeverQueuesCloudSummary() async throws {
        let fixture = try ProcessingControllerFixture()
        let runner = WorkflowProcessRunner()
        let controller = fixture.controller(runner: runner)
        let item = try fixture.item(title: "Agent Summary Workflow")
        XCTAssertFalse(controller.isCloudSummaryConfigured)

        controller.processLibraryItem(item)

        try await waitForProcessingCondition("default local processing completes") {
            controller.processingReport != nil && !controller.stage.isRunning
        }
        XCTAssertEqual(runner.methods.filter { $0 != "sync" }, ["transcribe", "qa"])
        XCTAssertNil(controller.cloudProcessingTaskStatus)
    }

    func testLocalOnlyQAFailureFinishesAsWarningWithoutCloudSummary() async throws {
        let fixture = try ProcessingControllerFixture()
        let runner = WorkflowProcessRunner()
        let controller = fixture.controller(runner: runner)
        let item = try fixture.item(title: "Local Only Warning")

        controller.processLibraryItem(item, workflow: .localOnly)

        try await waitForProcessingCondition("local-only warning completes") {
            controller.processingReport?.title == "本地转写完成，QA 需复查"
        }
        XCTAssertEqual(runner.methods.filter { $0 != "sync" }, ["transcribe", "qa"])
        XCTAssertEqual(controller.processingTaskStatus?.state, .warning)
        XCTAssertEqual(controller.cloudProcessingTaskStatus, nil)
        XCTAssertEqual(controller.processingReport?.items.first?.reason.hasPrefix("QA failed"), true)
    }

    func testSummaryWorkflowQueuesCloudSummaryAfterQAFailureWarning() async throws {
        let fixture = try ProcessingControllerFixture(configureCloud: true)
        let runner = WorkflowProcessRunner()
        let controller = fixture.controller(runner: runner)
        let item = try fixture.item(title: "Warning With Summary")

        controller.processLibraryItem(item, workflow: .transcribeAndSummarize)

        try await waitForProcessingCondition("cloud summary completes after qa warning", timeout: 2) {
            controller.processingReport?.items.contains { $0.id == "\(item.id)-cloud" } == true
        }
        XCTAssertEqual(runner.methods.filter { $0 != "sync" }, ["transcribe", "qa", "cloud_prepare", "cloud_summarize"])
        XCTAssertFalse(runner.methods.contains("sync"))
        XCTAssertEqual(controller.processingTaskStatus?.state, .warning)
        XCTAssertEqual(controller.cloudProcessingTaskStatus?.state, .success)
        XCTAssertEqual(controller.processingReport?.title, "处理完成，需复查")
        XCTAssertTrue(controller.processingReport?.detail.contains("本地：QA failed") == true)
        XCTAssertTrue(controller.processingReport?.detail.contains("云：Cloud summary completed") == true)
    }

    func testSummaryWorkflowTreatsFailedCloudPayloadAsFailure() async throws {
        let fixture = try ProcessingControllerFixture(configureCloud: true)
        let runner = WorkflowProcessRunner(cloudSummaryBehavior: .failedPayload)
        let controller = fixture.controller(runner: runner)
        let item = try fixture.item(title: "Failed Cloud Payload")

        controller.processLibraryItem(item, workflow: .transcribeAndSummarize)

        try await waitForProcessingCondition("cloud summary failed from payload", timeout: 2) {
            controller.processingReport?.items.first { $0.id == "\(item.id)-cloud" }?.state == .failure
        }
        XCTAssertEqual(runner.methods.filter { $0 != "sync" }, ["transcribe", "qa", "cloud_prepare", "cloud_summarize"])
        XCTAssertFalse(runner.methods.contains("sync"))
        XCTAssertEqual(controller.cloudProcessingTaskStatus?.state, .failure)
        XCTAssertTrue(controller.cloudProcessingTaskStatus?.detail.contains("Cloud chunk summaries failed") == true)
        XCTAssertTrue(controller.cloudProcessingTaskStatus?.detail.contains("Cloud responses API response has no text content.") == true)
        XCTAssertEqual(controller.processingReport?.title, "处理部分完成")
        XCTAssertTrue(controller.processingReport?.detail.contains("Cloud chunk summaries failed") == true)
        XCTAssertTrue(controller.processingReport?.detail.contains("Cloud responses API response has no text content.") == true)
        XCTAssertFalse(FileManager.default.fileExists(atPath: item.outputURL.appendingPathComponent("cloud/summary.md").path))
    }

    func testProcessingRequestClearsStaleCloudFailureImmediately() throws {
        let fixture = try ProcessingControllerFixture()
        let runner = WorkflowProcessRunner()
        let controller = fixture.controller(runner: runner)
        let failedCloudItem = try fixture.item(title: "Old Failed Cloud")
        let cloud = failedCloudItem.outputURL.appendingPathComponent("cloud")
        try FileManager.default.createDirectory(at: cloud, withIntermediateDirectories: true)
        try "summary".write(to: cloud.appendingPathComponent("summary.md"), atomically: true, encoding: .utf8)
        let nextItem = try fixture.item(title: "Next Local Task")

        controller.regenerateTitle(for: failedCloudItem)
        XCTAssertEqual(controller.cloudProcessingTaskStatus?.state, .failure)

        controller.processLibraryItem(nextItem, workflow: .localOnly)

        XCTAssertNil(controller.cloudProcessingTaskStatus)
        XCTAssertNil(controller.processingTaskStatus)
    }

    func testManualSummaryProgressKeepsCurrentRunOverStaleCloudFailure() throws {
        let fixture = try ProcessingControllerFixture()
        let runner = WorkflowProcessRunner()
        let controller = fixture.controller(runner: runner)
        let item = try fixture.item(title: "Retry Cloud Summary")
        try fixture.writeStaleCloudSummaryFailure(
            for: item,
            message: "Cloud chunk summaries failed: chunk_0001.summary.json"
        )

        controller.beginCloudOnlyTask(
            itemTitle: "Retry Cloud",
            detail: "准备请求云总结",
            state: .queued
        )
        controller.refreshManualSummaryProgress(
            for: item,
            fallbackDetail: "正在请求云总结",
            fallbackFraction: 0.25
        )

        XCTAssertEqual(controller.cloudProcessingTaskStatus?.state, .running)
        XCTAssertEqual(controller.cloudProcessingTaskStatus?.detail, "正在请求云总结")
    }

    func testBackgroundSummaryProgressKeepsCurrentRunOverStaleCloudFailure() throws {
        let fixture = try ProcessingControllerFixture(configureCloud: true)
        let runner = WorkflowProcessRunner()
        let controller = fixture.controller(runner: runner)
        let item = try fixture.item(title: "Queued Cloud Retry")
        try fixture.writeStaleCloudSummaryFailure(for: item, message: "old cloud failure")
        let job = fixture.backgroundSummaryJob(for: item)

        controller.handleBackgroundSummaryQueueEvent(
            .output(
                job: job,
                text: "starting summary",
                snapshot: BackgroundSummaryQueueSnapshot(total: 1, completed: 0, pending: 0, isRunning: true)
            )
        )

        XCTAssertEqual(controller.cloudProcessingTaskStatus?.state, .running)
        XCTAssertEqual(controller.cloudProcessingTaskStatus?.detail, "云总结处理中")
        XCTAssertFalse(controller.cloudProcessingTaskStatus?.detail.contains("old cloud failure") == true)
    }

    func testManualLibraryRefreshDoesNotRunStandaloneSyncCommands() async throws {
        let fixture = try ProcessingControllerFixture()
        _ = try fixture.configureLocalLibrary()
        let runner = WorkflowProcessRunner()
        let controller = fixture.controller(runner: runner)

        await controller.refreshLibraryNow().value

        XCTAssertEqual(controller.libraryRefreshMessage, "Library refreshed")
        XCTAssertFalse(runner.methods.contains("sync"))
    }

    func testLibraryRootUsesConfiguredLocalRoot() throws {
        let fixture = try ProcessingControllerFixture()
        let customRoot = fixture.root.appendingPathComponent("custom-library-root")
        var settings = AppSettings()
        settings.libraryStorage = "local"
        settings.libraryLocalRoot = customRoot.path
        try fixture.settingsStore.save(settings, environment: [:])

        XCTAssertEqual(
            fixture.settingsStore.libraryRoot().path,
            customRoot.appendingPathComponent("Audio2TextLibrary").path
        )
    }

    func testLibraryRefreshAfterProcessingDoesNotRunStandaloneSyncCommands() async throws {
        let fixture = try ProcessingControllerFixture()
        _ = try fixture.configureLocalLibrary()
        let runner = WorkflowProcessRunner()
        let controller = fixture.controller(runner: runner)

        await controller.refreshLibraryAfterProcessing(runtime: fixture.runtime)

        XCTAssertFalse(runner.methods.contains("sync"))
    }

    func testRunTitleCommandPublishesCanonicalTitle() async throws {
        let fixture = try ProcessingControllerFixture()
        let runner = WorkflowProcessRunner()
        let controller = fixture.controller(runner: runner)
        let libraryRoot = try fixture.configureLocalLibrary()
        let episodeID = "episode-title"
        let episodeRoot = libraryRoot.appendingPathComponent("episodes/\(episodeID)", isDirectory: true)
        let recordURL = episodeRoot.appendingPathComponent("episode.json")
        let outputDirectory = fixture.dataRoot.appendingPathComponent("work/\(episodeID)", isDirectory: true)
        try FileManager.default.createDirectory(at: episodeRoot, withIntermediateDirectories: true)
        try writeJSONObject(
            [
                "schema_version": 1,
                "kind": "audio2text.library.episode",
                "episode_id": episodeID,
                "title": "旧标题",
                "documents": [],
            ],
            to: recordURL
        )
        try LibraryWriter.rebuildManifest(libraryRoot: libraryRoot)

        try await controller.runTitleCommand(
            outputDirectory: outputDirectory,
            runtime: fixture.runtime,
            cloudSettings: CloudSettings.load(environment: [:])
        )
        let record = try readJSONObject(recordURL)

        XCTAssertEqual(runner.methods, ["cloud_title"])
        XCTAssertEqual(record["title"] as? String, "重新生成的标题")
    }
}

private struct ProcessingControllerFixture {
    let root: URL
    let dataRoot: URL
    let runtime: RuntimeContext
    let settingsStore: AppSettingsStore

    init(configureCloud: Bool = false) throws {
        root = URL(fileURLWithPath: NSTemporaryDirectory()).appendingPathComponent(UUID().uuidString)
        dataRoot = root.appendingPathComponent("data")
        runtime = RuntimeContext(
            dataRoot: dataRoot,
            workingDirectory: dataRoot.appendingPathComponent("cache"),
            cli: root.appendingPathComponent("Audio2TextCli"),
            environment: ["ATOT_TEST": "1"]
        )
        settingsStore = AppSettingsStore(dataRoot: dataRoot, credentials: MemoryCloudCredentials())
        try FileManager.default.createDirectory(at: runtime.workingDirectory, withIntermediateDirectories: true)
        var settings = AppSettings()
        settings.libraryStorage = "local"
        try settingsStore.save(settings, environment: [:])
        if configureCloud {
            settings.apiBase = "https://api.example/v1"
            settings.apiKey = "test-key"
            try settingsStore.save(settings, environment: [:])
        }
    }

    func configureLocalLibrary() throws -> URL {
        try FileManager.default.createDirectory(at: dataRoot, withIntermediateDirectories: true)
        try """
        [library]
        storage = "local"
        icloud_root = ""
        local_root = ""
        """.write(to: dataRoot.appendingPathComponent("config.toml"), atomically: true, encoding: .utf8)
        return dataRoot.appendingPathComponent("Audio2TextLibrary", isDirectory: true)
    }

    @MainActor
    func controller(runner: WorkflowProcessRunner) -> JobController {
        JobController(
            settingsStore: settingsStore,
            runner: runner,
            runtimeProvider: { runtime },
            loadsLibrarySynchronously: true
        )
    }

    func item(title: String) throws -> ProcessLibraryItem {
        let audioURL = root.appendingPathComponent("\(UUID().uuidString).m4a")
        try FileManager.default.createDirectory(at: audioURL.deletingLastPathComponent(), withIntermediateDirectories: true)
        try Data("audio".utf8).write(to: audioURL)
        return ProcessLibraryItem(
            id: audioURL.path,
            title: title,
            groupName: ProcessLibrary.defaultGroupName,
            nodeStatus: .import,
            audioURL: audioURL,
            outputURL: dataRoot.appendingPathComponent("work/\(UUID().uuidString)"),
            status: "Not processed",
            detail: "",
            hasFile: true,
            hasProcessed: false,
            hasTranscript: false,
            hasOutput: false,
            runStatus: "missing",
            source: "local",
            sourceURL: nil,
            subscriptionID: nil,
            seriesURL: nil,
            mediaURL: nil,
            originalPath: nil,
            originalBookmark: nil,
            isRead: false,
            isStarred: false,
            queueStatus: .unread,
            modifiedAt: Date()
        )
    }

    func backgroundSummaryJob(for item: ProcessLibraryItem) -> BackgroundSummaryJob {
        BackgroundSummaryJob(
            itemID: item.id,
            title: item.title,
            outputDirectory: item.outputURL,
            runtime: runtime,
            cloudSettings: settingsStore.cloudSettings(environment: runtime.environment),
            localState: .success,
            localReason: "Local transcript ready"
        )
    }

    func writeStaleCloudSummaryFailure(for item: ProcessLibraryItem, message: String) throws {
        let details = item.outputURL
        let input = item.outputURL.appendingPathComponent("cloud/input")
        let chunks = input.appendingPathComponent("chunks")
        let summaries = item.outputURL.appendingPathComponent("cloud/chunk_summaries")
        try FileManager.default.createDirectory(at: details, withIntermediateDirectories: true)
        try FileManager.default.createDirectory(at: chunks, withIntermediateDirectories: true)
        try FileManager.default.createDirectory(at: summaries, withIntermediateDirectories: true)
        try "transcript".write(
            to: details.appendingPathComponent("transcript.timestamped.md"),
            atomically: true,
            encoding: .utf8
        )
        try "chunk".write(
            to: chunks.appendingPathComponent("chunk_0001.md"),
            atomically: true,
            encoding: .utf8
        )
        try #"{"text_chunks":["chunks/chunk_0001.md"]}"#.write(
            to: input.appendingPathComponent("manifest.json"),
            atomically: true,
            encoding: .utf8
        )
        try """
        {
          "success": true,
          "chunks": [{}],
          "chunk_status_counts": {"transcribed": 1},
          "cloud": {
            "summary_state": "failed",
            "summary_stage": "chunk_summaries",
            "error": "\(message)"
          }
        }
        """.write(to: details.appendingPathComponent("run.json"), atomically: true, encoding: .utf8)
        try """
        {
          "success": false,
          "source": "failed",
          "retry": {
            "error": "\(message)"
          }
        }
        """.write(
            to: summaries.appendingPathComponent("chunk_0001.summary.json"),
            atomically: true,
            encoding: .utf8
        )
    }
}

private final class WorkflowProcessRunner: ProcessRunning {
    enum CloudSummaryBehavior {
        case success
        case failedPayload
    }

    private let cloudSummaryBehavior: CloudSummaryBehavior
    private(set) var methods: [String] = []

    init(cloudSummaryBehavior: CloudSummaryBehavior = .success) {
        self.cloudSummaryBehavior = cloudSummaryBehavior
    }

    func run(
        executable _: URL,
        arguments: [String],
        currentDirectory _: URL,
        environment _: [String: String]?,
        onOutput: @escaping @MainActor (String) -> Void
    ) async throws -> ProcessResult {
        let request = serviceRequest(arguments)
        let method = request.method ?? "unknown"
        methods.append(method)
        switch method {
        case "transcribe":
            try writeTranscriptionOutputs(outputDirectory: request.urlParam("job_dir"))
            await onOutput("transcribed\n")
            return ProcessResult(code: 0, output: "transcribed")
        case "qa":
            try writeQAReport(outputDirectory: request.urlParam("output"))
            throw AppError.processFailed(command: "qa", code: 2, output: "Status: FAIL\nQA issues")
        case "cloud_prepare":
            try writeCloudInput(outputDirectory: request.urlParam("output"))
            await onOutput("prepared cloud input\n")
            return ProcessResult(code: 0, output: "prepared")
        case "cloud_summarize":
            if cloudSummaryBehavior == .failedPayload {
                try writeFailedCloudChunkSummary(outputDirectory: request.urlParam("output"))
                let output = """
                {
                  "id": null,
                  "ok": false,
                  "error": {
                    "message": "Cloud chunk summaries failed: chunk_0001.summary.json, chunk_0002.summary.json",
                    "type": "RuntimeError"
                  }
                }
                """
                await onOutput(output)
                return ProcessResult(code: 0, output: output)
            }
            try writeCloudSummary(outputDirectory: request.urlParam("output"))
            await onOutput("summarized\n")
            return ProcessResult(code: 0, output: "summarized")
        case "cloud_title":
            try writeCloudTitle(outputDirectory: request.urlParam("output"))
            await onOutput("title\n")
            return ProcessResult(code: 0, output: "title")
        default:
            return ProcessResult(code: 0, output: method)
        }
    }

    private func serviceRequest(_ arguments: [String]) -> WorkflowServiceRequest {
        guard
            let index = arguments.firstIndex(of: "--request-json"),
            arguments.indices.contains(index + 1),
            let data = arguments[index + 1].data(using: .utf8),
            let request = try? JSONSerialization.jsonObject(with: data) as? [String: Any]
        else {
            return WorkflowServiceRequest(method: nil, params: [:])
        }
        return WorkflowServiceRequest(
            method: request["method"] as? String,
            params: request["params"] as? [String: Any] ?? [:]
        )
    }

    private func writeTranscriptionOutputs(outputDirectory: URL) throws {
        let details = outputDirectory
        try FileManager.default.createDirectory(at: details, withIntermediateDirectories: true)
        try "transcript".write(
            to: details.appendingPathComponent("transcript.timestamped.md"),
            atomically: true,
            encoding: .utf8
        )
        try #"{"success":true,"chunks":[{}],"chunk_status_counts":{"transcribed":1}}"#.write(
            to: details.appendingPathComponent("run.json"),
            atomically: true,
            encoding: .utf8
        )
    }

    private func writeQAReport(outputDirectory: URL) throws {
        let details = outputDirectory
        try FileManager.default.createDirectory(at: details, withIntermediateDirectories: true)
        try #"{"success":false,"summary":{"issue_count":3,"blocking_issue_count":1,"repair_window_count":1}}"#.write(
            to: details.appendingPathComponent("qa.json"),
            atomically: true,
            encoding: .utf8
        )
    }

    private func writeCloudInput(outputDirectory: URL) throws {
        let input = outputDirectory.appendingPathComponent("cloud/input")
        let chunks = input.appendingPathComponent("chunks")
        try FileManager.default.createDirectory(at: chunks, withIntermediateDirectories: true)
        try "transcript".write(to: input.appendingPathComponent("transcript.for_cloud.md"), atomically: true, encoding: .utf8)
        try "chunk".write(to: chunks.appendingPathComponent("chunk_0001.md"), atomically: true, encoding: .utf8)
        try #"{"text_chunks":["chunks/chunk_0001.md"]}"#.write(
            to: input.appendingPathComponent("manifest.json"),
            atomically: true,
            encoding: .utf8
        )
    }

    private func writeCloudSummary(outputDirectory: URL) throws {
        let cloud = outputDirectory.appendingPathComponent("cloud")
        try FileManager.default.createDirectory(at: cloud, withIntermediateDirectories: true)
        try "summary".write(to: cloud.appendingPathComponent("summary.md"), atomically: true, encoding: .utf8)
    }

    private func writeCloudTitle(outputDirectory: URL) throws {
        let cloud = outputDirectory.appendingPathComponent("cloud")
        try FileManager.default.createDirectory(at: cloud, withIntermediateDirectories: true)
        try "重新生成的标题\n".write(to: cloud.appendingPathComponent("short_title.txt"), atomically: true, encoding: .utf8)
    }

    private func writeFailedCloudChunkSummary(outputDirectory: URL) throws {
        let chunks = outputDirectory.appendingPathComponent("cloud/chunk_summaries")
        try FileManager.default.createDirectory(at: chunks, withIntermediateDirectories: true)
        try """
        {
          "success": false,
          "chunk": 1,
          "summary": "",
          "source": "failed",
          "retry": {
            "error": "Cloud responses API response has no text content."
          }
        }
        """.write(to: chunks.appendingPathComponent("chunk_0001.summary.json"), atomically: true, encoding: .utf8)
    }
}

private func readJSONObject(_ url: URL) throws -> [String: Any] {
    let data = try Data(contentsOf: url)
    return try XCTUnwrap(JSONSerialization.jsonObject(with: data) as? [String: Any])
}

private func writeJSONObject(_ object: [String: Any], to url: URL) throws {
    try FileManager.default.createDirectory(at: url.deletingLastPathComponent(), withIntermediateDirectories: true)
    let data = try JSONSerialization.data(withJSONObject: object, options: [.prettyPrinted, .sortedKeys])
    try data.write(to: url, options: .atomic)
}

private struct WorkflowServiceRequest {
    let method: String?
    let params: [String: Any]

    func urlParam(_ key: String) -> URL {
        URL(fileURLWithPath: params[key] as? String ?? NSTemporaryDirectory())
    }
}

@MainActor
private func waitForProcessingCondition(
    _ description: String,
    timeout: TimeInterval = 1,
    condition: @escaping () -> Bool
) async throws {
    let deadline = Date().addingTimeInterval(timeout)
    while Date() < deadline {
        if condition() {
            return
        }
        try await Task.sleep(nanoseconds: 10_000_000)
    }
    XCTFail(description)
}
