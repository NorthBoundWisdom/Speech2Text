import SwiftUI
#if canImport(Audio2TextCore)
    import Audio2TextCore
#endif

enum ProcessSidebarLayoutMode {
    case combined
    case sourcesOnly
    case itemsOnly
    case statusOnly
}

struct ProcessSidebarView: View {
    static let libraryListAnimation = Animation.easeInOut(duration: 0.22)
    static var libraryItemTransition: AnyTransition {
        .asymmetric(
            insertion: .move(edge: .top).combined(with: .opacity),
            removal: .move(edge: .top).combined(with: .opacity)
        )
    }

    @ObservedObject var store: AppStore
    var layoutMode: ProcessSidebarLayoutMode = .combined
    @State var pendingReprocessItem: ProcessLibraryItem?
    @State var pendingReprocessWorkflow: ProcessingWorkflow = .localOnly
    @State var pendingDeleteItem: ProcessLibraryItem?
    @State var pendingBulkDeleteItems: [ProcessLibraryItem] = []
    @State var pendingDeleteGroupName: String?
    @State var selectedItemIDs: Set<String> = []
    @State var lastSelectedItemID: String?
    @State var renamingGroupID: String?
    @State var renamingGroupName = ""
    @State var newGroupName = ""
    @State var presentedProcessingReport: ProcessingReport?
    @State private var statusContentHeight: CGFloat = 96

    var controller: JobController {
        store.job
    }

    enum SidebarMetrics {
        static let sectionSpacing: CGFloat = 10
        static let rowSpacing: CGFloat = 2
        static let sourceRowHeight: CGFloat = 30
        static let itemRowHeight: CGFloat = 28
        static let sourceIconSize: CGFloat = 19
        static let sourceIconFrame: CGFloat = 22
        static let rowCornerRadius: CGFloat = 7
        static let rowHorizontalPadding: CGFloat = 8
        static let titleFontSize: CGFloat = 14
        static let countFontSize: CGFloat = 12
        static let headerFontSize: CGFloat = 12
    }

    private var boundedStatusPanel: some View {
        ScrollView {
            processingProgressHeader
                .background(GeometryReader { geometry in
                    Color.clear.preference(key: StatusContentHeightKey.self, value: geometry.size.height)
                })
        }
        .frame(height: min(statusContentHeight, 260))
        .onPreferenceChange(StatusContentHeightKey.self) { height in
            if abs(statusContentHeight - height) > 0.5 { statusContentHeight = height }
        }
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            switch layoutMode {
            case .combined:
                boundedStatusPanel
                processList
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            case .sourcesOnly:
                boundedStatusPanel
                sourceList
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            case .statusOnly:
                ScrollView {
                    processingProgressHeader
                }
            case .itemsOnly:
                itemList
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            }
            Spacer()
        }
        .padding(.leading, 10)
        .padding(.trailing, 4)
        .padding(.top, 10)
        .padding(.bottom, 14)
        .onChange(of: controller.selectedSidebarSource) { _ in
            clearItemSelection()
        }
        .onChange(of: controller.visibleLibraryItems.map(\.id)) { visibleIDs in
            reconcileItemSelection(visibleIDs: Set(visibleIDs))
        }
        .onChange(of: store.isNewGroupPanelPresented) { isPresented in
            if isPresented {
                newGroupName = ""
            }
        }
        .alert("Reprocess?", isPresented: reprocessConfirmationBinding, presenting: pendingReprocessItem) { item in
            Button("Cancel", role: .cancel) {
                pendingReprocessItem = nil
            }
            Button(pendingReprocessWorkflow.actionTitle(reprocess: true, isCloudConfigured: controller.isCloudSummaryConfigured), role: .destructive) {
                if !controller.stage.isRunning {
                    controller.processLibraryItem(item, reprocess: true, workflow: pendingReprocessWorkflow)
                }
                pendingReprocessItem = nil
            }
        } message: { item in
            let scope = pendingReprocessWorkflow == .localOnly ? "transcript and QA results" : "transcript, QA, and summary results"
            Text("This clears and regenerates the \(scope) for \(item.title).")
        }
        .alert("Delete item?", isPresented: deleteConfirmationBinding, presenting: pendingDeleteItem) { item in
            Button("Cancel", role: .cancel) {
                pendingDeleteItem = nil
            }
            Button("Delete", role: .destructive) {
                controller.deleteLibraryItem(item)
                pendingDeleteItem = nil
            }
        } message: { item in
            Text("This deletes cached files and outputs for \(item.title). Subscription items will not reappear after refresh.")
        }
        .alert("Delete selected items?", isPresented: bulkDeleteConfirmationBinding) {
            Button("Cancel", role: .cancel) {
                pendingBulkDeleteItems = []
            }
            Button("Delete \(pendingBulkDeleteItems.count) items", role: .destructive) {
                controller.deleteLibraryItems(pendingBulkDeleteItems)
                clearItemSelection()
                pendingBulkDeleteItems = []
            }
        } message: {
            Text("This deletes the selected items' cached files and outputs. Subscription items will not reappear after refresh.")
        }
        .alert("Delete group?", isPresented: deleteGroupConfirmationBinding, presenting: pendingDeleteGroupName) { groupName in
            Button("Cancel", role: .cancel) {
                pendingDeleteGroupName = nil
            }
            Button("Delete group", role: .destructive) {
                controller.deleteGroup(groupName)
                pendingDeleteGroupName = nil
            }
        } message: { groupName in
            Text("This removes the \(groupName) label and moves its items to \(ProcessLibrary.defaultGroupName). Episodes and files are preserved.")
        }
        .sheet(item: $presentedProcessingReport) { report in
            ProcessingReportDialog(report: report)
                .frame(width: 640, height: 520)
        }
    }
}


private struct StatusContentHeightKey: PreferenceKey {
    static var defaultValue: CGFloat = 96
    static func reduce(value: inout CGFloat, nextValue: () -> CGFloat) { value = nextValue() }
}
