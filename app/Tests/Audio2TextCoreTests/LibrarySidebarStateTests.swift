@testable import Audio2TextCore
import XCTest

final class LibrarySidebarStateTests: XCTestCase {
    func testFiltersCountsTodayAndSelectionReconciliation() {
        let processed = sidebarTestItem(id: "processed", title: "Processed", hasProcessed: true, modifiedAt: Date(), processedAt: Date())
        let defaultProcessed = sidebarTestItem(id: "default", title: "Default", groupName: nil, hasProcessed: true)
        let starred = sidebarTestItem(id: "starred", title: "Starred", groupName: "Research", hasProcessed: true, isStarred: true)
        let pending = sidebarTestItem(id: "pending", title: "Pending", queueStatus: .toProcess)
        let subscribedPending = sidebarTestItem(
            id: "subscribed",
            title: "Subscribed",
            queueStatus: .processLater,
            subscriptionID: "podcast-main",
            seriesURL: "https://example.com/feed/"
        )
        let archived = sidebarTestItem(
            id: "archived",
            title: "Archived",
            hasProcessed: true,
            isStarred: true,
            isArchived: true,
            subscriptionID: "podcast-main"
        )
        let subscription = LibrarySidebarSubscription(
            id: "podcast-main",
            title: "Podcast Main",
            url: "https://example.com/feed",
            feedURL: "https://example.com/feed"
        )
        let state = LibrarySidebarState(
            items: [processed, defaultProcessed, starred, pending, subscribedPending, archived],
            subscriptions: [subscription],
            selectedSidebarSource: .smart(.unprocessed),
            unprocessedQueueFilter: .toProcess
        )

        XCTAssertEqual(LibrarySidebarSmartFeed.allCases.map(\.rawValue), ["today", "unprocessed", "starred", "archive"])
        XCTAssertEqual(state.filteredItems(for: .library).map(\.title), ["Processed", "Default", "Starred"])
        XCTAssertEqual(state.filteredItems(for: .smart(.today)).map(\.title), ["Processed"])
        XCTAssertEqual(state.filteredItems(for: .smart(.unprocessed)).map(\.title), ["Pending", "Subscribed"])
        XCTAssertEqual(state.filteredItems(for: .smart(.starred)).map(\.title), ["Starred"])
        XCTAssertEqual(state.filteredItems(for: .smart(.archive)).map(\.title), ["Archived"])
        XCTAssertEqual(state.filteredItems(for: .group("Research")).map(\.title), ["Starred"])
        XCTAssertEqual(state.visibleItems.map(\.title), ["Pending"])
        XCTAssertEqual(state.unprocessedQueueFilterCount(for: .toProcess), 1)
        XCTAssertEqual(state.count(for: .subscriptions), 1)

        let folders = state.groupSections(including: ["Empty", "生活"]).map { ($0.title, $0.count) }
        XCTAssertEqual(folders.map(\.0), ["Default", "Empty", "Research", "生活"])
        XCTAssertEqual(folders.map(\.1), [2, 0, 1, 0])

        let counts = state.subscriptionItemCounts(for: subscription)
        XCTAssertEqual(counts.unprocessed, 1)
        XCTAssertEqual(counts.processed, 0)
        XCTAssertEqual(counts.total, 1)

        XCTAssertEqual(LibrarySidebarState.uniqueItems(from: [pending, pending, processed]).map(\.id), [pending.id, processed.id])
        XCTAssertEqual(
            LibrarySidebarState.reconciledSelectionID(currentID: starred.id, visibleItems: [starred, processed]),
            starred.id
        )
        XCTAssertEqual(
            LibrarySidebarState.reconciledSelectionID(currentID: starred.id, visibleItems: [processed], forceFirstVisible: true),
            processed.id
        )
        XCTAssertNil(LibrarySidebarState.reconciledSelectionID(currentID: starred.id, visibleItems: []))
    }

    func testTodayRequiresProcessedAtToday() {
        let now = Date()
        let yesterday = Calendar.current.date(byAdding: .day, value: -1, to: now) ?? Date(timeIntervalSinceNow: -86400)
        let processedToday = sidebarTestItem(id: "today", title: "Today", hasProcessed: true, modifiedAt: now, processedAt: now)
        let modifiedOnly = sidebarTestItem(id: "modified", title: "Modified", hasProcessed: true, modifiedAt: now)
        let pendingToday = sidebarTestItem(id: "pending", title: "Pending", modifiedAt: now, processedAt: now)
        let processedYesterday = sidebarTestItem(id: "yesterday", title: "Yesterday", hasProcessed: true, processedAt: yesterday)
        let archivedToday = sidebarTestItem(id: "archived", title: "Archived", hasProcessed: true, isArchived: true, processedAt: now)
        let state = LibrarySidebarState(items: [processedToday, modifiedOnly, pendingToday, processedYesterday, archivedToday])

        XCTAssertEqual(state.filteredItems(for: .smart(.today)).map(\.id), ["today"])
    }

