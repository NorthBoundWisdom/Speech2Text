import SwiftUI
#if canImport(Audio2TextCore)
    import Audio2TextCore
#endif

enum ProcessSidebarLayoutMode {
    case combined
    case sourcesOnly
    case itemsOnly
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

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            switch layoutMode {
            case .combined:
                processingProgressHeader
                processList
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            case .sourcesOnly:
                processingProgressHeader
                sourceList
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
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
        .alert("重新处理？", isPresented: reprocessConfirmationBinding, presenting: pendingReprocessItem) { item in
            Button("取消", role: .cancel) {
                pendingReprocessItem = nil
            }
            Button(pendingReprocessWorkflow.actionTitle(reprocess: true, isCloudConfigured: controller.isCloudSummaryConfigured), role: .destructive) {
                if !controller.stage.isRunning {
                    controller.processLibraryItem(item, reprocess: true, workflow: pendingReprocessWorkflow)
                }
                pendingReprocessItem = nil
            }
        } message: { item in
            let scope = pendingReprocessWorkflow == .localOnly ? "转写和 QA 结果" : "转写、QA 和摘要结果"
            Text("这会清理并重新生成“\(item.title)”的\(scope)。")
        }
        .alert("删除条目？", isPresented: deleteConfirmationBinding, presenting: pendingDeleteItem) { item in
            Button("取消", role: .cancel) {
                pendingDeleteItem = nil
            }
            Button("删除", role: .destructive) {
                controller.deleteLibraryItem(item)
                pendingDeleteItem = nil
            }
        } message: { item in
            Text("这会删除“\(item.title)”的缓存文件和输出结果；订阅来源的条目后续刷新不会重新出现。")
        }
        .alert("删除所选条目？", isPresented: bulkDeleteConfirmationBinding) {
            Button("取消", role: .cancel) {
                pendingBulkDeleteItems = []
            }
            Button("删除 \(pendingBulkDeleteItems.count) 个", role: .destructive) {
                controller.deleteLibraryItems(pendingBulkDeleteItems)
                clearItemSelection()
                pendingBulkDeleteItems = []
            }
        } message: {
            Text("这会删除所选条目的缓存文件和输出结果；订阅来源的条目后续刷新不会重新出现。")
        }
        .alert("删除分组？", isPresented: deleteGroupConfirmationBinding, presenting: pendingDeleteGroupName) { groupName in
            Button("取消", role: .cancel) {
                pendingDeleteGroupName = nil
            }
            Button("删除分组", role: .destructive) {
                controller.deleteGroup(groupName)
                pendingDeleteGroupName = nil
            }
        } message: { groupName in
            Text("这只会删除“\(groupName)”分组标签；该分组下的内容会移动回 \(ProcessLibrary.defaultGroupName)，不会删除节目或文件。")
        }
        .sheet(item: $presentedProcessingReport) { report in
            ProcessingReportDialog(report: report)
                .frame(width: 640, height: 520)
        }
    }
}
