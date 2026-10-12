@testable import Audio2TextApp
import Audio2TextCore
import XCTest

final class SubscriptionLibraryTests: XCTestCase {
    func testChannelEpisodeDetailsUseFetchedEpisodeMetadata() throws {
        let root = URL(fileURLWithPath: NSTemporaryDirectory())
            .appendingPathComponent(UUID().uuidString)
        let dataRoot = root.appendingPathComponent("data")
        let writtenEpisode = try writeTestLibraryEpisode(
            dataRoot: dataRoot,
            id: "episode-detail",
            title: "Fallback Title",
            metadata: [
                "app_status": ArticleNodeStatus.link.rawValue,
                "source": "podcast_rss",
                "source_url": "https://example.com/episodes/raw",
                "canonical_url": "https://example.com/episodes/detail",
                "series_name": "Fetched Channel",
                "series_url": "https://example.com/feed.xml",
                "published_at": "2026-06-01T00:00:00Z",
                "duration": "00:42:00",
                "description": "Fetched description from the channel feed.",
                "audio_url": "https://media.example/detail.m4a",
                "image_url": "https://example.com/art.jpg",
                "guid": "guid-detail",
                "subscription_id": "podcast_rss-detail",
            ],
            audioContents: nil
        )
        let item = try XCTUnwrap(ProcessLibrary.scan(dataRoot: dataRoot).first { $0.id == writtenEpisode.id })

        let details = ProcessLibrary.channelEpisodeDetails(for: item)

        XCTAssertEqual(details.title, "Fallback Title")
        XCTAssertEqual(details.seriesName, "Fetched Channel")
        XCTAssertEqual(details.sourceName, "Podcast RSS")
        XCTAssertEqual(details.sourceURL, "https://example.com/episodes/detail")
        XCTAssertEqual(details.seriesURL, "https://example.com/feed.xml")
        XCTAssertEqual(details.publishedAt, "2026-06-01T00:00:00Z")
        XCTAssertEqual(details.duration, "00:42:00")
        XCTAssertEqual(details.description, "Fetched description from the channel feed.")
        XCTAssertEqual(details.audioURL, "https://media.example/detail.m4a")
        XCTAssertEqual(details.imageURL, "https://example.com/art.jpg")
        XCTAssertEqual(details.guid, "guid-detail")
    }

    func testSubscriptionBulkSelectionKeepsSelectedItemsButProcessesOnlyEligibleUnprocessedItems() {
        let root = URL(fileURLWithPath: NSTemporaryDirectory())
            .appendingPathComponent(UUID().uuidString)
        let pending = testLibraryItem(
            id: "pending-\(UUID().uuidString)",
            title: "Pending",
            audioURL: root.appendingPathComponent("pending.m4a"),
            modifiedAt: Date(timeIntervalSince1970: 1)
        )
        let processed = testLibraryItem(
            id: "processed-\(UUID().uuidString)",
            title: "Processed",
            audioURL: root.appendingPathComponent("processed.m4a"),
            status: "QA pass",
            hasProcessed: true,
            hasTranscript: true,
            modifiedAt: Date(timeIntervalSince1970: 2)
        )
        let blocked = testLibraryItem(
            id: "blocked-\(UUID().uuidString)",
            title: "Blocked",
            audioURL: root.appendingPathComponent("blocked.m4a"),
            modifiedAt: Date(timeIntervalSince1970: 3)
        )
        let episodes = [pending, processed, blocked].map(SubscriptionEpisodeDisplayItem.init)
        let selectedIDs = Set([pending.id, processed.id, blocked.id, "stale"])

        let selectedItems = SubscriptionBulkSelection.selectedItems(from: episodes, selectedIDs: selectedIDs)
        let processableItems = SubscriptionBulkSelection.processableItems(from: selectedItems) { item in
            item.id == pending.id || item.id == processed.id
        }
        let reconciledIDs = SubscriptionBulkSelection.reconciledSelection(selectedIDs, episodes: episodes)

        XCTAssertEqual(selectedItems.map(\.id), [pending.id, processed.id, blocked.id])
        XCTAssertEqual(processableItems.map(\.id), [pending.id])
        XCTAssertEqual(reconciledIDs, Set([pending.id, processed.id, blocked.id]))
    }

