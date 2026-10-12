@testable import Audio2TextCore
import XCTest

final class LibraryFilteringTests: XCTestCase {
    func testProjectsEpisodeSourcesAndFiltersSubscriptionsByIdentityAndURLs() {
        let directMatch = sidebarEpisode(
            id: "direct",
            subscriptionID: "sub-main",
            sourceURL: "https://example.com/direct",
            seriesURL: "https://example.com/other"
        )
        let seriesURLMatch = sidebarEpisode(
            id: "series",
            sourceURL: nil,
            canonicalURL: "https://example.com/canonical",
            seriesURL: "HTTPS://EXAMPLE.COM/FEED/"
        )
        let sourceURLMatch = sidebarEpisode(
            id: "source",
            sourceURL: "https://example.com/rss/",
            seriesURL: nil,
            documents: []
        )
        let explicitOtherSubscription = sidebarEpisode(
            id: "explicit-other",
            subscriptionID: "other-sub",
            sourceURL: "https://example.com/rss/",
            seriesURL: "https://example.com/feed"
        )
        let archived = sidebarEpisode(
            id: "archived",
            subscriptionID: "sub-main",
            isArchived: true
        )
        let items = LibrarySidebarState.items(from: [
            directMatch,
            seriesURLMatch,
            sourceURLMatch,
            explicitOtherSubscription,
            archived,
        ])
        let subscription = LibrarySidebarSubscription(
            id: "sub-main",
            title: "Main Feed",
            url: "https://example.com/feed",
            feedURL: "https://example.com/rss"
        )
        let state = LibrarySidebarState(items: items, subscriptions: [subscription])

        XCTAssertEqual(items.first { $0.id == "series" }?.sourceURL, "https://example.com/canonical")
        XCTAssertEqual(state.subscriptionItems(for: subscription).map(\.id), ["direct", "series", "source"])
        XCTAssertEqual(state.subscriptionItemCounts(for: subscription), SubscriptionItemCounts(unprocessed: 1, total: 3))
        XCTAssertEqual(state.filteredItems(for: .library).map(\.id), ["direct", "series", "explicit-other"])
        XCTAssertEqual(state.filteredItems(for: .smart(.archive)).map(\.id), ["archived"])
        XCTAssertEqual(state.count(for: .subscriptions), 1)
    }
}

private func sidebarEpisode(
    id: String,
    subscriptionID: String? = nil,
    sourceURL: String? = "https://example.com/source",
    canonicalURL: String? = "https://example.com/canonical",
    seriesURL: String? = "https://example.com/feed",
    isArchived: Bool = false,
    documents: [LibraryDocument] = [LibraryDocument(name: "summary.md", path: "documents/summary.md", bytes: 16)]
) -> LibraryEpisode {
    LibraryEpisode(
        episodeID: id,
        title: id,
        sourceURL: sourceURL,
        canonicalURL: canonicalURL,
        seriesURL: seriesURL,
        subscriptionID: subscriptionID,
        appStatus: isArchived ? "archived" : "link",
        productStatus: documents.isEmpty ? LibraryConstants.productStatusMetadataOnly : LibraryConstants.productStatusAvailable,
        documents: documents
    )
}
