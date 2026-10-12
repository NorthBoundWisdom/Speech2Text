import Foundation
#if canImport(Audio2TextCore)
    import Audio2TextCore
#endif

enum ArticleNodeStatus: String, Equatable, Codable {
    case link
    case `import`
    case outside
}

typealias AppQueueStatus = LibraryQueueStatus

struct ChannelEpisodeDetails: Equatable {
    let title: String
    let seriesName: String?
    let sourceName: String?
    let sourceURL: String?
    let seriesURL: String?
    let publishedAt: String?
    let duration: String?
    let description: String
    let audioURL: String?
    let imageURL: String?
    let guid: String?

    var primaryURL: String? {
        sourceURL ?? seriesURL ?? audioURL
    }
}

struct ProcessLibraryItem: Identifiable, Equatable, Codable {
    let id: String
    let title: String
    let originalTitle: String?
    let groupName: String
    let nodeStatus: ArticleNodeStatus
    let audioURL: URL
    let outputURL: URL
    let documentsURL: URL?
    let status: String
    let detail: String
    let hasFile: Bool
    let hasProcessed: Bool
    let hasTranscript: Bool
    let hasOutput: Bool
    let runStatus: String
    let source: String
    let sourceURL: String?
    let subscriptionID: String?
    let seriesURL: String?
    let mediaURL: String?
    let publishedAt: String?
    let originalPath: String?
    let originalBookmark: Data?
    let isRead: Bool
    let isStarred: Bool
    let queueStatus: AppQueueStatus
    let isArchived: Bool
    let modifiedAt: Date
    let processedAt: Date?

    init(
        id: String,
        title: String,
        originalTitle: String? = nil,
        groupName: String,
        nodeStatus: ArticleNodeStatus,
        audioURL: URL,
        outputURL: URL,
        documentsURL: URL? = nil,
        status: String,
        detail: String,
        hasFile: Bool,
        hasProcessed: Bool,
        hasTranscript: Bool,
        hasOutput: Bool,
        runStatus: String,
        source: String,
        sourceURL: String?,
        subscriptionID: String?,
        seriesURL: String?,
        mediaURL: String?,
        publishedAt: String? = nil,
        originalPath: String?,
        originalBookmark: Data?,
        isRead: Bool,
        isStarred: Bool,
        queueStatus: AppQueueStatus,
        isArchived: Bool = false,
        modifiedAt: Date,
        processedAt: Date? = nil
    ) {
        self.id = id
        self.title = title
        self.originalTitle = originalTitle
        self.groupName = groupName
        self.nodeStatus = nodeStatus
        self.audioURL = audioURL
        self.outputURL = outputURL
        self.documentsURL = documentsURL
        self.status = status
        self.detail = detail
        self.hasFile = hasFile
        self.hasProcessed = hasProcessed
        self.hasTranscript = hasTranscript
        self.hasOutput = hasOutput
        self.runStatus = runStatus
        self.source = source
        self.sourceURL = sourceURL
        self.subscriptionID = subscriptionID
        self.seriesURL = seriesURL
        self.mediaURL = mediaURL
        self.publishedAt = publishedAt
        self.originalPath = originalPath
        self.originalBookmark = originalBookmark
        self.isRead = isRead
        self.isStarred = isStarred
        self.queueStatus = queueStatus
        self.isArchived = isArchived
        self.modifiedAt = modifiedAt
        self.processedAt = processedAt
    }

    var isAudioPresent: Bool {
        hasFile
    }

    var isProcessed: Bool {
        hasProcessed
    }

    var needsReanalysis: Bool {
        isAudioPresent && hasOutput && !isProcessed
    }

    var remoteAudioURL: URL? {
        guard source != "local", let mediaURL else { return nil }
        return URL(string: mediaURL)
    }

    var canDownloadAudio: Bool {
        !isProcessed && remoteAudioURL != nil
    }

    var canRestoreAudio: Bool {
        guard !isAudioPresent else { return false }
        if remoteAudioURL != nil {
            return true
        }
        if originalBookmark != nil {
            return true
        }
        if let originalPath {
            return ProcessLibrary.isExistingNonEmptyFile(URL(fileURLWithPath: originalPath))
        }
        return false
    }

