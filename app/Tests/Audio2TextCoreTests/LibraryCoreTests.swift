@testable import Audio2TextCore
import XCTest

final class LibraryCoreTests: XCTestCase {
    func testCloudModelDefaultsMatchCurrentMacDefaults() {
        XCTAssertEqual(CloudModelDefaults.defaultAPIBase, "")
        XCTAssertEqual(CloudModelDefaults.defaultModel, "gpt-5.4-mini")
        XCTAssertEqual(
            CloudModelDefaults.defaultModelOptions,
            ["gpt-5.4-mini", "gpt-5.4", "gpt-5.5", "gpt-5.6-sol", "gpt-5.6-terra", "gpt-5.6-luna"]
        )
    }

    func testMobileCloudSettingsRequiresEndpointAndAPIKey() {
        XCTAssertFalse(MobileCloudSettings(apiBase: "", apiKey: "test-key").isConfigured)
        XCTAssertFalse(MobileCloudSettings(apiBase: "https://api.example/v1", apiKey: "").isConfigured)
        XCTAssertTrue(MobileCloudSettings(apiBase: "https://api.example/v1", apiKey: "test-key").isConfigured)
    }

    func testMobileCloudSettingsStorePersistsDefaultsAndSecureAPIKey() throws {
        let defaults = try temporaryDefaults()
        let store = MobileCloudSettingsStore(defaults: defaults, credentials: MemoryCloudCredentials())
        defer { try? store.delete() }

        try store.save(MobileCloudSettings(apiBase: " https://api.example/v1 ", apiKey: " test-key ", model: " model-x "))
        let loaded = try store.load()

        XCTAssertEqual(loaded.apiBase, "https://api.example/v1")
        XCTAssertEqual(loaded.model, "model-x")
        XCTAssertEqual(loaded.apiKey, "test-key")
        XCTAssertNil(defaults.string(forKey: MobileCloudSettingsStore.apiKeyKey))
        XCTAssertTrue(loaded.isConfigured)
    }

    func testMobileCloudSettingsStoreFallsBackToDefaultModelWhenSavedModelIsEmpty() throws {
        let defaults = try temporaryDefaults()
        let store = MobileCloudSettingsStore(defaults: defaults, credentials: MemoryCloudCredentials())
        defer { try? store.delete() }

        try store.save(MobileCloudSettings(apiBase: "", apiKey: "", model: "   "))
        let loaded = try store.load()

        XCTAssertEqual(loaded.model, CloudModelDefaults.defaultModel)
        XCTAssertEqual(loaded.apiKey, "")
        XCTAssertFalse(loaded.isConfigured)
    }

    func testMobileCloudSettingsStoreClearsSecureAPIKeyWhenSavedEmpty() throws {
        let defaults = try temporaryDefaults()
        let store = MobileCloudSettingsStore(defaults: defaults, credentials: MemoryCloudCredentials())
        defer { try? store.delete() }

        try store.save(MobileCloudSettings(apiBase: "", apiKey: "test-key", model: "model-x"))
        XCTAssertEqual(try store.load().apiKey, "test-key")

        try store.save(MobileCloudSettings(apiBase: "", apiKey: "", model: "model-x"))

        XCTAssertEqual(try store.load().apiKey, "")
        XCTAssertNil(defaults.string(forKey: MobileCloudSettingsStore.apiKeyKey))
    }

    func testLibraryRefreshSummaryAggregatesSuccessesAndFailures() {
        var summary = LibraryRefreshSummary()

        summary.recordSuccess(
            LibraryWriteResult(
                subscriptionID: "sub-1",
                writtenEpisodeCount: 2,
                skippedAvailableEpisodeCount: 1,
                reusedMetadataEpisodeCount: 3,
                tombstoneSkippedEpisodeCount: 4
            )
        )
        summary.recordFailure(title: "Broken Feed", message: "network unavailable")

        XCTAssertEqual(summary.refreshedSubscriptionCount, 1)
        XCTAssertEqual(summary.failedSubscriptionCount, 1)
        XCTAssertEqual(summary.writtenEpisodeCount, 2)
        XCTAssertEqual(summary.reusedMetadataEpisodeCount, 3)
        XCTAssertEqual(summary.skippedAvailableEpisodeCount, 1)
        XCTAssertEqual(summary.tombstoneSkippedEpisodeCount, 4)
        XCTAssertEqual(summary.metadataCountText, "2 new, 3 refreshed, 1 processed kept, 4 deleted skipped")
        XCTAssertEqual(
            summary.refreshAllStatusText,
            "Refreshed 1 subscription: 2 new, 3 refreshed, 1 processed kept, 4 deleted skipped. Failed 1 subscription: Broken Feed: network unavailable"
        )
    }

