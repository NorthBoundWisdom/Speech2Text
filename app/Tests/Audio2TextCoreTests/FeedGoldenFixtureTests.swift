@testable import Audio2TextCore
import XCTest

final class FeedGoldenFixtureTests: XCTestCase {
    func testSharedFeedGoldenFixturesMatchDiscoveryAndIDContracts() throws {
        let expected = try loadExpected()

        let rss = try FeedDiscoveryParser.parseRSSOrAtom(
            fixtureData("rss.xml"),
            feedURL: expected.rss.feedURL,
            sourceURL: expected.rss.url
        )
        assertDiscovery(rss, matches: expected.rss)

        let appleFeedURL = try FeedDiscoveryParser.parseAppleLookupFeedURL(fixtureData("apple_lookup.json"))
        XCTAssertEqual(appleFeedURL, expected.apple.lookupFeedURL)
        let appleRSS = try FeedDiscoveryParser.parseRSSOrAtom(
            fixtureData("rss.xml"),
            feedURL: appleFeedURL,
            sourceURL: expected.apple.sourceURL
        )
        XCTAssertEqual(LibraryWriter.subscriptionID(for: appleRSS), expected.rss.subscriptionID)

        let atom = try FeedDiscoveryParser.parseRSSOrAtom(
            fixtureData("atom.xml"),
            feedURL: expected.atom.feedURL,
            sourceURL: expected.atom.url
        )
        assertDiscovery(atom, matches: expected.atom)

        let xiaoyuzhou = try FeedDiscoveryParser.parseXiaoyuzhouPodcastHTML(
            fixtureText("xiaoyuzhou.html"),
            sourceURL: expected.xiaoyuzhou.url
        )
        assertDiscovery(xiaoyuzhou, matches: expected.xiaoyuzhou)
    }

    func testSharedFeedGoldenFixtureWritesDeterministicLibraryCounts() throws {
        let expected = try loadExpected()
        let root = temporaryLibraryRoot()
        defer { try? FileManager.default.removeItem(at: root) }

        let discovery = try FeedDiscoveryParser.parseRSSOrAtom(
            fixtureData("rss.xml"),
            feedURL: expected.rss.feedURL,
            sourceURL: expected.rss.url
        )
        try writeExistingMetadataOnlyEpisode(
            id: expected.libraryWrite.reusedEpisodeID,
            subscriptionID: expected.rss.subscriptionID,
            to: root
        )
        try writeTombstone(id: expected.libraryWrite.tombstoneEpisodeID, subscriptionID: expected.rss.subscriptionID, to: root)

        let result = try LibraryWriter.writeMetadataOnly(
            discovery: discovery,
            to: root,
            groupName: expected.libraryWrite.groupName
        )
        let episodes = try LibraryStore.loadEpisodes(from: root)
        let manifest = try LibraryStore.loadManifest(from: root)

        XCTAssertEqual(result.subscriptionID, expected.rss.subscriptionID)
        XCTAssertEqual(result.writtenEpisodeCount, expected.libraryWrite.importedCount)
        XCTAssertEqual(result.reusedMetadataEpisodeCount, expected.libraryWrite.reusedCount)
        XCTAssertEqual(result.tombstoneSkippedEpisodeCount, expected.libraryWrite.skippedCount)
        XCTAssertEqual(result.skippedAvailableEpisodeCount, 0)
        XCTAssertEqual(episodes.map(\.id).sorted(), [
            expected.libraryWrite.reusedEpisodeID,
            expected.libraryWrite.newEpisodeID,
        ].sorted())
        XCTAssertEqual(manifest.subscriptionCount, 1)
        XCTAssertEqual(manifest.episodeCount, 2)
        XCTAssertEqual(manifest.tombstoneCount, 1)

        let reused = try XCTUnwrap(episodes.first { $0.id == expected.libraryWrite.reusedEpisodeID })
        let created = try XCTUnwrap(episodes.first { $0.id == expected.libraryWrite.newEpisodeID })
        XCTAssertEqual(reused.title, "Existing Metadata Title")
        XCTAssertEqual(reused.appGroup, expected.libraryWrite.groupName)
        XCTAssertEqual(created.title, "001. Golden RSS")
        XCTAssertEqual(created.appGroup, expected.libraryWrite.groupName)
    }

    private func assertDiscovery(_ discovery: PodcastFeedDiscovery, matches expected: ExpectedFeed) {
        let subscriptionID = LibraryWriter.subscriptionID(for: discovery)
        XCTAssertEqual(discovery.title, expected.title)
        XCTAssertEqual(discovery.source, expected.source)
        XCTAssertEqual(discovery.feedURL, expected.feedURL)
        XCTAssertEqual(discovery.url, expected.url)
        XCTAssertEqual(subscriptionID, expected.subscriptionID)
        XCTAssertEqual(episodeIDs(for: discovery, subscriptionID: subscriptionID), expected.episodeIDs)
    }

