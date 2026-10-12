@testable import Audio2TextApp
import Audio2TextCore
import XCTest

final class ProcessLibraryOperationsTests: XCTestCase {
    func testDeleteRemoteLibraryItemRecordsTombstoneBeforeRemovingFiles() throws {
        let root = URL(fileURLWithPath: NSTemporaryDirectory())
            .appendingPathComponent(UUID().uuidString)
        let dataRoot = root.appendingPathComponent("data")
        let episode = try writeTestLibraryEpisode(
            dataRoot: dataRoot,
            id: "delete-me",
            title: "删除节目",
            metadata: [
                "audio_url": "https://media.example/delete-me.m4a",
                "guid": "delete-me-guid",
                "source": "podcast_rss",
                "subscription_id": "podcast-main",
            ],
            audioFileName: "delete-me.m4a"
        )
        try FileManager.default.createDirectory(at: episode.workRoot, withIntermediateDirectories: true)
        let item = try XCTUnwrap(ProcessLibrary.scan(dataRoot: dataRoot).first)

        try ProcessLibraryOperations.deleteItem(item, dataRoot: dataRoot)

        XCTAssertFalse(FileManager.default.fileExists(atPath: episode.materialRoot.path))
        XCTAssertFalse(FileManager.default.fileExists(atPath: episode.workRoot.path))
        XCTAssertFalse(FileManager.default.fileExists(atPath: episode.episodeRoot.path))
        let tombstone = try readJSON(episode.libraryRoot.appendingPathComponent("tombstones/episodes/delete-me.json"))
        XCTAssertEqual(tombstone["audio_url"] as? String, "https://media.example/delete-me.m4a")
        XCTAssertEqual(tombstone["guid"] as? String, "delete-me-guid")
    }

    @MainActor
    func testCreateGroupDoesNotChangeSelectedSidebarSource() async throws {
        let groupName = "Test-\(UUID().uuidString)"
        let normalizedGroupName = ProcessLibrary.pathComponent(forGroupName: groupName)
        let controller = testJobController()
        controller.selectedSidebarSource = .smart(.today)

        controller.createGroup(named: groupName)

        XCTAssertEqual(controller.selectedSidebarSource, .smart(.today))
        try await waitForCondition("created group appears") {
            controller.availableGroupNames.contains(normalizedGroupName)
        }
        XCTAssertTrue(controller.availableGroupNames.contains(normalizedGroupName))
    }

    func testDeleteEmptyCustomGroupRemovesGroupOnly() throws {
        let root = URL(fileURLWithPath: NSTemporaryDirectory())
            .appendingPathComponent(UUID().uuidString)
        let dataRoot = root.appendingPathComponent("data")
        let libraryRoot = try configureLocalTestLibrary(dataRoot: dataRoot)
        let groupName = "Empty-\(UUID().uuidString)"
        let normalizedGroupName = ProcessLibrary.pathComponent(forGroupName: groupName)
        try ProcessLibrary.createGroup(normalizedGroupName, in: libraryRoot)

        XCTAssertTrue(ProcessLibrary.groupNames(dataRoot: dataRoot).contains(normalizedGroupName))
        XCTAssertFalse(try LibraryStore.loadGroups(from: libraryRoot).isEmpty)

        let result = try ProcessLibraryOperations.deleteGroup(groupName, dataRoot: dataRoot)

        XCTAssertTrue(result.deleted)
        XCTAssertEqual(result.movedItemCount, 0)
        XCTAssertFalse(ProcessLibrary.groupNames(dataRoot: dataRoot).contains(normalizedGroupName))
        XCTAssertFalse(try LibraryStore.loadGroups(from: libraryRoot).contains { $0.displayName == normalizedGroupName })
    }

    func testDeleteGroupMovesItemsBackToDefaultWithoutDeletingThem() throws {
        let root = URL(fileURLWithPath: NSTemporaryDirectory())
            .appendingPathComponent(UUID().uuidString)
        let dataRoot = root.appendingPathComponent("data")
        let groupName = "Research-\(UUID().uuidString)"
        let episode = try writeTestLibraryEpisode(
            dataRoot: dataRoot,
            id: "group-delete",
            title: "Group Delete",
            metadata: ["app_group": groupName],
            documents: ["transcript.md": "Transcript"]
        )

        let result = try ProcessLibraryOperations.deleteGroup(groupName, dataRoot: dataRoot)
        let item = try XCTUnwrap(ProcessLibrary.scan(dataRoot: dataRoot).first)
        let metadata = try readJSON(episode.recordURL)

        XCTAssertTrue(result.deleted)
        XCTAssertEqual(result.movedItemCount, 1)
        XCTAssertEqual(item.groupName, ProcessLibrary.defaultGroupName)
        XCTAssertEqual(metadata["app_group"] as? String, ProcessLibrary.defaultGroupName)
        XCTAssertTrue(FileManager.default.fileExists(atPath: episode.recordURL.path))
        XCTAssertTrue(FileManager.default.fileExists(atPath: episode.documentsRoot.appendingPathComponent("transcript.md").path))
        XCTAssertTrue(FileManager.default.fileExists(atPath: episode.audioURL.path))
    }

