import SwiftUI
#if canImport(Audio2TextCore)
    import Audio2TextCore
#endif

struct MobileAdaptiveShell: View {
    @ObservedObject var store: MobileLibraryViewModel
    @ObservedObject var navigation: MobileNavigationState
    @Binding var isAddingSubscription: Bool
    @Binding var isShowingSettings: Bool
    @Binding var readingStyle: ReadingStyleSettings

    var body: some View {
        GeometryReader { proxy in
            let context = MobileLayoutContext(size: proxy.size, safeAreaInsets: proxy.safeAreaInsets)
            workspace(context: context)
                .onAppear {
                    if context.isLandscape {
                        ensureVisibleSelection()
                    }
                }
                .onChange(of: context.isLandscape) { _, isLandscape in
                    if isLandscape {
                        ensureVisibleSelection()
                    } else {
                        navigation.restorePortraitPath(selectedEpisodeID: store.selectedEpisodeID)
                    }
                }
                .onChange(of: store.episodes) { _, episodes in
                    navigation.pruneInvalidEpisodes(validEpisodeIDs: Set(episodes.map(\.id)))
                    if context.isLandscape {
                        ensureVisibleSelection()
                    }
                }
                .onChange(of: store.subscriptions) { _, _ in
                    if context.isLandscape {
                        ensureVisibleSelection()
                    }
                }
                .onChange(of: navigation.selectedSource) { _, _ in
                    if context.isLandscape {
                        ensureVisibleSelection()
                    }
                }
                .onChange(of: store.hidesReadItems) { _, _ in
                    ensureVisibleSelection()
                }
        }
    }

    @ViewBuilder
    private func workspace(context: MobileLayoutContext) -> some View {
        if context.isLandscape {
            landscapeWorkspace(context: context)
        } else {
            portraitWorkspace
        }
    }

    private var portraitWorkspace: some View {
        MobilePortraitLibraryShell(
            store: store,
            navigation: navigation,
            isAddingSubscription: $isAddingSubscription,
            isShowingSettings: $isShowingSettings,
            readingStyle: $readingStyle,
            sidebarState: sidebarState,
            sourceTitle: sourceTitle,
            sectionsForSource: episodeSections,
            episodeForID: episode,
            selectSource: selectPortraitSource,
            selectEpisode: selectPortraitEpisode,
            canToggleHidingReadItems: { canToggleHidingReadItems(for: $0) },
            markEpisodeRead: markEpisodeRead,
            toggleEpisodeStar: toggleEpisodeStar,
            toggleHidingReadItems: toggleHidingReadItems,
            archiveEpisode: archiveEpisode,
            deleteEpisode: deleteEpisode,
            moveEpisode: moveEpisode,
            copyEpisodeLink: copyEpisodeLink,
            refreshSubscription: refreshSubscription,
            fetchSubscriptionHistory: fetchSubscriptionHistory,
            deleteSubscription: deleteSubscription,
            copySubscriptionLink: copySubscriptionLink
        )
    }