    func withProcessingStatus(
        status: String,
        detail: String,
        hasProcessed: Bool,
        hasTranscript: Bool,
        hasOutput: Bool,
        runStatus: String,
        processedAt: Date?
    ) -> ProcessLibraryItem {
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

struct ProcessLibrarySection: Identifiable, Equatable {
    let id: String
    let title: String
    let items: [ProcessLibraryItem]

    var processedCount: Int {
        items.filter(\.isProcessed).count
    }
}

enum ProcessLibrary {
    static let defaultGroupName = LibrarySidebarState.defaultGroupName

    #if DEBUG
        static var scanInvocationObserver: ((URL) -> Void)?
    #endif

    private static let mediaExtensions: Set<String> = [
        "m4a", "mp3", "wav", "flac", "aac",
        "mp4", "m4v", "mov", "mkv", "webm",
    ]

    static func pathComponent(forGroupName name: String) -> String {
        guard !name.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
            return defaultGroupName
        }
        let normalized = PathTools.sanitizedSlug(name)
        return normalized.isEmpty ? defaultGroupName : normalized
    }

    static func scan(dataRoot: URL = AppPaths.dataRoot()) -> [ProcessLibraryItem] {
        #if DEBUG
            scanInvocationObserver?(dataRoot)
        #endif
        return scanUnifiedLibrary(dataRoot: dataRoot)
    }

    private static func scanUnifiedLibrary(dataRoot: URL) -> [ProcessLibraryItem] {
        let manager = FileManager.default
        let libraryRoot = authoritativeLibraryRoot(dataRoot: dataRoot)
        let fingerprint = libraryFingerprint(dataRoot: dataRoot)
        if let cached = loadIndex(dataRoot: dataRoot, fingerprint: fingerprint) {
            return cached
        }
        let episodeRoot = libraryRoot.appendingPathComponent("episodes", isDirectory: true)
        let episodeDirectories = (try? manager.contentsOfDirectory(
            at: episodeRoot,
            includingPropertiesForKeys: [.isDirectoryKey, .contentModificationDateKey],
            options: [.skipsHiddenFiles]
        )) ?? []

        var items: [ProcessLibraryItem] = []
        for episodeDirectory in episodeDirectories where isDirectory(episodeDirectory) {
            let episodeID = episodeDirectory.lastPathComponent
            let metadata = metadataObject(in: episodeDirectory)
            guard !metadata.isEmpty else { continue }
            let localMetadata = localMetadataObject(forEpisodeID: episodeID, dataRoot: dataRoot)
            let audioURL = localAudioURL(forEpisodeID: episodeID, metadata: metadata, dataRoot: dataRoot)
            let recoverableAudioPath = recoverableLocalAudioPath(
                forEpisodeID: episodeID,
                metadata: metadata,
                localMetadata: localMetadata,
                dataRoot: dataRoot
            )
            let outputURL = AppPaths.workRoot(dataRoot: dataRoot).appendingPathComponent(episodeID, isDirectory: true)
            let documentsURL = episodeDirectory.appendingPathComponent("documents", isDirectory: true)
            let snapshot = OutputWatcher.libraryListSnapshot(outputDirectory: outputURL, documentsDirectory: documentsURL)
            let isAudioPresent = isExistingNonEmptyFile(audioURL)
            let hasDocuments = isExistingNonEmptyFile(documentsURL.appendingPathComponent("summary.md"))
                || isExistingNonEmptyFile(documentsURL.appendingPathComponent("transcript.md"))
            let hasOutput = FileManager.default.fileExists(atPath: outputURL.path) || hasDocuments
            let hasProcessed = hasDocuments || isProcessed(snapshot)
            let processingModifiedAt = modificationDate(for: documentsURL)
                ?? modificationDate(for: outputURL)
            let modifiedAt = modificationDate(for: documentsURL)
                ?? modificationDate(for: outputURL)
                ?? modificationDate(for: audioURL)
                ?? modificationDate(for: episodeDirectory.appendingPathComponent("episode.json"))
                ?? .distantPast
            let processedAt = parsedDate(optionalStringValue(metadata["processed_at"]))
                ?? (hasProcessed ? processingModifiedAt : nil)
            let title = episodeTitle(from: metadata)
                ?? episodeID
            items.append(
                ProcessLibraryItem(
                    id: episodeID,
                    title: title,
                    originalTitle: optionalStringValue(metadata["original_title"]),
                    groupName: groupName(from: metadata),
                    nodeStatus: nodeStatus(from: metadata),
                    audioURL: audioURL,
                    outputURL: outputURL,
                    documentsURL: documentsURL,
                    status: status(for: snapshot, outputURL: outputURL, isAudioPresent: isAudioPresent),
                    detail: detail(for: snapshot, outputURL: outputURL, isAudioPresent: isAudioPresent),
                    hasFile: isAudioPresent,
                    hasProcessed: hasProcessed,
                    hasTranscript: hasTranscript(snapshot),
                    hasOutput: hasOutput,
                    runStatus: snapshot.runStatus,
                    source: optionalStringValue(metadata["source"]) ?? "",
                    sourceURL: optionalStringValue(metadata["source_url"]) ?? optionalStringValue(metadata["canonical_url"]),
                    subscriptionID: optionalStringValue(metadata["subscription_id"]),
                    seriesURL: optionalStringValue(metadata["series_url"]),
                    mediaURL: optionalStringValue(metadata["audio_url"]),
                    publishedAt: optionalStringValue(metadata["local_published_at"])
                        ?? optionalStringValue(metadata["published_at"]),
                    originalPath: recoverableAudioPath,
                    originalBookmark: bookmarkData(from: localMetadata["original_bookmark"]),
                    isRead: boolValue(metadata["app_read"]),
                    isStarred: boolValue(metadata["app_star"]),
                    queueStatus: queueStatus(from: metadata),
                    isArchived: optionalStringValue(metadata["app_status"]) == "archived",
                    modifiedAt: modifiedAt,
                    processedAt: processedAt
                )
            )
        }
        let sortedItems = items.sorted {
            if $0.modifiedAt != $1.modifiedAt {
                return $0.modifiedAt > $1.modifiedAt
            }
            return $0.title.localizedStandardCompare($1.title) == .orderedAscending
        }
        writeIndex(dataRoot: dataRoot, fingerprint: fingerprint, items: sortedItems)
        return sortedItems
    }

    static func sections(from items: [ProcessLibraryItem]) -> [ProcessLibrarySection] {
        sections(from: items, including: [])
    }

    static func sections(from items: [ProcessLibraryItem], including groupNames: [String]) -> [ProcessLibrarySection] {
        let grouped = Dictionary(grouping: items.filter { !$0.isArchived }, by: \.groupName)
        let allGroupNames = Set(grouped.keys).union(groupNames).union([defaultGroupName])
        return allGroupNames.sorted(by: groupSort).map { groupName in
            let sectionItems = (grouped[groupName] ?? []).sorted {
                if $0.modifiedAt != $1.modifiedAt {
                    return $0.modifiedAt > $1.modifiedAt
                }
                return $0.title.localizedStandardCompare($1.title) == .orderedAscending
            }
            return ProcessLibrarySection(id: groupName, title: groupName, items: sectionItems)
        }
    }

    static func groupNames(dataRoot: URL = AppPaths.dataRoot()) -> [String] {
        groupNames(from: scan(dataRoot: dataRoot), dataRoot: dataRoot)
    }

    static func groupNames(from items: [ProcessLibraryItem], dataRoot: URL = AppPaths.dataRoot()) -> [String] {
        return Array(
            Set(items.filter { !$0.isArchived }.map(\.groupName))
                .union(sharedGroupNames(dataRoot: dataRoot))
                .union([defaultGroupName])
        ).sorted(by: groupSort)
    }

    static func metadataText(for item: ProcessLibraryItem) -> String {
        let metadataURL = episodeRecordURL(for: item)
        guard
            let data = try? Data(contentsOf: metadataURL),
            let object = try? JSONSerialization.jsonObject(with: data) as? [String: Any]
        else {
            return localFileMetadataText(for: item)
        }

        if hasEpisodeMetadata(object) {
            return episodeMetadataText(object, item: item)
        }
        return localFileMetadataText(for: item)
    }

    static func channelEpisodeDetails(for item: ProcessLibraryItem) -> ChannelEpisodeDetails {
        let metadata = metadataObject(at: episodeRecordURL(for: item))
        return ChannelEpisodeDetails(
            title: optionalStringValue(metadata["title"]) ?? item.title,
            seriesName: optionalStringValue(metadata["series_name"]),
            sourceName: sourceTitle(from: metadata) ?? optionalStringValue(item.source),
            sourceURL: optionalStringValue(metadata["canonical_url"])
                ?? optionalStringValue(metadata["source_url"])
                ?? item.sourceURL,
            seriesURL: optionalStringValue(metadata["series_url"]) ?? item.seriesURL,
            publishedAt: optionalStringValue(metadata["local_published_at"])
                ?? optionalStringValue(metadata["published_at"]),
            duration: optionalStringValue(metadata["duration"]),
            description: cleanedDescription(metadata["description"]),
            audioURL: optionalStringValue(metadata["audio_url"]) ?? item.mediaURL,
            imageURL: optionalStringValue(metadata["image_url"]),
            guid: optionalStringValue(metadata["guid"])
        )
    }

    static func unprocessedDetailText(for item: ProcessLibraryItem, metadataText: String) -> String {
        var sections: [String] = []
        let metadata = metadataText.trimmingCharacters(in: .whitespacesAndNewlines)
        sections.append(metadata.isEmpty ? localFileMetadataText(for: item) : metadata)

        var statusLines = [
            "## Processing state",
            "",
            "- Queue: \(item.queueStatus.compactTitle)",
            "- Current state: \(item.status)",
            "- Audio: \(item.isAudioPresent ? "ready" : "download or restoration required")",
        ]
        if !item.detail.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            statusLines.append("- Details: \(item.detail)")
        }
        if item.canDownloadAudio {
            statusLines.append("- Available action: download source audio, then process.")
        } else if item.canRestoreAudio {
            statusLines.append("- Available action: restore audio, then process.")
        } else if item.isAudioPresent {
            statusLines.append("- Available action: mark as Process, then transcribe.")
        }
        sections.append(statusLines.joined(separator: "\n"))

        return sections.joined(separator: "\n\n")
    }

