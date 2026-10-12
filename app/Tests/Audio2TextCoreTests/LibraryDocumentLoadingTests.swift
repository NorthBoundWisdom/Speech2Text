@testable import Audio2TextCore
import XCTest

final class LibraryDocumentLoadingTests: XCTestCase {
    func testDocumentContentsUsePreferredOrderAndSkipMissingOrBlankDocuments() throws {
        let root = URL(fileURLWithPath: NSTemporaryDirectory())
            .appendingPathComponent("Audio2TextCoreTests-\(UUID().uuidString)", isDirectory: true)
        defer { try? FileManager.default.removeItem(at: root) }
        let documentsRoot = root.appendingPathComponent("episodes/episode-1/documents", isDirectory: true)
        try FileManager.default.createDirectory(at: documentsRoot, withIntermediateDirectories: true)
        try "# Summary\n".write(to: documentsRoot.appendingPathComponent("summary.md"), atomically: true, encoding: .utf8)
        try "# Transcript\n".write(to: documentsRoot.appendingPathComponent("transcript.md"), atomically: true, encoding: .utf8)
        try "   \n".write(to: documentsRoot.appendingPathComponent("blank.md"), atomically: true, encoding: .utf8)
        try "notes\n".write(to: documentsRoot.appendingPathComponent("notes.md"), atomically: true, encoding: .utf8)
        let episode = LibraryEpisode(
            episodeID: "episode-1",
            title: "Episode",
            productStatus: LibraryConstants.productStatusAvailable,
            documents: [
                LibraryDocument(name: "transcript.md", path: "documents/transcript.md", bytes: 13),
                LibraryDocument(name: "summary.md", path: "documents/summary.md", bytes: 10),
                LibraryDocument(name: "blank.md", path: "documents/blank.md", bytes: 4),
                LibraryDocument(name: "missing.md", path: "documents/missing.md", bytes: 10),
                LibraryDocument(name: "notes.md", path: "documents/notes.md", bytes: 6),
            ]
        )

        let defaultDocuments = MobileLibraryStore.documentContents(for: episode, libraryRoot: root)
        let customDocuments = MobileLibraryStore.documentContents(
            for: episode,
            libraryRoot: root,
            preferredNames: ["blank.md", "missing.md", "notes.md"]
        )

        XCTAssertEqual(defaultDocuments.map(\.name), ["summary.md", "transcript.md"])
        XCTAssertEqual(defaultDocuments.map(\.title), ["Summary", "Transcript"])
        XCTAssertEqual(customDocuments, [MobileLibraryDocumentContent(name: "notes.md", title: "notes.md", text: "notes\n")])
        XCTAssertNil(MobileLibraryStore.documentText(for: episode, named: "blank.md", libraryRoot: root))
        XCTAssertNil(MobileLibraryStore.documentText(for: episode, named: "missing.md", libraryRoot: root))
    }
}
