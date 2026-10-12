@testable import Audio2TextApp
import Audio2TextCore
import XCTest

@MainActor
func testJobController() -> JobController {
    let dataRoot = URL(fileURLWithPath: NSTemporaryDirectory()).appendingPathComponent(UUID().uuidString)
    _ = try? configureLocalTestLibrary(dataRoot: dataRoot)
    let settingsStore = AppSettingsStore(dataRoot: dataRoot, credentials: MemoryCloudCredentials())
    return JobController(settingsStore: settingsStore, loadsLibrarySynchronously: true)
}

func testLibraryItem(
    id: String,
    title: String,
    originalTitle: String? = nil,
    groupName: String = ProcessLibrary.defaultGroupName,
    audioURL: URL,
    status: String = "Not processed",
    nodeStatus: ArticleNodeStatus = .import,
    hasFile: Bool? = nil,
    hasProcessed: Bool? = nil,
    hasTranscript: Bool = false,
    hasOutput: Bool = false,
    runStatus: String = "missing",
    source: String = "local",
    sourceURL: String? = nil,
    subscriptionID: String? = nil,
    seriesURL: String? = nil,
    mediaURL: String? = nil,
    publishedAt: String? = nil,
    originalPath: String? = nil,
    originalBookmark: Data? = nil,
    isRead: Bool = false,
    isStarred: Bool = false,
    queueStatus: AppQueueStatus = .unread,
    isArchived: Bool = false,
    processedAt: Date? = nil,
    modifiedAt: Date
) -> ProcessLibraryItem {
    let resolvedHasFile = hasFile ?? ProcessLibrary.isExistingNonEmptyFile(audioURL)
    let resolvedHasProcessed = hasProcessed ?? ((status == "QA pass" || status == "Processed") && hasTranscript)
    return ProcessLibraryItem(
        id: id,
        title: title,
        originalTitle: originalTitle,
        groupName: groupName,
        nodeStatus: nodeStatus,
        audioURL: audioURL,
        outputURL: audioURL.deletingLastPathComponent().appendingPathComponent("output-\(id)"),
        status: status,
        detail: "",
        hasFile: resolvedHasFile,
        hasProcessed: resolvedHasProcessed,
        hasTranscript: hasTranscript,
        hasOutput: hasOutput,
        runStatus: runStatus,
        source: source,
        sourceURL: sourceURL,
        subscriptionID: subscriptionID,
        seriesURL: seriesURL,
        mediaURL: mediaURL,
        publishedAt: publishedAt,
        originalPath: originalPath,
        originalBookmark: originalBookmark,
        isRead: isRead,
        isStarred: isStarred,
        queueStatus: queueStatus,
        isArchived: isArchived,
        modifiedAt: modifiedAt,
        processedAt: processedAt
    )
}

extension ProcessLibraryItem {
    func withDocumentsURL(_ documentsURL: URL) -> ProcessLibraryItem {
        ProcessLibraryItem(
            id: id,
            title: title,
            originalTitle: originalTitle,
            groupName: groupName,
            nodeStatus: nodeStatus,
            audioURL: audioURL,
            outputURL: outputURL,
            documentsURL: documentsURL,
            status: status,
            detail: detail,
            hasFile: hasFile,
            hasProcessed: hasProcessed,
            hasTranscript: hasTranscript,
            hasOutput: hasOutput,
            runStatus: runStatus,
            source: source,
            sourceURL: sourceURL,
            subscriptionID: subscriptionID,
            seriesURL: seriesURL,
            mediaURL: mediaURL,
            publishedAt: publishedAt,
            originalPath: originalPath,
            originalBookmark: originalBookmark,
            isRead: isRead,
            isStarred: isStarred,
            queueStatus: queueStatus,
            isArchived: isArchived,
            modifiedAt: modifiedAt,
            processedAt: processedAt
        )
    }
}

struct TestLibraryEpisode {
    let id: String
    let libraryRoot: URL
    let episodeRoot: URL
    let recordURL: URL
    let materialRoot: URL
    let audioURL: URL
    let workRoot: URL
    let documentsRoot: URL
}

@discardableResult
func configureLocalTestLibrary(dataRoot: URL) throws -> URL {
    try FileManager.default.createDirectory(at: dataRoot, withIntermediateDirectories: true)
    try """
    [library]
    storage = "local"
    icloud_root = ""
    local_root = ""
    """.write(to: dataRoot.appendingPathComponent("config.toml"), atomically: true, encoding: .utf8)
    return dataRoot.appendingPathComponent("Audio2TextLibrary", isDirectory: true)
}