    static func updateGroup(_ groupName: String, for item: ProcessLibraryItem) throws {
        let metadataURL = episodeRecordURL(for: item)
        var object = metadataObject(at: metadataURL)
        let groupName = displayGroupName(forGroupName: groupName)
        try LibraryWriter.upsertGroup(groupName, in: authoritativeLibraryRoot(dataRoot: resolvedDataRoot(nil, for: item)))
        object["app_group"] = groupName
        try writeMetadataObject(object, to: metadataURL)
        invalidateIndex(for: item)
    }

    static func updateRead(_ isRead: Bool, for item: ProcessLibraryItem) throws {
        try updateAppState(for: item) { object in
            object["app_read"] = isRead
        }
    }

    static func updateStar(_ isStarred: Bool, for item: ProcessLibraryItem) throws {
        try updateAppState(for: item) { object in
            object["app_star"] = isStarred
        }
    }

    static func updateQueueStatus(_ status: AppQueueStatus, for item: ProcessLibraryItem) throws {
        try updateAppState(for: item) { object in
            object["app_queue_status"] = status.rawValue
        }
    }

    static func updateNodeStatus(_ status: ArticleNodeStatus, for item: ProcessLibraryItem) throws {
        try updateAppState(for: item) { object in
            object["app_status"] = status.rawValue
        }
    }

