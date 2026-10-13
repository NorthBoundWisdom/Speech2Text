import AppKit
import SwiftUI

struct MacLibraryWorkspace<SourceColumn: View, ListColumn: View, DetailColumn: View>: NSViewControllerRepresentable {
    @Binding var sourceCollapsed: Bool
    @Binding var listCollapsed: Bool
    var preferences: UserDefaults = .standard
    var statusContent: AnyView? = nil
    @ViewBuilder let sourceColumn: () -> SourceColumn
    @ViewBuilder let listColumn: () -> ListColumn
    @ViewBuilder let detailColumn: () -> DetailColumn

    func makeCoordinator() -> Coordinator {
        Coordinator(sourceCollapsed: $sourceCollapsed, listCollapsed: $listCollapsed)
    }

    func makeNSViewController(context: Context) -> LibrarySplitViewController {
        let controller = LibrarySplitViewController(
            source: AnyView(sourceColumn()), list: AnyView(listColumn()), detail: AnyView(detailColumn()),
            preferences: preferences
        )
        controller.statusContent = statusContent
        let coordinator = context.coordinator
        controller.onLayoutChange = { [weak coordinator, weak controller] in
            guard let controller else { return }
            coordinator?.synchronizeCollapseState(from: controller)
        }
        controller.applyCollapseState(source: sourceCollapsed, list: listCollapsed)
        return controller
    }

    func updateNSViewController(_ controller: LibrarySplitViewController, context: Context) {
        controller.statusContent = statusContent
        context.coordinator.sourceCollapsed = $sourceCollapsed
        context.coordinator.listCollapsed = $listCollapsed
        controller.updateContent(source: AnyView(sourceColumn()), list: AnyView(listColumn()), detail: AnyView(detailColumn()))
        controller.applyCollapseState(source: sourceCollapsed, list: listCollapsed)
    }

    func sizeThatFits(_ proposal: ProposedViewSize, nsViewController: LibrarySplitViewController, context: Context) -> CGSize? {
        proposal.replacingUnspecifiedDimensions(by: CGSize(width: 1320, height: 680))
    }

    final class Coordinator {
        var sourceCollapsed: Binding<Bool>
        var listCollapsed: Binding<Bool>
        private var synchronizationPending = false

        init(sourceCollapsed: Binding<Bool>, listCollapsed: Binding<Bool>) {
            self.sourceCollapsed = sourceCollapsed
            self.listCollapsed = listCollapsed
        }

        func synchronizeCollapseState(from controller: LibrarySplitViewController) {
            guard !synchronizationPending else { return }
            synchronizationPending = true
            // Native divider callbacks may arrive during a SwiftUI view update.
            DispatchQueue.main.async { [weak self, weak controller] in
                guard let self, let controller else { return }
                self.synchronizationPending = false
                let source = controller.splitViewItems[0].isCollapsed
                let list = controller.splitViewItems[1].isCollapsed
                if self.sourceCollapsed.wrappedValue != source { self.sourceCollapsed.wrappedValue = source }
                if self.listCollapsed.wrappedValue != list { self.listCollapsed.wrappedValue = list }
            }
        }
    }
}

final class LibrarySplitViewController: NSSplitViewController {
    static let sourceWidthKey = "sonafolio.workspace.sourceWidth"
    static let listWidthKey = "sonafolio.workspace.listWidth"
    static let sourceCollapsedKey = "sonafolio.workspace.sourceCollapsed"
    static let listCollapsedKey = "sonafolio.workspace.listCollapsed"

    let sourceHost: NSHostingController<AnyView>
    let listHost: NSHostingController<AnyView>
    let detailHost: NSHostingController<AnyView>
    var statusContent: AnyView? {
        didSet { windowToolbar?.updateStatusContent() }
    }
    var onLayoutChange: (() -> Void)?
    private let preferences: UserDefaults
    private var resizeObserver: NSObjectProtocol?
    private var windowToolbar: LibraryWindowToolbar?
    private var collapseObservers: [NSKeyValueObservation] = []
    private var hasPlacedColumns = false
    private var isApplyingLayout = false

    init(source: AnyView, list: AnyView, detail: AnyView, preferences: UserDefaults = .standard) {
        self.preferences = preferences
        sourceHost = NSHostingController(rootView: source)
        listHost = NSHostingController(rootView: list)
        detailHost = NSHostingController(rootView: detail)
        super.init(nibName: nil, bundle: nil)
    }

    required init?(coder: NSCoder) { fatalError("Use the programmatic initializer.") }