    func testDeleteDefaultGroupIsNoOp() throws {
        let root = URL(fileURLWithPath: NSTemporaryDirectory())
            .appendingPathComponent(UUID().uuidString)
        let dataRoot = root.appendingPathComponent("data")
        _ = try configureLocalTestLibrary(dataRoot: dataRoot)

        let result = try ProcessLibraryOperations.deleteGroup(ProcessLibrary.defaultGroupName, dataRoot: dataRoot)

        XCTAssertFalse(result.deleted)
        XCTAssertEqual(result.movedItemCount, 0)
        XCTAssertTrue(ProcessLibrary.groupNames(dataRoot: dataRoot).contains(ProcessLibrary.defaultGroupName))
    }

    @MainActor
    func testDeleteSelectedGroupSwitchesSidebarToDefault() {
        let groupName = "Selected-\(UUID().uuidString)"
        let normalizedGroupName = ProcessLibrary.pathComponent(forGroupName: groupName)
        let controller = testJobController()
        controller.createGroup(named: normalizedGroupName)
        controller.selectedSidebarSource = .group(normalizedGroupName)
        controller.selectedGroupName = normalizedGroupName

        controller.deleteGroup(normalizedGroupName)

        XCTAssertEqual(controller.selectedSidebarSource, .group(ProcessLibrary.defaultGroupName))
        XCTAssertEqual(controller.selectedGroupName, ProcessLibrary.defaultGroupName)
        XCTAssertFalse(controller.availableGroupNames.contains(normalizedGroupName))
    }

    @MainActor
    func testBatchQueueStatusUpdatesSelectedUnprocessedItems() throws {
        let root = URL(fileURLWithPath: NSTemporaryDirectory())
            .appendingPathComponent(UUID().uuidString)
        let dataRoot = root.appendingPathComponent("data")
        let firstRecord = try writeTestLibraryEpisode(dataRoot: dataRoot, id: "first", title: "First")
        let secondRecord = try writeTestLibraryEpisode(dataRoot: dataRoot, id: "second", title: "Second")
        let processedRecord = try writeTestLibraryEpisode(
            dataRoot: dataRoot,
            id: "processed",
            title: "Processed",
            documents: ["transcript.md": "done"]
        )
        try FileManager.default.createDirectory(at: processedRecord.workRoot, withIntermediateDirectories: true)
        try #"{"success":true,"chunks":[]}"#.write(to: processedRecord.workRoot.appendingPathComponent("run.json"), atomically: true, encoding: .utf8)
        let scanned = ProcessLibrary.scan(dataRoot: dataRoot)
        let first = try XCTUnwrap(scanned.first { $0.id == "first" })
        let second = try XCTUnwrap(scanned.first { $0.id == "second" })
        let processed = try XCTUnwrap(scanned.first { $0.id == "processed" })
        let controller = testJobController()

        controller.markQueueStatus(.delete, for: [first, second, processed, first])

        XCTAssertEqual(try readJSON(firstRecord.recordURL)["app_queue_status"] as? String, AppQueueStatus.delete.rawValue)
        XCTAssertEqual(try readJSON(secondRecord.recordURL)["app_queue_status"] as? String, AppQueueStatus.delete.rawValue)
        XCTAssertEqual(try readJSON(processedRecord.recordURL)["app_queue_status"] as? String, AppQueueStatus.unread.rawValue)
    }

    @MainActor
    func testBatchDeleteRemovesSelectedItemsAcrossProcessingStates() throws {
        let root = URL(fileURLWithPath: NSTemporaryDirectory())
            .appendingPathComponent(UUID().uuidString)
        let dataRoot = root.appendingPathComponent("data")
        let firstRecord = try writeTestLibraryEpisode(dataRoot: dataRoot, id: "first", title: "First")
        let processedRecord = try writeTestLibraryEpisode(
            dataRoot: dataRoot,
            id: "processed",
            title: "Processed",
            documents: ["transcript.md": "done"]
        )
        try FileManager.default.createDirectory(at: firstRecord.workRoot, withIntermediateDirectories: true)
        try FileManager.default.createDirectory(at: processedRecord.workRoot, withIntermediateDirectories: true)
        let scanned = ProcessLibrary.scan(dataRoot: dataRoot)
        let first = try XCTUnwrap(scanned.first { $0.id == "first" })
        let processed = try XCTUnwrap(scanned.first { $0.id == "processed" })
        let controller = testJobController()

        controller.deleteLibraryItems([first, processed])

        XCTAssertFalse(FileManager.default.fileExists(atPath: firstRecord.materialRoot.path))
        XCTAssertFalse(FileManager.default.fileExists(atPath: firstRecord.workRoot.path))
        XCTAssertFalse(FileManager.default.fileExists(atPath: firstRecord.episodeRoot.path))
        XCTAssertFalse(FileManager.default.fileExists(atPath: processedRecord.materialRoot.path))
        XCTAssertFalse(FileManager.default.fileExists(atPath: processedRecord.workRoot.path))
        XCTAssertFalse(FileManager.default.fileExists(atPath: processedRecord.episodeRoot.path))
    }