@discardableResult
func writeTestLibraryEpisode(
    dataRoot: URL,
    id: String = "episode-\(UUID().uuidString)",
    title: String,
    metadata: [String: Any] = [:],
    audioFileName: String = "show.m4a",
    audioContents: String? = "audio",
    documents: [String: String] = [:]
) throws -> TestLibraryEpisode {
    let libraryRoot = try configureLocalTestLibrary(dataRoot: dataRoot)
    let episodeRoot = libraryRoot.appendingPathComponent("episodes", isDirectory: true).appendingPathComponent(id, isDirectory: true)
    let documentsRoot = episodeRoot.appendingPathComponent("documents", isDirectory: true)
    let materialRoot = dataRoot.appendingPathComponent("materials", isDirectory: true).appendingPathComponent(id, isDirectory: true)
    let workRoot = dataRoot.appendingPathComponent("work", isDirectory: true).appendingPathComponent(id, isDirectory: true)
    try FileManager.default.createDirectory(at: episodeRoot, withIntermediateDirectories: true)
    try FileManager.default.createDirectory(at: materialRoot, withIntermediateDirectories: true)
    if !documents.isEmpty {
        try FileManager.default.createDirectory(at: documentsRoot, withIntermediateDirectories: true)
        for (name, text) in documents {
            try text.write(to: documentsRoot.appendingPathComponent(name), atomically: true, encoding: .utf8)
        }
    }
    let audioURL = materialRoot.appendingPathComponent(audioFileName)
    if let audioContents {
        try audioContents.write(to: audioURL, atomically: true, encoding: .utf8)
    }

    var record: [String: Any] = [
        "schema_version": 1,
        "kind": "audio2text.library.episode",
        "episode_id": id,
        "title": title,
        "source": metadata["source"] ?? "local",
        "app_group": metadata["app_group"] ?? ProcessLibrary.defaultGroupName,
        "app_read": metadata["app_read"] ?? false,
        "app_star": metadata["app_star"] ?? false,
        "app_queue_status": metadata["app_queue_status"] ?? AppQueueStatus.unread.rawValue,
        "product_status": documents.isEmpty ? "metadata_only" : "available",
        "documents": documents.keys.sorted().map { ["name": $0, "path": "documents/\($0)"] },
        "media_filename": audioFileName,
    ]
    if record["source"] as? String == "local" {
        record["app_status"] = metadata["app_status"] ?? ArticleNodeStatus.import.rawValue
    }
    for (key, value) in metadata {
        record[key] = value
    }
    try writeJSON(record, to: episodeRoot.appendingPathComponent("episode.json"))
    try writeLibraryManifest(root: libraryRoot)
    return TestLibraryEpisode(
        id: id,
        libraryRoot: libraryRoot,
        episodeRoot: episodeRoot,
        recordURL: episodeRoot.appendingPathComponent("episode.json"),
        materialRoot: materialRoot,
        audioURL: audioURL,
        workRoot: workRoot,
        documentsRoot: documentsRoot
    )
}

func writeLibraryManifest(root: URL) throws {
    let episodesRoot = root.appendingPathComponent("episodes", isDirectory: true)
    let subscriptionsRoot = root.appendingPathComponent("subscriptions", isDirectory: true)
    let episodes = ((try? FileManager.default.contentsOfDirectory(at: episodesRoot, includingPropertiesForKeys: nil)) ?? [])
        .filter { FileManager.default.fileExists(atPath: $0.appendingPathComponent("episode.json").path) }
        .map { ["episode_id": $0.lastPathComponent, "path": "episodes/\($0.lastPathComponent)/episode.json"] }
        .sorted { ($0["episode_id"] ?? "") < ($1["episode_id"] ?? "") }
    let subscriptions = ((try? FileManager.default.contentsOfDirectory(at: subscriptionsRoot, includingPropertiesForKeys: nil)) ?? [])
        .filter { $0.pathExtension == "json" }
        .map { ["id": $0.deletingPathExtension().lastPathComponent, "path": "subscriptions/\($0.lastPathComponent)"] }
        .sorted { ($0["id"] ?? "") < ($1["id"] ?? "") }
    try writeJSON(
        [
            "schema_version": 1,
            "kind": "audio2text.library.manifest",
            "updated_at": "2026-05-29T00:00:00Z",
            "episode_count": episodes.count,
            "subscription_count": subscriptions.count,
            "tombstone_count": 0,
            "episodes": episodes,
            "subscriptions": subscriptions,
            "tombstones": [],
        ],
        to: root.appendingPathComponent("manifest.json")
    )
}