    func testStableEpisodeIDMatchesPythonContract() {
        let id = StableEpisodeID.make(
            source: "podcast_rss",
            subscriptionID: "podcast-1",
            guid: "episode-guid",
            audioURL: "https://media.example/episode.m4a",
            canonicalURL: "https://example.com/episode"
        )

        XCTAssertEqual(id, "bd355180622d13097b4a110c")
        XCTAssertEqual(
            id,
            StableEpisodeID.make(
                source: "podcast_rss",
                subscriptionID: "podcast-1",
                guid: "episode-guid",
                audioURL: "https://media.example/changed.m4a",
                canonicalURL: "https://example.com/episode"
            )
        )
    }

    func testLibraryDateParserReadsPythonISOWithFractionalSeconds() {
        let date = LibraryDateParser.date(from: "2026-06-20T17:47:27.420892+08:00")

        XCTAssertNotNil(date)
    }

    func testDecodesLibraryEpisode() throws {
        let json = """
        {
          "schema_version": 1,
          "kind": "audio2text.library.episode",
          "episode_id": "episode-1",
          "title": "测试节目",
          "source": "podcast_rss",
          "source_url": "https://example.com/e",
          "canonical_url": "https://example.com/e",
          "series_name": "测试播客",
          "audio_url": "https://media.example/e.m4a",
          "subscription_id": "podcast-1",
          "app_star": true,
          "product_status": "available",
          "documents": [
            {"name": "summary.md", "path": "documents/summary.md", "bytes": 10, "sha256": "abc"}
          ]
        }
        """

        let episode = try JSONDecoder().decode(LibraryEpisode.self, from: Data(json.utf8))

        XCTAssertEqual(episode.id, "episode-1")
        XCTAssertEqual(episode.title, "测试节目")
        XCTAssertEqual(episode.normalizedProductStatus, LibraryConstants.productStatusAvailable)
        XCTAssertTrue(episode.isStarred)
        XCTAssertEqual(episode.documents.map(\.name), ["summary.md"])
    }

    func testLibraryWriterUpdatesTitle() throws {
        let root = URL(fileURLWithPath: NSTemporaryDirectory())
            .appendingPathComponent("Audio2TextCoreTests-\(UUID().uuidString)", isDirectory: true)
        defer { try? FileManager.default.removeItem(at: root) }
        let episodeRoot = root.appendingPathComponent("episodes/episode-1", isDirectory: true)
        try FileManager.default.createDirectory(at: episodeRoot, withIntermediateDirectories: true)
        let episodeURL = episodeRoot.appendingPathComponent("episode.json")
        try writeJSONObject(
            [
                "schema_version": 1,
                "kind": "audio2text.library.episode",
                "episode_id": "episode-1",
                "title": "原始标题",
                "documents": [],
            ],
            to: episodeURL
        )

        try LibraryWriter.updateTitle("  AI 标题  ", forEpisodeID: "episode-1", in: root)
        let updated = try JSONDecoder().decode(LibraryEpisode.self, from: Data(contentsOf: episodeURL))
        let updatedObject = try jsonObject(at: episodeURL)

        XCTAssertEqual(updated.title, "AI 标题")
        XCTAssertEqual(updated.originalTitle, "原始标题")
        XCTAssertEqual(updatedObject["title"] as? String, "AI 标题")
        XCTAssertEqual(updatedObject["original_title"] as? String, "原始标题")
    }

    func testLibraryWriterKeepsExistingOriginalTitleWhenUpdatingTitleAgain() throws {
        let root = URL(fileURLWithPath: NSTemporaryDirectory())
            .appendingPathComponent("Audio2TextCoreTests-\(UUID().uuidString)", isDirectory: true)
        defer { try? FileManager.default.removeItem(at: root) }
        let episodeRoot = root.appendingPathComponent("episodes/episode-1", isDirectory: true)
        try FileManager.default.createDirectory(at: episodeRoot, withIntermediateDirectories: true)
        let episodeURL = episodeRoot.appendingPathComponent("episode.json")
        try writeJSONObject(
            [
                "schema_version": 1,
                "kind": "audio2text.library.episode",
                "episode_id": "episode-1",
                "title": "第一个 AI 标题",
                "original_title": "原始标题",
                "documents": [],
            ],
            to: episodeURL
        )

        try LibraryWriter.updateTitle("第二个 AI 标题", forEpisodeID: "episode-1", in: root)
        let updated = try JSONDecoder().decode(LibraryEpisode.self, from: Data(contentsOf: episodeURL))
        let updatedObject = try jsonObject(at: episodeURL)

        XCTAssertEqual(updated.title, "第二个 AI 标题")
        XCTAssertEqual(updated.originalTitle, "原始标题")
        XCTAssertEqual(updatedObject["original_title"] as? String, "原始标题")
    }