    func testSubscriptionBulkSelectionTogglesAllVisibleEpisodes() {
        let root = URL(fileURLWithPath: NSTemporaryDirectory())
            .appendingPathComponent(UUID().uuidString)
        let first = testLibraryItem(
            id: "first-\(UUID().uuidString)",
            title: "First",
            audioURL: root.appendingPathComponent("first.m4a"),
            modifiedAt: Date(timeIntervalSince1970: 1)
        )
        let second = testLibraryItem(
            id: "second-\(UUID().uuidString)",
            title: "Second",
            audioURL: root.appendingPathComponent("second.m4a"),
            modifiedAt: Date(timeIntervalSince1970: 2)
        )
        let episodes = [first, second].map(SubscriptionEpisodeDisplayItem.init)

        let selectedAll = SubscriptionBulkSelection.toggledVisibleSelection(
            Set([first.id, "hidden"]),
            episodes: episodes
        )
        let clearedAll = SubscriptionBulkSelection.toggledVisibleSelection(
            Set([first.id, second.id, "hidden"]),
            episodes: episodes
        )
        let emptySelection = SubscriptionBulkSelection.toggledVisibleSelection(
            Set([first.id, "hidden"]),
            episodes: []
        )

        XCTAssertEqual(selectedAll, Set([first.id, second.id]))
        XCTAssertEqual(clearedAll, [])
        XCTAssertEqual(emptySelection, [])
    }

    func testSubscriptionBulkSelectionSelectsFrontVisibleEpisodes() {
        let root = URL(fileURLWithPath: NSTemporaryDirectory())
            .appendingPathComponent(UUID().uuidString)
        let items = (0..<25).map { index in
            testLibraryItem(
                id: "front-\(index)-\(UUID().uuidString)",
                title: "Front \(index)",
                audioURL: root.appendingPathComponent("front-\(index).m4a"),
                modifiedAt: Date(timeIntervalSince1970: TimeInterval(index))
            )
        }
        let episodes = items.map(SubscriptionEpisodeDisplayItem.init)

        let frontTwentyIDs = SubscriptionBulkSelection.frontVisibleSelection(
            episodes: episodes,
            limit: 20
        )
        let frontTenIDs = SubscriptionBulkSelection.frontVisibleSelection(
            episodes: episodes,
            limit: 10
        )
        let smallerSelection = SubscriptionBulkSelection.frontVisibleSelection(
            episodes: Array(episodes.prefix(3)),
            limit: 20
        )

        XCTAssertEqual(frontTwentyIDs.count, 20)
        XCTAssertEqual(frontTwentyIDs, Set(items.prefix(20).map(\.id)))
        XCTAssertFalse(frontTwentyIDs.contains(items[20].id))
        XCTAssertEqual(frontTenIDs.count, 10)
        XCTAssertEqual(frontTenIDs, Set(items.prefix(10).map(\.id)))
        XCTAssertFalse(frontTenIDs.contains(items[10].id))
        XCTAssertEqual(smallerSelection, Set(items.prefix(3).map(\.id)))
    }

    func testSubscriptionEpisodeDisplayUsesPublishedDateBeforeModifiedDate() throws {
        let root = URL(fileURLWithPath: NSTemporaryDirectory())
            .appendingPathComponent(UUID().uuidString)
        let publishedAt = "2026-06-07T20:30:00+08:00"
        let publishedDate = try XCTUnwrap(LibraryDateParser.date(from: publishedAt))
        let fetchedDate = try XCTUnwrap(LibraryDateParser.date(from: "2026-07-09T12:00:00+08:00"))
        let item = testLibraryItem(
            id: "published-\(UUID().uuidString)",
            title: "Published",
            audioURL: root.appendingPathComponent("published.m4a"),
            publishedAt: publishedAt,
            modifiedAt: fetchedDate
        )

        let episode = SubscriptionEpisodeDisplayItem(item: item)

        XCTAssertEqual(episode.filterDate, publishedDate)
        XCTAssertEqual(episode.dateTitle, publishedDate.formatted(date: .abbreviated, time: .omitted))
    }

