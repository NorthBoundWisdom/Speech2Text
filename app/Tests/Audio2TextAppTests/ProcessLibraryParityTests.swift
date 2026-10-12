@testable import Audio2TextApp
import XCTest

final class ProcessLibraryParityTests: XCTestCase {
    @MainActor
    func testScanUsesLibraryEpisodesAsPrimarySourceAndIgnoresStrayRuntimeFolders() throws {
        let dataRoot = temporaryDataRoot()
        defer { try? FileManager.default.removeItem(at: dataRoot.deletingLastPathComponent()) }
        try configureLocalLibrary(dataRoot: dataRoot)
        try writeLibraryEpisode(
            dataRoot: dataRoot,
            id: "library-only",
            title: "Library Metadata Episode",
            metadata: [
                "source": "podcast_rss",
                "source_url": "https://podcast.example/golden/rss/001",
                "canonical_url": "https://podcast.example/golden/rss/001",
                "audio_url": "https://media.example/golden/rss-001.m4a",
                "subscription_id": "podcast_rss-test",
            ]
        )
        try writeStrayRuntimeFiles(dataRoot: dataRoot, id: "runtime-only")

        let items = ProcessLibrary.scan(dataRoot: dataRoot)
        let item = try XCTUnwrap(items.first)

        XCTAssertEqual(items.map(\.id), ["library-only"])
        XCTAssertEqual(item.title, "Library Metadata Episode")
        XCTAssertEqual(item.source, "podcast_rss")
        XCTAssertEqual(item.sourceURL, "https://podcast.example/golden/rss/001")
        XCTAssertEqual(item.subscriptionID, "podcast_rss-test")
        XCTAssertEqual(item.mediaURL, "https://media.example/golden/rss-001.m4a")
        XCTAssertEqual(item.status, "Audio pending")
        XCTAssertEqual(item.detail, "Metadata exists")
        XCTAssertFalse(item.hasFile)
        XCTAssertFalse(item.hasProcessed)
        XCTAssertTrue(item.canDownloadAudio)
        XCTAssertTrue(item.canRestoreAudio)
        let controller = JobController(settingsStore: AppSettingsStore(dataRoot: dataRoot, credentials: MemoryCloudCredentials()), loadsLibrarySynchronously: true)
        XCTAssertTrue(controller.canDownloadAudio(for: item))
        XCTAssertTrue(controller.canProcessLibraryItem(item, workflow: .localOnly))
        XCTAssertFalse(controller.canProcessLibraryItem(item, workflow: .transcribeAndSummarize))
        XCTAssertEqual(
            item.audioURL.resolvingSymlinksInPath().path,
            dataRoot.appendingPathComponent("materials/library-only/Library-Metadata-Episode.m4a").resolvingSymlinksInPath().path
        )
        XCTAssertEqual(
            item.outputURL.resolvingSymlinksInPath().path,
            dataRoot.appendingPathComponent("work/library-only").resolvingSymlinksInPath().path
        )
    }

    func testLocalMaterialsAndWorkOnlyDecorateExistingLibraryEpisodes() throws {
        let dataRoot = temporaryDataRoot()
        defer { try? FileManager.default.removeItem(at: dataRoot.deletingLastPathComponent()) }
        try configureLocalLibrary(dataRoot: dataRoot)
        try writeLibraryEpisode(
            dataRoot: dataRoot,
            id: "ready-to-process",
            title: "Ready To Process",
            metadata: [
                "source": "podcast_rss",
                "audio_url": "https://media.example/golden/ready.mp3",
            ]
        )
        try writeLibraryEpisode(
            dataRoot: dataRoot,
            id: "processed-by-work",
            title: "Processed By Work",
            metadata: [
                "source": "podcast_rss",
                "audio_url": "https://media.example/golden/processed.mp3",
            ]
        )
        try writeMaterial(dataRoot: dataRoot, id: "processed-by-work", filename: "source.mp3")
        try writeCompletedWork(dataRoot: dataRoot, id: "processed-by-work")
        try writeStrayRuntimeFiles(dataRoot: dataRoot, id: "runtime-only")

        let items = Dictionary(uniqueKeysWithValues: ProcessLibrary.scan(dataRoot: dataRoot).map { ($0.id, $0) })
        let ready = try XCTUnwrap(items["ready-to-process"])
        let processed = try XCTUnwrap(items["processed-by-work"])

        XCTAssertEqual(Set(items.keys), ["ready-to-process", "processed-by-work"])
        XCTAssertFalse(ready.hasFile)
        XCTAssertFalse(ready.hasOutput)
        XCTAssertFalse(ready.hasProcessed)
        XCTAssertEqual(ready.status, "Audio pending")

        XCTAssertEqual(
            processed.audioURL.resolvingSymlinksInPath().path,
            dataRoot.appendingPathComponent("materials/processed-by-work/source.mp3").resolvingSymlinksInPath().path
        )
        XCTAssertEqual(
            processed.outputURL.resolvingSymlinksInPath().path,
            dataRoot.appendingPathComponent("work/processed-by-work").resolvingSymlinksInPath().path
        )
        XCTAssertTrue(processed.hasFile)
        XCTAssertTrue(processed.hasOutput)
        XCTAssertTrue(processed.hasTranscript)
        XCTAssertTrue(processed.hasProcessed)
        XCTAssertEqual(processed.status, "Processed")
        XCTAssertTrue(processed.detail.hasPrefix("Chunks 1/1"))
        XCTAssertNotNil(processed.processedAt)
    }
}

