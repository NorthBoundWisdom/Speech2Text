import Foundation
#if canImport(Audio2TextCore)
    import Audio2TextCore
#endif

extension ProcessLibraryItem {
    var sidebarItem: LibrarySidebarItem {
        LibrarySidebarItem(
            id: id,
            title: title,
            groupName: groupName,
            hasProcessed: hasProcessed,
            isRead: isRead,
            isStarred: isStarred,
            queueStatus: queueStatus,
            isArchived: isArchived,
            modifiedAt: modifiedAt,
            processedAt: processedAt,
            sourceURL: sourceURL,
            subscriptionID: subscriptionID,
            seriesURL: seriesURL
        )
    }
}

extension PodcastSubscriptionItem {
    var sidebarSubscription: LibrarySidebarSubscription {
        LibrarySidebarSubscription(
            id: id,
            title: title,
            url: url,
            feedURL: feedURL
        )
    }
}
