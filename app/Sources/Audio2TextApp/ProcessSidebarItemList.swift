import AppKit
import SwiftUI
#if canImport(Audio2TextCore)
    import Audio2TextCore
#endif

extension ProcessSidebarView {
    var itemList: some View {
        VStack(alignment: .leading, spacing: 0) {
            itemListHeader
                .padding(.top, 4)
                .padding(.trailing, 12)

            ScrollView {
                LazyVStack(alignment: .leading, spacing: SidebarMetrics.rowSpacing) {
                    itemListRows
                }
                .padding(.top, SidebarMetrics.rowSpacing)
                .padding(.trailing, 12)
                .animation(Self.libraryListAnimation, value: itemListAnimationIDs)
            }
            .overlay {
                if controller.visibleLibraryItems.isEmpty && !isShowingSubscriptions {
                    Text("No items")
                        .foregroundStyle(.secondary)
                }
            }
        }
    }

    @ViewBuilder
    var itemListHeader: some View {
        if isShowingSubscriptions {
            subscriptionsHeader
        } else {
            itemsHeader
        }
    }

    @ViewBuilder
    var itemListRows: some View {
        if isShowingSubscriptions {
            subscriptionsRows
        } else {
            itemsRows
        }
    }

    var itemsSection: some View {
        VStack(alignment: .leading, spacing: SidebarMetrics.rowSpacing) {
            itemsHeader
            itemsRows
        }
    }

    var itemsHeader: some View {
        HStack(spacing: 8) {
            sidebarHeader(itemsSectionTitle)
            Spacer()
            if isShowingUnprocessedItems {
                unprocessedFilterMenu
            }
            if showsReadFilterToggle {
                readFilterToggle
            }
        }
    }

    @ViewBuilder
    var itemsRows: some View {
        if controller.visibleLibraryItems.isEmpty {
            Text("No items")
                .font(.system(size: SidebarMetrics.countFontSize, weight: .regular))
                .foregroundStyle(.secondary)
                .padding(.leading, 26)
                .frame(height: SidebarMetrics.itemRowHeight)
        } else {
            ForEach(controller.visibleLibraryItems) { item in
                processItemRow(item)
            }
        }
    }

    var itemListAnimationIDs: [String] {
        isShowingSubscriptions
            ? controller.subscriptions.map(\.id)
            : controller.visibleLibraryItems.map(\.id)
    }

    var unprocessedFilterMenu: some View {
        Menu {
            Button {
                controller.setUnprocessedQueueFilter(nil)
            } label: {
                Label("全部状态", systemImage: controller.unprocessedQueueFilter == nil ? "checkmark" : "line.3.horizontal.decrease.circle")
            }

            Divider()

            ForEach(AppQueueStatus.allCases) { status in
                Button {
                    controller.setUnprocessedQueueFilter(status)
                } label: {
                    Label(
                        "\(status.compactTitle) (\(controller.unprocessedQueueFilterCount(for: status)))",
                        systemImage: controller.unprocessedQueueFilter == status ? "checkmark" : queueStatusIcon(for: status)
                    )
                }
            }
        } label: {
            Image(systemName: controller.unprocessedQueueFilter == nil ? "line.3.horizontal.decrease.circle" : "line.3.horizontal.decrease.circle.fill")
                .font(.system(size: 12, weight: .medium))
                .frame(width: 22, height: 20)
        }
        .menuStyle(.borderlessButton)
        .fixedSize()
        .foregroundStyle(controller.unprocessedQueueFilter == nil ? Color.secondary : Color.accentColor)
        .help(unprocessedFilterHelp)
        .padding(.trailing, 6)
    }