    func testReadFilterHidesReadItemsOnlyForReadableSources() {
        let now = Date()
        let unreadProcessed = sidebarTestItem(id: "unread", title: "Unread Processed", hasProcessed: true, processedAt: now)
        let readProcessed = sidebarTestItem(id: "read", title: "Read Processed", hasProcessed: true, isRead: true, processedAt: now)
        let readStarred = sidebarTestItem(id: "starred", title: "Read Starred", hasProcessed: true, isRead: true, isStarred: true)
        let readPending = sidebarTestItem(id: "pending", title: "Read Pending", isRead: true)
        let readArchived = sidebarTestItem(id: "archived-read", title: "Read Archived", hasProcessed: true, isRead: true, isArchived: true)
        let unreadArchived = sidebarTestItem(id: "archived-unread", title: "Unread Archived", hasProcessed: true, isArchived: true)
        let state = LibrarySidebarState(
            items: [unreadProcessed, readProcessed, readStarred, readPending, readArchived, unreadArchived],
            selectedSidebarSource: .library,
            hidesReadItems: true
        )

        XCTAssertTrue(LibrarySidebarState.canFilterReadItems(for: .library))
        XCTAssertFalse(LibrarySidebarState.canFilterReadItems(for: .smart(.unprocessed)))
        XCTAssertEqual(state.filteredItems(for: .library).map(\.id), ["unread"])
        XCTAssertEqual(state.filteredItems(for: .smart(.today)).map(\.id), ["unread"])
        XCTAssertEqual(state.filteredItems(for: .smart(.starred)).map(\.id), [])
        XCTAssertEqual(state.filteredItems(for: .smart(.archive)).map(\.id), ["archived-unread"])
        XCTAssertEqual(state.filteredItems(for: .smart(.unprocessed)).map(\.id), ["pending"])
        XCTAssertEqual(state.count(for: .library), 1)
        XCTAssertEqual(state.readCounts(for: .library), LibraryReadCounts(unread: 1, total: 3))
        XCTAssertEqual(state.readCounts(for: .library).displayText, "1/3")
        XCTAssertEqual(state.readCounts(for: .group(LibrarySidebarState.defaultGroupName)).displayText, "1/3")
    }

    func testProjectsMobileEpisodesIntoSharedSidebarItems() {
        let ready = LibraryEpisode(
            episodeID: "ready",
            title: "AI Ready",
            sourceURL: "https://example.com/e",
            seriesURL: "https://example.com/feed",
            localPublishedAt: "2026-06-01T00:00:00Z",
            processedAt: "2026-06-20T09:00:00Z",
            subscriptionID: "sub-1",
            appGroup: "科技",
            appStatus: "link",
            appQueueStatus: "to_process",
            appRead: true,
            appStar: true,
            productStatus: LibraryConstants.productStatusAvailable,
            documents: [LibraryDocument(name: "summary.md", path: "documents/summary.md", bytes: 16)]
        )
        let metadataOnly = LibraryEpisode(
            episodeID: "metadata",
            title: "Metadata",
            appGroup: "",
            appStatus: "archived",
            productStatus: LibraryConstants.productStatusMetadataOnly
        )
        let emptyDocument = LibraryEpisode(
            episodeID: "empty",
            title: "Empty Document",
            productStatus: LibraryConstants.productStatusAvailable,
            documents: [LibraryDocument(name: "summary.md", path: "documents/summary.md", bytes: 0)]
        )

        let items = LibrarySidebarState.items(from: [ready, metadataOnly, emptyDocument])

        XCTAssertEqual(items.map(\.id), ["ready", "metadata", "empty"])
        XCTAssertEqual(items.map(\.title), ["AI Ready", "Metadata", "Empty Document"])
        XCTAssertEqual(items[0].groupName, "科技")
        XCTAssertTrue(items[0].hasProcessed)
        XCTAssertTrue(items[0].isRead)
        XCTAssertTrue(items[0].isStarred)
        XCTAssertNotNil(items[0].processedAt)
        XCTAssertEqual(items[0].queueStatus, .toProcess)
        XCTAssertEqual(items[1].groupName, LibrarySidebarState.defaultGroupName)
        XCTAssertFalse(items[1].hasProcessed)
        XCTAssertTrue(items[1].isArchived)
        XCTAssertFalse(items[2].hasProcessed)
        XCTAssertEqual(LibrarySidebarState(items: items).filteredItems(for: .library).map(\.id), ["ready"])
    }
}

private func sidebarTestItem(
    id: String,
    title: String,
    groupName: String? = LibrarySidebarState.defaultGroupName,
    hasProcessed: Bool = false,
    isRead: Bool = false,
    isStarred: Bool = false,
    queueStatus: LibraryQueueStatus = .unread,
    isArchived: Bool = false,
    modifiedAt: Date = .distantPast,
    processedAt: Date? = nil,
    subscriptionID: String? = nil,
    seriesURL: String? = nil
) -> LibrarySidebarItem {
    LibrarySidebarItem(
        id: id,
        title: title,
        groupName: groupName ?? "",
        hasProcessed: hasProcessed,
        isRead: isRead,
        isStarred: isStarred,
        queueStatus: queueStatus,
        isArchived: isArchived,
        modifiedAt: modifiedAt,
        processedAt: processedAt,
        subscriptionID: subscriptionID,
        seriesURL: seriesURL
    )
}