    func testMobileSnapshotDoesNotDeriveTitleFromSummaryHeading() throws {
        let root = URL(fileURLWithPath: NSTemporaryDirectory())
            .appendingPathComponent("Audio2TextCoreTests-\(UUID().uuidString)", isDirectory: true)
        defer { try? FileManager.default.removeItem(at: root) }
        let episodeRoot = root.appendingPathComponent("episodes/episode-1", isDirectory: true)
        let documentsRoot = episodeRoot.appendingPathComponent("documents", isDirectory: true)
        try FileManager.default.createDirectory(at: documentsRoot, withIntermediateDirectories: true)
        let episode = LibraryEpisode(
            episodeID: "episode-1",
            title: "原始长标题",
            productStatus: LibraryConstants.productStatusAvailable,
            documents: [LibraryDocument(name: "summary.md", path: "documents/summary.md", bytes: 16)]
        )
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        try encoder.encode(episode).write(to: episodeRoot.appendingPathComponent("episode.json"), options: .atomic)
        try "# AI 总结标题\n\n正文".write(to: documentsRoot.appendingPathComponent("summary.md"), atomically: true, encoding: .utf8)
        try LibraryWriter.rebuildManifest(libraryRoot: root)

        let snapshot = try MobileLibraryStore.loadSnapshot(from: root)

        XCTAssertEqual(snapshot.episodes.first?.title, "原始长标题")
    }

    func testZeroByteDocumentsDoNotCountAsSyncedContent() {
        let emptyDocumentEpisode = LibraryEpisode(
            episodeID: "empty-doc",
            title: "Empty",
            productStatus: LibraryConstants.productStatusAvailable,
            documents: [LibraryDocument(name: "summary.md", path: "documents/summary.md", bytes: 0)]
        )
        XCTAssertFalse(emptyDocumentEpisode.hasSyncedDocuments)
    }

    func testSharedLibraryFixtureMatchesPythonValidatorSchema() throws {
        let root = try sharedFixtureLibraryRoot()

        let manifest = try LibraryStore.loadManifest(from: root)
        let episodes = try LibraryStore.loadEpisodes(from: root)
        let subscriptions = try LibraryStore.loadSubscriptions(from: root)
        let documents = try MobileLibraryStore.documentContents(for: XCTUnwrap(episodes.first), libraryRoot: root)

        XCTAssertEqual(manifest.kind, LibraryConstants.libraryManifestKind)
        XCTAssertEqual(manifest.episodeCount, 1)
        XCTAssertEqual(manifest.subscriptionCount, 1)
        XCTAssertEqual(manifest.tombstoneCount, 1)
        XCTAssertEqual(manifest.episodes, [LibraryManifest.EpisodeEntry(episodeID: "episode-shared-0001", path: "episodes/episode-shared-0001/episode.json")])
        XCTAssertEqual(manifest.tombstones, [LibraryManifest.TombstoneEntry(episodeID: "episode-deleted-0001", path: "tombstones/episodes/episode-deleted-0001.json")])
        XCTAssertEqual(episodes.map(\.title), ["001. Shared Fixture"])
        XCTAssertEqual(subscriptions.map(\.id), ["podcast_rss-shared"])
        XCTAssertEqual(documents.map(\.name), ["summary.md", "transcript.md"])
    }

    func testLibraryPathsResolveSelectedFilesFolder() throws {
        let root = URL(fileURLWithPath: NSTemporaryDirectory())
            .appendingPathComponent("Audio2TextCoreTests-\(UUID().uuidString)", isDirectory: true)
        defer { try? FileManager.default.removeItem(at: root) }
        let audio2TextRoot = root.appendingPathComponent("Audio2Text", isDirectory: true)
        let libraryRoot = audio2TextRoot.appendingPathComponent("Audio2TextLibrary", isDirectory: true)
        try FileManager.default.createDirectory(at: libraryRoot, withIntermediateDirectories: true)
        try "{}".write(to: libraryRoot.appendingPathComponent("manifest.json"), atomically: true, encoding: .utf8)

        XCTAssertEqual(LibraryPaths.existingLibraryRoot(in: audio2TextRoot).path, libraryRoot.path)
        XCTAssertEqual(LibraryPaths.existingLibraryRoot(in: libraryRoot).path, libraryRoot.path)
        XCTAssertEqual(LibraryPaths.existingLibraryRoot(in: root).path, libraryRoot.path)
        XCTAssertEqual(
            LibraryPaths.libraryRoot(in: root.appendingPathComponent("Empty", isDirectory: true)).path,
            root.appendingPathComponent("Empty/Audio2TextLibrary", isDirectory: true).path
        )
    }

