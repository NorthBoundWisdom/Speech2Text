@testable import Audio2TextCore
import XCTest

final class LibraryDeletionTests: XCTestCase {
    func testDeleteEpisodeWritesTombstoneRebuildsManifestAndCleansLocalRoots() throws {
        let root = URL(fileURLWithPath: NSTemporaryDirectory())
            .appendingPathComponent("Audio2TextCoreTests-\(UUID().uuidString)", isDirectory: true)
        let localMaterials = root.appendingPathComponent("materials", isDirectory: true)
        let localWork = root.appendingPathComponent("work", isDirectory: true)
        defer { try? FileManager.default.removeItem(at: root) }
        let episode = LibraryEpisode(
            episodeID: "episode-delete",
            title: "Delete Me",
            source: "podcast_rss",
            sourceURL: "https://example.com/e",
            canonicalURL: "https://example.com/e",
            audioURL: "https://media.example/e.m4a",
            guid: "guid-delete",
            subscriptionID: "sub-main",
            productStatus: LibraryConstants.productStatusMetadataOnly
        )
        let keep = LibraryEpisode(
            episodeID: "episode-keep",
            title: "Keep Me",
            productStatus: LibraryConstants.productStatusMetadataOnly
        )
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        for item in [episode, keep] {
            let episodeRoot = root.appendingPathComponent("episodes/\(item.id)", isDirectory: true)
            try FileManager.default.createDirectory(at: episodeRoot, withIntermediateDirectories: true)
            try encoder.encode(item).write(to: episodeRoot.appendingPathComponent("episode.json"))
            try FileManager.default.createDirectory(at: localMaterials.appendingPathComponent(item.id, isDirectory: true), withIntermediateDirectories: true)
            try FileManager.default.createDirectory(at: localWork.appendingPathComponent(item.id, isDirectory: true), withIntermediateDirectories: true)
        }
        try LibraryWriter.rebuildManifest(libraryRoot: root)

        try LibraryWriter.deleteEpisode(episode, from: root, localMaterialRoot: localMaterials, localWorkRoot: localWork)

        let manifest = try LibraryStore.loadManifest(from: root)
        let tombstoneURL = root.appendingPathComponent("tombstones/episodes/episode-delete.json")
        let tombstone = try XCTUnwrap(
            try JSONSerialization.jsonObject(with: Data(contentsOf: tombstoneURL)) as? [String: Any]
        )
        XCTAssertEqual(manifest.episodeCount, 1)
        XCTAssertEqual(manifest.tombstoneCount, 1)
        XCTAssertEqual(manifest.episodes.map(\.episodeID), ["episode-keep"])
        XCTAssertEqual(manifest.tombstones.map(\.episodeID), ["episode-delete"])
        XCTAssertFalse(FileManager.default.fileExists(atPath: root.appendingPathComponent("episodes/episode-delete").path))
        XCTAssertFalse(FileManager.default.fileExists(atPath: localMaterials.appendingPathComponent("episode-delete").path))
        XCTAssertFalse(FileManager.default.fileExists(atPath: localWork.appendingPathComponent("episode-delete").path))
        XCTAssertTrue(FileManager.default.fileExists(atPath: localMaterials.appendingPathComponent("episode-keep").path))
        XCTAssertTrue(FileManager.default.fileExists(atPath: localWork.appendingPathComponent("episode-keep").path))
        XCTAssertEqual(tombstone["kind"] as? String, LibraryConstants.libraryEpisodeTombstoneKind)
        XCTAssertEqual(tombstone["episode_id"] as? String, "episode-delete")
        XCTAssertEqual(tombstone["title"] as? String, "Delete Me")
        XCTAssertEqual(tombstone["source"] as? String, "podcast_rss")
        XCTAssertEqual(tombstone["source_url"] as? String, "https://example.com/e")
        XCTAssertEqual(tombstone["canonical_url"] as? String, "https://example.com/e")
        XCTAssertEqual(tombstone["audio_url"] as? String, "https://media.example/e.m4a")
        XCTAssertEqual(tombstone["guid"] as? String, "guid-delete")
        XCTAssertEqual(tombstone["subscription_id"] as? String, "sub-main")
        XCTAssertNotNil(tombstone["deleted_at"] as? String)
    }
}
