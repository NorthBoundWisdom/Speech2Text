import AppKit
import SwiftUI

@MainActor
final class LibraryWindowToolbar: NSObject, NSToolbarDelegate {
    static let columnsIdentifier = NSToolbarItem.Identifier("SonaFolio.LibraryColumns")
    static let statusIdentifier = NSToolbarItem.Identifier("SonaFolio.ApplicationStatus")
    static let titleIdentifier = NSToolbarItem.Identifier("SonaFolio.LibraryTitle")
    private weak var controller: LibrarySplitViewController?
    let toolbar = NSToolbar(identifier: "SonaFolio.LibraryWindow")
    private let statusPopover = NSPopover()
    private var statusHost: NSHostingController<AnyView>?
    private let columns = NSToolbarItemGroup(itemIdentifier: columnsIdentifier)

    init(controller: LibrarySplitViewController) {
        self.controller = controller
        super.init()
        toolbar.delegate = self
        toolbar.displayMode = .iconOnly
        toolbar.allowsUserCustomization = false
        toolbar.autosavesConfiguration = false
        columns.label = "Columns"
        columns.controlRepresentation = .expanded

        let sources = NSToolbarItem(itemIdentifier: .init("SonaFolio.ToggleSources"))
        sources.image = NSImage(systemSymbolName: "sidebar.left", accessibilityDescription: "Sources")
        sources.target = self
        sources.action = #selector(toggleSources(_:))
        let list = NSToolbarItem(itemIdentifier: .init("SonaFolio.ToggleEpisodeList"))
        list.image = NSImage(systemSymbolName: "list.bullet", accessibilityDescription: "Episode List")
        list.target = self
        list.action = #selector(toggleList(_:))
        columns.subitems = [sources, list]
        updateState()
    }

    func updateStatusContent() {
        guard let content = controller?.statusContent else { return }
        if let statusHost {
            statusHost.rootView = content
        } else {
            let host = NSHostingController(rootView: content)
            statusHost = host
            statusPopover.contentViewController = host
            statusPopover.behavior = .transient
            statusPopover.contentSize = NSSize(width: 360, height: 440)
        }
    }

    @objc func showStatus(_ sender: Any?) {
        updateStatusContent()
        guard let item = toolbar.items.first(where: { $0.itemIdentifier == Self.statusIdentifier }),
              let anchor = item.view else { return }
        if statusPopover.isShown { statusPopover.performClose(sender) }
        else { statusPopover.show(relativeTo: anchor.bounds, of: anchor, preferredEdge: .minY) }
    }

    func install(on window: NSWindow) {
        // No tracking separator: the controls belong beside the window buttons, not after the sidebar.
        window.toolbarStyle = .unifiedCompact
        window.titleVisibility = .hidden
        window.toolbar = toolbar
        updateState()
    }

    func updateState() {
        guard let controller, controller.isViewLoaded else { return }
        let sourcesTitle = controller.splitViewItems[0].isCollapsed ? "Show Sources" : "Hide Sources"
        let listTitle = controller.splitViewItems[1].isCollapsed ? "Show Episode List" : "Hide Episode List"
        columns.subitems[0].label = sourcesTitle
        columns.subitems[0].toolTip = "\(sourcesTitle) (Control-Command-S)"
        columns.subitems[1].label = listTitle
        columns.subitems[1].toolTip = "\(listTitle) (Control-Command-L)"
    }

    @objc func toggleSources(_ sender: Any?) {
        guard let controller else { return }
        controller.applyCollapseState(source: !controller.splitViewItems[0].isCollapsed, list: controller.splitViewItems[1].isCollapsed)
        updateState()
    }

    @objc func toggleList(_ sender: Any?) {
        guard let controller else { return }
        controller.applyCollapseState(source: controller.splitViewItems[0].isCollapsed, list: !controller.splitViewItems[1].isCollapsed)
        updateState()
    }

    func toolbarDefaultItemIdentifiers(_ toolbar: NSToolbar) -> [NSToolbarItem.Identifier] {
        [Self.columnsIdentifier, Self.titleIdentifier] + (controller?.statusContent == nil ? [] : [Self.statusIdentifier]) + [.flexibleSpace]
    }

    func toolbarAllowedItemIdentifiers(_ toolbar: NSToolbar) -> [NSToolbarItem.Identifier] {
        toolbarDefaultItemIdentifiers(toolbar)
    }

    func toolbar(_ toolbar: NSToolbar, itemForItemIdentifier identifier: NSToolbarItem.Identifier, willBeInsertedIntoToolbar flag: Bool) -> NSToolbarItem? {
        if identifier == Self.columnsIdentifier { return columns }
        if identifier == Self.statusIdentifier {
            let item = NSToolbarItem(itemIdentifier: identifier)
            item.label = "Application Status"
            item.toolTip = "View processing, sync, and cloud status"
            let button = NSButton(title: "Status", target: self, action: #selector(showStatus(_:)))
            button.image = NSImage(systemSymbolName: "info.circle", accessibilityDescription: "Application Status")
            button.imagePosition = .imageOnly
            button.bezelStyle = .texturedRounded
            button.setAccessibilityLabel("Application Status")
            item.view = button
            return item
        }
        if identifier == Self.titleIdentifier {
            let item = NSToolbarItem(itemIdentifier: identifier)
            item.label = "SonaFolio"
            let title = NSTextField(labelWithString: "SonaFolio")
            title.font = .systemFont(ofSize: NSFont.systemFontSize, weight: .semibold)
            item.view = title
            return item
        }
        return nil
    }
}