    private func landscapeWorkspace(context: MobileLayoutContext) -> some View {
        LibraryWorkspaceShell(
            showsSourceColumn: navigation.isSourcePanelVisibleInLandscape,
            sourceColumnWidth: context.sourceColumnWidth,
            listColumnWidth: context.episodeColumnWidth,
            sourceColumnMinimumWidth: 190,
            listColumnMinimumWidth: 240
        ) {
            MobileSourcePanel(
                store: store,
                sidebarState: sidebarState,
                selectedSource: navigation.selectedSource,
                isShowingSettings: $isShowingSettings,
                onSelectSource: selectLandscapeSource,
                titleDisplayMode: .compact
            )
        } listColumn: {
            MobileEpisodePanel(
                store: store,
                sections: episodeSections(for: navigation.selectedSource),
                selectedEpisodeID: store.selectedEpisodeID,
                selectedSubscriptionID: navigation.selectedSubscriptionID,
                selectedSource: navigation.selectedSource,
                selectedSourceTitle: sourceTitle(for: navigation.selectedSource),
                isSourcePanelVisible: navigation.isSourcePanelVisibleInLandscape,
                hidesReadItems: store.hidesReadItems,
                canToggleHidingReadItems: canToggleHidingReadItems(for: navigation.selectedSource),
                onToggleSourcePanel: navigation.toggleSourcePanelVisibilityInLandscape,
                onSelectEpisode: selectLandscapeEpisode,
                onSelectSubscription: selectLandscapeSubscription,
                onAddSubscription: { isAddingSubscription = true },
                onMarkEpisodeRead: markEpisodeRead,
                onToggleEpisodeStar: toggleEpisodeStar,
                onToggleHidingReadItems: toggleHidingReadItems,
                onArchiveEpisode: archiveEpisode,
                onDeleteEpisode: deleteEpisode,
                onMoveEpisode: moveEpisode,
                onCopyEpisodeLink: copyEpisodeLink,
                onRefreshSubscription: refreshSubscription,
                onFetchSubscriptionHistory: fetchSubscriptionHistory,
                onDeleteSubscription: deleteSubscription,
                onCopySubscriptionLink: copySubscriptionLink
            )
        } detailColumn: {
            if case .subscriptions = navigation.selectedSource {
                MobileSubscriptionDetailPane(
                    subscription: selectedSubscription(fallbackToFirst: true),
                    episodes: selectedSubscriptionEpisodes(fallbackToFirst: true),
                    isRefreshing: store.isRefreshing,
                    onRefresh: refreshSubscription,
                    onFetchHistory: fetchSubscriptionHistory,
                    onDelete: deleteSubscription,
                    onCopyLink: copySubscriptionLink
                )
            } else {
                MobileReaderPane(
                    episode: selectedEpisode(for: navigation.selectedSource, fallbackToFirst: true),
                    libraryRoot: store.libraryRoot,
                    section: $navigation.readerSection,
                    readingStyle: $readingStyle,
                    onMarkEpisodeRead: markEpisodeRead,
                    onToggleEpisodeStar: toggleEpisodeStar,
                    onArchiveEpisode: archiveEpisode,
                    onDeleteEpisode: deleteEpisode
                )
            }
        }
        .background(Color.mobileShellBackground)
        .ignoresSafeArea(.container, edges: .bottom)
    }

    private var sidebarState: LibrarySidebarState {
        store.sidebarState(selectedSource: navigation.selectedSource)
    }

    private func filteredEpisodes(for source: LibrarySidebarSource) -> [LibraryEpisode] {
        let state = store.sidebarState(selectedSource: source)
        return store.episodes(matching: state.filteredItems(for: source))
    }

    private func episodeSections(for source: LibrarySidebarSource) -> [MobileEpisodeSection] {
        [MobileEpisodeSection(title: sourceTitle(for: source), episodes: filteredEpisodes(for: source))]
    }

    private func selectedEpisode(for source: LibrarySidebarSource, fallbackToFirst: Bool) -> LibraryEpisode? {
        let visibleEpisodes = filteredEpisodes(for: source)
        guard !visibleEpisodes.isEmpty else {
            return nil
        }
        if let selectedEpisodeID = store.selectedEpisodeID,
           let episode = visibleEpisodes.first(where: { $0.id == selectedEpisodeID })
        {
            return episode
        }
        return fallbackToFirst ? visibleEpisodes.first : nil
    }

    private func episode(for id: String) -> LibraryEpisode? {
        store.episode(forID: id)
    }

    private func selectedSubscription(fallbackToFirst: Bool) -> LibrarySubscription? {
        if let selectedSubscriptionID = navigation.selectedSubscriptionID,
           let subscription = store.subscriptions.first(where: { $0.id == selectedSubscriptionID })
        {
            return subscription
        }
        return fallbackToFirst ? store.subscriptions.first : nil
    }

    private func episodes(for subscription: LibrarySubscription) -> [LibraryEpisode] {
        let sidebarSubscription = LibrarySidebarSubscription(
            id: subscription.id,
            title: subscription.title,
            url: subscription.url,
            feedURL: subscription.feedURL
        )
        let sidebarItems = sidebarState.subscriptionItems(for: sidebarSubscription)
        return store.episodes(matching: sidebarItems)
    }

    private func selectedSubscriptionEpisodes(fallbackToFirst: Bool) -> [LibraryEpisode] {
        guard let subscription = selectedSubscription(fallbackToFirst: fallbackToFirst) else {
            return []
        }
        return episodes(for: subscription)
    }

