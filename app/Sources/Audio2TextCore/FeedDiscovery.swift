import Foundation

public struct PodcastFeedEpisode: Codable, Equatable, Identifiable {
    public var id: String {
        guid?.isEmpty == false ? guid! : audioURL
    }

    public let title: String
    public let sourceURL: String
    public let canonicalURL: String
    public let seriesName: String
    public let seriesURL: String
    public let publishedAt: String
    public let duration: String?
    public let description: String?
    public let audioURL: String
    public let imageURL: String?
    public let source: String
    public let guid: String?

    public init(
        title: String,
        sourceURL: String,
        canonicalURL: String,
        seriesName: String,
        seriesURL: String,
        publishedAt: String,
        duration: String?,
        description: String?,
        audioURL: String,
        imageURL: String?,
        source: String,
        guid: String?
    ) {
        self.title = title
        self.sourceURL = sourceURL
        self.canonicalURL = canonicalURL
        self.seriesName = seriesName
        self.seriesURL = seriesURL
        self.publishedAt = publishedAt
        self.duration = duration
        self.description = description
        self.audioURL = audioURL
        self.imageURL = imageURL
        self.source = source
        self.guid = guid
    }
}

public struct PodcastFeedDiscovery: Codable, Equatable {
    public let title: String
    public let source: String
    public let url: String
    public let feedURL: String
    public let episodes: [PodcastFeedEpisode]
}

public enum FeedDiscoveryError: LocalizedError {
    case invalidData
    case missingPodcastMetadata
    case missingAppleFeedURL
    case missingXiaoyuzhouPayload

    public var errorDescription: String? {
        switch self {
        case .invalidData:
            return "Feed data could not be parsed."
        case .missingPodcastMetadata:
            return "Podcast metadata was not found."
        case .missingAppleFeedURL:
            return "Apple Podcasts lookup did not include a feed URL."
        case .missingXiaoyuzhouPayload:
            return "Xiaoyuzhou podcast page data was not found."
        }
    }
}

public enum FeedDiscoveryParser {
    public static func parseRSSOrAtom(
        _ data: Data,
        feedURL: String,
        sourceURL: String,
        limit: Int? = nil
    ) throws -> PodcastFeedDiscovery {
        let delegate = PodcastXMLParser(feedURL: feedURL)
        let parser = XMLParser(data: data)
        parser.delegate = delegate
        guard parser.parse() else {
            throw FeedDiscoveryError.invalidData
        }
        let episodes = Array(delegate.episodes.prefix(limit ?? delegate.episodes.count))
        guard !delegate.title.isEmpty || !episodes.isEmpty else {
            throw FeedDiscoveryError.missingPodcastMetadata
        }
        return PodcastFeedDiscovery(
            title: delegate.title.isEmpty ? feedURL : delegate.title,
            source: "podcast_rss",
            url: sourceURL,
            feedURL: feedURL,
            episodes: episodes
        )
    }