private func temporaryDataRoot() -> URL {
    URL(fileURLWithPath: NSTemporaryDirectory())
        .appendingPathComponent("ProcessLibraryParityTests-\(UUID().uuidString)", isDirectory: true)
        .appendingPathComponent("data", isDirectory: true)
}

private func configureLocalLibrary(dataRoot: URL) throws {
    try FileManager.default.createDirectory(at: dataRoot, withIntermediateDirectories: true)
    try """
    [library]
    storage = "local"
    icloud_root = ""
    local_root = ""
    """.write(to: dataRoot.appendingPathComponent("config.toml"), atomically: true, encoding: .utf8)
}

private func writeLibraryEpisode(
    dataRoot: URL,
    id: String,
    title: String,
    metadata: [String: Any] = [:]
) throws {
    let libraryRoot = dataRoot.appendingPathComponent("Audio2TextLibrary", isDirectory: true)
    let episodeRoot = libraryRoot.appendingPathComponent("episodes/\(id)", isDirectory: true)
    var record: [String: Any] = [
        "schema_version": 1,
        "kind": "audio2text.library.episode",
        "episode_id": id,
        "title": title,
        "source": "podcast_rss",
        "app_group": ProcessLibrary.defaultGroupName,
        "app_read": false,
        "app_star": false,
        "app_status": ArticleNodeStatus.link.rawValue,
        "app_queue_status": AppQueueStatus.unread.rawValue,
        "product_status": "metadata_only",
        "documents": [],
    ]
    for (key, value) in metadata {
        record[key] = value
    }
    try writeJSONObject(record, to: episodeRoot.appendingPathComponent("episode.json"))
    try writeLibraryManifest(dataRoot: dataRoot)
}

private func writeMaterial(dataRoot: URL, id: String, filename: String) throws {
    let url = dataRoot.appendingPathComponent("materials/\(id)/\(filename)")
    try FileManager.default.createDirectory(at: url.deletingLastPathComponent(), withIntermediateDirectories: true)
    try "audio".write(to: url, atomically: true, encoding: .utf8)
}

private func writeCompletedWork(dataRoot: URL, id: String) throws {
    let workRoot = dataRoot.appendingPathComponent("work/\(id)", isDirectory: true)
    try FileManager.default.createDirectory(at: workRoot, withIntermediateDirectories: true)
    try #"{"success":true,"chunks":[{}],"chunk_status_counts":{"transcribed":1}}"#.write(
        to: workRoot.appendingPathComponent("run.json"),
        atomically: true,
        encoding: .utf8
    )
    try "transcript".write(to: workRoot.appendingPathComponent("transcript.readable.md"), atomically: true, encoding: .utf8)
}

private func writeStrayRuntimeFiles(dataRoot: URL, id: String) throws {
    try writeMaterial(dataRoot: dataRoot, id: id, filename: "stray.m4a")
    let workRoot = dataRoot.appendingPathComponent("work/\(id)", isDirectory: true)
    try FileManager.default.createDirectory(at: workRoot, withIntermediateDirectories: true)
    try #"{"success":true}"#.write(to: workRoot.appendingPathComponent("run.json"), atomically: true, encoding: .utf8)
}

private func writeLibraryManifest(dataRoot: URL) throws {
    let libraryRoot = dataRoot.appendingPathComponent("Audio2TextLibrary", isDirectory: true)
    let episodeRoot = libraryRoot.appendingPathComponent("episodes", isDirectory: true)
    let episodes = ((try? FileManager.default.contentsOfDirectory(at: episodeRoot, includingPropertiesForKeys: nil)) ?? [])
        .filter { FileManager.default.fileExists(atPath: $0.appendingPathComponent("episode.json").path) }
        .map { ["episode_id": $0.lastPathComponent, "path": "episodes/\($0.lastPathComponent)/episode.json"] }
        .sorted { ($0["episode_id"] ?? "") < ($1["episode_id"] ?? "") }
    try writeJSONObject(
        [
            "schema_version": 1,
            "kind": "audio2text.library.manifest",
            "updated_at": "2026-05-31T00:00:00Z",
            "episode_count": episodes.count,
            "subscription_count": 0,
            "tombstone_count": 0,
            "episodes": episodes,
            "subscriptions": [],
            "tombstones": [],
        ],
        to: libraryRoot.appendingPathComponent("manifest.json")
    )
}

private func writeJSONObject(_ object: [String: Any], to url: URL) throws {
    try FileManager.default.createDirectory(at: url.deletingLastPathComponent(), withIntermediateDirectories: true)
    let data = try JSONSerialization.data(withJSONObject: object, options: [.prettyPrinted, .sortedKeys])
    try data.write(to: url, options: .atomic)
}
