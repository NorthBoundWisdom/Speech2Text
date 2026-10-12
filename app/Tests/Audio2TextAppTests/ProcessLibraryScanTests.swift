@testable import Audio2TextApp
import Audio2TextCore
import XCTest

final class ProcessLibraryScanTests: XCTestCase {
    func testProcessLibraryScansAudioAndStatus() throws {
        let root = URL(fileURLWithPath: NSTemporaryDirectory())
            .appendingPathComponent(UUID().uuidString)
        let dataRoot = root.appendingPathComponent("data")
        let episode = try writeTestLibraryEpisode(
            dataRoot: dataRoot,
            id: "show",
            title: "测试节目",
            metadata: ["source": "manual"],
            documents: ["transcript.md": "转写文字"]
        )
        let details = episode.workRoot
        try FileManager.default.createDirectory(at: details, withIntermediateDirectories: true)
        try #"{"success":true,"chunks":[{}],"chunk_status_counts":{"transcribed":1}}"#.write(
            to: details.appendingPathComponent("run.json"),
            atomically: true,
            encoding: .utf8
        )
        try #"{"success":true}"#.write(to: details.appendingPathComponent("qa.json"), atomically: true, encoding: .utf8)
        try "转写文字".write(to: details.appendingPathComponent("transcript.timestamped.md"), atomically: true, encoding: .utf8)

        let items = ProcessLibrary.scan(dataRoot: dataRoot)

