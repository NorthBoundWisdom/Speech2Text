@testable import Audio2TextApp
import AppKit
import SwiftUI
import XCTest

final class MacLibrarySplitViewTests: XCTestCase {
    @MainActor
    func testCompactToolbarUsesTheLeadingAreaAndKeepsBothCollapseActions() throws {
        let fixture = try WorkspaceFixture(usesTitlebar: true)
        defer { fixture.close() }
        let owner = LibraryWindowToolbar(controller: fixture.controller)
        owner.install(on: fixture.window)
        fixture.settle()
        XCTAssertEqual(fixture.window.toolbarStyle, .unifiedCompact)
        XCTAssertEqual(fixture.window.titleVisibility, .hidden)
        XCTAssertEqual(owner.toolbar.items.first?.itemIdentifier, LibraryWindowToolbar.columnsIdentifier)
        XCTAssertFalse(owner.toolbar.items.contains { $0.itemIdentifier == .sidebarTrackingSeparator })
        let title = try XCTUnwrap(owner.toolbar.items.first { $0.itemIdentifier == LibraryWindowToolbar.titleIdentifier }?.view)
        fixture.window.contentView?.superview?.layoutSubtreeIfNeeded()
        let titleFrame = title.convert(title.bounds, to: nil)
        XCTAssertLessThan(titleFrame.maxX, 320, "Controls and title must occupy the leading window area.")
        if let snapshotDirectory = ProcessInfo.processInfo.environment["ATOT_LAYOUT_SNAPSHOT_DIR"] {
            let frame = try XCTUnwrap(fixture.window.contentView?.superview)
            let bitmap = try XCTUnwrap(frame.bitmapImageRepForCachingDisplay(in: frame.bounds))
            frame.cacheDisplay(in: frame.bounds, to: bitmap)
            let png = try XCTUnwrap(bitmap.representation(using: .png, properties: [:]))
            let directory = URL(fileURLWithPath: snapshotDirectory, isDirectory: true)
            try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
            try png.write(to: directory.appendingPathComponent("compact-library-toolbar.png"))
        }
        let group = try XCTUnwrap(owner.toolbar.items.first as? NSToolbarItemGroup)
        XCTAssertEqual(group.subitems.count, 2)
        owner.toggleSources(nil)
        fixture.settle()
        XCTAssertTrue(fixture.controller.splitViewItems[0].isCollapsed)
        XCTAssertEqual(group.subitems[0].label, "Show Sources")
        owner.toggleList(nil)
        fixture.settle()
        XCTAssertTrue(fixture.controller.splitViewItems[1].isCollapsed)
        XCTAssertEqual(group.subitems[1].label, "Show Episode List")
        XCTAssertNotNil(fixture.window.toolbar)
    }

    @MainActor
    func testSwiftUIBridgeFillsTheWindowInsteadOfUsingItsIntrinsicMinimum() throws {
        let fixture = try WorkspaceFixture()
        defer { fixture.close() }
        let workspace = MacLibraryWorkspace(
            sourceCollapsed: .constant(false), listCollapsed: .constant(false), preferences: fixture.preferences
        ) {
            Text("Sources")
        } listColumn: {
            Text("Episodes")
        } detailColumn: {
            Text("Reader")
        }
        let hosting = NSHostingView(rootView: workspace)
        fixture.window.contentViewController = nil
        fixture.window.contentView = hosting
        fixture.window.setContentSize(NSSize(width: 980, height: 680))
        for _ in 0..<20 {
            hosting.layoutSubtreeIfNeeded()
            RunLoop.main.run(until: Date().addingTimeInterval(0.01))
        }
        func findSplit(in view: NSView) -> NSSplitView? {
            if let split = view as? NSSplitView { return split }
            return view.subviews.lazy.compactMap { findSplit(in: $0) }.first
        }
        let split = try XCTUnwrap(findSplit(in: hosting))
        XCTAssertEqual(split.bounds.width, 980, accuracy: 2)
        XCTAssertEqual(split.bounds.height, 680, accuracy: 2)
    }

    @MainActor
    func testNativeDividersResizeBothColumnsAndSaveExpandedWidths() throws {
        let fixture = try WorkspaceFixture()
        defer { fixture.close() }
        let controller = fixture.controller
        let split = controller.splitView
        XCTAssertEqual(controller.columnFrame(at: 0).width, 270, accuracy: 2)
        XCTAssertEqual(controller.columnFrame(at: 1).width, 340, accuracy: 2)
        split.setPosition(320, ofDividerAt: 0)
        fixture.settle()
        split.setPosition(320 + split.dividerThickness + 410, ofDividerAt: 1)
        fixture.settle()
        XCTAssertEqual(controller.columnFrame(at: 0).width, 320, accuracy: 2)
        XCTAssertEqual(controller.columnFrame(at: 1).width, 410, accuracy: 2)
        XCTAssertEqual(fixture.preferences.double(forKey: LibrarySplitViewController.sourceWidthKey), 320, accuracy: 2)
        XCTAssertEqual(fixture.preferences.double(forKey: LibrarySplitViewController.listWidthKey), 410, accuracy: 2)
        XCTAssertGreaterThanOrEqual(controller.columnFrame(at: 2).width, 320)
    }

