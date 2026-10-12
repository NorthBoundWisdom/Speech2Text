import Foundation

struct PodcastSubscriptionItem: Identifiable, Codable, Equatable {
    let id: String
    let title: String
    let source: String
    let url: String
    let feedURL: String
    let groupName: String
    let createdAt: String
    let lastCheckedAt: String

    enum CodingKeys: String, CodingKey {
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

struct PodcastSubscriptionsPayload: Decodable {
    let subscriptions: [PodcastSubscriptionItem]
}

enum SubscriptionLibrary {
    static func subscriptionsFile(dataRoot: URL = AppPaths.dataRoot()) -> URL {
        libraryRoot(dataRoot: dataRoot).appendingPathComponent("subscriptions")
    }

    static func load(dataRoot: URL = AppPaths.dataRoot()) -> [PodcastSubscriptionItem] {
        let root = subscriptionsFile(dataRoot: dataRoot)
        let files = ((try? FileManager.default.contentsOfDirectory(at: root, includingPropertiesForKeys: nil)) ?? [])
            .filter { $0.pathExtension == "json" }
        let subscriptions = files.compactMap { url -> PodcastSubscriptionItem? in
            guard let data = try? Data(contentsOf: url) else { return nil }
            return try? JSONDecoder().decode(PodcastSubscriptionItem.self, from: data)
        }
        return subscriptions.sorted {
            $0.title.localizedStandardCompare($1.title) == .orderedAscending
        }
    }

    private static func libraryRoot(dataRoot: URL) -> URL {
        let config = (try? CloudConfigFile.load(dataRoot: dataRoot)) ?? CloudConfigFile()
        return AppPaths.libraryRoot(
            storage: config.libraryStorage,
            iCloudRoot: config.libraryICloudRoot,
            localRoot: config.libraryLocalRoot,
            dataRoot: dataRoot
        )
    }

    static func decodeCLIOutput(_ output: String) -> PodcastSubscriptionsPayload? {
        guard let data = output.data(using: .utf8) else { return nil }
        if let payload = try? JSONDecoder().decode(PodcastSubscriptionsPayload.self, from: data) {
            return payload
        }
        guard
            let start = output.firstIndex(of: "{"),
            let end = output.lastIndex(of: "}")
        else {
            return nil
        }
        return try? JSONDecoder().decode(
            PodcastSubscriptionsPayload.self,
            from: Data(String(output[start ... end]).utf8)
        )
    }
}
