import Foundation

public enum FeedDiscoveryServiceError: LocalizedError {
    case invalidAppleURL
    case invalidFeedURL

    public var errorDescription: String? {
        switch self {
        case .invalidAppleURL:
            return "Could not find an Apple Podcasts id in the URL."
        case .invalidFeedURL:
            return "The subscription feed URL is invalid."
        }
    }
}

public enum FeedDiscoveryService {
    public static func discover(url: URL, limit: Int? = 10) async throws -> PodcastFeedDiscovery {
        let text = url.absoluteString
        if text.contains("xiaoyuzhoufm.com/podcast/") {
            let (data, _) = try await URLSession.shared.data(from: url)
            let html = String(data: data, encoding: .utf8) ?? ""
            return try FeedDiscoveryParser.parseXiaoyuzhouPodcastHTML(html, sourceURL: text, limit: limit)
        }
        if text.contains("podcasts.apple.com") {
            let id = try applePodcastID(from: text)
            let lookupURL = URL(string: "https://itunes.apple.com/lookup?id=\(id)&entity=podcast")!
            let (lookupData, _) = try await URLSession.shared.data(from: lookupURL)
            let feedURLString = try FeedDiscoveryParser.parseAppleLookupFeedURL(lookupData)
            guard let feedURL = URL(string: feedURLString) else {
                throw FeedDiscoveryServiceError.invalidFeedURL
            }
            let (feedData, _) = try await URLSession.shared.data(from: feedURL)
            return try FeedDiscoveryParser.parseRSSOrAtom(feedData, feedURL: feedURLString, sourceURL: text, limit: limit)
        }
        let (data, _) = try await URLSession.shared.data(from: url)
        return try FeedDiscoveryParser.parseRSSOrAtom(data, feedURL: text, sourceURL: text, limit: limit)
    }

    private static func applePodcastID(from text: String) throws -> String {
        guard let match = text.range(of: #"/id(\d+)"#, options: .regularExpression) else {
            throw FeedDiscoveryServiceError.invalidAppleURL
        }
        return String(text[match]).replacingOccurrences(of: "/id", with: "")
    }
}
