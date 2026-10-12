import CryptoKit
import Foundation

public struct LibraryWriteResult: Equatable {
    public let subscriptionID: String
    public let writtenEpisodeCount: Int
    public let skippedAvailableEpisodeCount: Int
    public let reusedMetadataEpisodeCount: Int
    public let tombstoneSkippedEpisodeCount: Int

    public init(
        subscriptionID: String,
        writtenEpisodeCount: Int,
        skippedAvailableEpisodeCount: Int,
        reusedMetadataEpisodeCount: Int = 0,
        tombstoneSkippedEpisodeCount: Int = 0
    ) {
        self.subscriptionID = subscriptionID
        self.writtenEpisodeCount = writtenEpisodeCount
        self.skippedAvailableEpisodeCount = skippedAvailableEpisodeCount
        self.reusedMetadataEpisodeCount = reusedMetadataEpisodeCount
        self.tombstoneSkippedEpisodeCount = tombstoneSkippedEpisodeCount
    }
}

public struct LibrarySubscriptionDeleteResult: Equatable {
    public let subscriptionID: String
    public let removedMetadataOnlyEpisodeCount: Int
    public let preservedAvailableEpisodeCount: Int

    public init(
        subscriptionID: String,
        removedMetadataOnlyEpisodeCount: Int,
        preservedAvailableEpisodeCount: Int
    ) {
        self.subscriptionID = subscriptionID
        self.removedMetadataOnlyEpisodeCount = removedMetadataOnlyEpisodeCount
        self.preservedAvailableEpisodeCount = preservedAvailableEpisodeCount
    }
}

public enum LibraryWriter {
    @discardableResult
    public static func writeMetadataOnly(
        discovery: PodcastFeedDiscovery,
        to libraryRoot: URL,
        groupName: String = "Default"
    ) throws -> LibraryWriteResult {
        try upsertGroup(groupName, in: libraryRoot)
        let subscriptionID = subscriptionID(for: discovery)
        let now = ISO8601DateFormatter().string(from: Date())
        let subscription = LibrarySubscription(
            id: subscriptionID,
            title: discovery.title,
            source: discovery.source,
            url: discovery.url,
            feedURL: discovery.feedURL,
            groupName: groupName,
            createdAt: now,
            lastCheckedAt: now
        )

        try createDirectory(libraryRoot.appendingPathComponent("subscriptions", isDirectory: true))
        try createDirectory(libraryRoot.appendingPathComponent("episodes", isDirectory: true))
        try writeJSON(subscription, to: libraryRoot.appendingPathComponent("subscriptions/\(subscriptionID).json"))

        var written = 0
        var skippedAvailable = 0
        var reusedMetadata = 0
        var tombstoneSkipped = 0
        for episode in discovery.episodes {
            let episodeID = StableEpisodeID.make(
                source: episode.source,
                subscriptionID: subscriptionID,
                guid: episode.guid,
                audioURL: episode.audioURL,
                canonicalURL: episode.canonicalURL,
                sourceURL: episode.sourceURL,
                title: episode.title
            )
            if FileManager.default.fileExists(atPath: tombstoneURL(for: episodeID, in: libraryRoot).path) {
                tombstoneSkipped += 1
                continue
            }
            let episodeRoot = libraryRoot.appendingPathComponent("episodes/\(episodeID)", isDirectory: true)
            let episodeRecordURL = episodeRoot.appendingPathComponent("episode.json")
            let existing = try? JSONDecoder().decode(LibraryEpisode.self, from: Data(contentsOf: episodeRecordURL))
            if let existing {
                if existing.normalizedProductStatus == LibraryConstants.productStatusAvailable {
                    skippedAvailable += 1
                    continue
                }
                reusedMetadata += 1
            }
            let record = LibraryEpisode(
                episodeID: episodeID,
                title: existing?.title ?? episode.title,
                source: episode.source,
                sourceURL: episode.sourceURL,
                canonicalURL: episode.canonicalURL,
                seriesName: episode.seriesName,
                seriesURL: episode.seriesURL,
                publishedAt: episode.publishedAt,
                localPublishedAt: episode.publishedAt,
                duration: episode.duration,
                description: episode.description,
                audioURL: episode.audioURL,
                imageURL: episode.imageURL,
                guid: episode.guid,
                subscriptionID: subscriptionID,
                appGroup: existing?.appGroup ?? groupName,
                appStatus: existing?.appStatus ?? "link",
                appQueueStatus: existing?.appQueueStatus ?? "unread",
                appRead: existing?.appRead ?? false,
                appStar: existing?.appStar ?? false,
                productStatus: LibraryConstants.productStatusMetadataOnly,
                documents: []
            )
            try createDirectory(episodeRoot)
            try writeJSON(record, to: episodeRecordURL)
            if existing == nil {
                written += 1
            }
        }
        try rebuildManifest(libraryRoot: libraryRoot)
        return LibraryWriteResult(
            subscriptionID: subscriptionID,
            writtenEpisodeCount: written,
            skippedAvailableEpisodeCount: skippedAvailable,
            reusedMetadataEpisodeCount: reusedMetadata,
            tombstoneSkippedEpisodeCount: tombstoneSkipped
        )
    }

