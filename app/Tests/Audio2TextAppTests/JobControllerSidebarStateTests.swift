@testable import Audio2TextApp
import Audio2TextCore
import XCTest

final class JobControllerSidebarStateTests: XCTestCase {
    @MainActor
    func testSidebarSmartFeedCountsAndFilters() throws {
        let root = URL(fileURLWithPath: NSTemporaryDirectory())
            .appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        let processedAudio = try writeAudioFile(root.appendingPathComponent("processed.m4a"))
        let pendingAudio = try writeAudioFile(root.appendingPathComponent("pending.m4a"))
        let missingAudio = root.appendingPathComponent("missing.m4a")
        let metadataOnlyAudio = root.appendingPathComponent("metadata-only.m4a")
        let now = Date()
        let old = Date(timeIntervalSinceNow: -86400 * 3)
        let processed = testLibraryItem(
            id: "processed-\(UUID().uuidString)",
            title: "Processed Today",
            groupName: "Default",
            audioURL: processedAudio,
            status: "QA pass",
            hasTranscript: true,
            hasOutput: true,
            runStatus: "done",
            processedAt: now,
            modifiedAt: now
        )
        let pending = testLibraryItem(
            id: "pending-\(UUID().uuidString)",
            title: "Pending Today",
            groupName: "Default",
            audioURL: pendingAudio,
            status: "Not processed",
            hasOutput: false,
            runStatus: "missing",
            modifiedAt: now
        )
        let missing = testLibraryItem(
            id: "missing-\(UUID().uuidString)",
            title: "Missing Audio",
            groupName: "Research",
            audioURL: missingAudio,
            status: "QA pass",
            hasTranscript: true,
            hasOutput: true,
            runStatus: "done",
            isStarred: true,
            processedAt: old,
            modifiedAt: old
        )
        let metadataOnly = testLibraryItem(
            id: "metadata-\(UUID().uuidString)",
            title: "Metadata Only",
            groupName: "Research",
            audioURL: metadataOnlyAudio,
            status: "Audio pending",
            modifiedAt: old
        )
        let archived = try testLibraryItem(
            id: "archived-\(UUID().uuidString)",
            title: "Archived Today",
            groupName: "Research",
            audioURL: writeAudioFile(root.appendingPathComponent("archived.m4a")),
            status: "QA pass",
            hasTranscript: true,
            hasOutput: true,
            runStatus: "done",
            isStarred: true,
            isArchived: true,
            processedAt: now,
            modifiedAt: now
        )
        let controller = testJobController()
        controller.libraryItems = [processed, pending, missing, metadataOnly, archived]
        controller.librarySections = ProcessLibrary.sections(from: controller.libraryItems, including: ["Default", "Research"])

        XCTAssertEqual(controller.count(for: .library), 2)
        XCTAssertEqual(controller.count(for: .smart(.today)), 1)
        XCTAssertEqual(controller.count(for: .smart(.unprocessed)), 2)
        XCTAssertEqual(controller.count(for: .smart(.starred)), 1)
        XCTAssertEqual(controller.count(for: .smart(.archive)), 1)
        XCTAssertEqual(controller.count(for: .group("Default")), 1)
        XCTAssertEqual(controller.count(for: .group("Research")), 1)
        XCTAssertEqual(controller.filteredLibraryItems(for: .library).map(\.title), ["Processed Today", "Missing Audio"])
        XCTAssertEqual(controller.filteredLibraryItems(for: .smart(.today)).map(\.title), ["Processed Today"])
        XCTAssertEqual(controller.filteredLibraryItems(for: .smart(.unprocessed)).map(\.title), ["Pending Today", "Metadata Only"])
        XCTAssertEqual(controller.filteredLibraryItems(for: .smart(.starred)).map(\.title), ["Missing Audio"])
        XCTAssertEqual(controller.filteredLibraryItems(for: .smart(.archive)).map(\.title), ["Archived Today"])
    }