    static func ensureAppStateDefaults(for item: ProcessLibraryItem) throws {
        try updateAppState(for: item) { object in
            if object["app_status"] == nil {
                object["app_status"] = item.nodeStatus.rawValue
            }
            if object["app_read"] == nil {
                object["app_read"] = item.isRead
            }
            if object["app_star"] == nil {
                object["app_star"] = item.isStarred
            }
            if object["app_queue_status"] == nil {
                object["app_queue_status"] = item.queueStatus.rawValue
            }
        }
    }

    static func createGroup(_ groupName: String, in libraryRoot: URL) throws {
        let groupName = displayGroupName(forGroupName: groupName)
        guard groupName != defaultGroupName else { return }
        try LibraryWriter.upsertGroup(groupName, in: libraryRoot)
    }

    static func invalidateIndex(dataRoot: URL = AppPaths.dataRoot()) {
        try? FileManager.default.removeItem(at: libraryIndexURL(dataRoot: dataRoot))
    }

    static func updateArchive(_ isArchived: Bool, for item: ProcessLibraryItem, dataRoot explicitDataRoot: URL? = nil) throws {
        let dataRoot = resolvedDataRoot(explicitDataRoot, for: item)
        let metadataURL = episodeRecordURL(for: item, dataRoot: dataRoot)
        var object = metadataObject(at: metadataURL)
        object["app_status"] = isArchived ? "archived" : defaultNodeStatus(for: object).rawValue
        object["app_status_updated_at"] = ISO8601DateFormatter().string(from: Date())
        try writeMetadataObject(object, to: metadataURL)
        invalidateIndex(dataRoot: dataRoot)
    }

    static func deleteEpisode(_ item: ProcessLibraryItem, dataRoot explicitDataRoot: URL? = nil) throws {
        let dataRoot = resolvedDataRoot(explicitDataRoot, for: item)
        let root = authoritativeLibraryRoot(dataRoot: dataRoot)
        let episodeDirectory = root.appendingPathComponent("episodes", isDirectory: true).appendingPathComponent(item.id, isDirectory: true)
        let metadata = metadataObject(at: episodeDirectory.appendingPathComponent("episode.json"))
        if FileManager.default.fileExists(atPath: episodeDirectory.path) {
            try FileManager.default.removeItem(at: episodeDirectory)
        }
        let tombstoneDirectory = root.appendingPathComponent("tombstones/episodes", isDirectory: true)
        try FileManager.default.createDirectory(at: tombstoneDirectory, withIntermediateDirectories: true)
        var tombstone: [String: Any] = [
            "schema_version": 1,
            "kind": "audio2text.library.episode_tombstone",
            "episode_id": item.id,
            "title": item.title,
            "deleted_at": ISO8601DateFormatter().string(from: Date()),
        ]
        for key in ["source", "source_url", "canonical_url", "audio_url", "guid", "subscription_id"] {
            if let value = optionalStringValue(metadata[key]) {
                tombstone[key] = value
            }
        }
        let data = try JSONSerialization.data(withJSONObject: tombstone, options: [.prettyPrinted, .sortedKeys])
        try data.write(to: tombstoneDirectory.appendingPathComponent("\(item.id).json"), options: .atomic)
        for directory in [
            AppPaths.materialsRoot(dataRoot: dataRoot).appendingPathComponent(item.id, isDirectory: true),
            AppPaths.workRoot(dataRoot: dataRoot).appendingPathComponent(item.id, isDirectory: true),
        ] where FileManager.default.fileExists(atPath: directory.path) {
            try FileManager.default.removeItem(at: directory)
        }
        try rebuildLibraryManifest(root: root)
        invalidateIndex(dataRoot: dataRoot)
    }

    private static func groupSort(_ lhs: String, _ rhs: String) -> Bool {
        if lhs == defaultGroupName { return true }
        if rhs == defaultGroupName { return false }
        return lhs.localizedStandardCompare(rhs) == .orderedAscending
    }

    private static func resolvedDataRoot(_ explicitDataRoot: URL?, for item: ProcessLibraryItem) -> URL {
        if let explicitDataRoot {
            return explicitDataRoot
        }
        return dataRoot(for: item) ?? AppPaths.dataRoot()
    }

    private static func dataRoot(for item: ProcessLibraryItem) -> URL? {
        let marker = "/materials/"
        let path = item.audioURL.standardizedFileURL.path
        guard let range = path.range(of: marker) else { return nil }
        let rootPath = String(path[..<range.lowerBound])
        return URL(fileURLWithPath: rootPath)
    }