    public static func parseAppleLookupFeedURL(_ data: Data) throws -> String {
        guard
            let object = try JSONSerialization.jsonObject(with: data) as? [String: Any],
            let results = object["results"] as? [[String: Any]],
            let feedURL = results.first?["feedUrl"] as? String,
            !feedURL.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
        else {
            throw FeedDiscoveryError.missingAppleFeedURL
        }
        return feedURL.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    public static func parseXiaoyuzhouPodcastHTML(_ html: String, sourceURL: String, limit: Int? = nil) throws -> PodcastFeedDiscovery {
        guard let payload = nextDataPayload(in: html),
              let props = payload["props"] as? [String: Any],
              let pageProps = props["pageProps"] as? [String: Any],
              let podcast = pageProps["podcast"] as? [String: Any]
        else {
            throw FeedDiscoveryError.missingXiaoyuzhouPayload
        }
        let title = clean(podcast["title"]) ?? ""
        guard !title.isEmpty else {
            throw FeedDiscoveryError.missingPodcastMetadata
        }
        let pid = clean(podcast["pid"]) ?? ""
        let canonicalURL = canonicalURL(in: html) ?? sourceURL
        let seriesURL = pid.isEmpty ? canonicalURL : "https://www.xiaoyuzhoufm.com/podcast/\(pid)"
        let imageURL = imageURL(from: podcast["image"]) ?? metaContent(in: html, property: "og:image")
        let rawEpisodes = podcast["episodes"] as? [[String: Any]] ?? []
        let episodes = rawEpisodes.prefix(limit ?? rawEpisodes.count).compactMap { item -> PodcastFeedEpisode? in
            xiaoyuzhouEpisode(from: item, podcastTitle: title, seriesURL: seriesURL, seriesImageURL: imageURL, fallbackURL: sourceURL)
        }
        return PodcastFeedDiscovery(
            title: title,
            source: "xiaoyuzhou",
            url: canonicalURL,
            feedURL: "",
            episodes: episodes
        )
    }

    private static func xiaoyuzhouEpisode(
        from item: [String: Any],
        podcastTitle: String,
        seriesURL: String,
        seriesImageURL: String?,
        fallbackURL: String
    ) -> PodcastFeedEpisode? {
        guard let title = clean(item["title"]), let audioURL = enclosureURL(from: item), let publishedAt = clean(item["pubDate"]) else {
            return nil
        }
        let eid = clean(item["eid"]) ?? clean(item["id"]) ?? ""
        let canonical = eid.isEmpty ? fallbackURL : "https://www.xiaoyuzhoufm.com/episode/\(eid)"
        return PodcastFeedEpisode(
            title: title,
            sourceURL: canonical,
            canonicalURL: canonical,
            seriesName: podcastTitle,
            seriesURL: seriesURL,
            publishedAt: publishedAt,
            duration: clean(item["duration"]),
            description: clean(item["shownotes"]) ?? clean(item["description"]),
            audioURL: audioURL,
            imageURL: imageURL(from: item["image"]) ?? seriesImageURL,
            source: "xiaoyuzhou",
            guid: eid.isEmpty ? nil : eid
        )
    }

    private static func nextDataPayload(in html: String) -> [String: Any]? {
        let marker = #"<script id="__NEXT_DATA__" type="application/json">"#
        guard let start = html.range(of: marker) else { return nil }
        let rest = html[start.upperBound...]
        guard let end = rest.range(of: "</script>") else { return nil }
        let text = String(rest[..<end.lowerBound])
            .replacingOccurrences(of: "&quot;", with: "\"")
            .replacingOccurrences(of: "&amp;", with: "&")
        guard let data = text.data(using: .utf8) else { return nil }
        return try? JSONSerialization.jsonObject(with: data) as? [String: Any]
    }

    private static func enclosureURL(from item: [String: Any]) -> String? {
        if let enclosure = item["enclosure"] as? [String: Any], let url = clean(enclosure["url"]) {
            return url
        }
        if let media = item["media"] as? [String: Any],
           let source = media["source"] as? [String: Any],
           let url = clean(source["url"])
        {
            return url
        }
        return nil
    }

    private static func imageURL(from value: Any?) -> String? {
        guard let object = value as? [String: Any] else { return nil }
        return clean(object["picUrl"]) ?? clean(object["url"])
    }

    private static func canonicalURL(in html: String) -> String? {
        linkContent(in: html, rel: "canonical")
    }

    private static func linkContent(in html: String, rel: String) -> String? {
        let pattern = #"<link[^>]*rel=["']\#(rel)["'][^>]*href=["']([^"']+)["'][^>]*>"#
        return firstCapture(in: html, pattern: pattern, group: 2)
    }

    private static func metaContent(in html: String, property: String) -> String? {
        let pattern = #"<meta[^>]*(?:property|name)=["']\#(property)["'][^>]*content=["']([^"']+)["'][^>]*>"#
        return firstCapture(in: html, pattern: pattern, group: 2)
    }

    private static func firstCapture(in text: String, pattern: String, group: Int) -> String? {
        guard let regex = try? NSRegularExpression(pattern: pattern, options: [.caseInsensitive, .dotMatchesLineSeparators]) else {
            return nil
        }
        let range = NSRange(text.startIndex ..< text.endIndex, in: text)
        guard let match = regex.firstMatch(in: text, range: range), match.numberOfRanges > group else {
            return nil
        }
        let capture = match.range(at: group)
        guard let swiftRange = Range(capture, in: text) else { return nil }
        return clean(String(text[swiftRange]))
    }

    fileprivate static func clean(_ value: Any?) -> String? {
        guard let value else { return nil }
        let text = String(describing: value)
            .replacingOccurrences(of: "\r\n", with: "\n")
            .replacingOccurrences(of: "\r", with: "\n")
            .trimmingCharacters(in: .whitespacesAndNewlines)
        return text.isEmpty ? nil : text
    }
}

private final class PodcastXMLParser: NSObject, XMLParserDelegate {
    let feedURL: String
    var title = ""
    var imageURL: String?
    var episodes: [PodcastFeedEpisode] = []

