import CryptoKit
import Foundation
#if canImport(Audio2TextCore)
    import Audio2TextCore
#endif

enum LocalImportMode: String, CaseIterable, Identifiable {
    case copy
    case reference

    var id: String {
        rawValue
    }

    var title: String {
        switch self {
        case .copy: return "复制"
        case .reference: return "引用"
        }
    }
}

struct LocalAudioImporter {
    let dataRoot: URL
    let libraryRoot: URL
    let groupName: String
    let now: () -> Date

    init(
        dataRoot: URL = AppPaths.dataRoot(),
        libraryRoot: URL? = nil,
        groupName: String = ProcessLibrary.defaultGroupName,
        now: @escaping () -> Date = Date.init
    ) {
        self.dataRoot = dataRoot
        self.libraryRoot = libraryRoot ?? AppSettingsStore(dataRoot: dataRoot).libraryRoot()
        self.groupName = groupName
        self.now = now
    }

    func importAudio(_ sourceURL: URL, mode: LocalImportMode = .copy) throws -> URL {
        let fileManager = FileManager.default
        guard fileManager.fileExists(atPath: sourceURL.path) else {
            throw AppError.missingLocalFile
        }
        let scopedAccess = sourceURL.startAccessingSecurityScopedResource()
        defer {
            if scopedAccess {
                sourceURL.stopAccessingSecurityScopedResource()
            }
        }

        let stem = sourceURL.deletingPathExtension().lastPathComponent
        let fingerprint = try fileFingerprint(sourceURL)
        let digest = fingerprint["sha256"] as? String
        let episodeID = StableEpisodeID.make(
            source: "local",
            subscriptionID: nil,
            guid: digest,
            audioURL: nil,
            canonicalURL: nil,
            sourceURL: nil,
            title: stem
        )
        let episodeDirectory = AppPaths.materialsRoot(dataRoot: dataRoot).appendingPathComponent(episodeID, isDirectory: true)
        try fileManager.createDirectory(at: episodeDirectory, withIntermediateDirectories: true)

        let target = episodeDirectory.appendingPathComponent(sourceURL.lastPathComponent)
        do {
            if !fileManager.fileExists(atPath: target.path) {
                switch mode {
                case .copy:
                    try fileManager.copyItem(at: sourceURL, to: target)
                case .reference:
                    try fileManager.createSymbolicLink(at: target, withDestinationURL: sourceURL)
                }
            }
            try writeTopic(for: target, sourceURL: sourceURL, episodeDirectory: episodeDirectory, mode: mode)
            try writeMetadata(
                episodeID: episodeID,
                for: target,
                sourceURL: sourceURL,
                episodeDirectory: episodeDirectory,
                fingerprint: fingerprint,
                mode: mode
            )
            return target
        } catch {
            throw AppError.fileCopyFailed("Could not import local media: \(error.localizedDescription)")
        }
    }

    private func uniqueDirectory(_ base: URL) -> URL {
        let fileManager = FileManager.default
        if !fileManager.fileExists(atPath: base.path) {
            return base
        }
        for index in 2 ... 999 {
            let candidate = URL(fileURLWithPath: "\(base.path)-\(index)")
            if !fileManager.fileExists(atPath: candidate.path) {
                return candidate
            }
        }
        return URL(fileURLWithPath: "\(base.path)-\(UUID().uuidString.prefix(8))")
    }

    private func writeTopic(for target: URL, sourceURL: URL, episodeDirectory: URL, mode: LocalImportMode) throws {
        let title = target.deletingPathExtension().lastPathComponent
        let formatter = ISO8601DateFormatter()
        let text = """
        # \(title)

        - 来源：本地音视频
        - 导入模式：\(mode.rawValue)
        - 导入时间：\(formatter.string(from: now()))
        - 原始文件：\(sourceURL.path)
        - 媒体：\(target.lastPathComponent)

        ## Shownotes

        本地导入音视频。
        """
        try text.write(
            to: episodeDirectory.appendingPathComponent("主题.md"),
            atomically: true,
            encoding: .utf8
        )
    }