    @MainActor
    func testLibraryItemSelectionKeepsCurrentTab() throws {
        let root = URL(fileURLWithPath: NSTemporaryDirectory())
            .appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        let pending = try testLibraryItem(
            id: "pending-\(UUID().uuidString)",
            title: "Pending",
            groupName: "Default",
            audioURL: writeAudioFile(root.appendingPathComponent("pending.m4a")),
            status: "Not processed",
            modifiedAt: Date()
        )
        let processed = try testLibraryItem(
            id: "processed-\(UUID().uuidString)",
            title: "Processed",
            groupName: "Default",
            audioURL: writeAudioFile(root.appendingPathComponent("processed.m4a")),
            status: "QA pass",
            hasTranscript: true,
            hasOutput: true,
            runStatus: "done",
            modifiedAt: Date()
        )
        let controller = testJobController()
        controller.libraryItems = [pending, processed]
        controller.selectedTab = .summary

        controller.selectLibraryItem(pending)
        XCTAssertEqual(controller.visibleContentTabs, [.metadata])
        XCTAssertEqual(controller.selectedTab, .summary)

        controller.selectLibraryItem(processed)
        XCTAssertEqual(controller.visibleContentTabs, ContentTab.displayOrder)
        XCTAssertEqual(controller.selectedTab, .summary)
    }

    @MainActor
    func testMarkedBatchSelectorsUseQueueStatusAndUnprocessedState() throws {
        let root = URL(fileURLWithPath: NSTemporaryDirectory())
            .appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        let toProcess = try testLibraryItem(
            id: "to-process-\(UUID().uuidString)",
            title: "To Process",
            groupName: "Default",
            audioURL: writeAudioFile(root.appendingPathComponent("to-process.m4a")),
            status: "Not processed",
            queueStatus: .toProcess,
            modifiedAt: Date()
        )
        let recoverableOriginal = try writeAudioFile(root.appendingPathComponent("recoverable-source.m4a"))
        let recoverableMissing = testLibraryItem(
            id: "recoverable-\(UUID().uuidString)",
            title: "Recoverable Missing",
            groupName: "Default",
            audioURL: root.appendingPathComponent("recoverable-missing.m4a"),
            status: "Audio pending",
            hasFile: false,
            source: "local",
            originalPath: recoverableOriginal.path,
            queueStatus: .toProcess,
            modifiedAt: Date()
        )
        let unavailableMissing = testLibraryItem(
            id: "unavailable-\(UUID().uuidString)",
            title: "Unavailable Missing",
            groupName: "Default",
            audioURL: root.appendingPathComponent("unavailable-missing.m4a"),
            status: "Audio pending",
            hasFile: false,
            source: "local",
            queueStatus: .toProcess,
            modifiedAt: Date()
        )
        let later = try testLibraryItem(
            id: "later-\(UUID().uuidString)",
            title: "Later",
            groupName: "Default",
            audioURL: writeAudioFile(root.appendingPathComponent("later.m4a")),
            status: "Not processed",
            queueStatus: .processLater,
            modifiedAt: Date()
        )
        let deleted = try testLibraryItem(
            id: "deleted-\(UUID().uuidString)",
            title: "Deleted",
            groupName: "Default",
            audioURL: writeAudioFile(root.appendingPathComponent("deleted.m4a")),
            status: "Not processed",
            queueStatus: .delete,
            modifiedAt: Date()
        )
        let processed = try testLibraryItem(
            id: "processed-\(UUID().uuidString)",
            title: "Processed",
            groupName: "Default",
            audioURL: writeAudioFile(root.appendingPathComponent("processed.m4a")),
            status: "QA pass",
            hasTranscript: true,
            hasOutput: true,
            runStatus: "done",
            queueStatus: .toProcess,
            modifiedAt: Date()
        )
        let controller = testJobController()
        controller.libraryItems = [toProcess, recoverableMissing, unavailableMissing, later, deleted, processed]

        XCTAssertEqual(controller.markedToProcessItems().map(\.title), ["To Process", "Recoverable Missing"])
        XCTAssertEqual(controller.markedDeletedItems().map(\.title), ["Deleted"])
        XCTAssertTrue(controller.canProcessLibraryItem(recoverableMissing))
        XCTAssertFalse(controller.canProcessLibraryItem(unavailableMissing))
        XCTAssertTrue(controller.canProcessLibraryItem(processed, reprocess: true))
    }

