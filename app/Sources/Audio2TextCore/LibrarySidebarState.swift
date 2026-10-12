import Foundation

public enum LibraryQueueStatus: String, CaseIterable, Identifiable, Equatable, Codable {
    case unread
    case toProcess = "to_process"
    case processLater = "process_later"
    case delete

    public var id: String {
        rawValue
    }

    public var title: String {
        switch self {
        case .unread: return "unread"
        case .toProcess: return "to process"
        case .processLater: return "process later"
        case .delete: return "delete"
        }
    }

    public var compactTitle: String {
        switch self {
        case .unread: return "Unread"
        case .toProcess: return "Process"
        case .processLater: return "Later"
        case .delete: return "Delete"
        }
    }

    public var shortcut: String {
        switch self {
        case .unread: return "U"
        case .toProcess: return "P"
        case .processLater: return "L"
        case .delete: return "X"
        }
    }
}

public enum LibrarySidebarSmartFeed: String, CaseIterable, Identifiable {
    case today
    case unprocessed
    case starred
    case archive

    public var id: String {
        rawValue
    }

    public var title: String {
        switch self {
        case .today: return "Today"
        case .unprocessed: return "Unprocessed"
        case .starred: return "Starred"
        case .archive: return "Archive"
        }
    }

    public var iconName: String {
        switch self {
        case .today: return "sun.max.fill"
        case .unprocessed: return "tray"
        case .starred: return "star.fill"
        case .archive: return "archivebox.fill"
        }
    }
}

public enum LibrarySidebarSource: Hashable {
    case library
    case smart(LibrarySidebarSmartFeed)
    case group(String)
    case subscriptions

    public var id: String {
        switch self {
        case .library: return "library"
        case let .smart(feed): return "smart:\(feed.rawValue)"
        case let .group(name): return "group:\(name)"
        case .subscriptions: return "subscriptions"
        }
    }
}

public struct LibrarySidebarItem: Equatable, Identifiable {
    public let id: String
    public let title: String
    public let groupName: String
    public let hasProcessed: Bool
    public let isRead: Bool
    public let isStarred: Bool
    public let queueStatus: LibraryQueueStatus
    public let isArchived: Bool
    public let modifiedAt: Date
    public let processedAt: Date?
    public let sourceURL: String?
    public let subscriptionID: String?
    public let seriesURL: String?

    public init(
        id: String,
        title: String,
        groupName: String,
        hasProcessed: Bool,
        isRead: Bool = false,
        isStarred: Bool = false,
        queueStatus: LibraryQueueStatus = .unread,
        isArchived: Bool = false,
        modifiedAt: Date = .distantPast,
        processedAt: Date? = nil,
        sourceURL: String? = nil,
        subscriptionID: String? = nil,
        seriesURL: String? = nil
    ) {
        self.id = id
        self.title = title
        self.groupName = Self.normalizedGroupName(groupName)
        self.hasProcessed = hasProcessed
        self.isRead = isRead
        self.isStarred = isStarred
        self.queueStatus = queueStatus
        self.isArchived = isArchived
        self.modifiedAt = modifiedAt
        self.processedAt = processedAt
        self.sourceURL = sourceURL
        self.subscriptionID = subscriptionID
        self.seriesURL = seriesURL
    }

    public static func normalizedGroupName(_ value: String?) -> String {
        let trimmed = value?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
        return trimmed.isEmpty ? LibrarySidebarState.defaultGroupName : trimmed
    }
}

public struct LibrarySidebarSubscription: Equatable, Identifiable {
    public let id: String
    public let title: String
    public let url: String?
    public let feedURL: String?

    public init(id: String, title: String, url: String? = nil, feedURL: String? = nil) {
        self.id = id
        self.title = title
        self.url = url
        self.feedURL = feedURL
    }
}

public struct LibrarySidebarSection: Equatable, Identifiable {
    public let source: LibrarySidebarSource
    public let title: String
    public let items: [LibrarySidebarItem]

    public var id: String {
        source.id
    }

    public var count: Int {
        items.count
    }