    func testSubscriptionEpisodeFiltersUseUnprocessedAndTimeRange() throws {
        let root = URL(fileURLWithPath: NSTemporaryDirectory())
            .appendingPathComponent(UUID().uuidString)
        var calendar = Calendar(identifier: .gregorian)
        calendar.timeZone = try XCTUnwrap(TimeZone(secondsFromGMT: 0))
        let now = try XCTUnwrap(calendar.date(from: DateComponents(year: 2026, month: 7, day: 9, hour: 12)))
        let yesterday = try XCTUnwrap(calendar.date(from: DateComponents(year: 2026, month: 7, day: 8, hour: 9)))
        let lastWeek = try XCTUnwrap(calendar.date(from: DateComponents(year: 2026, month: 7, day: 3, hour: 9)))
        let lastMonth = try XCTUnwrap(calendar.date(from: DateComponents(year: 2026, month: 6, day: 1, hour: 9)))
        let old = try XCTUnwrap(calendar.date(from: DateComponents(year: 2025, month: 12, day: 31, hour: 9)))
        let todayPending = testLibraryItem(
            id: "today-\(UUID().uuidString)",
            title: "Today Pending",
            audioURL: root.appendingPathComponent("today.m4a"),
            modifiedAt: now
        )
        let yesterdayProcessed = testLibraryItem(
            id: "processed-\(UUID().uuidString)",
            title: "Yesterday Processed",
            audioURL: root.appendingPathComponent("processed.m4a"),
            status: "QA pass",
            hasProcessed: true,
            hasTranscript: true,
            modifiedAt: yesterday
        )
        let weekPending = testLibraryItem(
            id: "week-\(UUID().uuidString)",
            title: "Week Pending",
            audioURL: root.appendingPathComponent("week.m4a"),
            modifiedAt: lastWeek
        )
        let monthPending = testLibraryItem(
            id: "month-\(UUID().uuidString)",
            title: "Month Pending",
            audioURL: root.appendingPathComponent("month.m4a"),
            modifiedAt: lastMonth
        )
        let oldPending = testLibraryItem(
            id: "old-\(UUID().uuidString)",
            title: "Old Pending",
            audioURL: root.appendingPathComponent("old.m4a"),
            modifiedAt: old
        )
        let episodes = [todayPending, yesterdayProcessed, weekPending, monthPending, oldPending]
            .map(SubscriptionEpisodeDisplayItem.init)

        let unprocessedRecent = SubscriptionEpisodeFilters.filteredEpisodes(
            episodes,
            showsOnlyUnprocessed: true,
            timeFilter: .last7Days,
            now: now,
            calendar: calendar
        )
        let todayOnly = SubscriptionEpisodeFilters.filteredEpisodes(
            episodes,
            showsOnlyUnprocessed: false,
            timeFilter: .today,
            now: now,
            calendar: calendar
        )
        let thisYear = SubscriptionEpisodeFilters.filteredEpisodes(
            episodes,
            showsOnlyUnprocessed: false,
            timeFilter: .thisYear,
            now: now,
            calendar: calendar
        )

        XCTAssertEqual(unprocessedRecent.map(\.id), [todayPending.id, weekPending.id])
        XCTAssertEqual(todayOnly.map(\.id), [todayPending.id])
        XCTAssertEqual(thisYear.map(\.id), [todayPending.id, yesterdayProcessed.id, weekPending.id, monthPending.id])
    }

    @MainActor
    func testOpenProcessedSubscriptionItemShowsSummaryReader() {
        let root = URL(fileURLWithPath: NSTemporaryDirectory())
            .appendingPathComponent(UUID().uuidString)
        let controller = testJobController()
        let processed = testLibraryItem(
            id: "processed-\(UUID().uuidString)",
            title: "AI 短标题",
            originalTitle: "来自订阅源的原始节目标题",
            audioURL: root.appendingPathComponent("processed.m4a"),
            status: "QA pass",
            hasProcessed: true,
            hasTranscript: true,
            source: "podcast_rss",
            subscriptionID: "podcast_rss-crossing",
            modifiedAt: Date(timeIntervalSince1970: 2)
        )
        controller.libraryItems = [processed]
        controller.selectedSidebarSource = .subscriptions
        controller.selectedTab = .metadata

        controller.openProcessedSubscriptionItem(processed)

        XCTAssertEqual(controller.selectedLibraryItemID, processed.id)
        XCTAssertNotEqual(controller.selectedSidebarSource, .subscriptions)
        XCTAssertEqual(controller.selectedTab, .summary)
    }

    @MainActor
    func testSelectedSubscriptionDetailSnapshotUsesCachedPresentationItems() throws {
        let root = URL(fileURLWithPath: NSTemporaryDirectory())
            .appendingPathComponent(UUID().uuidString)
        let subscription = PodcastSubscriptionItem(
            id: "podcast_rss-cached",
            title: "缓存订阅",
            source: "podcast_rss",
            url: "https://example.com/feed.xml",
            feedURL: "https://example.com/feed.xml",
            groupName: "Default",
            createdAt: "2026-07-01T00:00:00+08:00",
            lastCheckedAt: ""
        )
        let item = testLibraryItem(
            id: "cached-\(UUID().uuidString)",
            title: "AI 标题",
            originalTitle: "订阅源原始标题",
            audioURL: root.appendingPathComponent("cached.m4a"),
            status: "QA pass",
            hasProcessed: true,
            hasTranscript: true,
            subscriptionID: subscription.id,
            modifiedAt: Date(timeIntervalSince1970: 2)
        )
        let controller = testJobController()
        controller.subscriptions = [subscription]
        controller.libraryItems = [item]
        controller.selectedSubscriptionID = subscription.id

        let snapshot = try XCTUnwrap(controller.selectedSubscriptionDetailSnapshot)

        XCTAssertEqual(snapshot.counts.total, 1)
        XCTAssertEqual(snapshot.counts.processed, 1)
        XCTAssertEqual(snapshot.episodes.first?.title, "AI 标题")
        XCTAssertEqual(snapshot.episodes.first?.primaryCaption, "原名：订阅源原始标题")
        let snapshotVersion = controller.subscriptionDetailSnapshotVersion

        controller.message = "Unrelated progress update"

        XCTAssertEqual(controller.subscriptionDetailSnapshotVersion, snapshotVersion)
        XCTAssertEqual(controller.selectedSubscriptionDetailSnapshot, snapshot)
    }

