import Foundation
#if canImport(Audio2TextCore)
    import Audio2TextCore
#endif

struct LibraryLoadSnapshot {
    let libraryItems: [ProcessLibraryItem]
    let subscriptions: [PodcastSubscriptionItem]
    let librarySections: [ProcessLibrarySection]
    let librarySyncStatus: LibrarySyncStatus
    let selectedSnapshot: OutputSnapshot?

    static func load(
        dataRoot: URL,
        libraryRoot: URL,
        selectedOutputDirectory: URL?
    ) -> LibraryLoadSnapshot {
        let items = ProcessLibrary.scan(dataRoot: dataRoot)
        let subscriptions = SubscriptionLibrary.load(dataRoot: dataRoot)
        let sections = ProcessLibrary.sections(
            from: items,
            including: ProcessLibrary.groupNames(from: items, dataRoot: dataRoot)
        )
        let selectedSnapshot = selectedOutputDirectory.flatMap { outputDirectory in
            if let item = items.first(where: { $0.outputURL.standardizedFileURL.path == outputDirectory.standardizedFileURL.path }) {
                return OutputWatcher.snapshot(outputDirectory: item.outputURL, documentsDirectory: item.documentsURL)
            }
            return OutputWatcher.snapshot(outputDirectory: outputDirectory)
        }
        return LibraryLoadSnapshot(
            libraryItems: items,
            subscriptions: subscriptions,
            librarySections: sections,
            librarySyncStatus: LibrarySyncStatusProbe.status(for: libraryRoot),
            selectedSnapshot: selectedSnapshot
        )
    }
}

extension JobController {
    func snapshot(for item: ProcessLibraryItem) -> OutputSnapshot {
        OutputWatcher.snapshot(outputDirectory: item.outputURL, documentsDirectory: item.documentsURL)
    }

    func snapshotForOutputDirectory(_ outputDirectory: URL?) -> OutputSnapshot {
        guard let outputDirectory else {
            return OutputWatcher.snapshot(outputDirectory: nil)
        }
        if let item = libraryItems.first(where: { $0.outputURL.standardizedFileURL.path == outputDirectory.standardizedFileURL.path }) {
            return snapshot(for: item)
        }
        return OutputWatcher.snapshot(outputDirectory: outputDirectory)
    }

    func libraryListSnapshotForOutputDirectory(_ outputDirectory: URL?) -> OutputSnapshot {
        guard let outputDirectory else {
            return OutputWatcher.libraryListSnapshot(outputDirectory: nil)
        }
        if let item = libraryItems.first(where: { $0.outputURL.standardizedFileURL.path == outputDirectory.standardizedFileURL.path }) {
            return OutputWatcher.libraryListSnapshot(outputDirectory: item.outputURL, documentsDirectory: item.documentsURL)
        }
        return OutputWatcher.libraryListSnapshot(outputDirectory: outputDirectory)
    }

    func refresh() {
        refreshLibraryInBackground()
    }

    func loadLibrarySynchronously() {
        let dataRoot = settingsStore.dataRoot()
        let loadSnapshot = LibraryLoadSnapshot.load(
            dataRoot: dataRoot,
            libraryRoot: settingsStore.libraryRoot(),
            selectedOutputDirectory: snapshot.outputDirectory
        )
        applyLibraryLoadSnapshot(loadSnapshot)
    }

    func refreshLibraryInBackground() {
        libraryLoadTask?.cancel()
        libraryLoadGeneration += 1
        let generation = libraryLoadGeneration
        let request = libraryLoadRequest()
        libraryLoadTask = Task { [weak self] in
            let loadSnapshot = await Task.detached(priority: .userInitiated) {
                LibraryLoadSnapshot.load(
                    dataRoot: request.dataRoot,
                    libraryRoot: request.libraryRoot,
                    selectedOutputDirectory: request.selectedOutputDirectory
                )
            }.value
            guard !Task.isCancelled else { return }
            guard let self, self.libraryLoadGeneration == generation else { return }
            self.applyLibraryLoadSnapshot(loadSnapshot)
        }
    }

