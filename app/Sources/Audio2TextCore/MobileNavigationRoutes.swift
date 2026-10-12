import Foundation

public enum MobilePortraitRoute: Hashable {
    case episodes(LibrarySidebarSource)
    case reader(String)
}

public struct MobileNavigationRouteState: Equatable {
    public var selectedSource: LibrarySidebarSource
    public var portraitPath: [MobilePortraitRoute]

    public init(
        selectedSource: LibrarySidebarSource = .library,
        portraitPath: [MobilePortraitRoute] = []
    ) {
        self.selectedSource = selectedSource
        self.portraitPath = portraitPath
    }

    public mutating func selectSource(_ source: LibrarySidebarSource) {
        selectedSource = source
    }

    public mutating func openSource(_ source: LibrarySidebarSource) {
        selectedSource = source
        portraitPath = [.episodes(source)]
    }

    public mutating func openReader(_ episodeID: String) {
        if portraitPath.first != .episodes(selectedSource) {
            portraitPath = [.episodes(selectedSource)]
        }
        if portraitPath.last != .reader(episodeID) {
            portraitPath.append(.reader(episodeID))
        }
    }

    public mutating func restorePortraitPath(selectedEpisodeID: String?) {
        if let selectedEpisodeID {
            portraitPath = [.episodes(selectedSource), .reader(selectedEpisodeID)]
        } else if selectedSource == .library {
            portraitPath = []
        } else {
            portraitPath = [.episodes(selectedSource)]
        }
    }

    public mutating func pruneDeletedEpisode(_ episodeID: String) {
        portraitPath.removeAll { route in
            if case let .reader(id) = route {
                return id == episodeID
            }
            return false
        }
    }

    public mutating func pruneInvalidEpisodes(validEpisodeIDs: Set<String>) {
        portraitPath.removeAll { route in
            if case let .reader(id) = route {
                return !validEpisodeIDs.contains(id)
            }
            return false
        }
    }

    public mutating func popPortraitRoute() {
        if !portraitPath.isEmpty {
            portraitPath.removeLast()
        }
    }
}
