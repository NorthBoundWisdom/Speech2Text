import Foundation
#if canImport(Audio2TextCore)
    import Audio2TextCore
#endif

@MainActor
extension JobController {
    var canStart: Bool {
        if stage.isRunning { return false }
        if ProcessLibrary.pathComponent(forGroupName: selectedGroupName).isEmpty { return false }
        switch inputMode {
        case .xiaoyuzhou:
            return !urlText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
        case .localFile:
            return selectedFile != nil
        }
    }

    var availableGroupNames: [String] {
        let names = Set(librarySections.map(\.title)).union([ProcessLibrary.defaultGroupName])
        return names.sorted { lhs, rhs in
            if lhs == ProcessLibrary.defaultGroupName { return true }
            if rhs == ProcessLibrary.defaultGroupName { return false }
            return lhs.localizedStandardCompare(rhs) == .orderedAscending
        }
    }

    var visibleLibraryItems: [ProcessLibraryItem] {
        refreshLibrarySidebarDerivedStateIfNeeded()
        return cachedVisibleLibraryItems
    }

    var selectedLibraryItem: ProcessLibraryItem? {
        guard let selectedLibraryItemID else { return nil }
        return libraryItems.first { $0.id == selectedLibraryItemID }
    }

    var visibleContentTabs: [ContentTab] {
        if case .subscriptions = selectedSidebarSource {
            return []
        }
        guard let selectedLibraryItem else {
            return ContentTab.displayOrder
        }
        return selectedLibraryItem.isProcessed ? ContentTab.displayOrder : ContentTab.unprocessedDisplayOrder
    }

    var isLinkValidForCurrentURL: Bool {
        let url = urlText.trimmingCharacters(in: .whitespacesAndNewlines)
        if case let .valid(checkedURL, _) = linkCheckStatus {
            return checkedURL == url
        }
        return false
    }

    var canConfirmImport: Bool {
        guard !stage.isRunning else { return false }
        guard !ProcessLibrary.pathComponent(forGroupName: selectedGroupName).isEmpty else { return false }
        switch inputMode {
        case .xiaoyuzhou:
            return isLinkValidForCurrentURL
        case .localFile:
            return selectedFile != nil
        }
    }
}

extension JobController {
    func markLibrarySidebarDerivedStateDirty() {
        librarySidebarDerivedStateIsDirty = true
    }

    func refreshLibrarySidebarDerivedStateIfNeeded() {
        guard librarySidebarDerivedStateIsDirty else { return }
        var itemsByID: [String: ProcessLibraryItem] = [:]
        for item in libraryItems where itemsByID[item.id] == nil {
            itemsByID[item.id] = item
        }
        let state = LibrarySidebarState(
            items: libraryItems.map(\.sidebarItem),
            subscriptions: subscriptions.map(\.sidebarSubscription),
            groupNames: librarySections.map(\.title),
            selectedSidebarSource: selectedSidebarSource,
            unprocessedQueueFilter: unprocessedQueueFilter,
            hidesReadItems: hidesReadLibraryItems
        )
        cachedLibrarySidebarState = state
        cachedVisibleLibraryItems = state.visibleItems.compactMap { itemsByID[$0.id] }
        cachedSubscriptionDetailSnapshots = subscriptionDetailSnapshots(
            for: subscriptions,
            sidebarState: state,
            itemsByID: itemsByID
        )
        cachedSubscriptionDetailSnapshotVersion += 1
        librarySidebarDerivedStateIsDirty = false
    }

    func libraryItems(matching sidebarItems: [LibrarySidebarItem], in candidates: [ProcessLibraryItem]? = nil) -> [ProcessLibraryItem] {
        let sourceItems = candidates ?? libraryItems
        var itemsByID: [String: ProcessLibraryItem] = [:]
        for item in sourceItems where itemsByID[item.id] == nil {
            itemsByID[item.id] = item
        }
        return sidebarItems.compactMap { itemsByID[$0.id] }
    }

    private func subscriptionDetailSnapshots(
        for subscriptions: [PodcastSubscriptionItem],
        sidebarState: LibrarySidebarState,
        itemsByID: [String: ProcessLibraryItem]
    ) -> [String: SubscriptionDetailSnapshot] {
        var snapshots: [String: SubscriptionDetailSnapshot] = [:]
        snapshots.reserveCapacity(subscriptions.count)
        for subscription in subscriptions {
            let sidebarItems = sidebarState.subscriptionItems(for: subscription.sidebarSubscription)
            let items = sidebarItems.compactMap { itemsByID[$0.id] }
            snapshots[subscription.id] = SubscriptionDetailSnapshot(subscription: subscription, items: items)
        }
        return snapshots
    }
}
