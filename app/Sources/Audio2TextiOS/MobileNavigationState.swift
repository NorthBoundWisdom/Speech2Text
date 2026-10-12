import SwiftUI
#if canImport(Audio2TextCore)
    import Audio2TextCore
#endif

@MainActor
final class MobileNavigationState: ObservableObject {
    @Published var selectedSource: LibrarySidebarSource = .library
    @Published var selectedSubscriptionID: String?
    @Published var portraitPath: [MobilePortraitRoute] = []
    @Published var readerSection: MobileReaderSection = .intro
    @Published var isSourcePanelVisibleInLandscape = true

    func selectSource(_ source: LibrarySidebarSource) {
        updateRoutes { $0.selectSource(source) }
    }

    func openSource(_ source: LibrarySidebarSource) {
        updateRoutes { $0.openSource(source) }
    }

    func openReader(_ episodeID: String) {
        updateRoutes { $0.openReader(episodeID) }
    }

    func restorePortraitPath(selectedEpisodeID: String?) {
        updateRoutes { $0.restorePortraitPath(selectedEpisodeID: selectedEpisodeID) }
    }

    func pruneDeletedEpisode(_ episodeID: String) {
        updateRoutes { $0.pruneDeletedEpisode(episodeID) }
    }

    func pruneInvalidEpisodes(validEpisodeIDs: Set<String>) {
        updateRoutes { $0.pruneInvalidEpisodes(validEpisodeIDs: validEpisodeIDs) }
    }

    func popPortraitRoute() {
        updateRoutes { $0.popPortraitRoute() }
    }

    func toggleSourcePanelVisibilityInLandscape() {
        withAnimation(.easeInOut(duration: 0.18)) {
            isSourcePanelVisibleInLandscape.toggle()
        }
    }

    private func updateRoutes(_ update: (inout MobileNavigationRouteState) -> Void) {
        var state = MobileNavigationRouteState(
            selectedSource: selectedSource,
            portraitPath: portraitPath
        )
        update(&state)
        selectedSource = state.selectedSource
        portraitPath = state.portraitPath
    }
}