    public init(source: LibrarySidebarSource, title: String, items: [LibrarySidebarItem]) {
        self.source = source
        self.title = title
        self.items = items
    }
}

public struct LibrarySidebarRow: Equatable, Identifiable {
    public let source: LibrarySidebarSource
    public let title: String
    public let systemImage: String
    public let count: Int

    public var id: String {
        source.id
    }

    public init(source: LibrarySidebarSource, title: String, systemImage: String, count: Int) {
        self.source = source
        self.title = title
        self.systemImage = systemImage
        self.count = count
    }
}

public struct SubscriptionItemCounts: Equatable {
    public let unprocessed: Int
    public let total: Int

    public var processed: Int {
        max(total - unprocessed, 0)
    }

    public init(unprocessed: Int, total: Int) {
        self.unprocessed = unprocessed
        self.total = total
    }
}

public struct LibraryReadCounts: Equatable {
    public let unread: Int
    public let total: Int

    public var read: Int {
        max(total - unread, 0)
    }

    public var displayText: String? {
        total > 0 ? "\(unread)/\(total)" : nil
    }

    public var accessibilityText: String? {
        total > 0 ? "未读 \(unread)，总数 \(total)" : nil
    }

    public init(unread: Int, total: Int) {
        self.unread = unread
        self.total = total
    }
}

public struct LibrarySidebarState {
    public static let defaultGroupName = LibraryConstants.defaultGroupName

    public let items: [LibrarySidebarItem]
    public let subscriptions: [LibrarySidebarSubscription]
    public let groupNames: [String]
    public let selectedSidebarSource: LibrarySidebarSource
    public let unprocessedQueueFilter: LibraryQueueStatus?
    public let hidesReadItems: Bool
    public var calendar: Calendar

    public init(
        items: [LibrarySidebarItem],
        subscriptions: [LibrarySidebarSubscription] = [],
        groupNames: [String] = [],
        selectedSidebarSource: LibrarySidebarSource = .library,
        unprocessedQueueFilter: LibraryQueueStatus? = nil,
        hidesReadItems: Bool = false,
        calendar: Calendar = .current
    ) {
        self.items = items
        self.subscriptions = subscriptions
        self.groupNames = groupNames
        self.selectedSidebarSource = selectedSidebarSource
        self.unprocessedQueueFilter = unprocessedQueueFilter
        self.hidesReadItems = hidesReadItems
        self.calendar = calendar
    }

    public var visibleItems: [LibrarySidebarItem] {
        let sourceItems = filteredItems(for: selectedSidebarSource)
        guard
            case .smart(.unprocessed) = selectedSidebarSource,
            let unprocessedQueueFilter
        else {
            return sourceItems
        }
        return sourceItems.filter { $0.queueStatus == unprocessedQueueFilter }
    }

    public var smartFeedRows: [LibrarySidebarRow] {
        [LibrarySidebarRow(source: .subscriptions, title: "Subscriptions", systemImage: "dot.radiowaves.left.and.right", count: count(for: .subscriptions))]
            + LibrarySidebarSmartFeed.allCases.map { feed in
                LibrarySidebarRow(
                    source: .smart(feed),
                    title: feed.title,
                    systemImage: feed.iconName,
                    count: count(for: .smart(feed))
                )
            }
    }

    public func folderRows(including groupNames: [String] = []) -> [LibrarySidebarRow] {
        [
            LibrarySidebarRow(source: .library, title: "Library", systemImage: "books.vertical", count: count(for: .library)),
        ] + groupSections(including: self.groupNames + groupNames).map { section in
            LibrarySidebarRow(
                source: section.source,
                title: section.title,
                systemImage: "folder",
                count: section.count
            )
        }
    }

    public func groupSections(including groupNames: [String] = []) -> [LibrarySidebarSection] {
        let normalizedNames = groupNames.map(LibrarySidebarItem.normalizedGroupName)
        let processedVisibleItems = items.filter { !$0.isArchived && !Self.itemIsUnprocessed($0) }
        let names = Set(processedVisibleItems.map(\.groupName)).union(normalizedNames).union([Self.defaultGroupName])
        return names.sorted(by: Self.groupSort).map { groupName in
            let source = LibrarySidebarSource.group(groupName)
            return LibrarySidebarSection(
                source: source,
                title: groupName,
                items: readFilteredItems(
                    processedVisibleItems.filter { $0.groupName == groupName },
                    for: source
                )
            )
        }
    }