    private func sourceTitle(for source: LibrarySidebarSource) -> String {
        sidebarState.title(for: source)
    }

    private func selectLandscapeSource(_ source: LibrarySidebarSource) {
        navigation.selectSource(source)
        if case .subscriptions = source {
            store.selectedEpisodeID = nil
            ensureVisibleSubscriptionSelection()
        } else {
            store.selectedEpisodeID = filteredEpisodes(for: source).first?.id
        }
    }

    private func selectPortraitSource(_ source: LibrarySidebarSource) {
        navigation.openSource(source)
    }

    private func selectLandscapeEpisode(_ episode: LibraryEpisode) {
        store.selectedEpisodeID = episode.id
    }

    private func selectLandscapeSubscription(_ subscription: LibrarySubscription) {
        navigation.selectedSubscriptionID = subscription.id
        store.selectedEpisodeID = nil
    }

    private func selectPortraitEpisode(_ episode: LibraryEpisode) {
        store.selectedEpisodeID = episode.id
        navigation.openReader(episode.id)
    }

    private func markEpisodeRead(_ episode: LibraryEpisode) {
        withAnimation(.easeInOut(duration: 0.22)) {
            store.markEpisodeRead(episode)
        }
    }

    private func toggleEpisodeStar(_ episode: LibraryEpisode) {
        store.toggleEpisodeStar(episode)
    }

    private func toggleHidingReadItems() {
        withAnimation(.easeInOut(duration: 0.22)) {
            store.toggleHidingReadItems()
        }
    }

    private func archiveEpisode(_ episode: LibraryEpisode) {
        store.archiveEpisode(episode)
    }

    private func deleteEpisode(_ episode: LibraryEpisode) {
        navigation.pruneDeletedEpisode(episode.id)
        store.deleteEpisode(episode)
    }

    private func moveEpisode(_ episode: LibraryEpisode, toGroup groupName: String) {
        store.moveEpisode(episode, toGroup: groupName)
    }

    private func copyEpisodeLink(_ episode: LibraryEpisode) {
        store.copyEpisodeLink(episode)
    }

    private func refreshSubscription(_ subscription: LibrarySubscription) {
        Task {
            await store.refreshSubscription(subscription)
        }
    }

    private func fetchSubscriptionHistory(_ subscription: LibrarySubscription) {
        Task {
            await store.fetchSubscriptionHistory(subscription)
        }
    }

    private func deleteSubscription(_ subscription: LibrarySubscription) {
        store.deleteSubscription(subscription)
    }

    private func copySubscriptionLink(_ subscription: LibrarySubscription) {
        store.copySubscriptionLink(subscription)
    }

    private func ensureVisibleEpisodeSelection() {
        let visibleEpisodes = filteredEpisodes(for: navigation.selectedSource)
        if let selectedEpisodeID = store.selectedEpisodeID,
           visibleEpisodes.contains(where: { $0.id == selectedEpisodeID })
        {
            return
        }
        store.selectedEpisodeID = visibleEpisodes.first?.id
    }

    private func ensureVisibleSubscriptionSelection() {
        if let selectedSubscriptionID = navigation.selectedSubscriptionID,
           store.subscriptions.contains(where: { $0.id == selectedSubscriptionID })
        {
            return
        }
        navigation.selectedSubscriptionID = store.subscriptions.first?.id
    }

    private func ensureVisibleSelection() {
        if case .subscriptions = navigation.selectedSource {
            store.selectedEpisodeID = nil
            ensureVisibleSubscriptionSelection()
        } else {
            ensureVisibleEpisodeSelection()
        }
    }

    private func canToggleHidingReadItems(for source: LibrarySidebarSource) -> Bool {
        LibrarySidebarState.canFilterReadItems(for: source)
    }
}

private struct MobileLayoutContext {
    let size: CGSize
    let safeAreaInsets: EdgeInsets

    var isLandscape: Bool {
        size.width > size.height
    }

    var sourceColumnWidth: CGFloat {
        min(280, max(190, size.width * 0.27))
    }

    var episodeColumnWidth: CGFloat {
        min(390, max(240, size.width * 0.34))
    }
}
