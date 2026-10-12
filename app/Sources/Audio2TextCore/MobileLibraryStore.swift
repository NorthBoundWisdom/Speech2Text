import Foundation

public struct MobileLibrarySnapshot: Equatable {
    public let episodes: [LibraryEpisode]
    public let subscriptions: [LibrarySubscription]
    public let groupNames: [String]

    public init(episodes: [LibraryEpisode], subscriptions: [LibrarySubscription], groupNames: [String] = []) {
        self.episodes = episodes
        self.subscriptions = subscriptions
        self.groupNames = groupNames
    }
}

public struct MobileLibraryDocumentContent: Equatable, Identifiable {
    public var id: String {
        name
    }

    public let name: String
    public let title: String
    public let text: String

    public init(name: String, title: String, text: String) {
        self.name = name
        self.title = title
        self.text = text
    }
}

public enum MobileLibraryStore {
    public static func loadSnapshot(from libraryRoot: URL) throws -> MobileLibrarySnapshot {
        let manifest = try LibraryStore.loadManifest(from: libraryRoot)
        let episodes = try LibraryStore.loadEpisodes(from: libraryRoot, manifest: manifest)
        let subscriptions = try LibraryStore.loadSubscriptions(from: libraryRoot, manifest: manifest)
        let groupNames = try LibraryStore.loadGroups(from: libraryRoot).map(\.displayName)
        return MobileLibrarySnapshot(episodes: episodes, subscriptions: subscriptions, groupNames: groupNames)
    }

    public static func documentText(
        for episode: LibraryEpisode,
        named name: String,
        libraryRoot: URL
    ) -> String? {
        guard let document = episode.documents.first(where: { $0.name == name }) else {
            return nil
        }
        let url = libraryRoot
            .appendingPathComponent("episodes/\(episode.id)", isDirectory: true)
            .appendingPathComponent(document.path)
        guard let text = try? String(contentsOf: url, encoding: .utf8) else {
            return nil
        }
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        return trimmed.isEmpty ? nil : text
    }

    public static func documentContents(
        for episode: LibraryEpisode,
        libraryRoot: URL,
        preferredNames: [String] = ["summary.md", "transcript.md"]
    ) -> [MobileLibraryDocumentContent] {
        preferredNames.compactMap { name in
            guard let text = documentText(for: episode, named: name, libraryRoot: libraryRoot) else {
                return nil
            }
            return MobileLibraryDocumentContent(name: name, title: displayTitle(for: name), text: text)
        }
    }

    public static func displayTitle(for documentName: String) -> String {
        switch documentName {
        case "summary.md":
            return "摘要"
        case "transcript.md":
            return "转写"
        default:
            return documentName
        }
    }
}