    private static func updateAppState(for item: ProcessLibraryItem, mutate: (inout [String: Any]) -> Void) throws {
        let metadataURL = episodeRecordURL(for: item)
        var object = metadataObject(at: metadataURL)
        if object["app_status"] == nil {
            object["app_status"] = item.nodeStatus.rawValue
        }
        if object["app_read"] == nil {
            object["app_read"] = item.isRead
        }
        if object["app_star"] == nil {
            object["app_star"] = item.isStarred
        }
        if object["app_queue_status"] == nil {
            object["app_queue_status"] = item.queueStatus.rawValue
        }
        mutate(&object)
        object["app_status_updated_at"] = ISO8601DateFormatter().string(from: Date())
        try writeMetadataObject(object, to: metadataURL)
        invalidateIndex(for: item)
    }

    private static func writeMetadataObject(_ object: [String: Any], to metadataURL: URL) throws {
        let data = try JSONSerialization.data(withJSONObject: object, options: [.prettyPrinted, .sortedKeys])
        try data.write(to: metadataURL, options: .atomic)
    }

    private struct LibraryIndex: Codable {
        let schemaVersion: Int
        let fingerprint: String
        let items: [ProcessLibraryItem]
    }

    private static let libraryIndexSchemaVersion = 8

    private static func libraryIndexURL(dataRoot: URL) -> URL {
        dataRoot.appendingPathComponent("cache/library.index.json")
    }

    private static func libraryFingerprint(dataRoot: URL) -> String {
        [
            "library=\(directoryFingerprint(authoritativeLibraryRoot(dataRoot: dataRoot)))",
            "materials=\(directoryFingerprint(AppPaths.materialsRoot(dataRoot: dataRoot)))",
            "work=\(directoryFingerprint(AppPaths.workRoot(dataRoot: dataRoot)))",
        ].joined(separator: ";")
    }

    static func authoritativeLibraryRoot(dataRoot: URL = AppPaths.dataRoot()) -> URL {
        let config = (try? CloudConfigFile.load(dataRoot: dataRoot)) ?? CloudConfigFile()
        return AppPaths.libraryRoot(
            storage: config.libraryStorage,
            iCloudRoot: config.libraryICloudRoot,
            localRoot: config.libraryLocalRoot,
            dataRoot: dataRoot
        )
    }

    private static func sharedGroupNames(dataRoot: URL) -> [String] {
        ((try? LibraryStore.loadGroups(from: authoritativeLibraryRoot(dataRoot: dataRoot))) ?? [])
            .map(\.displayName)
    }

    private static func episodeRecordURL(for item: ProcessLibraryItem, dataRoot explicitDataRoot: URL? = nil) -> URL {
        let dataRoot = explicitDataRoot ?? dataRoot(for: item) ?? AppPaths.dataRoot()
        return authoritativeLibraryRoot(dataRoot: dataRoot)
            .appendingPathComponent("episodes", isDirectory: true)
            .appendingPathComponent(item.id, isDirectory: true)
            .appendingPathComponent("episode.json")
    }

    private static func localAudioURL(forEpisodeID episodeID: String, metadata: [String: Any], dataRoot: URL) -> URL {
        let materialDirectory = AppPaths.materialsRoot(dataRoot: dataRoot).appendingPathComponent(episodeID, isDirectory: true)
        let existing = sourceMedia(in: materialDirectory)
        if let existing {
            return existing
        }
        if let filename = optionalStringValue(metadata["media_filename"]) {
            return materialDirectory.appendingPathComponent(filename)
        }
        let title = optionalStringValue(metadata["title"]) ?? episodeID
        let suffix = audioSuffix(from: optionalStringValue(metadata["audio_url"]) ?? "")
        return materialDirectory.appendingPathComponent("\(PathTools.sanitizedSlug(title))\(suffix)")
    }

    private static func recoverableLocalAudioPath(
        forEpisodeID _: String,
        metadata _: [String: Any],
        localMetadata: [String: Any],
        dataRoot _: URL
    ) -> String? {
        if let originalPath = optionalStringValue(localMetadata["original_path"]) {
            let originalURL = URL(fileURLWithPath: originalPath)
            if isExistingNonEmptyFile(originalURL) {
                return originalURL.path
            }
        }
        return nil
    }

    private static func audioSuffix(from urlText: String) -> String {
        guard let url = URL(string: urlText), !url.pathExtension.isEmpty else {
            return ".m4a"
        }
        return ".\(url.pathExtension)"
    }

