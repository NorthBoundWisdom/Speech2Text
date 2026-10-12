import SwiftUI
#if canImport(Audio2TextCore)
    import Audio2TextCore
#endif

struct MobilePortraitLibraryShell: View {
    @ObservedObject var store: MobileLibraryViewModel
    @ObservedObject var navigation: MobileNavigationState
    @Binding var isAddingSubscription: Bool
    @Binding var isShowingSettings: Bool
    @Binding var readingStyle: ReadingStyleSettings

    let sidebarState: LibrarySidebarState
    let sourceTitle: (LibrarySidebarSource) -> String
    let sectionsForSource: (LibrarySidebarSource) -> [MobileEpisodeSection]
    let episodeForID: (String) -> LibraryEpisode?
    let selectSource: (LibrarySidebarSource) -> Void
    let selectEpisode: (LibraryEpisode) -> Void
    let canToggleHidingReadItems: (LibrarySidebarSource) -> Bool
    let markEpisodeRead: (LibraryEpisode) -> Void
    let toggleEpisodeStar: (LibraryEpisode) -> Void
    let toggleHidingReadItems: () -> Void
    let archiveEpisode: (LibraryEpisode) -> Void
    let deleteEpisode: (LibraryEpisode) -> Void
    let moveEpisode: (LibraryEpisode, String) -> Void
    let copyEpisodeLink: (LibraryEpisode) -> Void
    let refreshSubscription: (LibrarySubscription) -> Void
    let fetchSubscriptionHistory: (LibrarySubscription) -> Void
    let deleteSubscription: (LibrarySubscription) -> Void
    let copySubscriptionLink: (LibrarySubscription) -> Void

    var body: some View {
        NavigationStack(path: $navigation.portraitPath) {
            MobileSourcePanel(
                store: store,
                sidebarState: sidebarState,
                selectedSource: navigation.selectedSource,
                isShowingSettings: $isShowingSettings,
                onSelectSource: selectSource,
                titleDisplayMode: .system
            )
            .navigationDestination(for: MobilePortraitRoute.self) { route in
                switch route {
                case let .episodes(source):
                    MobileEpisodePanel(
                        store: store,
                        sections: sectionsForSource(source),
                        selectedEpisodeID: store.selectedEpisodeID,
                        selectedSource: source,
                        selectedSourceTitle: sourceTitle(source),
                        hidesReadItems: store.hidesReadItems,
                        canToggleHidingReadItems: canToggleHidingReadItems(source),
                        onSelectEpisode: selectEpisode,
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
                        onCopySubscriptionLink: copySubscriptionLink,
                        headerDisplayMode: .systemNavigation
                    )
                case let .reader(episodeID):
                    MobileReaderPane(
                        episode: episodeForID(episodeID),
                        libraryRoot: store.libraryRoot,
                        section: $navigation.readerSection,
                        readingStyle: $readingStyle,
                        onMarkEpisodeRead: markEpisodeRead,
                        onToggleEpisodeStar: toggleEpisodeStar,
                        onArchiveEpisode: archiveEpisode,
                        onDeleteEpisode: deleteEpisode,
                        headerDisplayMode: .systemNavigation
                    )
                }
            }
        }
        .background(Color.mobileShellBackground)
    }
}