    public func filteredItems(for source: LibrarySidebarSource) -> [LibrarySidebarItem] {
        let visibleItems = items.filter { !$0.isArchived }
        switch source {
        case .library:
            return readFilteredItems(visibleItems.filter { !Self.itemIsUnprocessed($0) }, for: source)
        case let .smart(feed):
            let source = LibrarySidebarSource.smart(feed)
            switch feed {
            case .today:
                let items = visibleItems.filter { item in
                    guard let processedAt = item.processedAt else { return false }
                    return !Self.itemIsUnprocessed(item) && calendar.isDateInToday(processedAt)
                }
                return readFilteredItems(items, for: source)
            case .unprocessed:
                return visibleItems.filter { Self.itemIsUnprocessed($0) }
            case .starred:
                let items = visibleItems.filter { item in
                    !Self.itemIsUnprocessed(item) && item.isStarred
                }
                return readFilteredItems(items, for: source)
            case .archive:
                return readFilteredItems(items.filter(\.isArchived), for: source)
            }
        case let .group(groupName):
            return readFilteredItems(
                visibleItems.filter { $0.groupName == LibrarySidebarItem.normalizedGroupName(groupName) && !Self.itemIsUnprocessed($0) },
                for: source
            )
        case .subscriptions:
            return []
        }
    }

    public func count(for source: LibrarySidebarSource) -> Int {
        if case .subscriptions = source {
            return subscriptions.count
        }
        return filteredItems(for: source).count
    }

    public func readCounts(for source: LibrarySidebarSource) -> LibraryReadCounts {
        let items = readCountSourceItems(for: source)
        return LibraryReadCounts(
            unread: items.filter { !$0.isRead }.count,
            total: items.count
        )
    }

    public func title(for source: LibrarySidebarSource) -> String {
        switch source {
        case .library:
            return "Library"
        case .subscriptions:
            return "Subscriptions"
        case let .smart(feed):
            return feed.title
        case let .group(groupName):
            return LibrarySidebarItem.normalizedGroupName(groupName)
        }
    }

    public func unprocessedQueueFilterCount(for status: LibraryQueueStatus) -> Int {
        items.filter { item in
            !item.isArchived && Self.itemIsUnprocessed(item) && item.queueStatus == status
        }
        .count
    }

    public func subscriptionItemCounts(for subscription: LibrarySidebarSubscription) -> SubscriptionItemCounts {
        let matchingItems = subscriptionItems(for: subscription)
        return SubscriptionItemCounts(
            unprocessed: matchingItems.filter(Self.itemIsUnprocessed).count,
            total: matchingItems.count
        )
    }

    public func subscriptionItems(for subscription: LibrarySidebarSubscription) -> [LibrarySidebarItem] {
        let subscriptionURLs = Set(
            [subscription.url, subscription.feedURL].compactMap(Self.normalizedSubscriptionURL)
        )
        return items.filter { item in
            !item.isArchived && Self.itemMatches(subscription: subscription, subscriptionURLs: subscriptionURLs, item: item)
        }
    }

    public func unprocessedItems(from sourceItems: [LibrarySidebarItem]) -> [LibrarySidebarItem] {
        Self.uniqueItems(from: sourceItems).filter(Self.itemIsUnprocessed)
    }

    public static func itemIsUnprocessed(_ item: LibrarySidebarItem) -> Bool {
        !item.hasProcessed
    }

    public static func canFilterReadItems(for source: LibrarySidebarSource) -> Bool {
        switch source {
        case .library, .group:
            return true
        case let .smart(feed):
            return feed != .unprocessed
        case .subscriptions:
            return false
        }
    }

    public static func uniqueItems(from sourceItems: [LibrarySidebarItem]) -> [LibrarySidebarItem] {
        var seen = Set<String>()
        return sourceItems.filter { item in
            guard !seen.contains(item.id) else { return false }
            seen.insert(item.id)
            return true
        }
    }

