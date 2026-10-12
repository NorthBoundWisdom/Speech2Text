import CryptoKit
import Foundation

public enum LibraryConstants {
    public static let libraryDirectoryName = "Audio2TextLibrary"
    public static let schemaVersion = 1
    public static let episodeIDHexLength = 24
    public static let defaultGroupName = "Default"
    public static let productStatusAvailable = "available"
    public static let productStatusMetadataOnly = "metadata_only"
    public static let libraryManifestKind = "audio2text.library.manifest"
    public static let libraryEpisodeKind = "audio2text.library.episode"
    public static let librarySubscriptionKind = "audio2text.library.subscription"
    public static let libraryGroupKind = "audio2text.library.group"
    public static let libraryEpisodeTombstoneKind = "audio2text.library.episode_tombstone"
}

public enum LibraryDateParser {
    public static func date(from value: String?) -> Date? {
        guard let value, !value.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
            return nil
        }
        let trimmed = value.trimmingCharacters(in: .whitespacesAndNewlines)
        for options in [
            ISO8601DateFormatter.Options([.withInternetDateTime, .withFractionalSeconds]),
            ISO8601DateFormatter.Options([.withInternetDateTime]),
        ] {
            let formatter = ISO8601DateFormatter()
            formatter.formatOptions = options
            if let date = formatter.date(from: trimmed) {
                return date
            }
        }
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.dateFormat = "EEE, d MMM yyyy HH:mm:ss zzz"
        return formatter.date(from: trimmed)
    }
}

public enum LibraryPaths {
    public static func libraryRoot(in syncRoot: URL) -> URL {
        syncRoot.lastPathComponent == LibraryConstants.libraryDirectoryName
            ? syncRoot
            : syncRoot.appendingPathComponent(LibraryConstants.libraryDirectoryName, isDirectory: true)
    }

    public static func existingLibraryRoot(in selectedRoot: URL, fileManager: FileManager = .default) -> URL {
        for candidate in libraryRootCandidates(in: selectedRoot) where manifestExists(in: candidate, fileManager: fileManager) {
            return candidate
        }
        for candidate in libraryRootCandidates(in: selectedRoot) where directoryExists(candidate, fileManager: fileManager) {
            return candidate
        }
        return libraryRoot(in: selectedRoot)
    }

    public static func libraryRootCandidates(in selectedRoot: URL) -> [URL] {
        var candidates: [URL] = []
        if selectedRoot.lastPathComponent == LibraryConstants.libraryDirectoryName {
            candidates.append(selectedRoot)
        }
        if selectedRoot.lastPathComponent == "Audio2Text" {
            candidates.append(selectedRoot.appendingPathComponent(LibraryConstants.libraryDirectoryName, isDirectory: true))
        }
        candidates.append(
            selectedRoot
                .appendingPathComponent("Audio2Text", isDirectory: true)
                .appendingPathComponent(LibraryConstants.libraryDirectoryName, isDirectory: true)
        )
        candidates.append(selectedRoot.appendingPathComponent(LibraryConstants.libraryDirectoryName, isDirectory: true))
        return uniqueStandardizedURLs(candidates)
    }

    private static func manifestExists(in root: URL, fileManager: FileManager) -> Bool {
        fileManager.fileExists(atPath: root.appendingPathComponent("manifest.json").path)
    }

    private static func directoryExists(_ url: URL, fileManager: FileManager) -> Bool {
        var isDirectory: ObjCBool = false
        return fileManager.fileExists(atPath: url.path, isDirectory: &isDirectory) && isDirectory.boolValue
    }

    private static func uniqueStandardizedURLs(_ urls: [URL]) -> [URL] {
        var seen = Set<String>()
        var result: [URL] = []
        for url in urls {
            let standardized = url.standardizedFileURL
            if seen.insert(standardized.path).inserted {
                result.append(standardized)
            }
        }
        return result
    }
}

public enum StableEpisodeID {
    public static func make(
        source: String?,
        subscriptionID: String?,
        guid: String?,
        audioURL: String?,
        canonicalURL: String?,
        sourceURL: String? = nil,
        title: String? = nil
    ) -> String {
        let identity: (key: String, value: String)
        if let value = clean(guid) {
            identity = ("guid", value)
        } else if let value = clean(audioURL) {
            identity = ("audio_url", value)
        } else if let value = clean(canonicalURL) {
            identity = ("canonical_url", value)
        } else {
            identity = ("source_url", clean(sourceURL) ?? clean(title) ?? "")
        }
        let material = [
            clean(source) ?? "",
            clean(subscriptionID) ?? "",
            identity.key,
            identity.value,
        ].joined(separator: "\n")
        let digest = SHA256.hash(data: Data(material.utf8))
        return digest.map { String(format: "%02x", $0) }.joined().prefix(LibraryConstants.episodeIDHexLength).description
    }