    @MainActor
    func testUnprocessedQueueFilterOnlyAffectsVisibleUnprocessedItems() throws {
        let root = URL(fileURLWithPath: NSTemporaryDirectory())
            .appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        let unread = try testLibraryItem(
            id: "unread-\(UUID().uuidString)",
            title: "Unread",
            groupName: "Default",
            audioURL: writeAudioFile(root.appendingPathComponent("unread.m4a")),
            status: "Not processed",
            queueStatus: .unread,
            modifiedAt: Date()
        )
        let toProcess = try testLibraryItem(
            id: "to-process-\(UUID().uuidString)",
            title: "To Process",
            groupName: "Default",
            audioURL: writeAudioFile(root.appendingPathComponent("to-process.m4a")),
            status: "Not processed",
            queueStatus: .toProcess,
            modifiedAt: Date()
        )
        let later = try testLibraryItem(
            id: "later-\(UUID().uuidString)",
            title: "Later",
            groupName: "Default",
            audioURL: writeAudioFile(root.appendingPathComponent("later.m4a")),
            status: "Not processed",
            queueStatus: .processLater,
            modifiedAt: Date()
        )
        let deleted = try testLibraryItem(
            id: "deleted-\(UUID().uuidString)",
            title: "Deleted",
            groupName: "Default",
            audioURL: writeAudioFile(root.appendingPathComponent("deleted.m4a")),
            status: "Not processed",
            queueStatus: .delete,
            modifiedAt: Date()
        )
        let controller = testJobController()
        controller.libraryItems = [unread, toProcess, later, deleted]
        controller.selectedSidebarSource = .smart(.unprocessed)

        XCTAssertEqual(controller.count(for: .smart(.unprocessed)), 4)
        XCTAssertEqual(controller.visibleLibraryItems.map(\.title), ["Unread", "To Process", "Later", "Deleted"])
        XCTAssertEqual(controller.unprocessedQueueFilterCount(for: .toProcess), 1)

        controller.setUnprocessedQueueFilter(.toProcess)
        XCTAssertEqual(controller.count(for: .smart(.unprocessed)), 4)
        XCTAssertEqual(controller.visibleLibraryItems.map(\.title), ["To Process"])

        controller.setUnprocessedQueueFilter(nil)
        XCTAssertEqual(controller.visibleLibraryItems.map(\.title), ["Unread", "To Process", "Later", "Deleted"])
    }

    @MainActor
    func testHidingReadItemsFiltersReadableLibrarySources() throws {
        let root = URL(fileURLWithPath: NSTemporaryDirectory())
            .appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        let unreadProcessed = try testLibraryItem(
            id: "unread-\(UUID().uuidString)",
            title: "Unread Processed",
            audioURL: writeAudioFile(root.appendingPathComponent("unread.m4a")),
            status: "QA pass",
            hasTranscript: true,
            hasOutput: true,
            runStatus: "done",
            modifiedAt: Date()
        )
        let readProcessed = try testLibraryItem(
            id: "read-\(UUID().uuidString)",
            title: "Read Processed",
            audioURL: writeAudioFile(root.appendingPathComponent("read.m4a")),
            status: "QA pass",
            hasTranscript: true,
            hasOutput: true,
            runStatus: "done",
            isRead: true,
            modifiedAt: Date()
        )
        let readPending = try testLibraryItem(
            id: "pending-\(UUID().uuidString)",
            title: "Read Pending",
            audioURL: writeAudioFile(root.appendingPathComponent("pending.m4a")),
            isRead: true,
            modifiedAt: Date()
        )
        let controller = testJobController()
        controller.libraryItems = [unreadProcessed, readProcessed, readPending]
        controller.selectedSidebarSource = .library

        XCTAssertEqual(controller.count(for: .library), 2)
        XCTAssertEqual(controller.visibleLibraryItems.map(\.title), ["Unread Processed", "Read Processed"])

        controller.setHidesReadLibraryItems(true)
        XCTAssertEqual(controller.count(for: .library), 1)
        XCTAssertEqual(controller.visibleLibraryItems.map(\.title), ["Unread Processed"])

        controller.selectedSidebarSource = .smart(.unprocessed)
        XCTAssertEqual(controller.count(for: .smart(.unprocessed)), 1)
        XCTAssertEqual(controller.visibleLibraryItems.map(\.title), ["Read Pending"])

        controller.setHidesReadLibraryItems(false)
        controller.selectedSidebarSource = .library
        XCTAssertEqual(controller.visibleLibraryItems.map(\.title), ["Unread Processed", "Read Processed"])
    }