    public static func rebuildManifest(libraryRoot: URL) throws {
        let fileManager = FileManager.default
        let subscriptionRoot = libraryRoot.appendingPathComponent("subscriptions", isDirectory: true)
        let episodeRoot = libraryRoot.appendingPathComponent("episodes", isDirectory: true)
        let groupRoot = libraryRoot.appendingPathComponent("groups", isDirectory: true)
        let tombstoneRoot = libraryRoot.appendingPathComponent("tombstones/episodes", isDirectory: true)
        try createDirectory(subscriptionRoot)
        try createDirectory(episodeRoot)
        try createDirectory(groupRoot)
        try createDirectory(tombstoneRoot)
        let subscriptionFiles = (try? fileManager.contentsOfDirectory(at: subscriptionRoot, includingPropertiesForKeys: nil)) ?? []
        let episodeDirectories = (try? fileManager.contentsOfDirectory(at: episodeRoot, includingPropertiesForKeys: nil)) ?? []
        let tombstoneFiles = (try? fileManager.contentsOfDirectory(at: tombstoneRoot, includingPropertiesForKeys: nil)) ?? []
        let subscriptions = subscriptionFiles
            .filter { $0.pathExtension == "json" }
            .compactMap { try? JSONDecoder().decode(LibrarySubscription.self, from: Data(contentsOf: $0)) }
            .sorted { $0.id < $1.id }
        let episodes = episodeDirectories
            .map { $0.appendingPathComponent("episode.json") }
            .compactMap { try? JSONDecoder().decode(LibraryEpisode.self, from: Data(contentsOf: $0)) }
            .sorted { $0.id < $1.id }
        let tombstones = tombstoneFiles
            .filter { $0.pathExtension == "json" }
            .map { $0.deletingPathExtension().lastPathComponent }
            .sorted()
        let manifest = LibraryManifest(
            schemaVersion: LibraryConstants.schemaVersion,
            kind: LibraryConstants.libraryManifestKind,
            updatedAt: ISO8601DateFormatter().string(from: Date()),
            episodeCount: episodes.count,
            subscriptionCount: subscriptions.count,
            tombstoneCount: tombstones.count,
            episodes: episodes.map {
                LibraryManifest.EpisodeEntry(
                    episodeID: $0.id,
                    path: "episodes/\($0.id)/episode.json"
                )
            },
            subscriptions: subscriptions.map {
                LibraryManifest.SubscriptionEntry(id: $0.id, path: "subscriptions/\($0.id).json")
            },
            tombstones: tombstones.map {
                LibraryManifest.TombstoneEntry(episodeID: $0, path: "tombstones/episodes/\($0).json")
            }
        )
        try writeJSON(manifest, to: libraryRoot.appendingPathComponent("manifest.json"))
    }

    public static func deleteEpisode(
        _ episode: LibraryEpisode,
        from libraryRoot: URL,
        localMaterialRoot: URL? = nil,
        localWorkRoot: URL? = nil
    ) throws {
        let episodeRoot = libraryRoot.appendingPathComponent("episodes/\(episode.episodeID)", isDirectory: true)
        if FileManager.default.fileExists(atPath: episodeRoot.path) {
            try FileManager.default.removeItem(at: episodeRoot)
        }
        let tombstone: [String: Any] = [
            "schema_version": LibraryConstants.schemaVersion,
            "kind": LibraryConstants.libraryEpisodeTombstoneKind,
            "episode_id": episode.episodeID,
            "title": episode.title,
            "source": episode.source ?? "",
            "source_url": episode.sourceURL ?? "",
            "canonical_url": episode.canonicalURL ?? "",
            "audio_url": episode.audioURL ?? "",
            "guid": episode.guid ?? "",
            "subscription_id": episode.subscriptionID ?? "",
            "deleted_at": ISO8601DateFormatter().string(from: Date()),
        ]
        let data = try JSONSerialization.data(withJSONObject: tombstone, options: [.prettyPrinted, .sortedKeys])
        let tombstoneURL = tombstoneURL(for: episode.episodeID, in: libraryRoot)
        try createDirectory(tombstoneURL.deletingLastPathComponent())
        try data.write(to: tombstoneURL, options: .atomic)
        for root in [localMaterialRoot, localWorkRoot].compactMap({ $0 }) {
            let directory = root.appendingPathComponent(episode.episodeID, isDirectory: true)
            if FileManager.default.fileExists(atPath: directory.path) {
                try FileManager.default.removeItem(at: directory)
            }
        }
        try rebuildManifest(libraryRoot: libraryRoot)
    }