    private static func clean(_ value: String?) -> String? {
        guard let value else { return nil }
        let trimmed = value.trimmingCharacters(in: .whitespacesAndNewlines)
        return trimmed.isEmpty ? nil : trimmed
    }
}

public struct LibraryDocument: Codable, Equatable, Identifiable {
    public var id: String {
        name
    }

    public let name: String
    public let path: String
    public let bytes: Int?
    public let sha256: String?
    public var hasRecordedContent: Bool {
        (bytes ?? 0) > 0
    }

    public init(name: String, path: String, bytes: Int? = nil, sha256: String? = nil) {
        self.name = name
        self.path = path
        self.bytes = bytes
        self.sha256 = sha256
    }
}

public struct LibraryEpisode: Codable, Equatable, Identifiable {
    public let schemaVersion: Int?
    public let kind: String?
    public let episodeID: String
    public let source: String?
    public let sourceURL: String?
    public let canonicalURL: String?
    public let title: String
    public let originalTitle: String?
    public let seriesName: String?
    public let seriesURL: String?
    public let publishedAt: String?
    public let localPublishedAt: String?
    public let processedAt: String?
    public let duration: String?
    public let description: String?
    public let audioURL: String?
    public let imageURL: String?
    public let guid: String?
    public let subscriptionID: String?
    public let appGroup: String?
    public let appStatus: String?
    public let appQueueStatus: String?
    public let appRead: Bool?
    public let appStar: Bool?
    public let productStatus: String?
    public let documents: [LibraryDocument]

    public var id: String {
        episodeID
    }

    public var normalizedProductStatus: String {
        if let productStatus, !productStatus.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            return productStatus
        }
        return documents.isEmpty ? LibraryConstants.productStatusMetadataOnly : LibraryConstants.productStatusAvailable
    }

    public var hasSyncedDocuments: Bool {
        normalizedProductStatus == LibraryConstants.productStatusAvailable
            && documents.contains(where: \.hasRecordedContent)
    }

    public var isRead: Bool {
        appRead == true
    }

    public var isStarred: Bool {
        appStar == true
    }

    public var isArchived: Bool {
        appStatus == "archived"
    }

    public init(
        episodeID: String,
        title: String,
        schemaVersion: Int? = LibraryConstants.schemaVersion,
        kind: String? = LibraryConstants.libraryEpisodeKind,
        source: String? = nil,
        sourceURL: String? = nil,
        canonicalURL: String? = nil,
        originalTitle: String? = nil,
        seriesName: String? = nil,
        seriesURL: String? = nil,
        publishedAt: String? = nil,
        localPublishedAt: String? = nil,
        processedAt: String? = nil,
        duration: String? = nil,
        description: String? = nil,
        audioURL: String? = nil,
        imageURL: String? = nil,
        guid: String? = nil,
        subscriptionID: String? = nil,
        appGroup: String? = nil,
        appStatus: String? = nil,
        appQueueStatus: String? = nil,
        appRead: Bool? = nil,
        appStar: Bool? = nil,
        productStatus: String? = nil,
        documents: [LibraryDocument] = []
    ) {
        self.schemaVersion = schemaVersion
        self.kind = kind
        self.episodeID = episodeID
        self.source = source
        self.sourceURL = sourceURL
        self.canonicalURL = canonicalURL
        self.title = title
        self.originalTitle = originalTitle
        self.seriesName = seriesName
        self.seriesURL = seriesURL
        self.publishedAt = publishedAt
        self.localPublishedAt = localPublishedAt
        self.processedAt = processedAt
        self.duration = duration
        self.description = description
        self.audioURL = audioURL
        self.imageURL = imageURL
        self.guid = guid
        self.subscriptionID = subscriptionID
        self.appGroup = appGroup
        self.appStatus = appStatus
        self.appQueueStatus = appQueueStatus
        self.appRead = appRead
        self.appStar = appStar
        self.productStatus = productStatus
        self.documents = documents
    }

    enum CodingKeys: String, CodingKey {
        case schemaVersion = "schema_version"
        case kind
        case episodeID = "episode_id"
        case source
        case sourceURL = "source_url"
        case canonicalURL = "canonical_url"
        case title
        case originalTitle = "original_title"
        case seriesName = "series_name"
        case seriesURL = "series_url"
        case publishedAt = "published_at"
        case localPublishedAt = "local_published_at"
        case processedAt = "processed_at"
        case duration
        case description
        case audioURL = "audio_url"
        case imageURL = "image_url"
        case guid
        case subscriptionID = "subscription_id"
        case appGroup = "app_group"
        case appStatus = "app_status"
        case appQueueStatus = "app_queue_status"
        case appRead = "app_read"
        case appStar = "app_star"
        case productStatus = "product_status"
        case documents
    }
}