    public static func reconciledSelectionID(
        currentID: String?,
        visibleItems: [LibrarySidebarItem],
        forceFirstVisible: Bool = false
    ) -> String? {
        if
            !forceFirstVisible,
            let currentID,
            visibleItems.contains(where: { $0.id == currentID })
        {
            return currentID
        }
        return visibleItems.first?.id
    }

    public static func items(from episodes: [LibraryEpisode]) -> [LibrarySidebarItem] {
        episodes.map { episode in
            LibrarySidebarItem(
                id: episode.id,
                title: episode.title,
                groupName: episode.appGroup ?? Self.defaultGroupName,
                hasProcessed: episode.hasSyncedDocuments,
                isRead: episode.isRead,
                isStarred: episode.isStarred,
                queueStatus: episode.appQueueStatus.flatMap(LibraryQueueStatus.init(rawValue:)) ?? .unread,
                isArchived: episode.isArchived,
                modifiedAt: parsedDate(episode.localPublishedAt) ?? parsedDate(episode.publishedAt) ?? .distantPast,
                processedAt: parsedDate(episode.processedAt),
                sourceURL: episode.sourceURL ?? episode.canonicalURL,
                subscriptionID: episode.subscriptionID,
                seriesURL: episode.seriesURL
            )
        }
    }

    public static func subscriptions(from subscriptions: [LibrarySubscription]) -> [LibrarySidebarSubscription] {
        subscriptions.map {
            LibrarySidebarSubscription(id: $0.id, title: $0.title, url: $0.url, feedURL: $0.feedURL)
        }
    }

    private static func groupSort(_ lhs: String, _ rhs: String) -> Bool {
        if lhs == defaultGroupName { return true }
        if rhs == defaultGroupName { return false }
        return lhs.localizedStandardCompare(rhs) == .orderedAscending
    }

    private func readFilteredItems(_ sourceItems: [LibrarySidebarItem], for source: LibrarySidebarSource) -> [LibrarySidebarItem] {
        guard hidesReadItems, Self.canFilterReadItems(for: source) else {
            return sourceItems
        }
        return sourceItems.filter { !$0.isRead }
    }

    private func readCountSourceItems(for source: LibrarySidebarSource) -> [LibrarySidebarItem] {
        let visibleItems = items.filter { !$0.isArchived }
        switch source {
        case .library:
            return visibleItems.filter { !Self.itemIsUnprocessed($0) }
        case let .group(groupName):
            return visibleItems.filter {
                $0.groupName == LibrarySidebarItem.normalizedGroupName(groupName)
                    && !Self.itemIsUnprocessed($0)
            }
        case let .smart(feed):
            switch feed {
            case .today:
                return visibleItems.filter { item in
                    guard let processedAt = item.processedAt else { return false }
                    return !Self.itemIsUnprocessed(item) && calendar.isDateInToday(processedAt)
                }
            case .starred:
                return visibleItems.filter { !Self.itemIsUnprocessed($0) && $0.isStarred }
            case .archive:
                return items.filter(\.isArchived)
            case .unprocessed:
                return []
            }
        case .subscriptions:
            return []
        }
    }

    private static func parsedDate(_ value: String?) -> Date? {
        LibraryDateParser.date(from: value)
    }

    private static func normalizedSubscriptionURL(_ value: String?) -> String? {
        guard var text = value?.trimmingCharacters(in: .whitespacesAndNewlines), !text.isEmpty else {
            return nil
        }
        while text.hasSuffix("/") {
            text.removeLast()
        }
        return text.lowercased()
    }

    private static func itemMatches(
        subscription: LibrarySidebarSubscription,
        subscriptionURLs: Set<String>,
        item: LibrarySidebarItem
    ) -> Bool {
        if item.subscriptionID == subscription.id {
            return true
        }
        guard item.subscriptionID == nil else { return false }
        let itemURLs = [item.seriesURL, item.sourceURL].compactMap(normalizedSubscriptionURL)
        return itemURLs.contains { subscriptionURLs.contains($0) }
    }
}