    func testLibraryGroupsAreSharedSnapshotState() throws {
        let root = URL(fileURLWithPath: NSTemporaryDirectory())
            .appendingPathComponent("Audio2TextCoreTests-\(UUID().uuidString)", isDirectory: true)
        defer { try? FileManager.default.removeItem(at: root) }
        try LibraryWriter.rebuildManifest(libraryRoot: root)
        try LibraryWriter.upsertGroup("Research", in: root)
        try LibraryWriter.upsertGroup("生活", in: root)

        let groups = try LibraryStore.loadGroups(from: root)
        let snapshot = try MobileLibraryStore.loadSnapshot(from: root)

        XCTAssertEqual(groups.map(\.displayName), ["Research", "生活"])
        XCTAssertEqual(snapshot.groupNames, ["Research", "生活"])
        XCTAssertTrue(FileManager.default.fileExists(atPath: root.appendingPathComponent("groups/Research.json").path))
        XCTAssertTrue(FileManager.default.fileExists(atPath: root.appendingPathComponent("groups/生活.json").path))
    }

    func testLibrarySyncStatusReportsFriendlyStatesForLocalAndMissingLibraries() throws {
        let root = URL(fileURLWithPath: NSTemporaryDirectory())
            .appendingPathComponent("Audio2TextCoreTests-\(UUID().uuidString)", isDirectory: true)
        defer { try? FileManager.default.removeItem(at: root) }
        try LibraryWriter.rebuildManifest(libraryRoot: root)

        let localStatus = LibrarySyncStatusProbe.status(for: root)
        let missingStatus = LibrarySyncStatusProbe.status(for: root.appendingPathComponent("Missing", isDirectory: true))

        XCTAssertEqual(localStatus.state, .synced)
        XCTAssertEqual(localStatus.title, "同步成功")
        XCTAssertEqual(missingStatus.state, .offline)
        XCTAssertEqual(missingStatus.title, "网络断开")
    }

    func testLibrarySyncStatusTreatsPendingUploadsAsSyncingBeforeUploadErrors() throws {
        let root = URL(fileURLWithPath: NSTemporaryDirectory())
            .appendingPathComponent("Audio2TextCoreTests-\(UUID().uuidString)", isDirectory: true)
        defer { try? FileManager.default.removeItem(at: root) }
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        let manifestURL = root.appendingPathComponent("manifest.json")
        try "{}".write(to: manifestURL, atomically: true, encoding: .utf8)

        let status = LibrarySyncStatusProbe.status(for: root) { url in
            if url.standardizedFileURL == manifestURL.standardizedFileURL {
                return LibrarySyncResourceValues(
                    isCloudBacked: true,
                    isUploading: true,
                    isUploaded: false,
                    uploadingError: LibrarySyncStatusTestError()
                )
            }
            return LibrarySyncResourceValues(isCloudBacked: true, isUploaded: true)
        }

        XCTAssertEqual(status.state, .syncing)
        XCTAssertEqual(status.title, "同步中")
        XCTAssertEqual(status.pendingFileCount, 1)
        XCTAssertEqual(status.errorFileCount, 1)
    }

    func testLibrarySyncStatusReportsOfflineForUploadErrorsWithoutPendingWork() throws {
        let root = URL(fileURLWithPath: NSTemporaryDirectory())
            .appendingPathComponent("Audio2TextCoreTests-\(UUID().uuidString)", isDirectory: true)
        defer { try? FileManager.default.removeItem(at: root) }
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        let manifestURL = root.appendingPathComponent("manifest.json")
        try "{}".write(to: manifestURL, atomically: true, encoding: .utf8)

        let status = LibrarySyncStatusProbe.status(for: root) { url in
            if url.standardizedFileURL == manifestURL.standardizedFileURL {
                return LibrarySyncResourceValues(
                    isCloudBacked: true,
                    isUploading: false,
                    isUploaded: true,
                    uploadingError: LibrarySyncStatusTestError()
                )
            }
            return LibrarySyncResourceValues(isCloudBacked: true, isUploaded: true)
        }

        XCTAssertEqual(status.state, .offline)
        XCTAssertEqual(status.title, "网络断开")
        XCTAssertEqual(status.pendingFileCount, 0)
        XCTAssertEqual(status.errorFileCount, 1)
    }

