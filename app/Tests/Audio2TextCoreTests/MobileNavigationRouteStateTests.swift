@testable import Audio2TextCore
import XCTest

final class MobileNavigationRouteStateTests: XCTestCase {
    func testPortraitRouteStateRestoresReaderAndPrunesDeletedEpisodes() {
        var state = MobileNavigationRouteState()

        state.restorePortraitPath(selectedEpisodeID: nil)
        XCTAssertEqual(state.portraitPath, [])

        state.openSource(.smart(.unprocessed))
        XCTAssertEqual(state.selectedSource, .smart(.unprocessed))
        XCTAssertEqual(state.portraitPath, [.episodes(.smart(.unprocessed))])

        state.openReader("episode-1")
        state.openReader("episode-1")
        XCTAssertEqual(state.portraitPath, [.episodes(.smart(.unprocessed)), .reader("episode-1")])

        state.selectSource(.group("Research"))
        state.openReader("episode-2")
        XCTAssertEqual(state.portraitPath, [.episodes(.group("Research")), .reader("episode-2")])

        state.pruneInvalidEpisodes(validEpisodeIDs: ["episode-2"])
        XCTAssertEqual(state.portraitPath, [.episodes(.group("Research")), .reader("episode-2")])

        state.pruneDeletedEpisode("episode-2")
        XCTAssertEqual(state.portraitPath, [.episodes(.group("Research"))])

        state.popPortraitRoute()
        XCTAssertEqual(state.portraitPath, [])
    }

    func testPortraitRouteRestoreKeepsNonLibrarySourceVisibleWithoutSelection() {
        var state = MobileNavigationRouteState(selectedSource: .subscriptions)

        state.restorePortraitPath(selectedEpisodeID: nil)

        XCTAssertEqual(state.portraitPath, [.episodes(.subscriptions)])
    }
}