    @MainActor
    func testBatchMoveUpdatesSelectedItemsAcrossProcessingStates() throws {
        let root = URL(fileURLWithPath: NSTemporaryDirectory())
            .appendingPathComponent(UUID().uuidString)
        let dataRoot = root.appendingPathComponent("data")
        let firstRecord = try writeTestLibraryEpisode(dataRoot: dataRoot, id: "first", title: "First")
        let processedRecord = try writeTestLibraryEpisode(
            dataRoot: dataRoot,
            id: "processed",
            title: "Processed",
            documents: ["transcript.md": "done"]
        )
        let scanned = ProcessLibrary.scan(dataRoot: dataRoot)
        let first = try XCTUnwrap(scanned.first { $0.id == "first" })
        let processed = try XCTUnwrap(scanned.first { $0.id == "processed" })
        let controller = testJobController()

        controller.moveLibraryItems([first, processed, first], toGroup: "Research")

        XCTAssertEqual(try readJSON(firstRecord.recordURL)["app_group"] as? String, "Research")
        XCTAssertEqual(try readJSON(processedRecord.recordURL)["app_group"] as? String, "Research")
    }

    @MainActor
    func testBatchCleanupCacheKeepsAnalysisResults() throws {
        let root = URL(fileURLWithPath: NSTemporaryDirectory())
            .appendingPathComponent(UUID().uuidString)
        let item = try testLibraryItem(
            id: "processed-\(UUID().uuidString)",
            title: "Processed",
            groupName: "Default",
            audioURL: writeAudioFile(root.appendingPathComponent("processed/processed.m4a")),
            status: "QA pass",
            hasTranscript: true,
            hasOutput: true,
            runStatus: "done",
            modifiedAt: Date()
        )
        let details = item.outputURL
        let chunks = details.appendingPathComponent("chunks")
        try FileManager.default.createDirectory(at: chunks, withIntermediateDirectories: true)
        try "prepared".write(to: details.appendingPathComponent("prepared.wav"), atomically: true, encoding: .utf8)
        try "chunk wav".write(to: chunks.appendingPathComponent("chunk_0000.wav"), atomically: true, encoding: .utf8)
        try "{}".write(to: chunks.appendingPathComponent("chunk_0000.json"), atomically: true, encoding: .utf8)
        try "{}".write(to: details.appendingPathComponent("raw.json"), atomically: true, encoding: .utf8)
        try "raw".write(to: details.appendingPathComponent("transcript.raw.txt"), atomically: true, encoding: .utf8)
        try "corrected".write(to: details.appendingPathComponent("transcript.corrected.txt"), atomically: true, encoding: .utf8)
        try "qa".write(to: details.appendingPathComponent("qa.md"), atomically: true, encoding: .utf8)
        try "summary".write(to: item.outputURL.appendingPathComponent("summary.md"), atomically: true, encoding: .utf8)
        let controller = testJobController()

        controller.cleanupCache(for: [item])

        XCTAssertFalse(FileManager.default.fileExists(atPath: item.audioURL.path))
        XCTAssertFalse(FileManager.default.fileExists(atPath: details.appendingPathComponent("prepared.wav").path))
        XCTAssertFalse(FileManager.default.fileExists(atPath: chunks.path))
        XCTAssertFalse(FileManager.default.fileExists(atPath: details.appendingPathComponent("raw.json").path))
        XCTAssertFalse(FileManager.default.fileExists(atPath: details.appendingPathComponent("transcript.raw.txt").path))
        XCTAssertTrue(FileManager.default.fileExists(atPath: details.appendingPathComponent("transcript.corrected.txt").path))
        XCTAssertTrue(FileManager.default.fileExists(atPath: details.appendingPathComponent("qa.md").path))
        XCTAssertTrue(FileManager.default.fileExists(atPath: item.outputURL.appendingPathComponent("summary.md").path))
    }
}