    func testLibraryWriterCreatesMetadataOnlyRecordsAndPreservesAvailableEpisodes() throws {
        let root = URL(fileURLWithPath: NSTemporaryDirectory())
            .appendingPathComponent("Audio2TextCoreTests-\(UUID().uuidString)", isDirectory: true)
        defer { try? FileManager.default.removeItem(at: root) }
        let availableID = StableEpisodeID.make(
            source: "podcast_rss",
            subscriptionID: "podcast_rss-f0402f8804d1",
            guid: "episode-1",
            audioURL: "https://media.example/episode-1.m4a",
            canonicalURL: "https://example.com/episodes/1",
            sourceURL: "https://example.com/episodes/1",
            title: "001. 已处理"
        )
        let reusedID = StableEpisodeID.make(
            source: "podcast_rss",
            subscriptionID: "podcast_rss-f0402f8804d1",
            guid: "episode-2",
            audioURL: "https://media.example/episode-2.m4a",
            canonicalURL: "https://example.com/episodes/2",
            sourceURL: "https://example.com/episodes/2",
            title: "002. 已存在元信息"
        )
        let deletedID = StableEpisodeID.make(
            source: "podcast_rss",
            subscriptionID: "podcast_rss-f0402f8804d1",
            guid: "episode-deleted",
            audioURL: "https://media.example/episode-deleted.m4a",
            canonicalURL: "https://example.com/episodes/deleted",
            sourceURL: "https://example.com/episodes/deleted",
            title: "004. 已删除"
        )
        let availableRoot = root.appendingPathComponent("episodes/\(availableID)", isDirectory: true)
        let reusedRoot = root.appendingPathComponent("episodes/\(reusedID)", isDirectory: true)
        try FileManager.default.createDirectory(at: availableRoot.appendingPathComponent("documents", isDirectory: true), withIntermediateDirectories: true)
        try FileManager.default.createDirectory(at: reusedRoot, withIntermediateDirectories: true)
        try FileManager.default.createDirectory(at: root.appendingPathComponent("tombstones/episodes", isDirectory: true), withIntermediateDirectories: true)
        try "# Summary\n".write(to: availableRoot.appendingPathComponent("documents/summary.md"), atomically: true, encoding: .utf8)
        try "# Transcript\n".write(to: availableRoot.appendingPathComponent("documents/transcript.md"), atomically: true, encoding: .utf8)
        let availableEpisode = LibraryEpisode(
            episodeID: availableID,
            title: "001. 已处理",
            source: "podcast_rss",
            sourceURL: "https://example.com/episodes/1",
            canonicalURL: "https://example.com/episodes/1",
            seriesName: "测试播客",
            seriesURL: "https://example.com/feed.xml",
            publishedAt: "2026-05-28T00:00:00Z",
            audioURL: "https://media.example/episode-1.m4a",
            guid: "episode-1",
            subscriptionID: "podcast_rss-f0402f8804d1",
            productStatus: LibraryConstants.productStatusAvailable,
            documents: [
                LibraryDocument(name: "summary.md", path: "documents/summary.md", bytes: 16),
                LibraryDocument(name: "transcript.md", path: "documents/transcript.md", bytes: 18),
            ]
        )
        let reusedEpisode = LibraryEpisode(
            episodeID: reusedID,
            title: "002. 旧标题",
            source: "podcast_rss",
            sourceURL: "https://example.com/episodes/2",
            canonicalURL: "https://example.com/episodes/2",
            seriesName: "测试播客",
            seriesURL: "https://example.com/feed.xml",
            publishedAt: "2026-05-29T00:00:00Z",
            audioURL: "https://media.example/episode-2.m4a",
            guid: "episode-2",
            subscriptionID: "podcast_rss-f0402f8804d1",
            appGroup: "Research",
            appStatus: "link",
            appQueueStatus: "process_later",
            appRead: true,
            appStar: true,
            productStatus: LibraryConstants.productStatusMetadataOnly,
            documents: []
        )
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        try encoder.encode(availableEpisode).write(to: availableRoot.appendingPathComponent("episode.json"))
        try encoder.encode(reusedEpisode).write(to: reusedRoot.appendingPathComponent("episode.json"))
        try """
        {
          "schema_version": 1,
          "kind": "audio2text.library.episode_tombstone",
          "episode_id": "\(deletedID)"
        }
        """.write(to: root.appendingPathComponent("tombstones/episodes/\(deletedID).json"), atomically: true, encoding: .utf8)

        let discovery = PodcastFeedDiscovery(
            title: "测试播客",
            source: "podcast_rss",
            url: "https://example.com/show",
            feedURL: "https://example.com/feed.xml",
            episodes: [
                PodcastFeedEpisode(
                    title: "001. 已处理",
                    sourceURL: "https://example.com/episodes/1",
                    canonicalURL: "https://example.com/episodes/1",
                    seriesName: "测试播客",
                    seriesURL: "https://example.com/feed.xml",
                    publishedAt: "2026-05-28T00:00:00Z",
                    duration: nil,
                    description: "done",
                    audioURL: "https://media.example/episode-1.m4a",
                    imageURL: nil,
                    source: "podcast_rss",
                    guid: "episode-1"
                ),
                PodcastFeedEpisode(
                    title: "002. 已存在元信息",
                    sourceURL: "https://example.com/episodes/2",
                    canonicalURL: "https://example.com/episodes/2",
                    seriesName: "测试播客",
                    seriesURL: "https://example.com/feed.xml",
                    publishedAt: "2026-05-29T00:00:00Z",
                    duration: nil,
                    description: "new",
                    audioURL: "https://media.example/episode-2.m4a",
                    imageURL: nil,
                    source: "podcast_rss",
                    guid: "episode-2"
                ),
                PodcastFeedEpisode(
                    title: "003. 新订阅",
                    sourceURL: "https://example.com/episodes/3",
                    canonicalURL: "https://example.com/episodes/3",
                    seriesName: "测试播客",
                    seriesURL: "https://example.com/feed.xml",
                    publishedAt: "2026-05-30T00:00:00Z",
                    duration: nil,
                    description: "new",
                    audioURL: "https://media.example/episode-3.m4a",
                    imageURL: nil,
                    source: "podcast_rss",
                    guid: "episode-3"
                ),
                PodcastFeedEpisode(
                    title: "004. 已删除",
                    sourceURL: "https://example.com/episodes/deleted",
                    canonicalURL: "https://example.com/episodes/deleted",
                    seriesName: "测试播客",
                    seriesURL: "https://example.com/feed.xml",
                    publishedAt: "2026-05-31T00:00:00Z",
                    duration: nil,
                    description: "deleted",
                    audioURL: "https://media.example/episode-deleted.m4a",
                    imageURL: nil,
                    source: "podcast_rss",
                    guid: "episode-deleted"
                ),
            ]
        )

        let result = try LibraryWriter.writeMetadataOnly(discovery: discovery, to: root)
        let manifest = try LibraryStore.loadManifest(from: root)
        let episodes = try LibraryStore.loadEpisodes(from: root)

        XCTAssertEqual(result.writtenEpisodeCount, 1)
        XCTAssertEqual(result.skippedAvailableEpisodeCount, 1)
        XCTAssertEqual(result.reusedMetadataEpisodeCount, 1)
        XCTAssertEqual(result.tombstoneSkippedEpisodeCount, 1)
        XCTAssertEqual(manifest.episodeCount, 3)
        XCTAssertEqual(manifest.subscriptionCount, 1)
        XCTAssertEqual(manifest.tombstoneCount, 1)
        XCTAssertEqual(
            manifest.episodes,
            episodes.map { LibraryManifest.EpisodeEntry(episodeID: $0.id, path: "episodes/\($0.id)/episode.json") }
        )
        XCTAssertTrue(episodes.contains { $0.id == availableID && $0.normalizedProductStatus == LibraryConstants.productStatusAvailable })
        XCTAssertTrue(episodes.contains { $0.title == "003. 新订阅" && $0.normalizedProductStatus == LibraryConstants.productStatusMetadataOnly && $0.documents.isEmpty })
        let reused = try XCTUnwrap(episodes.first { $0.id == reusedID })
        XCTAssertEqual(reused.title, "002. 旧标题")
        XCTAssertEqual(reused.appGroup, "Research")
        XCTAssertTrue(reused.isRead)
        XCTAssertTrue(reused.isStarred)
    }

