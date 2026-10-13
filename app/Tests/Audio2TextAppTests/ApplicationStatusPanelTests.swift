import AppKit
import SwiftUI
import XCTest
import Vision
@testable import Audio2TextApp
import Audio2TextCore

final class ApplicationStatusPanelTests: XCTestCase {
    @MainActor
    func testSyncTitlesRemainFullyReadableAtMinimumSidebarWidth() throws {
        for state in [LibrarySyncStatus.State.synced, .syncing, .offline] {
            let title = state == .synced ? "Synced" : state == .syncing ? "Syncing" : "Offline"
            let status = LibrarySyncStatus(state: state, title: title,
                                           detail: "All library documents are available for reading.")
            let host = NSHostingView(rootView: LibrarySyncStatusCard(status: status, refresh: {}).frame(width: 154).environment(\.colorScheme, .light).background(Color.white))
            let window = NSWindow(contentRect: NSRect(x: -10000, y: -10000, width: 154, height: 240), styleMask: [.borderless], backing: .buffered, defer: false)
            window.appearance = NSAppearance(named: .aqua)
            window.isReleasedWhenClosed = false
            window.contentView = host
            window.orderFront(nil)
            RunLoop.main.run(until: Date().addingTimeInterval(0.05))
            defer { window.contentView = nil; window.close() }
            host.layoutSubtreeIfNeeded()
            XCTAssertLessThanOrEqual(host.fittingSize.width, 155)
            XCTAssertGreaterThan(host.fittingSize.height, 60)
            let text = try recognizedText(host)
            XCTAssertTrue(text.contains(title), "Sync title was clipped or unreadable: \(text)")
        }
    }

    @MainActor
    func testTaskCloudWarningAndSyncRemainVisibleTogether() throws {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: root) }
        try FileManager.default.createDirectory(at: root.appendingPathComponent("library"), withIntermediateDirectories: true)
        let settingsStore = AppSettingsStore(dataRoot: root, credentials: MemoryCloudCredentials())
        var settings = AppSettings()
        settings.libraryStorage = "local"
        settings.libraryLocalRoot = root.appendingPathComponent("library").path
        settings.workflowDefaultCloudSummary = true
        try settingsStore.save(settings, environment: [:])
        let store = AppStore(settingsStore: settingsStore, environment: ["ATOT_DATA_ROOT": root.path], runsStartupCloudPreflight: false)
        store.job.librarySyncStatus = LibrarySyncStatus(state: .synced, title: "Synced", detail: "All library documents are available.")
        store.job.processingTaskStatus = ProcessingTaskStatus(kind: .processing, title: "Process", itemTitle: "Sample episode", detail: "Transcribing locally", fraction: 0.4, state: .running)
        let host = NSHostingView(rootView: ProcessSidebarView(store: store, layoutMode: .statusOnly).frame(width: 360, height: 440).environment(\.colorScheme, .light).background(Color.white))
        let window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 360, height: 440), styleMask: [.borderless], backing: .buffered, defer: false)
        window.isReleasedWhenClosed = false
        window.setFrameOrigin(NSPoint(x: -10000, y: -10000))
        window.contentView = host
        window.orderFront(nil)
        RunLoop.main.run(until: Date().addingTimeInterval(0.05))
        defer { window.contentView = nil; window.close() }
        window.layoutIfNeeded()
        host.layoutSubtreeIfNeeded()
        let text = try recognizedText(host)
        XCTAssertTrue(text.contains("Library Sync"), "\(text)")
        XCTAssertTrue(text.contains("Configure an API key before cloud summary"), "\(text)")
        XCTAssertTrue(text.contains("Process"), "\(text)")
        if let directory = ProcessInfo.processInfo.environment["ATOT_STATUS_SNAPSHOT_DIR"] {
            let image = try XCTUnwrap(host.bitmapImageRepForCachingDisplay(in: host.bounds))
            host.cacheDisplay(in: host.bounds, to: image)
            let data = try XCTUnwrap(image.representation(using: .png, properties: [:]))
            let destination = URL(fileURLWithPath: directory, isDirectory: true)
            try FileManager.default.createDirectory(at: destination, withIntermediateDirectories: true)
            try data.write(to: destination.appendingPathComponent("application-status.png"))
        }
    }

    @MainActor
    private func recognizedText(_ view: NSView) throws -> String {
        let bitmap = try XCTUnwrap(view.bitmapImageRepForCachingDisplay(in: view.bounds))
        view.cacheDisplay(in: view.bounds, to: bitmap)
        let image = try XCTUnwrap(bitmap.cgImage)
        let request = VNRecognizeTextRequest()
        request.recognitionLevel = .accurate
        request.recognitionLanguages = ["en-US"]
        try VNImageRequestHandler(cgImage: image).perform([request])
        return (request.results ?? []).compactMap { $0.topCandidates(1).first?.string }.joined(separator: "\n")
    }
}