    @MainActor
    func testBothColumnsCanCollapseAndRestoreTheirPreviousWidths() throws {
        let fixture = try WorkspaceFixture()
        defer { fixture.close() }
        let controller = fixture.controller
        controller.splitView.setPosition(310, ofDividerAt: 0)
        controller.splitView.setPosition(310 + controller.splitView.dividerThickness + 380, ofDividerAt: 1)
        fixture.settle()
        controller.applyCollapseState(source: true, list: false)
        fixture.settle()
        XCTAssertTrue(controller.splitViewItems[0].isCollapsed)
        controller.applyCollapseState(source: true, list: true)
        fixture.settle()
        XCTAssertTrue(controller.splitViewItems[1].isCollapsed)
        XCTAssertEqual(controller.columnFrame(at: 2).width, controller.splitView.bounds.width, accuracy: 2)
        controller.applyCollapseState(source: false, list: false)
        fixture.settle()
        XCTAssertEqual(controller.columnFrame(at: 0).width, 310, accuracy: 2)
        XCTAssertEqual(controller.columnFrame(at: 1).width, 380, accuracy: 2)
    }

    @MainActor
    func testSavedWidthsRestoreWithInitiallyCollapsedSources() throws {
        let fixture = try WorkspaceFixture(sourceWidth: 325, listWidth: 390, sourceCollapsed: true)
        defer { fixture.close() }
        XCTAssertTrue(fixture.controller.splitViewItems[0].isCollapsed)
        fixture.controller.applyCollapseState(source: false, list: false)
        fixture.settle()
        XCTAssertEqual(fixture.controller.columnFrame(at: 0).width, 325, accuracy: 2)
        XCTAssertEqual(fixture.controller.columnFrame(at: 1).width, 390, accuracy: 2)
    }

    @MainActor
    func testNativeCollapseUpdatesThePreferenceUsedByToolbarControls() throws {
        let fixture = try WorkspaceFixture()
        defer { fixture.close() }
        fixture.controller.splitViewItems[0].isCollapsed = true
        fixture.settle()
        XCTAssertTrue(fixture.preferences.bool(forKey: LibrarySplitViewController.sourceCollapsedKey))
        XCTAssertEqual(fixture.preferences.double(forKey: LibrarySplitViewController.sourceWidthKey), 270, accuracy: 2)
    }

    @MainActor
    func testWindowShrinkKeepsTheReaderWithinBounds() throws {
        let fixture = try WorkspaceFixture(sourceWidth: 420, listWidth: 500)
        defer { fixture.close() }
        fixture.window.setContentSize(NSSize(width: 980, height: 680))
        fixture.settle()
        let controller = fixture.controller
        XCTAssertGreaterThanOrEqual(controller.columnFrame(at: 0).width, 180)
        XCTAssertGreaterThanOrEqual(controller.columnFrame(at: 1).width, 240)
        XCTAssertGreaterThanOrEqual(controller.columnFrame(at: 2).width, 320)
        XCTAssertLessThanOrEqual(controller.columnFrame(at: 2).maxX, controller.splitView.bounds.width + 1)
    }
}

@MainActor
private final class WorkspaceFixture {
    let suite = "SonaFolio-WorkspaceTests-\(UUID().uuidString)"
    let preferences: UserDefaults
    let controller: LibrarySplitViewController
    let window: NSWindow

    init(sourceWidth: Double = 270, listWidth: Double = 340, sourceCollapsed: Bool = false, usesTitlebar: Bool = false) throws {
        preferences = try XCTUnwrap(UserDefaults(suiteName: suite))
        preferences.set(sourceWidth, forKey: LibrarySplitViewController.sourceWidthKey)
        preferences.set(listWidth, forKey: LibrarySplitViewController.listWidthKey)
        controller = LibrarySplitViewController(
            source: AnyView(Text("Sources").frame(maxWidth: .infinity, maxHeight: .infinity)),
            list: AnyView(Text("Episodes").frame(maxWidth: .infinity, maxHeight: .infinity)),
            detail: AnyView(Text("Reader").frame(maxWidth: .infinity, maxHeight: .infinity)),
            preferences: preferences
        )
        controller.applyCollapseState(source: sourceCollapsed, list: false)
        window = NSWindow(
            contentRect: NSRect(x: 0, y: 0, width: 1320, height: 680),
            styleMask: usesTitlebar ? [.titled, .closable, .miniaturizable, .resizable] : [.borderless],
            backing: .buffered, defer: false
        )
        window.title = "SonaFolio"
        window.contentViewController = controller
        // Assigning a content controller adopts its initial minimum size; restore our test viewport.
        window.setContentSize(NSSize(width: 1320, height: 680))
        settle()
    }

    func settle() {
        let deadline = Date().addingTimeInterval(0.15)
        while Date() < deadline {
            controller.view.layoutSubtreeIfNeeded()
            controller.viewDidLayout()
            controller.view.layoutSubtreeIfNeeded()
            RunLoop.main.run(until: Date().addingTimeInterval(0.01))
        }
    }

    func close() {
        window.contentViewController = nil
        preferences.removePersistentDomain(forName: suite)
    }
}