    func testLibraryWriterTogglesReadStarAndArchiveState() throws {
        let root = URL(fileURLWithPath: NSTemporaryDirectory())
            .appendingPathComponent("Audio2TextCoreTests-\(UUID().uuidString)", isDirectory: true)
        defer { try? FileManager.default.removeItem(at: root) }
        let episodeRoot = root.appendingPathComponent("episodes/episode-1", isDirectory: true)
        try FileManager.default.createDirectory(at: episodeRoot, withIntermediateDirectories: true)
        let episode = LibraryEpisode(
            episodeID: "episode-1",
            title: "测试节目",
            appStatus: "link",
            appRead: false,
            appStar: false
        )
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        try encoder.encode(episode).write(to: episodeRoot.appendingPathComponent("episode.json"))

        try LibraryWriter.updateRead(true, for: episode, in: root)
        let readEpisode = try JSONDecoder().decode(
            LibraryEpisode.self,
            from: Data(contentsOf: episodeRoot.appendingPathComponent("episode.json"))
        )
        try LibraryWriter.updateRead(false, for: readEpisode, in: root)
        let unreadEpisode = try JSONDecoder().decode(
            LibraryEpisode.self,
            from: Data(contentsOf: episodeRoot.appendingPathComponent("episode.json"))
        )
        try LibraryWriter.updateArchived(true, for: unreadEpisode, in: root)
        let archivedEpisode = try JSONDecoder().decode(
            LibraryEpisode.self,
            from: Data(contentsOf: episodeRoot.appendingPathComponent("episode.json"))
        )
        try LibraryWriter.updateStar(true, for: archivedEpisode, in: root)
        let starredEpisode = try JSONDecoder().decode(
            LibraryEpisode.self,
            from: Data(contentsOf: episodeRoot.appendingPathComponent("episode.json"))
        )
        try LibraryWriter.updateStar(false, for: starredEpisode, in: root)
        let unstarredEpisode = try JSONDecoder().decode(
            LibraryEpisode.self,
            from: Data(contentsOf: episodeRoot.appendingPathComponent("episode.json"))
        )
        try LibraryWriter.updateArchived(false, for: unstarredEpisode, in: root)
        let unarchivedEpisode = try JSONDecoder().decode(
            LibraryEpisode.self,
            from: Data(contentsOf: episodeRoot.appendingPathComponent("episode.json"))
        )
        try LibraryWriter.updateGroup("  Research  ", for: unarchivedEpisode, in: root)
        let groupedEpisode = try JSONDecoder().decode(
            LibraryEpisode.self,
            from: Data(contentsOf: episodeRoot.appendingPathComponent("episode.json"))
        )
        try LibraryWriter.updateGroup("   ", for: groupedEpisode, in: root)
        let defaultGroupedEpisode = try JSONDecoder().decode(
            LibraryEpisode.self,
            from: Data(contentsOf: episodeRoot.appendingPathComponent("episode.json"))
        )

        XCTAssertTrue(readEpisode.isRead)
        XCTAssertFalse(unreadEpisode.isRead)
        XCTAssertFalse(archivedEpisode.isRead)
        XCTAssertTrue(archivedEpisode.isArchived)
        XCTAssertTrue(starredEpisode.isStarred)
        XCTAssertFalse(unstarredEpisode.isStarred)
        XCTAssertFalse(unarchivedEpisode.isArchived)
        XCTAssertEqual(groupedEpisode.appGroup, "Research")
        XCTAssertEqual(defaultGroupedEpisode.appGroup, LibrarySidebarState.defaultGroupName)
        XCTAssertEqual(try LibraryStore.loadManifest(from: root).episodeCount, 1)
    }