    override func viewDidLoad() {
        super.viewDidLoad()
        splitView.isVertical = true
        splitView.dividerStyle = .thin
        // Hosting content must adapt to the split item's bounds, rather than impose an intrinsic width.
        for host in [sourceHost, listHost, detailHost] { host.sizingOptions = [] }

        let source = NSSplitViewItem(sidebarWithViewController: sourceHost)
        source.minimumThickness = 180
        source.maximumThickness = 460
        source.holdingPriority = NSLayoutConstraint.Priority(260)
        source.canCollapse = true
        source.canCollapseFromWindowResize = false
        let list = NSSplitViewItem(contentListWithViewController: listHost)
        list.minimumThickness = 240
        list.maximumThickness = 700
        list.holdingPriority = NSLayoutConstraint.Priority(255)
        list.canCollapse = true
        list.canCollapseFromWindowResize = false
        let detail = NSSplitViewItem(viewController: detailHost)
        detail.minimumThickness = 320
        detail.holdingPriority = NSLayoutConstraint.Priority(250)
        addSplitViewItem(source)
        addSplitViewItem(list)
        addSplitViewItem(detail)
        collapseObservers = [source, list].map { item in
            item.observe(\.isCollapsed, options: [.new]) { [weak self] _, _ in self?.recordLayout() }
        }
        resizeObserver = NotificationCenter.default.addObserver(
            forName: NSSplitView.didResizeSubviewsNotification, object: splitView, queue: .main
        ) { [weak self] _ in self?.recordLayout() }
    }

    override func viewDidAppear() {
        super.viewDidAppear()
        guard let window = view.window else { return }
        let toolbar = windowToolbar ?? LibraryWindowToolbar(controller: self)
        windowToolbar = toolbar
        toolbar.install(on: window)
    }

    override func viewDidLayout() {
        super.viewDidLayout()
        guard !hasPlacedColumns, splitView.bounds.width >= 742 else { return }
        hasPlacedColumns = true
        isApplyingLayout = true
        let sourceWidth = preferredWidth(key: Self.sourceWidthKey, defaultValue: 270, range: 180...460)
        let listWidth = preferredWidth(key: Self.listWidthKey, defaultValue: 340, range: 240...700)
        if !splitViewItems[0].isCollapsed {
            splitView.setPosition(sourceWidth, ofDividerAt: 0)
            splitView.layoutSubtreeIfNeeded()
        }
        if !splitViewItems[1].isCollapsed {
            let origin = splitViewItems[0].isCollapsed ? 0 : columnFrame(at: 0).width + splitView.dividerThickness
            splitView.setPosition(origin + listWidth, ofDividerAt: 1)
        }
        isApplyingLayout = false
        recordLayout()
    }

    func updateContent(source: AnyView, list: AnyView, detail: AnyView) {
        sourceHost.rootView = source
        listHost.rootView = list
        detailHost.rootView = detail
    }

    func columnFrame(at index: Int) -> CGRect {
        // AppKit may wrap hosted content with sidebar material and safe-area insets.
        // Persist the pane allocation, not the smaller content controller's frame.
        splitView.arrangedSubviews[index].frame
    }

    func applyCollapseState(source: Bool, list: Bool) {
        _ = view
        guard splitViewItems[0].isCollapsed != source || splitViewItems[1].isCollapsed != list else { return }
        isApplyingLayout = true
        let sourceWidth = splitViewItems[0].isCollapsed
            ? preferredWidth(key: Self.sourceWidthKey, defaultValue: 270, range: 180...460)
            : columnFrame(at: 0).width
        let listWidth = splitViewItems[1].isCollapsed
            ? preferredWidth(key: Self.listWidthKey, defaultValue: 340, range: 240...700)
            : columnFrame(at: 1).width
        if splitViewItems[0].isCollapsed != source { splitViewItems[0].isCollapsed = source }
        if splitViewItems[1].isCollapsed != list { splitViewItems[1].isCollapsed = list }
        if hasPlacedColumns {
            splitView.layoutSubtreeIfNeeded()
            if !source {
                splitView.setPosition(sourceWidth, ofDividerAt: 0)
                splitView.layoutSubtreeIfNeeded()
            }
            if !list {
                let origin = source ? 0 : columnFrame(at: 0).width + splitView.dividerThickness
                splitView.setPosition(origin + listWidth, ofDividerAt: 1)
            }
        }
        isApplyingLayout = false
        recordLayout()
    }

    private func preferredWidth(key: String, defaultValue: CGFloat, range: ClosedRange<CGFloat>) -> CGFloat {
        guard let value = preferences.object(forKey: key) as? NSNumber, value.doubleValue.isFinite else { return defaultValue }
        return min(range.upperBound, max(range.lowerBound, CGFloat(value.doubleValue)))
    }

    private func recordLayout() {
        guard hasPlacedColumns, !isApplyingLayout else { return }
        for (index, key) in [(0, Self.sourceWidthKey), (1, Self.listWidthKey)] {
            let item = splitViewItems[index]
            let width = columnFrame(at: index).width
            if !item.isCollapsed, width >= item.minimumThickness {
                preferences.set(Double(width), forKey: key)
            }
        }
        preferences.set(splitViewItems[0].isCollapsed, forKey: Self.sourceCollapsedKey)
        preferences.set(splitViewItems[1].isCollapsed, forKey: Self.listCollapsedKey)
        windowToolbar?.updateState()
        onLayoutChange?()
    }

    deinit {
        if let resizeObserver { NotificationCenter.default.removeObserver(resizeObserver) }
    }
}