public struct LibrarySubscription: Codable, Equatable, Identifiable {
    public let schemaVersion: Int?
    public let kind: String?
    public let id: String
    public let title: String
    public let source: String?
    public let url: String?
    public let feedURL: String?
    public let groupName: String?
    public let createdAt: String?
    public let lastCheckedAt: String?

    public init(
        id: String,
        title: String,
        schemaVersion: Int? = LibraryConstants.schemaVersion,
        kind: String? = LibraryConstants.librarySubscriptionKind,
        source: String? = nil,
        url: String? = nil,
        feedURL: String? = nil,
        groupName: String? = nil,
        createdAt: String? = nil,
        lastCheckedAt: String? = nil
    ) {
        self.schemaVersion = schemaVersion
        self.kind = kind
        self.id = id
        self.title = title
        self.source = source
        self.url = url
        self.feedURL = feedURL
        self.groupName = groupName
        self.createdAt = createdAt
        self.lastCheckedAt = lastCheckedAt
    }

    enum CodingKeys: String, CodingKey {
        case schemaVersion = "schema_version"
        case kind
        case id
        case title
        case source
        case url
        case feedURL = "feed_url"
        case groupName = "group_name"
        case createdAt = "created_at"
        case lastCheckedAt = "last_checked_at"
    }
}

public struct LibraryGroup: Codable, Equatable, Identifiable {
    public let schemaVersion: Int?
    public let kind: String?
    public let id: String
    public let title: String?
    public let createdAt: String?
    public let updatedAt: String?

    public var displayName: String {
        Self.normalizedName(title ?? id)
    }

    public init(
        id: String,
        title: String? = nil,
        schemaVersion: Int? = LibraryConstants.schemaVersion,
        kind: String? = LibraryConstants.libraryGroupKind,
        createdAt: String? = nil,
        updatedAt: String? = nil
    ) {
        let normalized = Self.normalizedName(id)
        self.schemaVersion = schemaVersion
        self.kind = kind
        self.id = normalized
        self.title = title.map(Self.normalizedName) ?? normalized
        self.createdAt = createdAt
        self.updatedAt = updatedAt
    }

    public static func normalizedName(_ value: String?) -> String {
        let trimmed = value?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
        return trimmed.isEmpty ? LibraryConstants.defaultGroupName : trimmed
    }

    public static func recordFileName(for groupName: String) -> String {
        "\(recordStem(for: groupName)).json"
    }

    private static func recordStem(for groupName: String) -> String {
        let normalized = normalizedName(groupName)
        let scalars = normalized.unicodeScalars.map { scalar -> Character in
            if CharacterSet.alphanumerics.contains(scalar) || isCJK(scalar) || scalar == "-" || scalar == "_" {
                return Character(scalar)
            }
            return "-"
        }
        let collapsed = String(scalars)
            .replacingOccurrences(of: "-+", with: "-", options: .regularExpression)
            .trimmingCharacters(in: CharacterSet(charactersIn: "-. "))
        if !collapsed.isEmpty, collapsed.count <= 80 {
            return String(collapsed.prefix(80))
        }
        let digest = SHA256.hash(data: Data(normalized.utf8))
            .map { String(format: "%02x", $0) }
            .joined()
            .prefix(12)
        if !collapsed.isEmpty {
            return "\(String(collapsed.prefix(67)))-\(digest)"
        }
        return "group-\(digest)"
    }

    private static func isCJK(_ scalar: UnicodeScalar) -> Bool {
        (0x3400 ... 0x4DBF).contains(Int(scalar.value))
            || (0x4E00 ... 0x9FFF).contains(Int(scalar.value))
    }

    enum CodingKeys: String, CodingKey {
        case schemaVersion = "schema_version"
        case kind
        case id
        case title
        case createdAt = "created_at"
        case updatedAt = "updated_at"
    }
}

public struct LibraryManifest: Codable, Equatable {
    public let schemaVersion: Int
    public let kind: String?
    public let updatedAt: String?
    public let episodeCount: Int
    public let subscriptionCount: Int
    public let tombstoneCount: Int
    public let episodes: [EpisodeEntry]
    public let subscriptions: [SubscriptionEntry]
    public let tombstones: [TombstoneEntry]

    public struct EpisodeEntry: Codable, Equatable, Identifiable {
        public var id: String {
            episodeID
        }