    private func writeMetadata(
        episodeID: String,
        for target: URL,
        sourceURL: URL,
        episodeDirectory: URL,
        fingerprint: [String: Any],
        mode: LocalImportMode
    ) throws {
        let formatter = ISO8601DateFormatter()
        let timestamp = formatter.string(from: now())
        let normalizedGroupName = ProcessLibrary.pathComponent(forGroupName: groupName)
        try LibraryWriter.upsertGroup(normalizedGroupName, in: libraryRoot)
        let publicPayload: [String: Any] = [
            "schema_version": 1,
            "kind": "audio2text.library.episode",
            "episode_id": episodeID,
            "app_read": false,
            "app_star": false,
            "app_queue_status": AppQueueStatus.unread.rawValue,
            "app_status": ArticleNodeStatus.import.rawValue,
            "app_status_updated_at": timestamp,
            "source": "local",
            "title": target.deletingPathExtension().lastPathComponent,
            "app_group": normalizedGroupName,
            "imported_at": timestamp,
            "import_mode": mode.rawValue,
            "media_filename": target.lastPathComponent,
            "product_status": "metadata_only",
            "documents": [],
        ]
        let recordURL = libraryRoot
            .appendingPathComponent("episodes", isDirectory: true)
            .appendingPathComponent(episodeID, isDirectory: true)
            .appendingPathComponent("episode.json")
        try writeJSON(publicPayload, to: recordURL)

        var localPayload: [String: Any] = [
            "schema_version": 1,
            "episode_id": episodeID,
            "import_mode": mode.rawValue,
            "audio_path": target.path,
            "original_path": sourceURL.path,
            "original_fingerprint": fingerprint,
            "topic_path": episodeDirectory.appendingPathComponent("主题.md").path,
        ]
        if let bookmark = try? sourceURL.bookmarkData(
            options: [.withSecurityScope],
            includingResourceValuesForKeys: nil,
            relativeTo: nil
        ) {
            localPayload["original_bookmark"] = bookmark.base64EncodedString()
        }
        try writeJSON(localPayload, to: episodeDirectory.appendingPathComponent("local.json"))
        try rebuildManifest()
    }

    private func fileFingerprint(_ url: URL) throws -> [String: Any] {
        let data = try Data(contentsOf: url)
        let digest = SHA256.hash(data: data).map { String(format: "%02x", $0) }.joined()
        let values = try url.resourceValues(forKeys: [.fileSizeKey, .contentModificationDateKey])
        return [
            "size_bytes": values.fileSize ?? data.count,
            "mtime": values.contentModificationDate?.timeIntervalSince1970 ?? 0,
            "sha256": digest,
        ]
    }

    private func writeJSON(_ object: [String: Any], to url: URL) throws {
        try FileManager.default.createDirectory(at: url.deletingLastPathComponent(), withIntermediateDirectories: true)
        let data = try JSONSerialization.data(withJSONObject: object, options: [.prettyPrinted, .sortedKeys])
        try data.write(to: url, options: .atomic)
    }

    private func rebuildManifest() throws {
        let episodeRoot = libraryRoot.appendingPathComponent("episodes", isDirectory: true)
        let subscriptionRoot = libraryRoot.appendingPathComponent("subscriptions", isDirectory: true)
        let tombstoneRoot = libraryRoot.appendingPathComponent("tombstones/episodes", isDirectory: true)
        let episodes = ((try? FileManager.default.contentsOfDirectory(at: episodeRoot, includingPropertiesForKeys: nil)) ?? [])
            .filter { FileManager.default.fileExists(atPath: $0.appendingPathComponent("episode.json").path) }
            .map { ["episode_id": $0.lastPathComponent, "path": "episodes/\($0.lastPathComponent)/episode.json"] }
            .sorted { ($0["episode_id"] ?? "") < ($1["episode_id"] ?? "") }
        let subscriptions = ((try? FileManager.default.contentsOfDirectory(at: subscriptionRoot, includingPropertiesForKeys: nil)) ?? [])
            .filter { $0.pathExtension == "json" }
            .map { ["id": $0.deletingPathExtension().lastPathComponent, "path": "subscriptions/\($0.lastPathComponent)"] }
            .sorted { ($0["id"] ?? "") < ($1["id"] ?? "") }
        let tombstones = ((try? FileManager.default.contentsOfDirectory(at: tombstoneRoot, includingPropertiesForKeys: nil)) ?? [])
            .filter { $0.pathExtension == "json" }
            .map { ["episode_id": $0.deletingPathExtension().lastPathComponent, "path": "tombstones/episodes/\($0.lastPathComponent)"] }
            .sorted { ($0["episode_id"] ?? "") < ($1["episode_id"] ?? "") }
        try writeJSON(
            [
                "schema_version": 1,
                "kind": "audio2text.library.manifest",
                "updated_at": ISO8601DateFormatter().string(from: now()),
                "episode_count": episodes.count,
                "subscription_count": subscriptions.count,
                "tombstone_count": tombstones.count,
                "episodes": episodes,
                "subscriptions": subscriptions,
                "tombstones": tombstones,
            ],
            to: libraryRoot.appendingPathComponent("manifest.json")
        )
    }
}
