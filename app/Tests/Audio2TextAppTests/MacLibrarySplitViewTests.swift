@testable import Audio2TextApp
import AppKit
import SwiftUI
import XCTest

final class MacLibrarySplitViewTests: XCTestCase {
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
        XCTAssertEqual(controller.sourceHost.view.frame.width, 270, accuracy: 2)
        XCTAssertEqual(controller.listHost.view.frame.width, 340, accuracy: 2)
        split.setPosition(320, ofDividerAt: 0)
        fixture.settle()
        split.setPosition(320 + split.dividerThickness + 410, ofDividerAt: 1)
        fixture.settle()
        XCTAssertEqual(controller.sourceHost.view.frame.width, 320, accuracy: 2)
        XCTAssertEqual(controller.listHost.view.frame.width, 410, accuracy: 2)
        XCTAssertEqual(fixture.preferences.double(forKey: LibrarySplitViewController.sourceWidthKey), 320, accuracy: 2)
        XCTAssertEqual(fixture.preferences.double(forKey: LibrarySplitViewController.listWidthKey), 410, accuracy: 2)
        XCTAssertGreaterThanOrEqual(controller.detailHost.view.frame.width, 320)
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
        XCTAssertEqual(controller.detailHost.view.frame.width, controller.splitView.bounds.width, accuracy: 2)
        controller.applyCollapseState(source: false, list: false)
        fixture.settle()
        XCTAssertEqual(controller.sourceHost.view.frame.width, 310, accuracy: 2)
        XCTAssertEqual(controller.listHost.view.frame.width, 380, accuracy: 2)
    }

    @MainActor
    func testSavedWidthsRestoreWithInitiallyCollapsedSources() throws {
        let fixture = try WorkspaceFixture(sourceWidth: 325, listWidth: 390, sourceCollapsed: true)
        defer { fixture.close() }
        XCTAssertTrue(fixture.controller.splitViewItems[0].isCollapsed)
        fixture.controller.applyCollapseState(source: false, list: false)
        fixture.settle()
        XCTAssertEqual(fixture.controller.sourceHost.view.frame.width, 325, accuracy: 2)
        XCTAssertEqual(fixture.controller.listHost.view.frame.width, 390, accuracy: 2)
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
        XCTAssertGreaterThanOrEqual(controller.sourceHost.view.frame.width, 180)
        XCTAssertGreaterThanOrEqual(controller.listHost.view.frame.width, 240)
        XCTAssertGreaterThanOrEqual(controller.detailHost.view.frame.width, 320)
        XCTAssertLessThanOrEqual(controller.detailHost.view.frame.maxX, controller.splitView.bounds.width + 1)
    }
}

@MainActor
private final class WorkspaceFixture {
    let suite = "SonaFolio-WorkspaceTests-\(UUID().uuidString)"
    let preferences: UserDefaults
    let controller: LibrarySplitViewController
    let window: NSWindow

    init(sourceWidth: Double = 270, listWidth: Double = 340, sourceCollapsed: Bool = false) throws {
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
            styleMask: [.borderless], backing: .buffered, defer: false
        )
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