    private func episodeIDs(for discovery: PodcastFeedDiscovery, subscriptionID: String) -> [String] {
        discovery.episodes.map { episode in
            StableEpisodeID.make(
                source: episode.source,
                subscriptionID: subscriptionID,
                guid: episode.guid,
                audioURL: episode.audioURL,
                canonicalURL: episode.canonicalURL,
                sourceURL: episode.sourceURL,
                title: episode.title
            )
        }
    }

    private func writeExistingMetadataOnlyEpisode(id: String, subscriptionID: String, to root: URL) throws {
        let episode = LibraryEpisode(
            episodeID: id,
            title: "Existing Metadata Title",
            source: "podcast_rss",
            sourceURL: "https://podcast.example/golden/rss/002",
            canonicalURL: "https://podcast.example/golden/rss/002",
            seriesName: "Golden RSS Show",
            seriesURL: "https://podcast.example/golden/rss.xml",
            publishedAt: "Fri, 29 May 2026 00:00:00 GMT",
            duration: "00:24:00",
            audioURL: "https://media.example/golden/rss-002.m4a",
            guid: "golden-rss-002",
            subscriptionID: subscriptionID,
            appGroup: "Research",
            productStatus: LibraryConstants.productStatusMetadataOnly
        )
        let episodeRoot = root.appendingPathComponent("episodes/\(id)", isDirectory: true)
        try FileManager.default.createDirectory(at: episodeRoot, withIntermediateDirectories: true)
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        try encoder.encode(episode).write(to: episodeRoot.appendingPathComponent("episode.json"), options: .atomic)
    }

    private func writeTombstone(id: String, subscriptionID: String, to root: URL) throws {
        let tombstone: [String: Any] = [
            "schema_version": LibraryConstants.schemaVersion,
            "kind": LibraryConstants.libraryEpisodeTombstoneKind,
            "episode_id": id,
            "subscription_id": subscriptionID,
            "guid": "golden-rss-deleted",
            "deleted_at": "2026-05-31T00:00:00Z",
        ]
        let tombstoneURL = root.appendingPathComponent("tombstones/episodes/\(id).json")
        try FileManager.default.createDirectory(at: tombstoneURL.deletingLastPathComponent(), withIntermediateDirectories: true)
        let data = try JSONSerialization.data(withJSONObject: tombstone, options: [.prettyPrinted, .sortedKeys])
        try data.write(to: tombstoneURL, options: .atomic)
    }

    private func fixtureData(_ name: String) throws -> Data {
        try Data(contentsOf: fixtureURL(name))
    }

    private func fixtureText(_ name: String) throws -> String {
        try String(contentsOf: fixtureURL(name), encoding: .utf8)
    }

    private func loadExpected() throws -> ExpectedFeedGolden {
        try JSONDecoder().decode(ExpectedFeedGolden.self, from: fixtureData("expected.json"))
    }

    private func fixtureURL(_ name: String) throws -> URL {
        try XCTUnwrap(Bundle.module.url(forResource: name, withExtension: nil, subdirectory: "Fixtures/FeedGolden"))
    }

    private func temporaryLibraryRoot() -> URL {
        URL(fileURLWithPath: NSTemporaryDirectory())
            .appendingPathComponent("FeedGoldenFixtureTests-\(UUID().uuidString)", isDirectory: true)
    }
}

private struct ExpectedFeedGolden: Decodable {
    let rss: ExpectedFeed
    let atom: ExpectedFeed
    let apple: ExpectedAppleFeed
    let xiaoyuzhou: ExpectedFeed
    let libraryWrite: ExpectedLibraryWrite

    private enum CodingKeys: String, CodingKey {
        case rss
        case atom
        case apple
        case xiaoyuzhou
        case libraryWrite = "library_write"
    }
}

private struct ExpectedFeed: Decodable {
    let title: String
    let source: String
    let url: String
    let feedURL: String
    let subscriptionID: String
    let episodeIDs: [String]

    private enum CodingKeys: String, CodingKey {
        case title
        case source
        case url
        case feedURL = "feed_url"
        case subscriptionID = "subscription_id"
        case episodeIDs = "episode_ids"
    }
}

private struct ExpectedAppleFeed: Decodable {
    let lookupFeedURL: String
    let sourceURL: String

    private enum CodingKeys: String, CodingKey {
        case lookupFeedURL = "lookup_feed_url"
        case sourceURL = "source_url"
    }
}

private struct ExpectedLibraryWrite: Decodable {
    let groupName: String
    let newEpisodeID: String
    let reusedEpisodeID: String
    let tombstoneEpisodeID: String
    let importedCount: Int
    let reusedCount: Int
    let skippedCount: Int

    private enum CodingKeys: String, CodingKey {
        case groupName = "group_name"
        case newEpisodeID = "new_episode_id"
        case reusedEpisodeID = "reused_episode_id"
        case tombstoneEpisodeID = "tombstone_episode_id"
        case importedCount = "imported_count"
        case reusedCount = "reused_count"
        case skippedCount = "skipped_count"
    }
}