    @MainActor
    func testReadFilterPreferencePersistsAcrossControllers() throws {
        let dataRoot = URL(fileURLWithPath: NSTemporaryDirectory())
            .appendingPathComponent(UUID().uuidString)
        try configureLocalTestLibrary(dataRoot: dataRoot)
        let settingsStore = AppSettingsStore(dataRoot: dataRoot, credentials: MemoryCloudCredentials())
        let controller = JobController(settingsStore: settingsStore, loadsLibrarySynchronously: true)

        XCTAssertFalse(controller.hidesReadLibraryItems)

        controller.setHidesReadLibraryItems(true)

        let restored = JobController(settingsStore: settingsStore, loadsLibrarySynchronously: true)
        XCTAssertTrue(restored.hidesReadLibraryItems)
        XCTAssertTrue(settingsStore.load(environment: [:]).hideReadItems)
    }

    @MainActor
    func testMarkReadKeepsLibrarySyncBadgeSyncingAfterLocalMutation() throws {
        let dataRoot = URL(fileURLWithPath: NSTemporaryDirectory())
            .appendingPathComponent(UUID().uuidString)
        try writeTestLibraryEpisode(dataRoot: dataRoot, id: "read-sync", title: "Read Sync")
        let controller = JobController(
            settingsStore: AppSettingsStore(dataRoot: dataRoot, credentials: MemoryCloudCredentials()),
            loadsLibrarySynchronously: true
        )
        let item = try XCTUnwrap(controller.libraryItems.first { $0.id == "read-sync" })
        controller.librarySyncStatus = .unavailable("Probe reported offline while a local metadata file changed.")

        controller.markRead(true, for: item)

        let status = controller.displayedLibrarySyncStatus
        XCTAssertEqual(status.state, .syncing)
        XCTAssertEqual(status.title, "同步中")
        XCTAssertEqual(status.detail, "本地资料修改正在同步。")
    }

    @MainActor
    func testSidebarSourceSelectionKeepsOrReplacesSelectedItem() throws {
        let root = URL(fileURLWithPath: NSTemporaryDirectory())
            .appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        let defaultItem = try testLibraryItem(
            id: "default-\(UUID().uuidString)",
            title: "Default Item",
            groupName: "Default",
            audioURL: writeAudioFile(root.appendingPathComponent("default.m4a")),
            status: "QA pass",
            hasTranscript: true,
            hasOutput: true,
            runStatus: "done",
            modifiedAt: Date()
        )
        let researchItem = try testLibraryItem(
            id: "research-\(UUID().uuidString)",
            title: "Research Item",
            groupName: "Research",
            audioURL: writeAudioFile(root.appendingPathComponent("research.m4a")),
            status: "QA pass",
            hasTranscript: true,
            hasOutput: true,
            runStatus: "done",
            modifiedAt: Date()
        )
        let pendingDefaultItem = try testLibraryItem(
            id: "pending-default-\(UUID().uuidString)",
            title: "Pending Default Item",
            groupName: "Default",
            audioURL: writeAudioFile(root.appendingPathComponent("pending-default.m4a")),
            status: "Not processed",
            modifiedAt: Date()
        )
        let controller = testJobController()
        controller.libraryItems = [defaultItem, researchItem, pendingDefaultItem]
        controller.librarySections = ProcessLibrary.sections(from: controller.libraryItems, including: ["Default", "Research", "Empty"])

        controller.selectLibraryItem(researchItem)
        controller.selectSidebarSource(.group("Research"))
        XCTAssertEqual(controller.selectedLibraryItemID, researchItem.id)
        XCTAssertEqual(controller.visibleLibraryItems.map(\.title), ["Research Item"])

        controller.selectSidebarSource(.group("Default"))
        XCTAssertEqual(controller.selectedLibraryItemID, defaultItem.id)
        XCTAssertEqual(controller.visibleLibraryItems.map(\.title), ["Default Item"])

        controller.selectSidebarSource(.library)
        XCTAssertEqual(controller.selectedLibraryItemID, defaultItem.id)
        XCTAssertEqual(controller.visibleLibraryItems.map(\.title), ["Default Item", "Research Item"])

        controller.selectSidebarSource(.group("Empty"))
        XCTAssertNil(controller.selectedLibraryItemID)
        XCTAssertTrue(controller.visibleLibraryItems.isEmpty)
    }

