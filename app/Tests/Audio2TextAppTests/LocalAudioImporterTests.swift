@testable import Audio2TextApp
import Audio2TextCore
import XCTest

final class LocalAudioImporterTests: XCTestCase {
    func testLocalImporterCopiesVideoAndWritesMetadata() throws {
        let root = URL(fileURLWithPath: NSTemporaryDirectory())
            .appendingPathComponent(UUID().uuidString)
        let dataRoot = root.appendingPathComponent("data")
        let source = root.appendingPathComponent("clip.mp4")
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        try "video".write(to: source, atomically: true, encoding: .utf8)
        let libraryRoot = try configureLocalTestLibrary(dataRoot: dataRoot)
        let importer = LocalAudioImporter(
            dataRoot: dataRoot,
            libraryRoot: libraryRoot,
            groupName: "Clips",
            now: { Date(timeIntervalSince1970: 1_779_840_000) }
        )

        let target = try importer.importAudio(source)
        let metadataURL = dataRoot
            .appendingPathComponent("Audio2TextLibrary/episodes", isDirectory: true)
            .appendingPathComponent(target.deletingLastPathComponent().lastPathComponent, isDirectory: true)
            .appendingPathComponent("episode.json")
        let localMetadataURL = target.deletingLastPathComponent().appendingPathComponent("local.json")
        let metadata = try readJSON(metadataURL)
        let localMetadata = try readJSON(localMetadataURL)
        let items = ProcessLibrary.scan(dataRoot: dataRoot)
        let groups = try LibraryStore.loadGroups(from: libraryRoot)

        XCTAssertEqual(target.lastPathComponent, "clip.mp4")
        XCTAssertTrue(target.path.contains("/materials/"))
        XCTAssertTrue(FileManager.default.fileExists(atPath: metadataURL.path))
        XCTAssertEqual(metadata["import_mode"] as? String, "copy")
        XCTAssertNil(metadata["audio_path"])
        XCTAssertNil(metadata["original_path"])
        XCTAssertEqual((localMetadata["original_fingerprint"] as? [String: Any])?["size_bytes"] as? Int, 5)
        XCTAssertEqual(items.first?.title, "clip")
        XCTAssertEqual(items.first?.groupName, "Clips")
        XCTAssertTrue(groups.contains { $0.displayName == "Clips" })
        XCTAssertEqual(items.first?.nodeStatus, .import)
        XCTAssertEqual(items.first?.hasFile, true)
        XCTAssertEqual(items.first?.hasProcessed, false)
        XCTAssertEqual(items.first?.isRead, false)
        XCTAssertEqual(items.first?.isStarred, false)
    }

    func testLocalImporterReferenceModeCreatesSymlinkAndMetadata() throws {
        let root = URL(fileURLWithPath: NSTemporaryDirectory())
            .appendingPathComponent(UUID().uuidString)
        let dataRoot = root.appendingPathComponent("data")
        let source = root.appendingPathComponent("clip.wav")
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        try "audio".write(to: source, atomically: true, encoding: .utf8)
        let libraryRoot = try configureLocalTestLibrary(dataRoot: dataRoot)
        let importer = LocalAudioImporter(
            dataRoot: dataRoot,
            libraryRoot: libraryRoot,
            groupName: "Refs",
            now: { Date(timeIntervalSince1970: 1_779_840_000) }
        )

        let target = try importer.importAudio(source, mode: .reference)
        let metadataURL = dataRoot
            .appendingPathComponent("Audio2TextLibrary/episodes", isDirectory: true)
            .appendingPathComponent(target.deletingLastPathComponent().lastPathComponent, isDirectory: true)
            .appendingPathComponent("episode.json")
        let localMetadataURL = target.deletingLastPathComponent().appendingPathComponent("local.json")
        let metadata = try readJSON(metadataURL)
        let localMetadata = try readJSON(localMetadataURL)
        let items = ProcessLibrary.scan(dataRoot: dataRoot)

        XCTAssertEqual(try FileManager.default.destinationOfSymbolicLink(atPath: target.path), source.path)
        XCTAssertEqual(metadata["import_mode"] as? String, "reference")
        XCTAssertNil(metadata["original_path"])
        XCTAssertEqual(localMetadata["original_path"] as? String, source.path)
        XCTAssertEqual((localMetadata["original_fingerprint"] as? [String: Any])?["size_bytes"] as? Int, 5)
        XCTAssertEqual(items.first?.groupName, "Refs")
        XCTAssertEqual(items.first?.hasFile, true)
    }
}