    func testLibraryWriterDeletesSubscriptionAndPreservesProcessedEpisodes() throws {
        let root = URL(fileURLWithPath: NSTemporaryDirectory())
            .appendingPathComponent("Audio2TextCoreTests-\(UUID().uuidString)", isDirectory: true)
        defer { try? FileManager.default.removeItem(at: root) }
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]

        try FileManager.default.createDirectory(at: root.appendingPathComponent("subscriptions", isDirectory: true), withIntermediateDirectories: true)
        try FileManager.default.createDirectory(at: root.appendingPathComponent("episodes", isDirectory: true), withIntermediateDirectories: true)
        try encoder.encode(LibrarySubscription(id: "sub-1", title: "Sub 1")).write(to: root.appendingPathComponent("subscriptions/sub-1.json"))
        try encoder.encode(LibrarySubscription(id: "sub-2", title: "Sub 2")).write(to: root.appendingPathComponent("subscriptions/sub-2.json"))

        let metadataOnly = LibraryEpisode(episodeID: "metadata", title: "Metadata", subscriptionID: "sub-1", productStatus: LibraryConstants.productStatusMetadataOnly)
        let processed = LibraryEpisode(
            episodeID: "processed",
            title: "Processed",
            subscriptionID: "sub-1",
            productStatus: LibraryConstants.productStatusAvailable,
            documents: [LibraryDocument(name: "summary.md", path: "documents/summary.md", bytes: 16)]
        )
        let other = LibraryEpisode(episodeID: "other", title: "Other", subscriptionID: "sub-2", productStatus: LibraryConstants.productStatusMetadataOnly)
        for episode in [metadataOnly, processed, other] {
            let episodeRoot = root.appendingPathComponent("episodes/\(episode.id)", isDirectory: true)
            try FileManager.default.createDirectory(at: episodeRoot, withIntermediateDirectories: true)
            try encoder.encode(episode).write(to: episodeRoot.appendingPathComponent("episode.json"))
        }
        try LibraryWriter.rebuildManifest(libraryRoot: root)

        let result = try LibraryWriter.deleteSubscription(id: "sub-1", from: root)
        let episodes = try LibraryStore.loadEpisodes(from: root)
        let subscriptions = try LibraryStore.loadSubscriptions(from: root)