    private static func rebuildLibraryManifest(root: URL) throws {
        let episodeRoot = root.appendingPathComponent("episodes", isDirectory: true)
        let subscriptionRoot = root.appendingPathComponent("subscriptions", isDirectory: true)
        let tombstoneRoot = root.appendingPathComponent("tombstones/episodes", isDirectory: true)
        let episodeEntries = ((try? FileManager.default.contentsOfDirectory(at: episodeRoot, includingPropertiesForKeys: nil)) ?? [])
            .filter { FileManager.default.fileExists(atPath: $0.appendingPathComponent("episode.json").path) }
            .map { ["episode_id": $0.lastPathComponent, "path": "episodes/\($0.lastPathComponent)/episode.json"] }
            .sorted { ($0["episode_id"] ?? "") < ($1["episode_id"] ?? "") }
        let subscriptionEntries = ((try? FileManager.default.contentsOfDirectory(at: subscriptionRoot, includingPropertiesForKeys: nil)) ?? [])
            .filter { $0.pathExtension == "json" }
            .map { ["id": $0.deletingPathExtension().lastPathComponent, "path": "subscriptions/\($0.lastPathComponent)"] }
            .sorted { ($0["id"] ?? "") < ($1["id"] ?? "") }
        let tombstoneEntries = ((try? FileManager.default.contentsOfDirectory(at: tombstoneRoot, includingPropertiesForKeys: nil)) ?? [])
            .filter { $0.pathExtension == "json" }
            .map { ["episode_id": $0.deletingPathExtension().lastPathComponent, "path": "tombstones/episodes/\($0.lastPathComponent)"] }
            .sorted { ($0["episode_id"] ?? "") < ($1["episode_id"] ?? "") }
        let payload: [String: Any] = [
            "schema_version": 1,
            "kind": "audio2text.library.manifest",
            "updated_at": ISO8601DateFormatter().string(from: Date()),
            "episode_count": episodeEntries.count,
            "subscription_count": subscriptionEntries.count,
            "tombstone_count": tombstoneEntries.count,
            "episodes": episodeEntries,
            "subscriptions": subscriptionEntries,
            "tombstones": tombstoneEntries,
        ]
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        let data = try JSONSerialization.data(withJSONObject: payload, options: [.prettyPrinted, .sortedKeys])
        try data.write(to: root.appendingPathComponent("manifest.json"), options: .atomic)
    }

    private static func fileFingerprint(_ url: URL) -> String {
        guard
            let values = try? url.resourceValues(forKeys: [.contentModificationDateKey, .fileSizeKey])
        else {
            return "missing"
        }
        return "\(values.contentModificationDate?.timeIntervalSince1970 ?? 0):\(values.fileSize ?? 0)"
    }

    private static func directoryFingerprint(_ root: URL) -> String {
        let manager = FileManager.default
        guard let enumerator = manager.enumerator(
            at: root,
            includingPropertiesForKeys: [.contentModificationDateKey, .fileSizeKey],
            options: [.skipsHiddenFiles]
        ) else {
            return "missing"
        }
        var count = 0
        var maxMtime = 0.0
        var totalSize = 0
        for case let url as URL in enumerator {
            let fileName = url.lastPathComponent
            let isStateFile = [
                "episode.json",
                "summary.md",
                "transcript.md",
                "run.json",
                "qa.json",
                "short_title.txt",
                "title_candidates.json",
            ].contains(fileName)
            let isMediaFile = mediaExtensions.contains(url.pathExtension.lowercased())
            guard isStateFile || isMediaFile else {
                continue
            }
            count += 1
            let values = try? url.resourceValues(forKeys: [.contentModificationDateKey, .fileSizeKey])
            maxMtime = max(maxMtime, values?.contentModificationDate?.timeIntervalSince1970 ?? 0)
            totalSize += values?.fileSize ?? 0
        }
        return "\(count):\(maxMtime):\(totalSize)"
    }

    private static func loadIndex(dataRoot: URL, fingerprint: String) -> [ProcessLibraryItem]? {
        let url = libraryIndexURL(dataRoot: dataRoot)
        guard
            let data = try? Data(contentsOf: url),
            let index = try? JSONDecoder().decode(LibraryIndex.self, from: data),
            index.schemaVersion == libraryIndexSchemaVersion,
            index.fingerprint == fingerprint
        else {
            return nil
        }
        return index.items
    }

    private static func writeIndex(dataRoot: URL, fingerprint: String, items: [ProcessLibraryItem]) {
        let url = libraryIndexURL(dataRoot: dataRoot)
        do {
            try FileManager.default.createDirectory(at: url.deletingLastPathComponent(), withIntermediateDirectories: true)
            let data = try JSONEncoder().encode(LibraryIndex(schemaVersion: libraryIndexSchemaVersion, fingerprint: fingerprint, items: items))
            try data.write(to: url, options: .atomic)
        } catch {
            AppLogger.shared.log(.warning, category: "library", event: "library_index_write_failed", message: error.localizedDescription)
        }
    }

    private static func invalidateIndex(for item: ProcessLibraryItem) {
        let marker = "/materials/"
        let path = item.audioURL.standardizedFileURL.path
        guard let range = path.range(of: marker) else { return }
        let dataRootPath = String(path[..<range.lowerBound])
        invalidateIndex(dataRoot: URL(fileURLWithPath: dataRootPath))
    }

    static func isExistingNonEmptyFile(_ url: URL) -> Bool {
        if let resolved = resolveSymlink(url), resolved.path != url.path {
            return isExistingNonEmptyFile(resolved)
        }
        guard
            let attributes = try? FileManager.default.attributesOfItem(atPath: url.path),
            let type = attributes[.type] as? FileAttributeType,
            type == .typeRegular,
            let size = attributes[.size] as? NSNumber
        else {
            return false
        }
        return size.int64Value > 0
    }

    private static func resolveSymlink(_ url: URL) -> URL? {
        guard let destination = try? FileManager.default.destinationOfSymbolicLink(atPath: url.path) else {
            return nil
        }
        if destination.hasPrefix("/") {
            return URL(fileURLWithPath: destination)
        }
        return url.deletingLastPathComponent().appendingPathComponent(destination)
    }