        XCTAssertEqual(items.count, 1)
        XCTAssertEqual(items[0].title, "测试节目")
        XCTAssertEqual(items[0].groupName, "Default")
        XCTAssertEqual(items[0].status, "QA pass")
        XCTAssertEqual(items[0].detail, "Chunks 1/1")
        XCTAssertTrue(items[0].hasTranscript)
        XCTAssertTrue(items[0].hasFile)
        XCTAssertTrue(items[0].hasProcessed)
        XCTAssertNotNil(items[0].processedAt)
        XCTAssertEqual(items[0].nodeStatus, .outside)
        XCTAssertFalse(items[0].isRead)
        XCTAssertFalse(items[0].isStarred)
        XCTAssertEqual(items[0].queueStatus, .unread)
    }

    func testProcessLibraryScanReadsOriginalTitle() throws {
        let root = URL(fileURLWithPath: NSTemporaryDirectory())
            .appendingPathComponent(UUID().uuidString)
        let dataRoot = root.appendingPathComponent("data")
        try writeTestLibraryEpisode(
            dataRoot: dataRoot,
            id: "episode-with-original-title",
            title: "AI 短标题",
            metadata: ["original_title": "来自订阅源的原始节目标题"],
            documents: ["summary.md": "summary"]
        )

        let item = try XCTUnwrap(ProcessLibrary.scan(dataRoot: dataRoot).first { $0.id == "episode-with-original-title" })

        XCTAssertEqual(item.title, "AI 短标题")
        XCTAssertEqual(item.originalTitle, "来自订阅源的原始节目标题")
    }

    func testProcessLibraryWritesIndexAndInvalidatesAfterAppStateChange() throws {
        let root = URL(fileURLWithPath: NSTemporaryDirectory())
            .appendingPathComponent(UUID().uuidString)
        let dataRoot = root.appendingPathComponent("data")
        let indexURL = dataRoot.appendingPathComponent("cache/library.index.json")
        try writeTestLibraryEpisode(dataRoot: dataRoot, id: "show", title: "索引节目")

        let item = try XCTUnwrap(ProcessLibrary.scan(dataRoot: dataRoot).first)

        XCTAssertTrue(FileManager.default.fileExists(atPath: indexURL.path))

        try ProcessLibrary.updateRead(true, for: item)

        XCTAssertFalse(FileManager.default.fileExists(atPath: indexURL.path))

        let updated = try XCTUnwrap(ProcessLibrary.scan(dataRoot: dataRoot).first)

        XCTAssertTrue(updated.isRead)
        XCTAssertTrue(FileManager.default.fileExists(atPath: indexURL.path))
    }

    func testProcessLibraryScansMetadataBeforeAudioDownload() throws {
        let root = URL(fileURLWithPath: NSTemporaryDirectory())
            .appendingPathComponent(UUID().uuidString)
        let dataRoot = root.appendingPathComponent("data")
        try writeTestLibraryEpisode(
            dataRoot: dataRoot,
            id: "show",
            title: "元信息已存在",
            metadata: [
                "app_group": "科技",
                "audio_url": "https://media.example/show.m4a",
                "source": "xiaoyuzhou",
                "source_url": "https://www.xiaoyuzhoufm.com/episode/test",
            ],
            audioContents: nil
        )

        let items = ProcessLibrary.scan(dataRoot: dataRoot)

        XCTAssertEqual(items.count, 1)
        XCTAssertEqual(items[0].title, "元信息已存在")
        XCTAssertEqual(items[0].groupName, "科技")
        XCTAssertEqual(items[0].status, "Audio pending")
        XCTAssertEqual(items[0].detail, "Metadata exists")
        XCTAssertFalse(items[0].isAudioPresent)
        XCTAssertFalse(items[0].hasFile)
        XCTAssertFalse(items[0].hasProcessed)
        XCTAssertNil(items[0].processedAt)
        XCTAssertEqual(items[0].nodeStatus, .link)
        XCTAssertFalse(items[0].isRead)
        XCTAssertFalse(items[0].isStarred)
        XCTAssertEqual(items[0].queueStatus, .unread)
        XCTAssertTrue(items[0].canRestoreAudio)
    }

    func testProcessLibraryMetadataTextShowsPodcastEpisodeIntro() throws {
        let root = URL(fileURLWithPath: NSTemporaryDirectory())
            .appendingPathComponent(UUID().uuidString)
        let dataRoot = root.appendingPathComponent("data")
        try writeTestLibraryEpisode(
            dataRoot: dataRoot,
            id: "show",
            title: "未处理节目",
            metadata: [
                "app_group": "知识",
                "app_queue_status": "to_process",
                "audio_url": "https://media.example/show.m4a",
                "canonical_url": "https://episodes.example/show",
                "description": "这是站点提供的节目内容介绍。\\n包含嘉宾、主题和主要问题。",
                "duration": "01:02:03",
                "image_url": "https://images.example/show.jpg",
                "local_published_at": "2026-06-07T20:30:00+08:00",
                "published_at": "2026-06-07T12:30:00+00:00",
                "series_name": "站点节目",
                "series_url": "https://podcasts.example/series",
                "source": "podcast_rss",
                "source_url": "https://feed.example/item",
            ],
            audioContents: nil
        )

        let item = try XCTUnwrap(ProcessLibrary.scan(dataRoot: dataRoot).first)
        let text = ProcessLibrary.metadataText(for: item)

        XCTAssertEqual(item.status, "Audio pending")
        XCTAssertEqual(item.queueStatus, .toProcess)
        XCTAssertEqual(item.groupName, "知识")
        XCTAssertEqual(item.publishedAt, "2026-06-07T20:30:00+08:00")
        XCTAssertTrue(text.contains("# 未处理节目"))
        XCTAssertTrue(text.contains("- 节目：站点节目"))
        XCTAssertTrue(text.contains("- 来源：Podcast RSS"))
        XCTAssertTrue(text.contains("- 分组：知识"))
        XCTAssertTrue(text.contains("- 原始链接：https://episodes.example/show"))
        XCTAssertTrue(text.contains("- 节目链接：https://podcasts.example/series"))
        XCTAssertTrue(text.contains("- 发布时间：2026-06-07T20:30:00+08:00"))
        XCTAssertTrue(text.contains("- 时长：01:02:03"))
        XCTAssertTrue(text.contains("- 音频链接：https://media.example/show.m4a"))
        XCTAssertTrue(text.contains("- 封面：https://images.example/show.jpg"))
        XCTAssertTrue(text.contains("## 节目介绍"))
        XCTAssertTrue(text.contains("这是站点提供的节目内容介绍。"))
        XCTAssertTrue(text.contains("包含嘉宾、主题和主要问题。"))
    }

    func testUnprocessedDetailTextIncludesMetadataAndProcessingState() throws {
        let root = URL(fileURLWithPath: NSTemporaryDirectory())
            .appendingPathComponent(UUID().uuidString)
        let dataRoot = root.appendingPathComponent("data")
        try writeTestLibraryEpisode(
            dataRoot: dataRoot,
            id: "detail",
            title: "详情未处理节目",
            metadata: [
                "audio_url": "https://media.example/detail.m4a",
                "description": "未处理页也应该展示这段站点简介。",
                "series_name": "详情测试节目",
                "source": "podcast_rss",
                "source_url": "https://feed.example/detail",
            ],
            audioFileName: "detail.m4a",
            audioContents: nil
        )

        let item = try XCTUnwrap(ProcessLibrary.scan(dataRoot: dataRoot).first)
        let metadataText = ProcessLibrary.metadataText(for: item)
        let detailText = ProcessLibrary.unprocessedDetailText(for: item, metadataText: metadataText)

        XCTAssertTrue(detailText.contains("# 详情未处理节目"))
        XCTAssertTrue(detailText.contains("未处理页也应该展示这段站点简介。"))
        XCTAssertTrue(detailText.contains("## 处理状态"))
        XCTAssertTrue(detailText.contains("- 队列：Unread"))
        XCTAssertTrue(detailText.contains("- 当前状态：Audio pending"))
        XCTAssertTrue(detailText.contains("- 音频：待下载或待恢复"))
        XCTAssertTrue(detailText.contains("- 详情：Metadata exists"))
        XCTAssertTrue(detailText.contains("- 可操作：可以从来源音频链接下载后处理。"))
    }

    func testProcessLibraryIndexInvalidatesWhenPlannedAudioAppears() throws {
        let root = URL(fileURLWithPath: NSTemporaryDirectory())
            .appendingPathComponent(UUID().uuidString)
        let dataRoot = root.appendingPathComponent("data")
        let episode = try writeTestLibraryEpisode(
            dataRoot: dataRoot,
            id: "show",
            title: "待下载节目",
            metadata: [
                "audio_url": "https://media.example/show.m4a",
                "source": "podcast_rss",
            ],
            audioContents: nil
        )

        var items = ProcessLibrary.scan(dataRoot: dataRoot)
        XCTAssertEqual(items.first?.status, "Audio pending")
        XCTAssertEqual(items.first?.hasFile, false)

        try "audio".write(to: episode.audioURL, atomically: true, encoding: .utf8)
        items = ProcessLibrary.scan(dataRoot: dataRoot)

        XCTAssertEqual(items.first?.status, "Not processed")
        XCTAssertEqual(items.first?.hasFile, true)
    }

    func testProcessLibraryIndexInvalidatesWhenOutputAppears() throws {
        let root = URL(fileURLWithPath: NSTemporaryDirectory())
            .appendingPathComponent(UUID().uuidString)
        let dataRoot = root.appendingPathComponent("data")
        let episode = try writeTestLibraryEpisode(dataRoot: dataRoot, id: "show", title: "刚完成转写")
        let output = episode.workRoot

        var items = ProcessLibrary.scan(dataRoot: dataRoot)
        XCTAssertEqual(items.first?.status, "Not processed")
        XCTAssertEqual(items.first?.isProcessed, false)

        try FileManager.default.createDirectory(at: output, withIntermediateDirectories: true)
        try FileManager.default.createDirectory(at: episode.documentsRoot, withIntermediateDirectories: true)
        try #"{"success":true,"chunks":[]}"#.write(
            to: output.appendingPathComponent("run.json"),
            atomically: true,
            encoding: .utf8
        )
        try "transcript body".write(
            to: output.appendingPathComponent("transcript.timestamped.md"),
            atomically: true,
            encoding: .utf8
        )
        try "transcript body".write(to: episode.documentsRoot.appendingPathComponent("transcript.md"), atomically: true, encoding: .utf8)

        items = ProcessLibrary.scan(dataRoot: dataRoot)

        XCTAssertEqual(items.first?.status, "Processed")
        XCTAssertEqual(items.first?.isProcessed, true)
    }

    func testProcessLibraryMarksInterruptedOutputForReanalysis() throws {
        let root = URL(fileURLWithPath: NSTemporaryDirectory())
            .appendingPathComponent(UUID().uuidString)
        let dataRoot = root.appendingPathComponent("data")
        let episode = try writeTestLibraryEpisode(dataRoot: dataRoot, id: "show", title: "未完成节目")
        let output = episode.workRoot
        try FileManager.default.createDirectory(at: output, withIntermediateDirectories: true)
        try #"{"chunks":[{},{}],"chunk_status_counts":{"transcribed":1}}"#.write(
            to: output.appendingPathComponent("run.json"),
            atomically: true,
            encoding: .utf8
        )

        let item = try XCTUnwrap(ProcessLibrary.scan(dataRoot: dataRoot).first)

        XCTAssertEqual(item.status, "Incomplete")
        XCTAssertTrue(item.needsReanalysis)
        XCTAssertFalse(item.hasProcessed)
    }

    func testProcessLibraryPersistsReadAndStarState() throws {
        let root = URL(fileURLWithPath: NSTemporaryDirectory())
            .appendingPathComponent(UUID().uuidString)
        let dataRoot = root.appendingPathComponent("data")
        let episode = try writeTestLibraryEpisode(dataRoot: dataRoot, id: "show", title: "可读状态节目")
        let item = try XCTUnwrap(ProcessLibrary.scan(dataRoot: dataRoot).first)

        try ProcessLibrary.updateRead(true, for: item)
        try ProcessLibrary.updateStar(true, for: item)
        try ProcessLibrary.updateQueueStatus(.toProcess, for: item)
        let updated = try XCTUnwrap(ProcessLibrary.scan(dataRoot: dataRoot).first)
        let metadata = try readJSON(episode.recordURL)

        XCTAssertTrue(updated.isRead)
        XCTAssertTrue(updated.isStarred)
        XCTAssertEqual(updated.queueStatus, .toProcess)
        XCTAssertEqual(updated.nodeStatus, .import)
        XCTAssertEqual(metadata["app_read"] as? Bool, true)
        XCTAssertEqual(metadata["app_star"] as? Bool, true)
        XCTAssertEqual(metadata["app_queue_status"] as? String, "to_process")
        XCTAssertEqual(metadata["app_status"] as? String, "import")
        XCTAssertNotNil(metadata["app_status_updated_at"])
    }

    func testProcessLibraryReadsArchivedState() throws {
        let root = URL(fileURLWithPath: NSTemporaryDirectory())
            .appendingPathComponent(UUID().uuidString)
        let dataRoot = root.appendingPathComponent("data")
        try writeTestLibraryEpisode(
            dataRoot: dataRoot,
            id: "archived",
            title: "归档节目",
            metadata: [
                "app_status": "archived",
                "audio_url": "https://media.example/archived.m4a",
                "guid": "archived-guid",
                "source": "podcast_rss",
                "subscription_id": "podcast-main",
            ],
            audioFileName: "archived.m4a"
        )

        let items = ProcessLibrary.scan(dataRoot: dataRoot)
        let sections = ProcessLibrary.sections(from: items)

        XCTAssertEqual(items.count, 1)
        XCTAssertTrue(items[0].isArchived)
        XCTAssertTrue(sections.allSatisfy { $0.items.isEmpty })
    }

    func testProcessLibraryArchiveAndUnarchivePersistStateAndInvalidateIndex() throws {
        let root = URL(fileURLWithPath: NSTemporaryDirectory())
            .appendingPathComponent(UUID().uuidString)
        let dataRoot = root.appendingPathComponent("data")
        let indexURL = dataRoot.appendingPathComponent("cache/library.index.json")
        let episode = try writeTestLibraryEpisode(
            dataRoot: dataRoot,
            id: "archive-toggle",
            title: "归档切换节目",
            metadata: [
                "audio_url": "https://media.example/archive-toggle.m4a",
                "guid": "archive-toggle-guid",
                "source": "podcast_rss",
                "subscription_id": "podcast-main",
            ],
            audioFileName: "archive-toggle.m4a"
        )
        let item = try XCTUnwrap(ProcessLibrary.scan(dataRoot: dataRoot).first)
        XCTAssertTrue(FileManager.default.fileExists(atPath: indexURL.path))

        try ProcessLibrary.updateArchive(true, for: item, dataRoot: dataRoot)

        XCTAssertFalse(FileManager.default.fileExists(atPath: indexURL.path))
        XCTAssertEqual(try readJSON(episode.recordURL)["app_status"] as? String, "archived")
        let archived = try XCTUnwrap(ProcessLibrary.scan(dataRoot: dataRoot).first)
        XCTAssertTrue(archived.isArchived)

        try ProcessLibrary.updateArchive(false, for: archived, dataRoot: dataRoot)

        XCTAssertEqual(try readJSON(episode.recordURL)["app_status"] as? String, "link")
        let unarchived = try XCTUnwrap(ProcessLibrary.scan(dataRoot: dataRoot).first)
        XCTAssertFalse(unarchived.isArchived)
    }

    func testProcessLibraryBuildsCustomSections() {
        let first = ProcessLibraryItem(
            id: "a",
            title: "A",
            groupName: "Default",
            nodeStatus: .import,
            audioURL: URL(fileURLWithPath: "/tmp/a.m4a"),
            outputURL: URL(fileURLWithPath: "/tmp/output"),
            status: "QA pass",
            detail: "",
            hasFile: true,
            hasProcessed: true,
            hasTranscript: true,
            hasOutput: true,
            runStatus: "done",
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
            modifiedAt: Date(timeIntervalSince1970: 1)
        )
        let second = ProcessLibraryItem(
            id: "b",
            title: "B",
            groupName: "Research",
            nodeStatus: .import,
            audioURL: URL(fileURLWithPath: "/tmp/b.m4a"),
            outputURL: URL(fileURLWithPath: "/tmp/output"),
            status: "Not processed",
            detail: "",
            hasFile: false,
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
            modifiedAt: Date(timeIntervalSince1970: 2)
        )

        let sections = ProcessLibrary.sections(from: [first, second])

        XCTAssertEqual(sections.map(\.id), ["Default", "Research"])
        XCTAssertEqual(sections[0].processedCount, 1)
    }

    func testProcessLibraryGroupNamesCanReuseScannedItemsAndSharedGroups() throws {
        let root = URL(fileURLWithPath: NSTemporaryDirectory())
            .appendingPathComponent(UUID().uuidString)
        let dataRoot = root.appendingPathComponent("data")
        let episode = try writeTestLibraryEpisode(
            dataRoot: dataRoot,
            id: "group-reuse",
            title: "分组复用",
            metadata: ["app_group": "生活"]
        )
        try LibraryWriter.upsertGroup("Research", in: episode.libraryRoot)

        let items = ProcessLibrary.scan(dataRoot: dataRoot)
        let groupNames = ProcessLibrary.groupNames(from: items, dataRoot: dataRoot)

        XCTAssertEqual(groupNames, ["Default", "Research", "生活"])
    }

    @MainActor
    func testJobControllerLoadLibraryReusesSingleScanForSections() throws {
        let root = URL(fileURLWithPath: NSTemporaryDirectory())
            .appendingPathComponent(UUID().uuidString)
        let dataRoot = root.appendingPathComponent("data")
        try writeTestLibraryEpisode(
            dataRoot: dataRoot,
            id: "single-scan",
            title: "刷新计数",
            metadata: ["app_group": "Research"]
        )
        var scanCount = 0
        ProcessLibrary.scanInvocationObserver = { observedRoot in
            if observedRoot.standardizedFileURL.path == dataRoot.standardizedFileURL.path {
                scanCount += 1
            }
        }
        defer { ProcessLibrary.scanInvocationObserver = nil }

        let controller = JobController(settingsStore: AppSettingsStore(dataRoot: dataRoot, credentials: MemoryCloudCredentials()), loadsLibrarySynchronously: true)

        XCTAssertEqual(scanCount, 1)
        XCTAssertEqual(controller.libraryItems.map(\.id), ["single-scan"])
        XCTAssertEqual(controller.librarySections.map(\.id), ["Default", "Research"])
    }

    func testProcessLibraryMapsUntaggedDateFoldersToDefaultGroup() throws {
        let root = URL(fileURLWithPath: NSTemporaryDirectory())
            .appendingPathComponent(UUID().uuidString)
        let dataRoot = root.appendingPathComponent("data")
        try writeTestLibraryEpisode(dataRoot: dataRoot, id: "show", title: "Untagged")

        let sections = ProcessLibrary.sections(from: ProcessLibrary.scan(dataRoot: dataRoot))

        XCTAssertEqual(sections.map(\.title), ["Default"])
    }

    func testProcessLibraryRestoresPodcastRSSAudioSources() {
        let item = testLibraryItem(
            id: "rss-\(UUID().uuidString)",
            title: "RSS Item",
            groupName: "Default",
            audioURL: URL(fileURLWithPath: "/tmp/rss-item.m4a"),
            status: "Audio pending",
            nodeStatus: .link,
            hasFile: false,
            source: "podcast_rss",
            mediaURL: "https://media.example/rss-item.m4a",
            modifiedAt: Date()
        )

        XCTAssertTrue(item.canRestoreAudio)
    }

    func testProcessLibraryDownloadAudioOnlyForRemoteUnprocessedItems() {
        let remote = testLibraryItem(
            id: "remote-\(UUID().uuidString)",
            title: "Remote Item",
            groupName: "Default",
            audioURL: URL(fileURLWithPath: "/tmp/remote-item.m4a"),
            status: "Not processed",
            source: "podcast_rss",
            mediaURL: "https://media.example/remote-item.m4a",
            modifiedAt: Date()
        )
        let local = testLibraryItem(
            id: "local-\(UUID().uuidString)",
            title: "Local Item",
            groupName: "Default",
            audioURL: URL(fileURLWithPath: "/tmp/local-item.m4a"),
            status: "Not processed",
            source: "local",
            mediaURL: "https://media.example/local-item.m4a",
            modifiedAt: Date()
        )
        let processedRemote = testLibraryItem(
            id: "processed-remote-\(UUID().uuidString)",
            title: "Processed Remote Item",
            groupName: "Default",
            audioURL: URL(fileURLWithPath: "/tmp/processed-remote-item.m4a"),
            status: "QA pass",
            hasProcessed: true,
            hasTranscript: true,
            source: "xiaoyuzhou",
            mediaURL: "https://media.example/processed-remote-item.m4a",
            modifiedAt: Date()
        )

        XCTAssertTrue(remote.canDownloadAudio)
        XCTAssertFalse(local.canDownloadAudio)
        XCTAssertFalse(processedRemote.canDownloadAudio)
    }

    func testProcessLibraryIgnoresStaleCloudShortTitleDuringScan() throws {
        let root = URL(fileURLWithPath: NSTemporaryDirectory())
            .appendingPathComponent(UUID().uuidString)
        let dataRoot = root.appendingPathComponent("data")
        let episode = try writeTestLibraryEpisode(dataRoot: dataRoot, id: "show", title: "当前标题")
        let output = episode.workRoot
        try FileManager.default.createDirectory(at: output.appendingPathComponent("cloud"), withIntermediateDirectories: true)
        try "旧 work 标题".write(to: output.appendingPathComponent("cloud/short_title.txt"), atomically: true, encoding: .utf8)

        let item = try XCTUnwrap(ProcessLibrary.scan(dataRoot: dataRoot).first)
        let record = try readJSON(episode.recordURL)

        XCTAssertEqual(item.title, "当前标题")
        XCTAssertEqual(record["title"] as? String, "当前标题")
    }
}