        public let episodeID: String
        public let path: String

        public init(episodeID: String, path: String) {
            self.episodeID = episodeID
            self.path = path
        }

        enum CodingKeys: String, CodingKey {
            case episodeID = "episode_id"
            case path
        }
    }

    public struct SubscriptionEntry: Codable, Equatable, Identifiable {
        public let id: String
        public let path: String

        public init(id: String, path: String) {
            self.id = id
            self.path = path
        }
    }

    public struct TombstoneEntry: Codable, Equatable, Identifiable {
        public var id: String {
            episodeID
        }

        public let episodeID: String
        public let path: String

        public init(episodeID: String, path: String) {
            self.episodeID = episodeID
            self.path = path
        }

        enum CodingKeys: String, CodingKey {
            case episodeID = "episode_id"
            case path
        }
    }

    public init(
        schemaVersion: Int,
        kind: String?,
        updatedAt: String?,
        episodeCount: Int,
        subscriptionCount: Int,
        tombstoneCount: Int = 0,
        episodes: [EpisodeEntry],
        subscriptions: [SubscriptionEntry],
        tombstones: [TombstoneEntry] = []
    ) {
        self.schemaVersion = schemaVersion
        self.kind = kind
        self.updatedAt = updatedAt
        self.episodeCount = episodeCount
        self.subscriptionCount = subscriptionCount
        self.tombstoneCount = tombstoneCount
        self.episodes = episodes
        self.subscriptions = subscriptions
        self.tombstones = tombstones
    }

    enum CodingKeys: String, CodingKey {
        case schemaVersion = "schema_version"
        case kind
        case updatedAt = "updated_at"
        case episodeCount = "episode_count"
        case subscriptionCount = "subscription_count"
        case tombstoneCount = "tombstone_count"
        case episodes
        case subscriptions
        case tombstones
    }
}

public enum LibraryStore {
    public static func loadManifest(from libraryRoot: URL) throws -> LibraryManifest {
        let data = try Data(contentsOf: libraryRoot.appendingPathComponent("manifest.json"))
        return try JSONDecoder().decode(LibraryManifest.self, from: data)
    }

    public static func loadEpisodes(from libraryRoot: URL) throws -> [LibraryEpisode] {
        let manifest = try loadManifest(from: libraryRoot)
        return try loadEpisodes(from: libraryRoot, manifest: manifest)
    }

    public static func loadEpisodes(from libraryRoot: URL, manifest: LibraryManifest) throws -> [LibraryEpisode] {
        return try manifest.episodes.map { entry in
            let data = try Data(contentsOf: libraryRoot.appendingPathComponent(entry.path))
            return try JSONDecoder().decode(LibraryEpisode.self, from: data)
        }
    }

    public static func loadSubscriptions(from libraryRoot: URL) throws -> [LibrarySubscription] {
        let manifest = try loadManifest(from: libraryRoot)
        return try loadSubscriptions(from: libraryRoot, manifest: manifest)
    }

    public static func loadSubscriptions(
        from libraryRoot: URL,
        manifest: LibraryManifest
    ) throws -> [LibrarySubscription] {
        return try manifest.subscriptions.map { entry in
            let data = try Data(contentsOf: libraryRoot.appendingPathComponent(entry.path))
            return try JSONDecoder().decode(LibrarySubscription.self, from: data)
        }
    }

    public static func loadGroups(from libraryRoot: URL) throws -> [LibraryGroup] {
        let groupRoot = libraryRoot.appendingPathComponent("groups", isDirectory: true)
        let urls = (try? FileManager.default.contentsOfDirectory(
            at: groupRoot,
            includingPropertiesForKeys: nil,
            options: [.skipsHiddenFiles]
        )) ?? []
        return urls
            .filter { $0.pathExtension == "json" }
            .compactMap { url in
                guard
                    let data = try? Data(contentsOf: url),
                    let group = try? JSONDecoder().decode(LibraryGroup.self, from: data),
                    group.kind == nil || group.kind == LibraryConstants.libraryGroupKind
                else {
                    return nil
                }
                return group
            }
            .sorted { $0.displayName.localizedStandardCompare($1.displayName) == .orderedAscending }
    }
}

public typealias MobileSyncConstants = LibraryConstants
public typealias MobileSyncPaths = LibraryPaths
public typealias MobileSyncDocument = LibraryDocument
public typealias MobileSyncEpisode = LibraryEpisode
public typealias MobileSyncSubscription = LibrarySubscription
public typealias MobileSyncGroup = LibraryGroup
public typealias MobileSyncManifest = LibraryManifest
public typealias MobileSyncStore = LibraryStore