    private static func displayGroupName(forGroupName groupName: String) -> String {
        let trimmed = groupName.trimmingCharacters(in: .whitespacesAndNewlines)
        return trimmed.isEmpty ? defaultGroupName : trimmed
    }

    private static func sourceMedia(in episodeDirectory: URL) -> URL? {
        let urls = (try? FileManager.default.contentsOfDirectory(
            at: episodeDirectory,
            includingPropertiesForKeys: [.isRegularFileKey],
            options: [.skipsHiddenFiles]
        )) ?? []
        return urls
            .filter { mediaExtensions.contains($0.pathExtension.lowercased()) }
            .sorted { $0.lastPathComponent.localizedStandardCompare($1.lastPathComponent) == .orderedAscending }
            .first
    }

    private static func metadataObject(in episodeDirectory: URL) -> [String: Any] {
        metadataObject(at: episodeDirectory.appendingPathComponent("episode.json"))
    }

    private static func localMetadataObject(forEpisodeID episodeID: String, dataRoot: URL) -> [String: Any] {
        metadataObject(
            at: AppPaths.materialsRoot(dataRoot: dataRoot)
                .appendingPathComponent(episodeID, isDirectory: true)
                .appendingPathComponent("local.json")
        )
    }

    private static func metadataObject(at metadataURL: URL) -> [String: Any] {
        guard
            let data = try? Data(contentsOf: metadataURL),
            let object = try? JSONSerialization.jsonObject(with: data) as? [String: Any]
        else {
            return [:]
        }
        return object
    }

    private static func episodeTitle(from object: [String: Any]) -> String? {
        guard
            let title = object["title"] as? String,
            !title.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
        else {
            return nil
        }
        return title
    }

    private static func groupName(from object: [String: Any]) -> String {
        guard let groupName = object["app_group"] as? String else {
            return defaultGroupName
        }
        return displayGroupName(forGroupName: groupName)
    }

    private static func nodeStatus(from object: [String: Any]) -> ArticleNodeStatus {
        if
            let rawStatus = optionalStringValue(object["app_status"]),
            let status = ArticleNodeStatus(rawValue: rawStatus)
        {
            return status
        }
        if optionalStringValue(object["source_url"]) != nil || optionalStringValue(object["canonical_url"]) != nil {
            return .link
        }
        if optionalStringValue(object["source"]) == "xiaoyuzhou" {
            return .link
        }
        if optionalStringValue(object["source"]) == "local" || optionalStringValue(object["original_path"]) != nil {
            return .import
        }
        return .outside
    }

    private static func defaultNodeStatus(for object: [String: Any]) -> ArticleNodeStatus {
        if optionalStringValue(object["source"]) == "local" {
            return .import
        }
        if optionalStringValue(object["source_url"]) != nil
            || optionalStringValue(object["canonical_url"]) != nil
            || optionalStringValue(object["audio_url"]) != nil
        {
            return .link
        }
        return .outside
    }

    private static func queueStatus(from object: [String: Any]) -> AppQueueStatus {
        guard
            let rawStatus = optionalStringValue(object["app_queue_status"]),
            let status = AppQueueStatus(rawValue: rawStatus)
        else {
            return .unread
        }
        return status
    }

    private static func optionalStringValue(_ value: Any?) -> String? {
        guard let text = value as? String else { return nil }
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        return trimmed.isEmpty ? nil : trimmed
    }

    private static func bookmarkData(from value: Any?) -> Data? {
        guard let text = optionalStringValue(value) else { return nil }
        return Data(base64Encoded: text)
    }

    private static func boolValue(_ value: Any?) -> Bool {
        if let value = value as? Bool {
            return value
        }
        if let value = value as? String {
            return ["true", "yes", "1"].contains(value.trimmingCharacters(in: .whitespacesAndNewlines).lowercased())
        }
        if let value = value as? NSNumber {
            return value.boolValue
        }
        return false
    }

    private static func hasEpisodeMetadata(_ object: [String: Any]) -> Bool {
        optionalStringValue(object["source_url"]) != nil
            || optionalStringValue(object["canonical_url"]) != nil
            || optionalStringValue(object["series_name"]) != nil
            || optionalStringValue(object["description"]) != nil
            || optionalStringValue(object["audio_url"]) != nil
    }

    private static func episodeMetadataText(_ object: [String: Any], item: ProcessLibraryItem) -> String {
        var lines: [String] = []
        let title = optionalStringValue(object["title"]) ?? item.title
        lines.append("# \(title)")
        lines.append("")
        appendMetadataBullet("Podcast", value: object["series_name"], to: &lines)
        appendMetadataBullet("Source", value: sourceTitle(from: object), to: &lines)
        lines.append("- Group: \(item.groupName)")
        appendMetadataBullet("Original link", value: object["canonical_url"] ?? object["source_url"], to: &lines)
        appendMetadataBullet("Podcast link", value: object["series_url"], to: &lines)
        appendMetadataBullet("Published at", value: object["local_published_at"] ?? object["published_at"], to: &lines)
        appendMetadataBullet("Duration", value: object["duration"], to: &lines)
        appendMetadataBullet("Audio link", value: object["audio_url"], to: &lines)
        appendMetadataBullet("Cover", value: object["image_url"], to: &lines)

        let description = cleanedDescription(object["description"])
        lines.append("")
        lines.append("## Episode overview")
        lines.append("")
        if !description.isEmpty {
            lines.append(description)
        } else {
            lines.append("The source metadata has no episode description.")
        }
        return lines.joined(separator: "\n")
    }