    public static func updateRead(_ isRead: Bool, for episode: LibraryEpisode, in libraryRoot: URL) throws {
        try updateEpisodeRecord(episode, in: libraryRoot) { object in
            object["app_read"] = isRead
            object["app_read_updated_at"] = ISO8601DateFormatter().string(from: Date())
        }
    }

    public static func updateStar(_ isStarred: Bool, for episode: LibraryEpisode, in libraryRoot: URL) throws {
        try updateEpisodeRecord(episode, in: libraryRoot) { object in
            object["app_star"] = isStarred
            object["app_star_updated_at"] = ISO8601DateFormatter().string(from: Date())
        }
    }

    public static func updateArchived(_ isArchived: Bool, for episode: LibraryEpisode, in libraryRoot: URL) throws {
        try updateEpisodeRecord(episode, in: libraryRoot) { object in
            object["app_status"] = isArchived ? "archived" : "link"
            object["app_status_updated_at"] = ISO8601DateFormatter().string(from: Date())
        }
    }

    public static func updateGroup(_ groupName: String, for episode: LibraryEpisode, in libraryRoot: URL) throws {
        try upsertGroup(groupName, in: libraryRoot)
        try updateEpisodeRecord(episode, in: libraryRoot) { object in
            object["app_group"] = LibrarySidebarItem.normalizedGroupName(groupName)
            object["app_group_updated_at"] = ISO8601DateFormatter().string(from: Date())
        }
    }

    public static func updateTitle(_ title: String, forEpisodeID episodeID: String, in libraryRoot: URL) throws {
        let trimmed = title.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else {
            throw LibraryWriterError.emptyTitle
        }
        try updateEpisodeRecord(episodeID: episodeID, in: libraryRoot) { object in
            let currentTitle = (object["title"] as? String)?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
            let originalTitle = (object["original_title"] as? String)?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
            if originalTitle.isEmpty, !currentTitle.isEmpty, currentTitle != trimmed {
                object["original_title"] = currentTitle
            }
            object["title"] = trimmed
            object["title_updated_at"] = ISO8601DateFormatter().string(from: Date())
        }
    }

    @discardableResult
    public static func upsertGroup(_ groupName: String, in libraryRoot: URL) throws -> LibraryGroup {
        let normalizedName = LibraryGroup.normalizedName(groupName)
        guard normalizedName != LibraryConstants.defaultGroupName else {
            return LibraryGroup(id: normalizedName, title: normalizedName)
        }
        let now = ISO8601DateFormatter().string(from: Date())
        let root = libraryRoot.appendingPathComponent("groups", isDirectory: true)
        try createDirectory(root)
        let existingURL = existingGroupURL(for: normalizedName, in: libraryRoot)
        let url = existingURL ?? groupURL(for: normalizedName, in: libraryRoot)
        let existing = existingURL.flatMap { try? JSONDecoder().decode(LibraryGroup.self, from: Data(contentsOf: $0)) }
        let group = LibraryGroup(
            id: normalizedName,
            title: normalizedName,
            createdAt: existing?.createdAt ?? now,
            updatedAt: now
        )
        try writeJSON(group, to: url)
        return group
    }

    public static func deleteGroup(_ groupName: String, in libraryRoot: URL) throws {
        let normalizedName = LibraryGroup.normalizedName(groupName)
        guard normalizedName != LibraryConstants.defaultGroupName else { return }
        if let url = existingGroupURL(for: normalizedName, in: libraryRoot),
           FileManager.default.fileExists(atPath: url.path)
        {
            try FileManager.default.removeItem(at: url)
        }
    }

    public static func renameGroup(_ oldName: String, to newName: String, in libraryRoot: URL) throws {
        let oldName = LibraryGroup.normalizedName(oldName)
        let newName = LibraryGroup.normalizedName(newName)
        guard oldName != newName else { return }
        try deleteGroup(oldName, in: libraryRoot)
        try upsertGroup(newName, in: libraryRoot)
    }

    public static func deleteSubscription(_ subscription: LibrarySubscription, from libraryRoot: URL) throws -> LibrarySubscriptionDeleteResult {
        try deleteSubscription(id: subscription.id, from: libraryRoot)
    }