    @MainActor
    func testLibraryRefreshKeepsSelectedItemWhenItLeavesVisibleFilter() throws {
        let root = URL(fileURLWithPath: NSTemporaryDirectory())
            .appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        let selectedID = "selected-\(UUID().uuidString)"
        let selectedPending = try testLibraryItem(
            id: selectedID,
            title: "Selected Item",
            audioURL: writeAudioFile(root.appendingPathComponent("selected.m4a")),
            status: "Not processed",
            modifiedAt: Date()
        )
        let selectedProcessed = testLibraryItem(
            id: selectedID,
            title: "Selected Item",
            audioURL: selectedPending.audioURL,
            status: "QA pass",
            hasTranscript: true,
            hasOutput: true,
            runStatus: "done",
            modifiedAt: Date()
        )
        let nextPending = try testLibraryItem(
            id: "next-\(UUID().uuidString)",
            title: "Next Pending",
            audioURL: writeAudioFile(root.appendingPathComponent("next.m4a")),
            status: "Not processed",
            modifiedAt: Date()
        )
        let controller = testJobController()
        controller.selectedSidebarSource = .smart(.unprocessed)
        controller.libraryItems = [selectedPending, nextPending]
        controller.selectLibraryItem(selectedPending)

        controller.libraryItems = [selectedProcessed, nextPending]
        controller.reconcileVisibleSelection()

        XCTAssertEqual(controller.visibleLibraryItems.map(\.title), ["Next Pending"])
        XCTAssertEqual(controller.selectedLibraryItemID, selectedID)
        XCTAssertEqual(controller.selectedLibraryItem?.title, "Selected Item")
    }

    @MainActor
    func testSubscriptionsSidebarSourceDoesNotDisturbLibraryFeeds() throws {
        let controller = testJobController()
        controller.subscriptions = [
            PodcastSubscriptionItem(
                id: "podcast_rss-test",
                title: "测试订阅",
                source: "podcast_rss",
                url: "https://example.com/feed.xml",
                feedURL: "https://example.com/feed.xml",
                groupName: "Default",
                createdAt: "2026-05-29T00:00:00+08:00",
                lastCheckedAt: ""
            ),
        ]
        controller.libraryItems = try [
            testLibraryItem(
                id: "item-\(UUID().uuidString)",
                title: "Library Item",
                groupName: "Default",
                audioURL: writeAudioFile(URL(fileURLWithPath: NSTemporaryDirectory()).appendingPathComponent(UUID().uuidString).appendingPathComponent("item.m4a")),
                status: "Not processed",
                modifiedAt: Date()
            ),
        ]
        controller.librarySections = ProcessLibrary.sections(from: controller.libraryItems, including: ["Default"])

        controller.selectSidebarSource(.subscriptions)

        XCTAssertEqual(controller.count(for: .subscriptions), 1)
        XCTAssertEqual(controller.selectedSubscriptionID, "podcast_rss-test")
        XCTAssertTrue(controller.visibleLibraryItems.isEmpty)
        XCTAssertNil(controller.selectedLibraryItemID)
        XCTAssertEqual(controller.count(for: .group("Default")), 0)
        XCTAssertEqual(controller.count(for: .smart(.unprocessed)), 1)
    }
}