        XCTAssertEqual(result.removedMetadataOnlyEpisodeCount, 1)
        XCTAssertEqual(result.preservedAvailableEpisodeCount, 1)
        XCTAssertEqual(subscriptions.map(\.id), ["sub-2"])
        XCTAssertEqual(episodes.map(\.id).sorted(), ["other", "processed"])
        XCTAssertFalse(FileManager.default.fileExists(atPath: root.appendingPathComponent("episodes/metadata").path))
        XCTAssertTrue(FileManager.default.fileExists(atPath: root.appendingPathComponent("episodes/processed/episode.json").path))
    }

    func testParsesRSSAndAtomFeeds() throws {
        let rss = """
        <rss version="2.0">
          <channel>
            <title>测试播客</title>
            <item>
              <title>001. RSS 测试</title>
              <guid>episode-1</guid>
              <link>https://example.com/episodes/1</link>
              <pubDate>Thu, 28 May 2026 00:00:00 GMT</pubDate>
              <description><![CDATA[<p>Shownotes</p>]]></description>
              <enclosure url="https://media.example/episode-1.m4a" type="audio/mp4"/>
            </item>
          </channel>
        </rss>
        """
        let atom = """
        <feed xmlns="http://www.w3.org/2005/Atom">
          <title>Atom 播客</title>
          <entry>
            <title>001. Atom 测试</title>
            <id>tag:example.com,2026:atom-1</id>
            <link href="https://example.com/atom/1"/>
            <link rel="enclosure" href="https://media.example/atom-1.mp3" type="audio/mpeg"/>
            <published>2026-05-28T00:00:00Z</published>
            <summary>Atom shownotes</summary>
          </entry>
        </feed>
        """

        let rssDiscovery = try FeedDiscoveryParser.parseRSSOrAtom(Data(rss.utf8), feedURL: "https://example.com/feed.xml", sourceURL: "https://example.com/show")
        let atomDiscovery = try FeedDiscoveryParser.parseRSSOrAtom(Data(atom.utf8), feedURL: "https://example.com/atom.xml", sourceURL: "https://example.com/atom")

        XCTAssertEqual(rssDiscovery.title, "测试播客")
        XCTAssertEqual(rssDiscovery.episodes.first?.audioURL, "https://media.example/episode-1.m4a")
        XCTAssertEqual(atomDiscovery.title, "Atom 播客")
        XCTAssertEqual(atomDiscovery.episodes.first?.audioURL, "https://media.example/atom-1.mp3")
    }

    func testParsesAppleLookupAndXiaoyuzhouHTML() throws {
        let lookup = #"{"resultCount":1,"results":[{"feedUrl":"https://example.com/feed.xml"}]}"#
        XCTAssertEqual(try FeedDiscoveryParser.parseAppleLookupFeedURL(Data(lookup.utf8)), "https://example.com/feed.xml")

        let nextData = """
        <html><head><link rel="canonical" href="https://www.xiaoyuzhoufm.com/podcast/show"></head>
        <body><script id="__NEXT_DATA__" type="application/json">{"props":{"pageProps":{"podcast":{"pid":"show","title":"小宇宙栏目","episodes":[{"eid":"abc","title":"001. 小宇宙单集","pubDate":"2026-05-28T00:00:00Z","duration":"600","shownotes":"Shownotes","enclosure":{"url":"https://media.example/xyz.m4a"}}]}}}}</script></body></html>
        """

        let discovery = try FeedDiscoveryParser.parseXiaoyuzhouPodcastHTML(nextData, sourceURL: "https://www.xiaoyuzhoufm.com/podcast/show")

        XCTAssertEqual(discovery.title, "小宇宙栏目")
        XCTAssertEqual(discovery.source, "xiaoyuzhou")
        XCTAssertEqual(discovery.episodes.first?.guid, "abc")
        XCTAssertEqual(discovery.episodes.first?.audioURL, "https://media.example/xyz.m4a")
    }
}

private func temporaryDefaults() throws -> UserDefaults {
    let suiteName = "com.audio2text.tests.\(UUID().uuidString)"
    guard let defaults = UserDefaults(suiteName: suiteName) else {
        throw XCTSkip("Could not create isolated UserDefaults suite.")
    }
    defaults.removePersistentDomain(forName: suiteName)
    return defaults
}

private func sharedFixtureLibraryRoot() throws -> URL {
    try XCTUnwrap(Bundle.module.url(forResource: "Audio2TextLibrary", withExtension: nil, subdirectory: "Fixtures"))
}

private struct LibrarySyncStatusTestError: LocalizedError {
    var errorDescription: String? {
        "simulated upload error"
    }
}

private func jsonObject(at url: URL) throws -> [String: Any] {
    let data = try Data(contentsOf: url)
    return try XCTUnwrap(JSONSerialization.jsonObject(with: data) as? [String: Any])
}

private func writeJSONObject(_ object: [String: Any], to url: URL) throws {
    try FileManager.default.createDirectory(at: url.deletingLastPathComponent(), withIntermediateDirectories: true)
    let data = try JSONSerialization.data(withJSONObject: object, options: [.prettyPrinted, .sortedKeys])
    try data.write(to: url, options: .atomic)
}

extension LibraryCoreTests {
    func testMobileCredentialMigrationIsSecureAndFailureDoesNotEraseLegacyValue() throws {
        let defaults = try temporaryDefaults()
        let credentials = MemoryCloudCredentials()
        let store = MobileCloudSettingsStore(defaults: defaults, credentials: credentials)
        defaults.set("legacy-test-key", forKey: MobileCloudSettingsStore.apiKeyKey)
        credentials.fails = true
        XCTAssertThrowsError(try store.load())
        XCTAssertEqual(defaults.string(forKey: MobileCloudSettingsStore.apiKeyKey), "legacy-test-key")
        credentials.fails = false
        XCTAssertEqual(try store.load().apiKey, "legacy-test-key")
        XCTAssertNil(defaults.string(forKey: MobileCloudSettingsStore.apiKeyKey))
        try store.delete()
        XCTAssertNil(try credentials.load(account: "mobile.cloud.apiKey"))
    }
}