    public static func deleteSubscription(id subscriptionID: String, from libraryRoot: URL) throws -> LibrarySubscriptionDeleteResult {
        let subscriptionURL = libraryRoot.appendingPathComponent("subscriptions/\(subscriptionID).json")
        guard FileManager.default.fileExists(atPath: subscriptionURL.path) else {
            throw LibraryWriterError.unknownSubscription(subscriptionID)
        }
        try FileManager.default.removeItem(at: subscriptionURL)

        let episodes = (try? LibraryStore.loadEpisodes(from: libraryRoot)) ?? []
        var removedMetadataOnly = 0
        var preservedAvailable = 0
        for episode in episodes where episode.subscriptionID == subscriptionID {
            let episodeRoot = libraryRoot.appendingPathComponent("episodes/\(episode.episodeID)", isDirectory: true)
            if episode.hasSyncedDocuments || !episode.documents.isEmpty {
                preservedAvailable += 1
                continue
            }
            if FileManager.default.fileExists(atPath: episodeRoot.path) {
                try FileManager.default.removeItem(at: episodeRoot)
                removedMetadataOnly += 1
            }
        }
        try rebuildManifest(libraryRoot: libraryRoot)
        return LibrarySubscriptionDeleteResult(
            subscriptionID: subscriptionID,
            removedMetadataOnlyEpisodeCount: removedMetadataOnly,
            preservedAvailableEpisodeCount: preservedAvailable
        )
    }

    public static func subscriptionID(for discovery: PodcastFeedDiscovery) -> String {
        let stable = discovery.feedURL.isEmpty ? discovery.url : discovery.feedURL
        let material = "\(discovery.source):\(stable)"
        let digest = Insecure.SHA1.hash(data: Data(material.utf8))
            .map { String(format: "%02x", $0) }
            .joined()
            .prefix(12)
        return "\(discovery.source)-\(digest)"
    }

    private static func createDirectory(_ url: URL) throws {
        try FileManager.default.createDirectory(at: url, withIntermediateDirectories: true)
    }

    private static func writeJSON<T: Encodable>(_ value: T, to url: URL) throws {
        try createDirectory(url.deletingLastPathComponent())
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        let data = try encoder.encode(value)
        try data.write(to: url, options: .atomic)
    }

    private static func writeJSONObject(_ object: [String: Any], to url: URL) throws {
        try createDirectory(url.deletingLastPathComponent())
        let data = try JSONSerialization.data(withJSONObject: object, options: [.prettyPrinted, .sortedKeys])
        try data.write(to: url, options: .atomic)
    }

    private static func updateEpisodeRecord(
        _ episode: LibraryEpisode,
        in libraryRoot: URL,
        mutate: (inout [String: Any]) -> Void
    ) throws {
        try updateEpisodeRecord(episodeID: episode.episodeID, in: libraryRoot, mutate: mutate)
    }

    private static func updateEpisodeRecord(
        episodeID: String,
        in libraryRoot: URL,
        mutate: (inout [String: Any]) -> Void
    ) throws {
        let recordURL = libraryRoot
            .appendingPathComponent("episodes/\(episodeID)", isDirectory: true)
            .appendingPathComponent("episode.json")
        let data = try Data(contentsOf: recordURL)
        var object = try JSONSerialization.jsonObject(with: data) as? [String: Any] ?? [:]
        mutate(&object)
        try writeJSONObject(object, to: recordURL)
        try rebuildManifest(libraryRoot: libraryRoot)
    }

    private static func tombstoneURL(for episodeID: String, in libraryRoot: URL) -> URL {
        libraryRoot
            .appendingPathComponent("tombstones", isDirectory: true)
            .appendingPathComponent("episodes", isDirectory: true)
            .appendingPathComponent("\(episodeID).json")
    }

    private static func groupURL(for groupName: String, in libraryRoot: URL) -> URL {
        libraryRoot
            .appendingPathComponent("groups", isDirectory: true)
            .appendingPathComponent(LibraryGroup.recordFileName(for: groupName))
    }

    private static func existingGroupURL(for groupName: String, in libraryRoot: URL) -> URL? {
        let groupRoot = libraryRoot.appendingPathComponent("groups", isDirectory: true)
        let urls = (try? FileManager.default.contentsOfDirectory(
            at: groupRoot,
            includingPropertiesForKeys: nil,
            options: [.skipsHiddenFiles]
        )) ?? []
        let normalizedName = LibraryGroup.normalizedName(groupName)
        return urls.first { url in
            guard
                url.pathExtension == "json",
                let data = try? Data(contentsOf: url),
                let group = try? JSONDecoder().decode(LibraryGroup.self, from: data)
            else {
                return false
            }
            return group.id == normalizedName || group.displayName == normalizedName
        }
    }
}

public enum LibraryWriterError: LocalizedError, Equatable {
    case emptyTitle
    case unknownSubscription(String)

    public var errorDescription: String? {
        switch self {
        case .emptyTitle:
            return "Title cannot be empty."
        case let .unknownSubscription(subscriptionID):
            return "Unknown subscription id: \(subscriptionID)."
        }
    }
}

public typealias MobileSyncWriteResult = LibraryWriteResult
public typealias MobileSyncWriter = LibraryWriter