    private static func localFileMetadataText(for item: ProcessLibraryItem) -> String {
        var lines = [
            "# \(item.title)",
            "",
            "- Group: \(item.groupName)",
            "- File: \(item.audioURL.lastPathComponent)",
        ]
        let metadata = metadataObject(at: episodeRecordURL(for: item))
        appendMetadataBullet("Import mode", value: metadata["import_mode"], to: &lines)
        if let dataRoot = dataRoot(for: item) {
            let localMetadata = localMetadataObject(forEpisodeID: item.id, dataRoot: dataRoot)
            appendMetadataBullet("Original file", value: localMetadata["original_path"], to: &lines)
        }
        let values = try? item.audioURL.resourceValues(forKeys: [.creationDateKey, .contentModificationDateKey])
        if let createdAt = values?.creationDate {
            lines.append("- Created at: \(displayDate(createdAt))")
        }
        if let modifiedAt = values?.contentModificationDate {
            lines.append("- Modified at: \(displayDate(modifiedAt))")
        }
        return lines.joined(separator: "\n")
    }

    private static func appendMetadataBullet(_ title: String, value: Any?, to lines: inout [String]) {
        let text = stringValue(value)
        guard !text.isEmpty else { return }
        lines.append("- \(title): \(text)")
    }

    private static func sourceTitle(from object: [String: Any]) -> String? {
        switch optionalStringValue(object["source"]) {
        case "xiaoyuzhou":
            return "Xiaoyuzhou"
        case "podcast_rss":
            return "Podcast RSS"
        case let source?:
            return source
        case nil:
            return nil
        }
    }

    private static func cleanedDescription(_ value: Any?) -> String {
        stringValue(value)
            .replacingOccurrences(of: "\r\n", with: "\n")
            .replacingOccurrences(of: "\r", with: "\n")
            .trimmingCharacters(in: .whitespacesAndNewlines)
    }

    private static func stringValue(_ value: Any?) -> String {
        guard let value else { return "" }
        return String(describing: value).trimmingCharacters(in: .whitespacesAndNewlines)
    }

    private static func displayDate(_ date: Date) -> String {
        let formatter = DateFormatter()
        formatter.dateStyle = .medium
        formatter.timeStyle = .medium
        return formatter.string(from: date)
    }

    private static func parsedDate(_ value: String?) -> Date? {
        LibraryDateParser.date(from: value)
    }

    static func status(for snapshot: OutputSnapshot, outputURL: URL, isAudioPresent: Bool) -> String {
        if !isAudioPresent {
            return "Audio pending"
        }
        if snapshot.runStatus == "running" {
            return "Incomplete"
        }
        if snapshot.runStatus == "failed" {
            return "Failed"
        }
        if snapshot.qaStatus == "pass" {
            return "QA pass"
        }
        if snapshot.qaStatus == "fail" {
            return "QA fail"
        }
        if snapshot.runStatus == "done" {
            return "Processed"
        }
        if snapshot.runStatus == "running" {
            return "Running"
        }
        if FileManager.default.fileExists(atPath: outputURL.path) {
            return "Incomplete"
        }
        return "Not processed"
    }

    static func detail(for snapshot: OutputSnapshot, outputURL: URL, isAudioPresent: Bool) -> String {
        if !isAudioPresent {
            return "Metadata exists"
        }
        if snapshot.totalChunks > 0 {
            return "Chunks \(snapshot.chunkProgress)\(diskSuffix(snapshot.diskUsageBytes))"
        }
        if !snapshot.transcriptText.isEmpty {
            return "Transcript available\(diskSuffix(snapshot.diskUsageBytes))"
        }
        return FileManager.default.fileExists(atPath: outputURL.path) ? "Output exists\(diskSuffix(snapshot.diskUsageBytes))" : ""
    }

    private static func diskSuffix(_ bytes: Int) -> String {
        guard bytes > 0 else { return "" }
        let mb = Double(bytes) / 1_048_576.0
        if mb >= 1 {
            return String(format: " · %.1f MB", mb)
        }
        return " · \(bytes) B"
    }

    static func hasTranscript(_ snapshot: OutputSnapshot) -> Bool {
        !snapshot.transcriptText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
    }

    static func isProcessed(_ snapshot: OutputSnapshot) -> Bool {
        snapshot.runStatus == "done" && !snapshot.transcriptText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
    }

    private static func modificationDate(for url: URL) -> Date? {
        (try? url.resourceValues(forKeys: [.contentModificationDateKey]))?.contentModificationDate
    }

    private static func isDirectory(_ url: URL) -> Bool {
        (try? url.resourceValues(forKeys: [.isDirectoryKey]))?.isDirectory == true
    }
}