    func refreshLibraryAndWait() async {
        libraryLoadTask?.cancel()
        libraryLoadGeneration += 1
        let generation = libraryLoadGeneration
        let request = libraryLoadRequest()
        let loadSnapshot = await Task.detached(priority: .userInitiated) {
            LibraryLoadSnapshot.load(
                dataRoot: request.dataRoot,
                libraryRoot: request.libraryRoot,
                selectedOutputDirectory: request.selectedOutputDirectory
            )
        }.value
        guard !Task.isCancelled, libraryLoadGeneration == generation else { return }
        applyLibraryLoadSnapshot(loadSnapshot)
    }

    private struct LibraryLoadRequest {
        let dataRoot: URL
        let libraryRoot: URL
        let selectedOutputDirectory: URL?
    }

    private func libraryLoadRequest() -> LibraryLoadRequest {
        LibraryLoadRequest(
            dataRoot: settingsStore.dataRoot(),
            libraryRoot: settingsStore.libraryRoot(),
            selectedOutputDirectory: snapshot.outputDirectory
        )
    }

    private func applyLibraryLoadSnapshot(_ loadSnapshot: LibraryLoadSnapshot) {
        let preloadedSelectedSnapshot = loadSnapshot.selectedSnapshot.map(snapshotApplyingPendingSummary)
        libraryItems = loadSnapshot.libraryItems
        subscriptions = loadSnapshot.subscriptions
        librarySections = loadSnapshot.librarySections
        if selectedGroupName.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            selectedGroupName = ProcessLibrary.defaultGroupName
        }
        applyLibrarySyncStatusIfChanged(loadSnapshot.librarySyncStatus)
        reconcileVisibleSelection(preloadedSnapshot: preloadedSelectedSnapshot)
    }

    func selectLibraryItem(_ item: ProcessLibraryItem) {
        if
            selectedLibraryItemID == item.id,
            selectedFile == item.audioURL,
            snapshot.outputDirectory?.standardizedFileURL.path == item.outputURL.standardizedFileURL.path
        {
            return
        }
        logEvent(
            category: "library",
            event: "library_item_selected",
            message: "Library item selected",
            fields: ["item_id": item.id, "source": item.source, "status": item.status]
        )
        selectLibraryItem(item, preloadedSnapshot: nil)
    }

    private func selectLibraryItem(_ item: ProcessLibraryItem, preloadedSnapshot: OutputSnapshot?) {
        flushPendingSummarySaveSynchronously()
        selectedLibraryItemID = item.id
        selectedFile = item.audioURL
        metadataText = ProcessLibrary.metadataText(for: item)
        snapshot = snapshotApplyingPendingSummary(preloadedSnapshot ?? snapshot(for: item))
        if !stage.isRunning {
            stopWatching()
            progressFraction = snapshot.progressFraction
            stage = .idle
            message = item.status
        }
    }

    func refreshSelectedLibraryItemDetails(_ item: ProcessLibraryItem) {
        refreshSelectedLibraryItemDetails(item, preloadedSnapshot: nil)
    }

    private func refreshSelectedLibraryItemDetails(_ item: ProcessLibraryItem, preloadedSnapshot: OutputSnapshot?) {
        selectedFile = item.audioURL
        metadataText = ProcessLibrary.metadataText(for: item)
        snapshot = snapshotApplyingPendingSummary(preloadedSnapshot ?? snapshot(for: item))
    }

    func updateSelectedLibraryItemDetails(from runningSnapshot: OutputSnapshot, outputDirectory: URL) {
        guard
            let index = libraryItems.firstIndex(where: { $0.outputURL.standardizedFileURL.path == outputDirectory.standardizedFileURL.path })
        else {
            return
        }
        let item = libraryItems[index]
        let updated = item.withProcessingStatus(
            status: ProcessLibrary.status(for: runningSnapshot, outputURL: outputDirectory, isAudioPresent: item.isAudioPresent),
            detail: ProcessLibrary.detail(for: runningSnapshot, outputURL: outputDirectory, isAudioPresent: item.isAudioPresent),
            hasProcessed: ProcessLibrary.isProcessed(runningSnapshot),
            hasTranscript: ProcessLibrary.hasTranscript(runningSnapshot),
            hasOutput: item.hasOutput || FileManager.default.fileExists(atPath: outputDirectory.path),
            runStatus: runningSnapshot.runStatus,
            processedAt: item.processedAt
        )
        guard updated != item else {
            return
        }
        libraryItems[index] = updated
    }

    func selectSidebarSource(_ source: SidebarSource) {
        logEvent(
            category: "library",
            event: "sidebar_source_selected",
            message: "Sidebar source selected",
            fields: ["source": "\(source)"]
        )
        selectedSidebarSource = source
        if case let .group(groupName) = source {
            selectedGroupName = groupName
        }
        if case .subscriptions = source {
            clearLibrarySelection()
            reconcileSelectedSubscription(forceFirstAvailable: true)
            return
        }
        reconcileVisibleSelection(forceFirstVisible: true)
    }

    func filteredLibraryItems(for source: SidebarSource) -> [ProcessLibraryItem] {
        libraryItems(matching: librarySidebarState.filteredItems(for: source))
    }

    func unprocessedQueueFilterCount(for status: AppQueueStatus) -> Int {
        librarySidebarState.unprocessedQueueFilterCount(for: status)
    }

    func unprocessedCount(for subscription: PodcastSubscriptionItem) -> Int {
        subscriptionItemCounts(for: subscription).unprocessed
    }

    func subscriptionItemCounts(for subscription: PodcastSubscriptionItem) -> SubscriptionItemCounts {
        subscriptionDetailSnapshot(for: subscription).counts.asSubscriptionItemCounts
    }

    var selectedSubscription: PodcastSubscriptionItem? {
        guard let selectedSubscriptionID else { return nil }
        return subscriptions.first { $0.id == selectedSubscriptionID }
    }

    var selectedSubscriptionDetailSnapshot: SubscriptionDetailSnapshot? {
        guard let subscription = selectedSubscription else { return nil }
        return subscriptionDetailSnapshot(for: subscription)
    }

    var subscriptionDetailViewState: SubscriptionDetailViewState {
        refreshLibrarySidebarDerivedStateIfNeeded()
        let snapshot = selectedSubscription.flatMap { subscription in
            cachedSubscriptionDetailSnapshots[subscription.id] ?? subscriptionDetailSnapshot(for: subscription)
        }
        return SubscriptionDetailViewState(
            snapshot: snapshot,
            snapshotVersion: cachedSubscriptionDetailSnapshotVersion,
            hasSubscriptions: !subscriptions.isEmpty,
            subscriptionCount: subscriptions.count,
            isAddingSubscription: isAddingSubscription,
            isRefreshingSubscriptions: isRefreshingSubscriptions,
            subscriptionURLText: subscriptionURLText,
            subscriptionGroupName: subscriptionGroupName,
            availableGroupNames: availableGroupNames,
            isProcessing: stage.isRunning,
            isCloudSummaryConfigured: isCloudSummaryConfigured
        )
    }

    var subscriptionDetailSnapshotVersion: Int {
        refreshLibrarySidebarDerivedStateIfNeeded()
        return cachedSubscriptionDetailSnapshotVersion
    }

    func selectSubscription(_ subscription: PodcastSubscriptionItem) {
        logEvent(
            category: "subscriptions",
            event: "subscription_selected",
            message: "Subscription selected",
            fields: ["subscription_id": subscription.id]
        )
        selectedSubscriptionID = subscription.id
        if case .subscriptions = selectedSidebarSource {
            clearLibrarySelection()
        }
    }

    func libraryItems(for subscription: PodcastSubscriptionItem) -> [ProcessLibraryItem] {
        subscriptionDetailSnapshot(for: subscription).episodes.map(\.item)
    }

    func subscriptionDetailSnapshot(for subscription: PodcastSubscriptionItem) -> SubscriptionDetailSnapshot {
        refreshLibrarySidebarDerivedStateIfNeeded()
        if let snapshot = cachedSubscriptionDetailSnapshots[subscription.id] {
            return snapshot
        }
        let items = libraryItems(matching: cachedLibrarySidebarState.subscriptionItems(for: subscription.sidebarSubscription))
        return SubscriptionDetailSnapshot(subscription: subscription, items: items)
    }

    func openProcessedSubscriptionItem(_ item: ProcessLibraryItem) {
        guard item.isProcessed else { return }
        logEvent(
            category: "subscriptions",
            event: "processed_subscription_item_opened",
            message: "Processed subscription item opened",
            fields: ["item_id": item.id, "subscription_id": item.subscriptionID ?? ""]
        )
        selectedSidebarSource = .library
        selectedTab = .summary
        selectLibraryItem(item)
    }

    func setUnprocessedQueueFilter(_ status: AppQueueStatus?) {
        unprocessedQueueFilter = status
        logEvent(
            category: "library",
            event: "unprocessed_queue_filter_changed",
            message: "Unprocessed queue filter changed",
            fields: ["queue_status": status?.rawValue ?? "all"]
        )
        if case .smart(.unprocessed) = selectedSidebarSource {
            reconcileVisibleSelection(forceFirstVisible: true)
        }
    }

    func setHidesReadLibraryItems(_ hidesReadItems: Bool) {
        guard hidesReadLibraryItems != hidesReadItems else { return }
        hidesReadLibraryItems = hidesReadItems
        persistReadFilterPreference(hidesReadItems)
        logEvent(
            category: "library",
            event: "read_filter_changed",
            message: "Read filter changed",
            fields: ["hides_read_items": "\(hidesReadItems)"]
        )
        if LibrarySidebarState.canFilterReadItems(for: selectedSidebarSource) {
            reconcileVisibleSelection(forceFirstVisible: true)
        }
    }

    private func persistReadFilterPreference(_ hidesReadItems: Bool) {
        do {
            var settings = settingsStore.load()
            settings.hideReadItems = hidesReadItems
            try settingsStore.save(settings)
        } catch {
            message = "Could not save read filter: \(error.localizedDescription)"
            logError(category: "library", event: "read_filter_save_failed", error: error)
        }
    }

    func count(for source: SidebarSource) -> Int {
        librarySidebarState.count(for: source)
    }

    func readCounts(for source: SidebarSource) -> LibraryReadCounts {
        librarySidebarState.readCounts(for: source)
    }

    var sidebarGroupName: String {
        if case let .group(groupName) = selectedSidebarSource {
            return groupName
        }
        return ""
    }

    func itemIsUnprocessed(_ item: ProcessLibraryItem) -> Bool {
        LibrarySidebarState.itemIsUnprocessed(item.sidebarItem)
    }

    func unprocessedItems(from items: [ProcessLibraryItem]) -> [ProcessLibraryItem] {
        libraryItems(matching: librarySidebarState.unprocessedItems(from: items.map(\.sidebarItem)), in: items)
    }

    func uniqueItems(from items: [ProcessLibraryItem]) -> [ProcessLibraryItem] {
        libraryItems(matching: LibrarySidebarState.uniqueItems(from: items.map(\.sidebarItem)), in: items)
    }

    func loadSubscriptions(dataRoot: URL = AppPaths.dataRoot()) {
        subscriptions = SubscriptionLibrary.load(dataRoot: dataRoot)
        reconcileSelectedSubscription()
    }

    func refreshLibrarySyncStatus() {
        let libraryRoot = settingsStore.libraryRoot()
        Task { [weak self] in
            let status = await Task.detached(priority: .utility) {
                LibrarySyncStatusProbe.status(for: libraryRoot)
            }.value
            guard let self else { return }
            self.applyLibrarySyncStatusIfChanged(status)
        }
    }

    func pollLibrarySyncStatus() async {
        while !Task.isCancelled {
            let libraryRoot = settingsStore.libraryRoot()
            let status = await Task.detached(priority: .utility) {
                LibrarySyncStatusProbe.status(for: libraryRoot)
            }.value
            guard !Task.isCancelled else { return }
            applyLibrarySyncStatusIfChanged(status)
            try? await Task.sleep(nanoseconds: 5_000_000_000)
        }
    }

    private func applyLibrarySyncStatusIfChanged(_ status: LibrarySyncStatus) {
        let status = adjustedLibrarySyncStatusAfterLocalMutation(status)
        guard librarySyncStatus.isMeaningfullyDifferent(from: status) else {
            return
        }
        librarySyncStatus = status
    }

    func noteLocalLibraryMutationForSyncStatus(_ detail: String = "本地资料修改正在同步。") {
        localLibraryMutationSyncingUntil = Date().addingTimeInterval(45)
        localLibraryMutationSyncDetail = detail
        librarySyncStatus = .syncing(
            detail,
            checkedAt: Date(),
            scannedFileCount: librarySyncStatus.scannedFileCount,
            pendingFileCount: max(librarySyncStatus.pendingFileCount, 1),
            errorFileCount: librarySyncStatus.errorFileCount
        )
    }

    func refreshLibraryAfterLocalMutation(_ detail: String = "本地资料修改正在同步。") {
        noteLocalLibraryMutationForSyncStatus(detail)
        refreshLibraryInBackground()
    }

    private func adjustedLibrarySyncStatusAfterLocalMutation(_ status: LibrarySyncStatus) -> LibrarySyncStatus {
        if status.state == .synced {
            localLibraryMutationSyncingUntil = nil
            return status
        }
        guard
            status.state == .offline,
            let localLibraryMutationSyncingUntil,
            localLibraryMutationSyncingUntil > Date()
        else {
            return status
        }
        return .syncing(
            localLibraryMutationSyncDetail,
            checkedAt: status.checkedAt,
            scannedFileCount: status.scannedFileCount,
            pendingFileCount: max(status.pendingFileCount, 1),
            errorFileCount: status.errorFileCount
        )
    }

    func reconcileVisibleSelection(forceFirstVisible: Bool = false, preloadedSnapshot: OutputSnapshot? = nil) {
        let items = visibleLibraryItems
        if
            !forceFirstVisible,
            let selectedLibraryItemID
        {
            guard let selectedItem = libraryItems.first(where: { $0.id == selectedLibraryItemID }) else {
                clearLibrarySelection()
                return
            }
            refreshSelectedLibraryItemDetails(selectedItem, preloadedSnapshot: preloadedSnapshot)
            return
        }
        guard let first = items.first else {
            clearLibrarySelection()
            return
        }
        selectLibraryItem(first)
    }

    func reconcileSelectedSubscription(forceFirstAvailable: Bool = false) {
        if
            !forceFirstAvailable,
            let selectedSubscriptionID,
            subscriptions.contains(where: { $0.id == selectedSubscriptionID })
        {
            return
        }
        if forceFirstAvailable || selectedSubscriptionID != nil || selectedSidebarSource == .subscriptions {
            selectedSubscriptionID = subscriptions.first?.id
        }
    }

    func clearLibrarySelection() {
        selectedLibraryItemID = nil
        selectedFile = nil
        metadataText = "No metadata is available."
        snapshot = OutputSnapshot()
        if !stage.isRunning {
            progressFraction = 0.0
            message = ""
        }
    }
}

private extension LibrarySyncStatus {
    func isMeaningfullyDifferent(from other: LibrarySyncStatus) -> Bool {
        state != other.state
            || title != other.title
            || detail != other.detail
            || scannedFileCount != other.scannedFileCount
            || pendingFileCount != other.pendingFileCount
            || errorFileCount != other.errorFileCount
            || progress != other.progress
    }
}