    @MainActor
    func testSubscriptionItemCountsUseCurrentPodcastChannel() throws {
        let root = URL(fileURLWithPath: NSTemporaryDirectory())
            .appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        let subscription = PodcastSubscriptionItem(
            id: "podcast_rss-crossing",
            title: "十字路口 Crossing",
            source: "podcast_rss",
            url: "https://feed.xyzfm.space/68fyjknth9hj",
            feedURL: "https://feed.xyzfm.space/68fyjknth9hj",
            groupName: "Default",
            createdAt: "2026-05-31T20:20:02+08:00",
            lastCheckedAt: ""
        )
        let pending = testLibraryItem(
            id: "pending-\(UUID().uuidString)",
            title: "Pending",
            audioURL: root.appendingPathComponent("pending.m4a"),
            subscriptionID: subscription.id,
            modifiedAt: Date(timeIntervalSince1970: 1)
        )
        let processed = testLibraryItem(
            id: "processed-\(UUID().uuidString)",
            title: "Processed",
            audioURL: root.appendingPathComponent("processed.m4a"),
            status: "QA pass",
            hasProcessed: true,
            subscriptionID: subscription.id,
            modifiedAt: Date(timeIntervalSince1970: 2)
        )
        let otherPodcast = testLibraryItem(
            id: "other-\(UUID().uuidString)",
            title: "Other Podcast",
            audioURL: root.appendingPathComponent("other.m4a"),
            subscriptionID: "podcast_rss-other",
            modifiedAt: Date(timeIntervalSince1970: 3)
        )
        let feedMatchedPending = testLibraryItem(
            id: "feed-\(UUID().uuidString)",
            title: "Feed Matched Pending",
            audioURL: root.appendingPathComponent("feed.m4a"),
            seriesURL: "https://feed.xyzfm.space/68fyjknth9hj/",
            modifiedAt: Date(timeIntervalSince1970: 4)
        )
        let controller = testJobController()
        controller.libraryItems = [pending, processed, otherPodcast, feedMatchedPending]
        let counts = controller.subscriptionItemCounts(for: subscription)

        XCTAssertEqual(counts.unprocessed, 2)
        XCTAssertEqual(counts.processed, 1)
        XCTAssertEqual(counts.total, 3)
        XCTAssertEqual(
            controller.libraryItems(for: subscription).map(\.title),
            ["Pending", "Processed", "Feed Matched Pending"]
        )
    }

    func testSubscriptionLibraryLoadsSubscriptions() throws {
        let root = URL(fileURLWithPath: NSTemporaryDirectory())
            .appendingPathComponent(UUID().uuidString)
        let dataRoot = root.appendingPathComponent("data")
        let libraryRoot = try configureLocalTestLibrary(dataRoot: dataRoot)
        try FileManager.default.createDirectory(
            at: libraryRoot.appendingPathComponent("subscriptions", isDirectory: true),
            withIntermediateDirectories: true
        )
        try """
        {
          "schema_version": 1,
          "kind": "audio2text.library.subscription",
          "id": "podcast_rss-test",
          "title": "测试订阅",
          "source": "podcast_rss",
          "url": "https://podcasts.apple.com/show/id123",
          "feed_url": "https://example.com/feed.xml",
          "group_name": "Research",
          "created_at": "2026-05-29T00:00:00+08:00",
          "last_checked_at": "2026-05-29T01:00:00+08:00"
        }
        """.write(
            to: libraryRoot.appendingPathComponent("subscriptions/podcast_rss-test.json"),
            atomically: true,
            encoding: .utf8
        )
        try writeLibraryManifest(root: libraryRoot)

        let subscriptions = SubscriptionLibrary.load(dataRoot: dataRoot)

        XCTAssertEqual(subscriptions.count, 1)
        XCTAssertEqual(subscriptions[0].title, "测试订阅")
        XCTAssertEqual(subscriptions[0].feedURL, "https://example.com/feed.xml")
        XCTAssertEqual(subscriptions[0].groupName, "Research")
    }
}