    private var elementStack: [String] = []
    private var text = ""
    private var inItem = false
    private var current = PodcastXMLItem()

    init(feedURL: String) {
        self.feedURL = feedURL
    }

    func parser(
        _: XMLParser,
        didStartElement elementName: String,
        namespaceURI _: String?,
        qualifiedName qName: String?,
        attributes attributeDict: [String: String] = [:]
    ) {
        let element = (qName ?? elementName).lowercased()
        elementStack.append(element)
        text = ""
        if element == "item" || element == "entry" {
            inItem = true
            current = PodcastXMLItem()
        }
        if inItem, element == "enclosure", let url = attributeDict["url"] {
            current.audioURL = url
        }
        if inItem, element == "link", current.audioURL == nil, attributeDict["rel"] == "enclosure", let href = attributeDict["href"] {
            current.audioURL = href
        }
        if inItem, element == "link", current.link == nil, let href = attributeDict["href"], attributeDict["rel"] != "enclosure" {
            current.link = href
        }
        if element == "itunes:image" || element == "image" {
            let href = attributeDict["href"] ?? attributeDict["url"]
            if inItem {
                current.imageURL = href
            } else if imageURL == nil {
                imageURL = href
            }
        }
    }

    func parser(_: XMLParser, foundCharacters string: String) {
        text += string
    }

    func parser(_: XMLParser, foundCDATA CDATABlock: Data) {
        if let cdata = String(data: CDATABlock, encoding: .utf8) {
            text += cdata
        }
    }

    func parser(_: XMLParser, didEndElement elementName: String, namespaceURI _: String?, qualifiedName qName: String?) {
        let element = (qName ?? elementName).lowercased()
        let value = FeedDiscoveryParser.clean(text)
        if inItem {
            applyItemValue(element: element, value: value)
        } else {
            applyFeedValue(element: element, value: value)
        }
        if element == "item" || element == "entry" {
            if let episode = current.episode(feedTitle: title, feedURL: feedURL, feedImageURL: imageURL) {
                episodes.append(episode)
            }
            inItem = false
            current = PodcastXMLItem()
        }
        if !elementStack.isEmpty {
            elementStack.removeLast()
        }
        text = ""
    }

    private func applyFeedValue(element: String, value: String?) {
        guard let value else { return }
        if title.isEmpty, element == "title" {
            title = value
        } else if imageURL == nil, element == "url", elementStack.contains("image") {
            imageURL = value
        }
    }

    private func applyItemValue(element: String, value: String?) {
        guard let value else { return }
        switch element {
        case "title":
            current.title = value
        case "guid", "id":
            current.guid = value
        case "link":
            if current.link == nil {
                current.link = value
            }
        case "pubdate", "published", "updated":
            if current.publishedAt == nil {
                current.publishedAt = value
            }
        case "description", "summary", "content":
            if current.summary == nil {
                current.summary = stripHTML(value)
            }
        case "itunes:duration", "duration":
            current.duration = value
        default:
            break
        }
    }

    private func stripHTML(_ value: String) -> String {
        value.replacingOccurrences(of: #"<[^>]+>"#, with: "", options: .regularExpression)
    }
}

private struct PodcastXMLItem {
    var title: String?
    var guid: String?
    var link: String?
    var publishedAt: String?
    var duration: String?
    var summary: String?
    var audioURL: String?
    var imageURL: String?

    func episode(feedTitle: String, feedURL: String, feedImageURL: String?) -> PodcastFeedEpisode? {
        guard let title, let audioURL else { return nil }
        let canonical = link ?? guid ?? feedURL
        return PodcastFeedEpisode(
            title: title,
            sourceURL: canonical,
            canonicalURL: canonical,
            seriesName: feedTitle,
            seriesURL: feedURL,
            publishedAt: publishedAt ?? ISO8601DateFormatter().string(from: Date()),
            duration: duration,
            description: summary,
            audioURL: audioURL,
            imageURL: imageURL ?? feedImageURL,
            source: "podcast_rss",
            guid: guid
        )
    }
}