    var readFilterToggle: some View {
        Button {
            withAnimation(Self.libraryListAnimation) {
                controller.setHidesReadLibraryItems(!controller.hidesReadLibraryItems)
            }
        } label: {
            Image(systemName: readFilterSystemName)
                .font(.system(size: 13, weight: .medium))
                .frame(width: 22, height: 20)
                .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .foregroundStyle(controller.hidesReadLibraryItems ? Color.accentColor : Color.secondary)
        .help(controller.hidesReadLibraryItems ? "显示已读" : "隐藏已读")
        .accessibilityLabel(controller.hidesReadLibraryItems ? "显示已读" : "隐藏已读")
        .fixedSize()
        .padding(.trailing, 6)
    }

    var readFilterSystemName: String {
        controller.hidesReadLibraryItems ? "line.3.horizontal.decrease.circle.fill" : "line.3.horizontal.decrease.circle"
    }

    var readFilterBinding: Binding<Bool> {
        Binding(
            get: { controller.hidesReadLibraryItems },
            set: { hidesReadItems in
                withAnimation(Self.libraryListAnimation) {
                    controller.setHidesReadLibraryItems(hidesReadItems)
                }
            }
        )
    }

    var unprocessedFilterHelp: String {
        if let status = controller.unprocessedQueueFilter {
            return "过滤：\(status.compactTitle)"
        }
        return "按标记状态过滤"
    }

    var isShowingUnprocessedItems: Bool {
        if case .smart(.unprocessed) = controller.selectedSidebarSource {
            return true
        }
        return false
    }

    var showsReadFilterToggle: Bool {
        LibrarySidebarState.canFilterReadItems(for: controller.selectedSidebarSource)
    }

    var itemsSectionTitle: String {
        switch controller.selectedSidebarSource {
        case .library:
            return "Library"
        case let .smart(feed):
            return feed.title
        case let .group(groupName):
            return groupName
        case .subscriptions:
            return "Subscriptions"
        }
    }

    var isShowingSubscriptions: Bool {
        if case .subscriptions = controller.selectedSidebarSource {
            return true
        }
        return false
    }

    func queueStatusFlagIcon(for status: AppQueueStatus) -> String {
        switch status {
        case .unread:
            return "circle"
        case .toProcess:
            return "play.fill"
        case .processLater:
            return "clock.fill"
        case .delete:
            return "trash.fill"
        }
    }

    func queueStatusIcon(for status: AppQueueStatus) -> String {
        switch status {
        case .unread:
            return "circle"
        case .toProcess:
            return "play.circle"
        case .processLater:
            return "clock"
        case .delete:
            return "trash"
        }
    }

    func queueStatusColor(for status: AppQueueStatus) -> Color {
        switch status {
        case .unread:
            return .secondary
        case .toProcess:
            return .blue
        case .processLater:
            return .orange
        case .delete:
            return .red
        }
    }

    @ViewBuilder
    func queueStatusFlag(for item: ProcessLibraryItem) -> some View {
        if !item.isProcessed {
            Image(systemName: queueStatusFlagIcon(for: item.queueStatus))
                .font(.system(size: 11, weight: .semibold))
                .foregroundStyle(queueStatusColor(for: item.queueStatus))
                .frame(width: 16, height: SidebarMetrics.itemRowHeight)
                .help(item.queueStatus.compactTitle)
                .accessibilityLabel(item.queueStatus.compactTitle)
        }
    }

    @ViewBuilder
    func itemLeadingIndicator(for item: ProcessLibraryItem) -> some View {
        if item.isProcessed {
            ProcessedItemContentIcon(hasTranscript: item.hasTranscript, hasFile: item.hasFile)
        } else {
            queueStatusFlag(for: item)
        }
    }

    func processItemRow(_ item: ProcessLibraryItem) -> some View {
        Button {
            selectProcessItemRow(item)
        } label: {
            HStack(alignment: .center, spacing: 6) {
                itemLeadingIndicator(for: item)
                Text(item.title)
                    .lineLimit(1)
                    .truncationMode(.tail)
                Spacer(minLength: 4)
                if item.isStarred {
                    Image(systemName: "star.fill")
                        .font(.caption)
                        .foregroundStyle(.yellow)
                        .accessibilityLabel("Starred")
                }
            }
            .font(.system(size: SidebarMetrics.titleFontSize, weight: item.isRead ? .regular : .semibold))
            .foregroundStyle(item.isRead ? Color.secondary : Color.primary)
            .frame(height: SidebarMetrics.itemRowHeight)
            .padding(.horizontal, SidebarMetrics.rowHorizontalPadding)
            .background(
                RoundedRectangle(cornerRadius: SidebarMetrics.rowCornerRadius)
                    .fill(processItemRowBackground(for: item))
            )
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .contextMenu {
            processItemContextMenu(for: item)
        }
        .transition(Self.libraryItemTransition)
    }

    func selectProcessItemRow(_ item: ProcessLibraryItem) {
        let modifiers = NSEvent.modifierFlags
        if modifiers.contains(.shift) {
            extendItemSelection(to: item)
        } else if modifiers.contains(.command) {
            toggleItemSelection(item)
        } else {
            selectedItemIDs = [item.id]
            lastSelectedItemID = item.id
        }
        controller.selectLibraryItem(item)
    }

    func extendItemSelection(to item: ProcessLibraryItem) {
        let items = controller.visibleLibraryItems
        guard
            let targetIndex = items.firstIndex(where: { $0.id == item.id }),
            let anchorID = lastSelectedItemID,
            let anchorIndex = items.firstIndex(where: { $0.id == anchorID })
        else {
            selectedItemIDs.insert(item.id)
            lastSelectedItemID = item.id
            return
        }
        let bounds = min(anchorIndex, targetIndex) ... max(anchorIndex, targetIndex)
        selectedItemIDs.formUnion(items[bounds].map(\.id))
    }

    func toggleItemSelection(_ item: ProcessLibraryItem) {
        if selectedItemIDs.contains(item.id) {
            selectedItemIDs.remove(item.id)
        } else {
            selectedItemIDs.insert(item.id)
        }
        lastSelectedItemID = item.id
    }

    func processItemRowBackground(for item: ProcessLibraryItem) -> Color {
        if selectedItemIDs.contains(item.id) {
            return Color.accentColor.opacity(0.28)
        }
        return controller.selectedLibraryItemID == item.id ? Color.accentColor.opacity(0.20) : Color.clear
    }

    func contextItems(for item: ProcessLibraryItem) -> [ProcessLibraryItem] {
        guard selectedItemIDs.contains(item.id) else {
            return [item]
        }
        let selectedItems = controller.visibleLibraryItems.filter { selectedItemIDs.contains($0.id) }
        return selectedItems.isEmpty ? [item] : selectedItems
    }

    func copyTitlesToPasteboard(_ items: [ProcessLibraryItem]) {
        let titles = items
            .map { $0.title.trimmingCharacters(in: .whitespacesAndNewlines) }
            .filter { !$0.isEmpty }
        guard !titles.isEmpty else { return }
        let pasteboard = NSPasteboard.general
        pasteboard.clearContents()
        pasteboard.setString(titles.joined(separator: "\n"), forType: .string)
    }

    func clearItemSelection() {
        selectedItemIDs.removeAll()
        lastSelectedItemID = nil
    }

    func reconcileItemSelection(visibleIDs: Set<String>) {
        selectedItemIDs = selectedItemIDs.intersection(visibleIDs)
        if let lastSelectedItemID, !visibleIDs.contains(lastSelectedItemID) {
            self.lastSelectedItemID = selectedItemIDs.first
        }
    }

    func processingActionButton(
        for item: ProcessLibraryItem,
        workflow: ProcessingWorkflow
    ) -> some View {
        let reprocess = item.isProcessed || item.needsReanalysis
        return Button {
            if item.isProcessed {
                pendingReprocessWorkflow = workflow
                pendingReprocessItem = item
            } else if !controller.stage.isRunning {
                controller.processLibraryItem(item, reprocess: item.needsReanalysis, workflow: workflow)
            }
        } label: {
            Label(
                workflow.actionTitle(reprocess: reprocess, isCloudConfigured: controller.isCloudSummaryConfigured),
                systemImage: workflow == .localOnly ? "waveform" : processActionIcon(for: item)
            )
        }
        .disabled(!controller.canProcessLibraryItem(item, reprocess: reprocess, workflow: workflow))
    }

    func processActionIcon(for item: ProcessLibraryItem) -> String {
        item.isProcessed || item.needsReanalysis ? "arrow.clockwise" : "play.fill"
    }

    var reprocessConfirmationBinding: Binding<Bool> {
        Binding(
            get: { pendingReprocessItem != nil },
            set: { if !$0 { pendingReprocessItem = nil } }
        )
    }

    var deleteConfirmationBinding: Binding<Bool> {
        Binding(
            get: { pendingDeleteItem != nil },
            set: { if !$0 { pendingDeleteItem = nil } }
        )
    }

    var bulkDeleteConfirmationBinding: Binding<Bool> {
        Binding(
            get: { !pendingBulkDeleteItems.isEmpty },
            set: { if !$0 { pendingBulkDeleteItems = [] } }
        )
    }

    var deleteGroupConfirmationBinding: Binding<Bool> {
        Binding(
            get: { pendingDeleteGroupName != nil },
            set: { if !$0 { pendingDeleteGroupName = nil } }
        )
    }
}
