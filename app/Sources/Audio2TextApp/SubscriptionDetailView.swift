import AppKit
import SwiftUI
#if canImport(Audio2TextCore)
    import Audio2TextCore
#endif

struct SubscriptionDetailViewState: Equatable {
    let snapshot: SubscriptionDetailSnapshot?
    let snapshotVersion: Int
    let hasSubscriptions: Bool
    let subscriptionCount: Int
    let isAddingSubscription: Bool
    let isRefreshingSubscriptions: Bool
    let subscriptionURLText: String
    let subscriptionGroupName: String
    let availableGroupNames: [String]
    let isProcessing: Bool
    let isCloudSummaryConfigured: Bool

    static func == (lhs: SubscriptionDetailViewState, rhs: SubscriptionDetailViewState) -> Bool {
        lhs.snapshotVersion == rhs.snapshotVersion
            && lhs.snapshot?.subscription.id == rhs.snapshot?.subscription.id
            && lhs.hasSubscriptions == rhs.hasSubscriptions
            && lhs.subscriptionCount == rhs.subscriptionCount
            && lhs.isAddingSubscription == rhs.isAddingSubscription
            && lhs.isRefreshingSubscriptions == rhs.isRefreshingSubscriptions
            && lhs.subscriptionURLText == rhs.subscriptionURLText
            && lhs.subscriptionGroupName == rhs.subscriptionGroupName
            && lhs.availableGroupNames == rhs.availableGroupNames
            && lhs.isProcessing == rhs.isProcessing
            && lhs.isCloudSummaryConfigured == rhs.isCloudSummaryConfigured
    }
}

struct SubscriptionDetailView: View, Equatable {
    let controller: JobController
    let state: SubscriptionDetailViewState
    @State private var presentedEpisode: ProcessLibraryItem?
    @State private var selectedEpisodeIDs: Set<String> = []
    @State private var pendingDeleteItems: [ProcessLibraryItem] = []
    @State private var showsOnlyUnprocessed = false
    @State private var episodeTimeFilter: SubscriptionEpisodeTimeFilter = .all

    static func == (lhs: SubscriptionDetailView, rhs: SubscriptionDetailView) -> Bool {
        lhs.state == rhs.state
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            header(snapshot: state.snapshot)
            Divider()
            SubscriptionStaticDetailContent(
                snapshot: state.snapshot,
                snapshotVersion: state.snapshotVersion,
                hasSubscriptions: state.hasSubscriptions,
                selectedEpisodeIDs: selectedEpisodeIDs,
                episodeFilterState: episodeFilterState,
                filteredEpisodes: filteredEpisodes,
                bulkActionState: bulkActionState,
                open: openSubscriptionEpisode,
                toggleSelection: toggleEpisodeSelection,
                toggleAllVisibleSelection: toggleAllVisibleEpisodeSelection,
                selectFrontVisibleSelection: selectFrontVisibleEpisodeSelection,
                clearSelection: clearEpisodeSelection,
                setShowsOnlyUnprocessed: setShowsOnlyUnprocessed,
                setTimeFilter: setTimeFilter,
                processSelection: processSelectedEpisodes,
                archiveSelection: archiveSelectedEpisodes,
                deleteSelection: requestDeleteSelectedEpisodes
            )
            .equatable()
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            Divider()
            addRow
                .padding(22)
        }
        .sheet(item: $presentedEpisode) { item in
            SubscriptionEpisodeInfoSheet(
                item: item,
                details: ProcessLibrary.channelEpisodeDetails(for: item)
            )
        }
        .alert("删除所选条目？", isPresented: deleteConfirmationBinding) {
            Button("取消", role: .cancel) {
                pendingDeleteItems = []
            }
            Button("删除 \(pendingDeleteItems.count) 个", role: .destructive) {
                let items = pendingDeleteItems
                controller.deleteLibraryItems(items)
                clearEpisodeSelection()
                pendingDeleteItems = []
            }
        } message: {
            Text("这会删除所选条目的缓存文件和输出结果；订阅来源的条目后续刷新不会重新出现。")
        }
        .onChange(of: state.snapshot?.subscription.id) { _ in
            clearEpisodeSelection()
        }
        .onChange(of: state.snapshotVersion) { _ in
            reconcileEpisodeSelection()
        }
        .onChange(of: showsOnlyUnprocessed) { _ in
            reconcileEpisodeSelection()
        }
        .onChange(of: episodeTimeFilter) { _ in
            reconcileEpisodeSelection()
        }
    }

    private func header(snapshot: SubscriptionDetailSnapshot?) -> some View {
        HStack(spacing: 10) {
            VStack(alignment: .leading, spacing: 2) {
                Text(snapshot?.subscription.title ?? "Subscriptions")
                    .font(.title3.weight(.semibold))
                    .lineLimit(1)
                Text(headerSubtitle(snapshot: snapshot))
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .lineLimit(1)
            }
            Spacer()
            if let subscription = snapshot?.subscription {
                subscriptionActionButton(tooltip: "Copy subscription link") {
                    copySubscriptionURLToPasteboard(subscription)
                } label: {
                    Image(systemName: "link")
                }
                subscriptionActionButton(
                    tooltip: "Refresh subscription",
                    disabled: state.isRefreshingSubscriptions || state.isAddingSubscription
                ) {
                    controller.refreshSubscription(subscription)
                } label: {
                    if state.isRefreshingSubscriptions {
                        ProgressView()
                            .controlSize(.small)
                    } else {
                        Image(systemName: "arrow.clockwise")
                    }
                }
                subscriptionActionButton(
                    tooltip: "抓取历史全部",
                    disabled: state.isRefreshingSubscriptions || state.isAddingSubscription
                ) {
                    controller.fetchSubscriptionHistory(subscription)
                } label: {
                    Image(systemName: "clock.arrow.circlepath")
                }
                subscriptionActionButton(
                    tooltip: "Remove subscription",
                    role: .destructive,
                    disabled: state.isRefreshingSubscriptions || state.isAddingSubscription
                ) {
                    controller.removeSubscription(subscription)
                } label: {
                    Image(systemName: "trash")
                }
            }
        }
        .padding(.horizontal, 22)
        .padding(.vertical, 14)
    }

    private func subscriptionActionButton<Label: View>(
        tooltip: String,
        role: ButtonRole? = nil,
        disabled: Bool = false,
        action: @escaping () -> Void,
        @ViewBuilder label: () -> Label
    ) -> some View {
        Button(role: role, action: action) {
            label()
                .frame(width: 24, height: 22)
        }
        .buttonStyle(SubscriptionHeaderActionButtonStyle(role: role))
        .disabled(disabled)
        .subscriptionFastTooltip(tooltip)
        .accessibilityLabel(tooltip)
    }

    private func headerSubtitle(snapshot: SubscriptionDetailSnapshot?) -> String {
        guard let snapshot else {
            return state.hasSubscriptions ? "\(state.subscriptionCount) subscriptions" : "No subscriptions yet"
        }
        let counts = snapshot.counts
        return "\(counts.total) episodes · \(counts.unprocessed) unprocessed"
    }

    private func openSubscriptionEpisode(_ item: ProcessLibraryItem) {
        if item.isProcessed {
            controller.openProcessedSubscriptionItem(item)
        } else {
            presentedEpisode = item
        }
    }

    private var currentEpisodes: [SubscriptionEpisodeDisplayItem] {
        state.snapshot?.episodes ?? []
    }

    private var episodeFilterState: SubscriptionEpisodeFilterState {
        SubscriptionEpisodeFilterState(
            showsOnlyUnprocessed: showsOnlyUnprocessed,
            timeFilter: episodeTimeFilter,
            filteredCount: filteredEpisodes.count,
            totalCount: currentEpisodes.count
        )
    }

    private var filteredEpisodes: [SubscriptionEpisodeDisplayItem] {
        SubscriptionEpisodeFilters.filteredEpisodes(
            currentEpisodes,
            showsOnlyUnprocessed: showsOnlyUnprocessed,
            timeFilter: episodeTimeFilter
        )
    }

    private var selectedItems: [ProcessLibraryItem] {
        SubscriptionBulkSelection.selectedItems(
            from: filteredEpisodes,
            selectedIDs: selectedEpisodeIDs
        )
    }

    private var bulkActionState: SubscriptionBulkActionState {
        let items = selectedItems
        return SubscriptionBulkActionState(
            selectedCount: items.count,
            unprocessedCount: SubscriptionBulkSelection.unprocessedItems(from: items).count,
            transcribeAndSummarizeCount: processableSelectedItems(workflow: .transcribeAndSummarize).count,
            localOnlyCount: processableSelectedItems(workflow: .localOnly).count,
            isProcessing: state.isProcessing,
            isCloudSummaryConfigured: state.isCloudSummaryConfigured
        )
    }

    private func processableSelectedItems(workflow: ProcessingWorkflow) -> [ProcessLibraryItem] {
        SubscriptionBulkSelection.processableItems(from: selectedItems) { item in
            controller.canProcessLibraryItem(item, workflow: workflow)
        }
    }

    private func toggleEpisodeSelection(_ item: ProcessLibraryItem) {
        if selectedEpisodeIDs.contains(item.id) {
            selectedEpisodeIDs.remove(item.id)
        } else {
            selectedEpisodeIDs.insert(item.id)
        }
    }

    private func toggleAllVisibleEpisodeSelection() {
        selectedEpisodeIDs = SubscriptionBulkSelection.toggledVisibleSelection(
            selectedEpisodeIDs,
            episodes: filteredEpisodes
        )
    }

    private func selectFrontVisibleEpisodeSelection(_ limit: Int) {
        selectedEpisodeIDs = SubscriptionBulkSelection.frontVisibleSelection(
            episodes: filteredEpisodes,
            limit: limit
        )
    }

    private func clearEpisodeSelection() {
        selectedEpisodeIDs.removeAll()
    }

    private func reconcileEpisodeSelection() {
        selectedEpisodeIDs = SubscriptionBulkSelection.reconciledSelection(
            selectedEpisodeIDs,
            episodes: filteredEpisodes
        )
    }

    private func setShowsOnlyUnprocessed(_ value: Bool) {
        showsOnlyUnprocessed = value
    }

    private func setTimeFilter(_ value: SubscriptionEpisodeTimeFilter) {
        episodeTimeFilter = value
    }

    private func processSelectedEpisodes(workflow: ProcessingWorkflow) {
        let items = processableSelectedItems(workflow: workflow)
        guard !items.isEmpty else { return }
        controller.processLibraryItems(items, workflow: workflow)
        clearEpisodeSelection()
    }

    private func archiveSelectedEpisodes() {
        let items = selectedItems
        guard !items.isEmpty else { return }
        controller.archiveLibraryItems(items)
        clearEpisodeSelection()
    }

    private func requestDeleteSelectedEpisodes() {
        let items = selectedItems
        guard !items.isEmpty else { return }
        pendingDeleteItems = items
    }

    private var deleteConfirmationBinding: Binding<Bool> {
        Binding(
            get: { !pendingDeleteItems.isEmpty },
            set: { if !$0 { pendingDeleteItems = [] } }
        )
    }

    private var addRow: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("Add Subscription")
                .font(.headline)
            HStack(spacing: 8) {
                TextField("Xiaoyuzhou, Apple Podcast, or RSS URL", text: subscriptionURLBinding)
                    .textFieldStyle(.roundedBorder)
                groupMenu
                Button {
                    controller.addSubscription()
                } label: {
                    if state.isAddingSubscription {
                        ProgressView()
                            .controlSize(.small)
                    } else {
                        Label("Add", systemImage: "plus")
                    }
                }
                .buttonStyle(SubscriptionControlButtonStyle(variant: .prominent))
                .disabled(
                    state.subscriptionURLText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
                        || state.isAddingSubscription
                        || state.isRefreshingSubscriptions
                )
            }
        }
    }

    private var groupMenu: some View {
        Menu {
            ForEach(state.availableGroupNames, id: \.self) { groupName in
                Button(groupName) {
                    controller.subscriptionGroupName = groupName
                }
            }
        } label: {
            SubscriptionMenuLabel(title: state.subscriptionGroupName, systemImage: "folder")
        }
        .fixedSize(horizontal: true, vertical: false)
        .menuStyle(.button)
        .menuIndicator(.hidden)
        .buttonStyle(SubscriptionControlButtonStyle())
    }

    private var subscriptionURLBinding: Binding<String> {
        Binding(
            get: { state.subscriptionURLText },
            set: { controller.subscriptionURLText = $0 }
        )
    }

    private func subscriptionDisplayURL(_ subscription: PodcastSubscriptionItem) -> String {
        let feedURL = subscription.feedURL.trimmingCharacters(in: .whitespacesAndNewlines)
        if !feedURL.isEmpty { return feedURL }
        let url = subscription.url.trimmingCharacters(in: .whitespacesAndNewlines)
        return url.isEmpty ? "No URL" : url
    }

    private func copySubscriptionURLToPasteboard(_ subscription: PodcastSubscriptionItem) {
        let url = subscriptionDisplayURL(subscription)
        guard url != "No URL" else { return }
        NSPasteboard.general.clearContents()
        NSPasteboard.general.setString(url, forType: .string)
    }
}

private struct SubscriptionStaticDetailContent: View, Equatable {
    let snapshot: SubscriptionDetailSnapshot?
    let snapshotVersion: Int
    let hasSubscriptions: Bool
    let selectedEpisodeIDs: Set<String>
    let episodeFilterState: SubscriptionEpisodeFilterState
    let filteredEpisodes: [SubscriptionEpisodeDisplayItem]
    let bulkActionState: SubscriptionBulkActionState
    let open: (ProcessLibraryItem) -> Void
    let toggleSelection: (ProcessLibraryItem) -> Void
    let toggleAllVisibleSelection: () -> Void
    let selectFrontVisibleSelection: (Int) -> Void
    let clearSelection: () -> Void
    let setShowsOnlyUnprocessed: (Bool) -> Void
    let setTimeFilter: (SubscriptionEpisodeTimeFilter) -> Void
    let processSelection: (ProcessingWorkflow) -> Void
    let archiveSelection: () -> Void
    let deleteSelection: () -> Void

    static func == (lhs: SubscriptionStaticDetailContent, rhs: SubscriptionStaticDetailContent) -> Bool {
        lhs.snapshotVersion == rhs.snapshotVersion
            && lhs.snapshot?.subscription.id == rhs.snapshot?.subscription.id
            && lhs.hasSubscriptions == rhs.hasSubscriptions
            && lhs.selectedEpisodeIDs == rhs.selectedEpisodeIDs
            && lhs.episodeFilterState == rhs.episodeFilterState
            && lhs.filteredEpisodes == rhs.filteredEpisodes
            && lhs.bulkActionState == rhs.bulkActionState
    }

    var body: some View {
        List {
            if let snapshot {
                subscriptionSummary(counts: snapshot.counts)
                    .listRowInsets(EdgeInsets(top: 22, leading: 22, bottom: 10, trailing: 22))
                    .listRowSeparator(.hidden)
                    .listRowBackground(Color.clear)
                currentEpisodesSection(filteredEpisodes, totalCount: snapshot.episodes.count)
                channelMetadataSection(snapshot.subscription)
                    .listRowInsets(EdgeInsets(top: 14, leading: 22, bottom: 22, trailing: 22))
                    .listRowSeparator(.hidden)
                    .listRowBackground(Color.clear)
            }
            if !hasSubscriptions {
                emptyState
                    .listRowInsets(EdgeInsets(top: 22, leading: 22, bottom: 22, trailing: 22))
                    .listRowSeparator(.hidden)
                    .listRowBackground(Color.clear)
            }
        }
        .listStyle(.plain)
        .scrollContentBackground(.hidden)
    }

    private func subscriptionSummary(counts: SubscriptionDetailCounts) -> some View {
        HStack(spacing: 12) {
            statBlock(title: "Episodes", value: "\(counts.total)", tint: .primary)
            statBlock(title: "Unprocessed", value: "\(counts.unprocessed)", tint: counts.unprocessed > 0 ? .blue : .secondary)
            statBlock(title: "Processed", value: "\(counts.processed)", tint: .green)
        }
    }

    private func statBlock(title: String, value: String, tint: Color) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(value)
                .font(.system(size: 24, weight: .semibold, design: .rounded).monospacedDigit())
                .foregroundStyle(tint)
            Text(title)
                .font(.caption)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(14)
        .background(Color.secondary.opacity(0.08), in: RoundedRectangle(cornerRadius: 8))
    }

    private func currentEpisodesSection(_ episodes: [SubscriptionEpisodeDisplayItem], totalCount: Int) -> some View {
        Section {
            if totalCount > 0 {
                SubscriptionEpisodeFilterBar(
                    filterState: episodeFilterState,
                    selectedCount: visibleSelectedCount(in: episodes),
                    setShowsOnlyUnprocessed: setShowsOnlyUnprocessed,
                    setTimeFilter: setTimeFilter,
                    toggleAllVisibleSelection: toggleAllVisibleSelection,
                    selectFrontVisibleSelection: selectFrontVisibleSelection
                )
                .listRowInsets(EdgeInsets(top: 4, leading: 22, bottom: 4, trailing: 22))
                .listRowSeparator(.hidden)
                .listRowBackground(Color.clear)
            }
            if totalCount == 0 {
                Label("No episodes imported for this subscription yet.", systemImage: "tray")
                    .font(.callout)
                    .foregroundStyle(.secondary)
                    .padding(.vertical, 10)
                    .listRowInsets(EdgeInsets(top: 4, leading: 22, bottom: 4, trailing: 22))
                    .listRowSeparator(.hidden)
                    .listRowBackground(Color.clear)
            } else if episodes.isEmpty {
                Label("没有符合过滤条件的节目。", systemImage: "line.3.horizontal.decrease.circle")
                    .font(.callout)
                    .foregroundStyle(.secondary)
                    .padding(.vertical, 10)
                    .listRowInsets(EdgeInsets(top: 4, leading: 22, bottom: 4, trailing: 22))
                    .listRowSeparator(.hidden)
                    .listRowBackground(Color.clear)
            } else {
                if bulkActionState.hasSelection {
                    SubscriptionBulkActionBar(
                        actionState: bulkActionState,
                        clearSelection: clearSelection,
                        processSelection: processSelection,
                        archiveSelection: archiveSelection,
                        deleteSelection: deleteSelection
                    )
                    .listRowInsets(EdgeInsets(top: 4, leading: 22, bottom: 4, trailing: 22))
                    .listRowSeparator(.hidden)
                    .listRowBackground(Color.clear)
                }
                ForEach(episodes) { episode in
                    SubscriptionEpisodeRow(
                        episode: episode,
                        isSelected: selectedEpisodeIDs.contains(episode.id),
                        open: open,
                        toggleSelection: toggleSelection
                    )
                        .equatable()
                        .listRowInsets(EdgeInsets(top: 4, leading: 22, bottom: 4, trailing: 22))
                        .listRowSeparator(.hidden)
                        .listRowBackground(Color.clear)
                }
            }
        } header: {
            Text("Current Episodes")
                .font(.headline)
                .foregroundStyle(.primary)
                .textCase(nil)
                .padding(.top, 8)
                .padding(.bottom, 2)
        }
    }

    private func visibleSelectedCount(in episodes: [SubscriptionEpisodeDisplayItem]) -> Int {
        episodes.reduce(into: 0) { count, episode in
            if selectedEpisodeIDs.contains(episode.id) {
                count += 1
            }
        }
    }

    private func channelMetadataSection(_ subscription: PodcastSubscriptionItem) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            sectionTitle("Channel Metadata")
            VStack(alignment: .leading, spacing: 8) {
                metadataRow(title: "Source", value: subscription.source)
                metadataRow(title: "Group", value: subscription.groupName)
                metadataRow(title: "Feed", value: subscriptionDisplayURL(subscription))
                metadataRow(title: "Created", value: emptyAware(subscription.createdAt))
                metadataRow(title: "Last Checked", value: emptyAware(subscription.lastCheckedAt))
            }
            .textSelection(.enabled)
            .padding(14)
            .background(Color.secondary.opacity(0.06), in: RoundedRectangle(cornerRadius: 8))
        }
    }

    private func sectionTitle(_ title: String) -> some View {
        Text(title)
            .font(.headline)
    }

    private func metadataRow(title: String, value: String) -> some View {
        HStack(alignment: .firstTextBaseline, spacing: 12) {
            Text(title)
                .font(.caption.weight(.semibold))
                .foregroundStyle(.secondary)
                .frame(width: 92, alignment: .leading)
            Text(value)
                .font(.callout)
                .lineLimit(2)
                .truncationMode(.middle)
            Spacer(minLength: 0)
        }
    }

    private var emptyState: some View {
        VStack(alignment: .leading, spacing: 8) {
            Image(systemName: "dot.radiowaves.left.and.right")
                .font(.title2)
                .foregroundStyle(.secondary)
            Text("No subscriptions")
                .font(.title3.weight(.semibold))
            Text("Add a podcast or RSS feed to create metadata-only episode records.")
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(.vertical, 10)
    }

    private func subscriptionDisplayURL(_ subscription: PodcastSubscriptionItem) -> String {
        let feedURL = subscription.feedURL.trimmingCharacters(in: .whitespacesAndNewlines)
        if !feedURL.isEmpty { return feedURL }
        let url = subscription.url.trimmingCharacters(in: .whitespacesAndNewlines)
        return url.isEmpty ? "No URL" : url
    }

    private func emptyAware(_ value: String) -> String {
        let trimmed = value.trimmingCharacters(in: .whitespacesAndNewlines)
        return trimmed.isEmpty ? "None" : trimmed
    }
}

struct SubscriptionDetailSnapshot: Equatable {
    let subscription: PodcastSubscriptionItem
    let counts: SubscriptionDetailCounts
    let episodes: [SubscriptionEpisodeDisplayItem]

    init(subscription: PodcastSubscriptionItem, items: [ProcessLibraryItem]) {
        self.subscription = subscription
        let unprocessedCount = items.reduce(into: 0) { count, item in
            if !item.isProcessed {
                count += 1
            }
        }
        counts = SubscriptionDetailCounts(
            unprocessed: unprocessedCount,
            total: items.count
        )
        episodes = items.map(SubscriptionEpisodeDisplayItem.init)
    }
}

struct SubscriptionDetailCounts: Equatable {
    let unprocessed: Int
    let total: Int

    var processed: Int {
        max(total - unprocessed, 0)
    }

    var asSubscriptionItemCounts: SubscriptionItemCounts {
        SubscriptionItemCounts(unprocessed: unprocessed, total: total)
    }
}

enum SubscriptionEpisodeTimeFilter: String, CaseIterable, Identifiable {
    case all
    case today
    case last7Days
    case last30Days
    case last90Days
    case thisYear

    var id: String {
        rawValue
    }

    var title: String {
        switch self {
        case .all: return "全部时间"
        case .today: return "今天"
        case .last7Days: return "最近 7 天"
        case .last30Days: return "最近 30 天"
        case .last90Days: return "最近 90 天"
        case .thisYear: return "今年"
        }
    }

    func includes(_ date: Date, now: Date = Date(), calendar: Calendar = .current) -> Bool {
        switch self {
        case .all:
            return true
        case .today:
            return calendar.isDate(date, inSameDayAs: now)
        case .last7Days:
            return date >= startDate(daysIncludingToday: 7, now: now, calendar: calendar)
        case .last30Days:
            return date >= startDate(daysIncludingToday: 30, now: now, calendar: calendar)
        case .last90Days:
            return date >= startDate(daysIncludingToday: 90, now: now, calendar: calendar)
        case .thisYear:
            return calendar.component(.year, from: date) == calendar.component(.year, from: now)
        }
    }

    private func startDate(daysIncludingToday: Int, now: Date, calendar: Calendar) -> Date {
        let startOfToday = calendar.startOfDay(for: now)
        return calendar.date(byAdding: .day, value: -(daysIncludingToday - 1), to: startOfToday) ?? startOfToday
    }
}

struct SubscriptionEpisodeFilterState: Equatable {
    let showsOnlyUnprocessed: Bool
    let timeFilter: SubscriptionEpisodeTimeFilter
    let filteredCount: Int
    let totalCount: Int
}

enum SubscriptionEpisodeFilters {
    static func filteredEpisodes(
        _ episodes: [SubscriptionEpisodeDisplayItem],
        showsOnlyUnprocessed: Bool,
        timeFilter: SubscriptionEpisodeTimeFilter,
        now: Date = Date(),
        calendar: Calendar = .current
    ) -> [SubscriptionEpisodeDisplayItem] {
        episodes.filter { episode in
            (!showsOnlyUnprocessed || !episode.isProcessed)
                && timeFilter.includes(episode.filterDate, now: now, calendar: calendar)
        }
    }
}

private struct SubscriptionEpisodeFilterBar: View {
    let filterState: SubscriptionEpisodeFilterState
    let selectedCount: Int
    let setShowsOnlyUnprocessed: (Bool) -> Void
    let setTimeFilter: (SubscriptionEpisodeTimeFilter) -> Void
    let toggleAllVisibleSelection: () -> Void
    let selectFrontVisibleSelection: (Int) -> Void

    var body: some View {
        HStack(spacing: 10) {
            Toggle("只看未处理", isOn: onlyUnprocessedBinding)
                .toggleStyle(.checkbox)
                .fixedSize(horizontal: true, vertical: false)

            Menu {
                ForEach(SubscriptionEpisodeTimeFilter.allCases) { filter in
                    Button {
                        setTimeFilter(filter)
                    } label: {
                        Label(filter.title, systemImage: filterState.timeFilter == filter ? "checkmark" : "calendar")
                    }
                }
            } label: {
                SubscriptionMenuLabel(title: filterState.timeFilter.title, systemImage: "calendar")
            }
            .fixedSize(horizontal: true, vertical: false)
            .menuStyle(.button)
            .menuIndicator(.hidden)
            .buttonStyle(SubscriptionControlButtonStyle())

            Button {
                toggleAllVisibleSelection()
            } label: {
                Label(selectAllTitle, systemImage: isAllVisibleSelected ? "checkmark.circle.fill" : "checkmark.circle")
                    .lineLimit(1)
            }
            .buttonStyle(SubscriptionControlButtonStyle())
            .disabled(filterState.filteredCount == 0)

            ForEach(SubscriptionBulkSelection.frontSelectionLimits, id: \.self) { limit in
                Button {
                    selectFrontVisibleSelection(limit)
                } label: {
                    Label("前 \(limit)", systemImage: "list.number")
                        .lineLimit(1)
                }
                .buttonStyle(SubscriptionControlButtonStyle())
                .disabled(filterState.filteredCount == 0)
                .accessibilityLabel("选择前 \(limit) 个")
            }

            Text("\(filterState.filteredCount) / \(filterState.totalCount)")
                .font(.caption.weight(.semibold))
                .foregroundStyle(.secondary)
                .monospacedDigit()

            Spacer(minLength: 8)
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 9)
        .background(Color.secondary.opacity(0.06), in: RoundedRectangle(cornerRadius: 8))
    }

    private var isAllVisibleSelected: Bool {
        filterState.filteredCount > 0 && selectedCount == filterState.filteredCount
    }

    private var selectAllTitle: String {
        isAllVisibleSelected ? "取消全选" : "全选"
    }

    private var onlyUnprocessedBinding: Binding<Bool> {
        Binding(
            get: { filterState.showsOnlyUnprocessed },
            set: setShowsOnlyUnprocessed
        )
    }
}

enum SubscriptionBulkSelection {
    static let frontSelectionLimits = [10, 20]

    static func selectedItems(
        from episodes: [SubscriptionEpisodeDisplayItem],
        selectedIDs: Set<String>
    ) -> [ProcessLibraryItem] {
        episodes
            .filter { selectedIDs.contains($0.id) }
            .map(\.item)
    }

    static func unprocessedItems(from items: [ProcessLibraryItem]) -> [ProcessLibraryItem] {
        items.filter { !$0.isProcessed }
    }

    static func processableItems(
        from items: [ProcessLibraryItem],
        canProcess: (ProcessLibraryItem) -> Bool
    ) -> [ProcessLibraryItem] {
        unprocessedItems(from: items).filter(canProcess)
    }

    static func reconciledSelection(
        _ selectedIDs: Set<String>,
        episodes: [SubscriptionEpisodeDisplayItem]
    ) -> Set<String> {
        selectedIDs.intersection(Set(episodes.map(\.id)))
    }

    static func toggledVisibleSelection(
        _ selectedIDs: Set<String>,
        episodes: [SubscriptionEpisodeDisplayItem]
    ) -> Set<String> {
        let visibleIDs = Set(episodes.map(\.id))
        guard !visibleIDs.isEmpty else { return [] }
        let selectedVisibleIDs = selectedIDs.intersection(visibleIDs)
        return selectedVisibleIDs.count == visibleIDs.count ? [] : visibleIDs
    }

    static func frontVisibleSelection(
        episodes: [SubscriptionEpisodeDisplayItem],
        limit: Int
    ) -> Set<String> {
        guard limit > 0 else { return [] }
        return Set(episodes.prefix(limit).map(\.id))
    }
}

struct SubscriptionBulkActionState: Equatable {
    let selectedCount: Int
    let unprocessedCount: Int
    let transcribeAndSummarizeCount: Int
    let localOnlyCount: Int
    let isProcessing: Bool
    let isCloudSummaryConfigured: Bool

    var hasSelection: Bool {
        selectedCount > 0
    }

    var canProcessAny: Bool {
        transcribeAndSummarizeCount > 0 || localOnlyCount > 0
    }
}

private struct SubscriptionBulkActionBar: View {
    let actionState: SubscriptionBulkActionState
    let clearSelection: () -> Void
    let processSelection: (ProcessingWorkflow) -> Void
    let archiveSelection: () -> Void
    let deleteSelection: () -> Void

    var body: some View {
        HStack(spacing: 8) {
            Text("已选 \(actionState.selectedCount)")
                .font(.callout.weight(.semibold))
                .lineLimit(1)

            Spacer(minLength: 8)

            Menu {
                Button {
                    processSelection(.transcribeAndSummarize)
                } label: {
                    Label(
                        "\(ProcessingWorkflow.transcribeAndSummarize.actionTitle(isCloudConfigured: actionState.isCloudSummaryConfigured)) \(actionState.transcribeAndSummarizeCount) 个",
                        systemImage: "play.fill"
                    )
                }
                .disabled(actionState.isProcessing || actionState.transcribeAndSummarizeCount == 0)

                Button {
                    processSelection(.localOnly)
                } label: {
                    Label("仅本地转写 \(actionState.localOnlyCount) 个", systemImage: "waveform")
                }
                .disabled(actionState.isProcessing || actionState.localOnlyCount == 0)
            } label: {
                SubscriptionMenuLabel(title: "处理 \(actionState.unprocessedCount) 个", systemImage: "play.fill")
            }
            .disabled(actionState.isProcessing || !actionState.canProcessAny)
            .menuStyle(.button)
            .menuIndicator(.hidden)
            .buttonStyle(SubscriptionControlButtonStyle())

            Button {
                archiveSelection()
            } label: {
                Label("归档 \(actionState.selectedCount) 个", systemImage: "archivebox")
                    .lineLimit(1)
            }
            .buttonStyle(SubscriptionControlButtonStyle())
            .disabled(actionState.isProcessing)

            Button(role: .destructive) {
                deleteSelection()
            } label: {
                Label("删除 \(actionState.selectedCount) 个", systemImage: "trash")
                    .lineLimit(1)
            }
            .buttonStyle(SubscriptionControlButtonStyle(variant: .destructive))
            .disabled(actionState.isProcessing)

            Button {
                clearSelection()
            } label: {
                Label("全部取消选择", systemImage: "xmark.circle")
                    .lineLimit(1)
            }
            .buttonStyle(SubscriptionControlButtonStyle())
            .accessibilityLabel("全部取消选择")
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 9)
        .background(Color.secondary.opacity(0.08), in: RoundedRectangle(cornerRadius: 8))
    }
}

struct SubscriptionEpisodeDisplayItem: Identifiable, Equatable {
    let item: ProcessLibraryItem
    let title: String
    let primaryCaption: String
    let queueTitle: String
    let dateTitle: String
    let filterDate: Date
    let iconName: String
    let isProcessed: Bool
    let isStarred: Bool
    let iconColor: Color
    let trailingIconName: String
    let accessibilityLabel: String

    var id: String {
        item.id
    }

    static func == (lhs: SubscriptionEpisodeDisplayItem, rhs: SubscriptionEpisodeDisplayItem) -> Bool {
        lhs.item == rhs.item
            && lhs.title == rhs.title
            && lhs.primaryCaption == rhs.primaryCaption
            && lhs.queueTitle == rhs.queueTitle
            && lhs.dateTitle == rhs.dateTitle
            && lhs.filterDate == rhs.filterDate
            && lhs.iconName == rhs.iconName
            && lhs.isProcessed == rhs.isProcessed
            && lhs.isStarred == rhs.isStarred
            && lhs.trailingIconName == rhs.trailingIconName
            && lhs.accessibilityLabel == rhs.accessibilityLabel
    }

    init(item: ProcessLibraryItem) {
        self.item = item
        title = item.title
        primaryCaption = Self.primaryCaption(for: item)
        queueTitle = item.queueStatus.compactTitle
        let displayDate = Self.publishedDate(for: item) ?? item.modifiedAt
        filterDate = displayDate
        dateTitle = displayDate.formatted(date: .abbreviated, time: .omitted)
        iconName = item.isProcessed ? "doc.text.fill" : "tray"
        isProcessed = item.isProcessed
        isStarred = item.isStarred
        iconColor = item.isProcessed ? .green : .blue
        trailingIconName = item.isProcessed ? "chevron.right" : "info.circle"
        accessibilityLabel = item.isProcessed
            ? "Open processed episode \(item.title)"
            : "Show episode details for \(item.title)"
    }

    private static func primaryCaption(for item: ProcessLibraryItem) -> String {
        let originalTitle = item.originalTitle?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
        let title = item.title.trimmingCharacters(in: .whitespacesAndNewlines)
        if !originalTitle.isEmpty && originalTitle != title {
            return "原名：\(originalTitle)"
        }
        return item.status
    }

    private static func publishedDate(for item: ProcessLibraryItem) -> Date? {
        LibraryDateParser.date(from: item.publishedAt)
    }
}

private struct SubscriptionEpisodeRow: View, Equatable {
    let episode: SubscriptionEpisodeDisplayItem
    let isSelected: Bool
    let open: (ProcessLibraryItem) -> Void
    let toggleSelection: (ProcessLibraryItem) -> Void

    static func == (lhs: SubscriptionEpisodeRow, rhs: SubscriptionEpisodeRow) -> Bool {
        lhs.episode == rhs.episode
            && lhs.isSelected == rhs.isSelected
    }

    var body: some View {
        HStack(alignment: .center, spacing: 10) {
            Button {
                toggleSelection(episode.item)
            } label: {
                Image(systemName: isSelected ? "checkmark.circle.fill" : "circle")
                    .font(.system(size: 16, weight: .semibold))
                    .foregroundStyle(isSelected ? Color.accentColor : Color.secondary)
                    .frame(width: 22, height: 44)
                    .contentShape(Rectangle())
            }
            .buttonStyle(.plain)
            .accessibilityLabel(isSelected ? "取消选择 \(episode.title)" : "选择 \(episode.title)")

            Button {
                open(episode.item)
            } label: {
                rowContent
            }
            .buttonStyle(.plain)
            .frame(maxWidth: .infinity, alignment: .leading)
            .accessibilityLabel(episode.accessibilityLabel)
        }
        .padding(12)
        .frame(
            maxWidth: .infinity,
            minHeight: SubscriptionEpisodeLayout.rowHeight,
            maxHeight: SubscriptionEpisodeLayout.rowHeight,
            alignment: .leading
        )
        .background(rowBackground, in: RoundedRectangle(cornerRadius: 8))
        .overlay {
            RoundedRectangle(cornerRadius: 8)
                .strokeBorder(isSelected ? Color.accentColor.opacity(0.36) : Color.clear, lineWidth: 1)
        }
        .contentShape(RoundedRectangle(cornerRadius: 8))
    }

    private var rowContent: some View {
        HStack(alignment: .center, spacing: 10) {
            Image(systemName: episode.iconName)
                .font(.system(size: 13, weight: .semibold))
                .foregroundStyle(episode.iconColor)
                .frame(width: 18)

            VStack(alignment: .leading, spacing: 3) {
                Text(episode.title)
                    .font(.headline)
                    .lineLimit(1)
                HStack(spacing: 8) {
                    Text(episode.primaryCaption)
                        .lineLimit(1)
                        .truncationMode(.tail)
                    Text(episode.queueTitle)
                        .fixedSize(horizontal: true, vertical: false)
                    Text(episode.dateTitle)
                        .fixedSize(horizontal: true, vertical: false)
                }
                .font(.caption)
                .foregroundStyle(.secondary)
                .lineLimit(1)
            }

            Spacer(minLength: 8)
            if episode.isStarred {
                Image(systemName: "star.fill")
                    .foregroundStyle(.yellow)
                    .accessibilityLabel("Starred")
            }
            Image(systemName: episode.trailingIconName)
                .font(.system(size: 13, weight: .semibold))
                .foregroundStyle(.secondary)
                .accessibilityHidden(true)
        }
        .contentShape(Rectangle())
    }

    private var rowBackground: Color {
        if isSelected {
            return Color.accentColor.opacity(0.14)
        }
        return Color.secondary.opacity(0.06)
    }
}

private enum SubscriptionEpisodeLayout {
    static let rowHeight: CGFloat = 68
}

private enum SubscriptionControlMetrics {
    static let controlHeight: CGFloat = 30
    static let iconButtonWidth: CGFloat = 48
    static let squareButtonWidth: CGFloat = 30
    static let cornerRadius: CGFloat = 8
}

private struct SubscriptionMenuLabel: View {
    let title: String
    let systemImage: String

    var body: some View {
        HStack(spacing: 6) {
            Label(title, systemImage: systemImage)
                .lineLimit(1)
            Image(systemName: "chevron.down")
                .font(.system(size: 9, weight: .bold))
                .accessibilityHidden(true)
        }
    }
}

private struct SubscriptionControlButtonStyle: ButtonStyle {
    enum Variant {
        case normal
        case destructive
        case prominent
    }

    let variant: Variant
    let width: CGFloat?

    init(variant: Variant = .normal, width: CGFloat? = nil) {
        self.variant = variant
        self.width = width
    }

    func makeBody(configuration: Configuration) -> some View {
        SubscriptionControlButton(
            configuration: configuration,
            variant: variant,
            width: width
        )
    }
}

private struct SubscriptionControlButton: View {
    let configuration: ButtonStyle.Configuration
    let variant: SubscriptionControlButtonStyle.Variant
    let width: CGFloat?

    @Environment(\.isEnabled) private var isEnabled
    @State private var isHovered = false

    var body: some View {
        configuration.label
            .font(.callout.weight(.semibold))
            .foregroundStyle(foregroundStyle)
            .padding(.horizontal, width == nil ? 12 : 0)
            .frame(width: width, height: SubscriptionControlMetrics.controlHeight)
            .background(backgroundStyle, in: RoundedRectangle(cornerRadius: SubscriptionControlMetrics.cornerRadius, style: .continuous))
            .overlay {
                RoundedRectangle(cornerRadius: SubscriptionControlMetrics.cornerRadius, style: .continuous)
                    .strokeBorder(borderStyle, lineWidth: borderLineWidth)
            }
            .contentShape(RoundedRectangle(cornerRadius: SubscriptionControlMetrics.cornerRadius, style: .continuous))
            .scaleEffect(configuration.isPressed ? 0.98 : 1)
            .animation(.easeOut(duration: 0.12), value: isHovered)
            .animation(.easeOut(duration: 0.08), value: configuration.isPressed)
            .onHover { isHovered = $0 }
    }

    private var foregroundStyle: Color {
        if !isEnabled {
            return .secondary.opacity(0.48)
        }
        switch variant {
        case .normal:
            return isHovered ? .primary : .secondary
        case .destructive:
            return isHovered ? .red : .secondary
        case .prominent:
            return .white
        }
    }

    private var backgroundStyle: Color {
        if !isEnabled {
            return Color.secondary.opacity(0.06)
        }
        switch variant {
        case .normal:
            if configuration.isPressed {
                return Color.accentColor.opacity(0.22)
            }
            return isHovered ? Color.accentColor.opacity(0.16) : Color.secondary.opacity(0.10)
        case .destructive:
            if configuration.isPressed {
                return Color.red.opacity(0.20)
            }
            return isHovered ? Color.red.opacity(0.14) : Color.secondary.opacity(0.10)
        case .prominent:
            if configuration.isPressed {
                return Color.accentColor.opacity(0.72)
            }
            return Color.accentColor.opacity(isHovered ? 0.88 : 0.82)
        }
    }

    private var borderStyle: Color {
        switch variant {
        case .normal:
            return Color.accentColor.opacity(0.36)
        case .destructive:
            return Color.red.opacity(0.32)
        case .prominent:
            return Color.clear
        }
    }

    private var borderLineWidth: CGFloat {
        isHovered && isEnabled && variant != .prominent ? 1 : 0
    }
}

private struct SubscriptionHeaderActionButtonStyle: ButtonStyle {
    let role: ButtonRole?

    func makeBody(configuration: Configuration) -> some View {
        SubscriptionHeaderActionButton(
            configuration: configuration,
            role: role
        )
    }
}

private struct SubscriptionHeaderActionButton: View {
    let configuration: ButtonStyle.Configuration
    let role: ButtonRole?

    @Environment(\.isEnabled) private var isEnabled
    @State private var isHovered = false

    var body: some View {
        configuration.label
            .font(.system(size: 17, weight: .medium))
            .foregroundStyle(foregroundStyle)
            .frame(width: SubscriptionControlMetrics.iconButtonWidth, height: SubscriptionControlMetrics.controlHeight)
            .background(backgroundStyle, in: RoundedRectangle(cornerRadius: SubscriptionControlMetrics.cornerRadius, style: .continuous))
            .overlay {
                RoundedRectangle(cornerRadius: SubscriptionControlMetrics.cornerRadius, style: .continuous)
                    .strokeBorder(borderStyle, lineWidth: isHovered && isEnabled ? 1 : 0)
            }
            .contentShape(RoundedRectangle(cornerRadius: SubscriptionControlMetrics.cornerRadius, style: .continuous))
            .scaleEffect(configuration.isPressed ? 0.97 : 1)
            .animation(.easeOut(duration: 0.12), value: isHovered)
            .animation(.easeOut(duration: 0.08), value: configuration.isPressed)
            .onHover { isHovered = $0 }
    }

    private var isDestructive: Bool {
        role == .destructive
    }

    private var foregroundStyle: Color {
        if !isEnabled {
            return .secondary.opacity(0.48)
        }
        if isDestructive && isHovered {
            return .red
        }
        return isHovered ? .primary : .secondary
    }

    private var backgroundStyle: Color {
        if !isEnabled {
            return Color.secondary.opacity(0.06)
        }
        if configuration.isPressed {
            return isDestructive ? Color.red.opacity(0.20) : Color.accentColor.opacity(0.22)
        }
        if isHovered {
            return isDestructive ? Color.red.opacity(0.14) : Color.accentColor.opacity(0.16)
        }
        return Color.secondary.opacity(0.10)
    }

    private var borderStyle: Color {
        isDestructive ? Color.red.opacity(0.32) : Color.accentColor.opacity(0.36)
    }
}

private struct SubscriptionFastTooltipModifier: ViewModifier {
    let text: String

    @State private var isHovered = false
    @State private var isPresented = false
    @State private var presentationTask: Task<Void, Never>?

    private let delayNanoseconds: UInt64 = 180_000_000

    func body(content: Content) -> some View {
        content
            .onHover(perform: updateHoverState)
            .overlay(alignment: .bottom) {
                if isPresented {
                    Text(text)
                        .font(.system(size: 12, weight: .medium))
                        .foregroundStyle(.white)
                        .lineLimit(1)
                        .fixedSize(horizontal: true, vertical: false)
                        .padding(.horizontal, 8)
                        .padding(.vertical, 5)
                        .background(
                            Color.black.opacity(0.86),
                            in: RoundedRectangle(cornerRadius: 6, style: .continuous)
                        )
                        .offset(y: 34)
                        .transition(.opacity.combined(with: .scale(scale: 0.98)))
                        .allowsHitTesting(false)
                }
            }
            .zIndex(isPresented ? 1 : 0)
            .animation(.easeOut(duration: 0.10), value: isPresented)
    }

    private func updateHoverState(_ hovered: Bool) {
        isHovered = hovered
        presentationTask?.cancel()

        if hovered {
            presentationTask = Task {
                try? await Task.sleep(nanoseconds: delayNanoseconds)
                guard !Task.isCancelled else { return }
                await MainActor.run {
                    if isHovered {
                        isPresented = true
                    }
                }
            }
        } else {
            isPresented = false
            presentationTask = nil
        }
    }
}

private extension View {
    func subscriptionFastTooltip(_ text: String) -> some View {
        modifier(SubscriptionFastTooltipModifier(text: text))
    }
}

private struct SubscriptionEpisodeInfoSheet: View {
    let item: ProcessLibraryItem
    let details: ChannelEpisodeDetails
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            header
                .padding(22)
            Divider()
            ScrollView {
                VStack(alignment: .leading, spacing: 18) {
                    metadataGrid
                    descriptionSection
                }
                .padding(22)
            }
            Divider()
            footer
                .padding(.horizontal, 22)
                .padding(.vertical, 14)
        }
        .frame(minWidth: 520, idealWidth: 620, maxWidth: 720, minHeight: 420, idealHeight: 560)
    }

    private var header: some View {
        HStack(alignment: .top, spacing: 14) {
            coverImage
            VStack(alignment: .leading, spacing: 7) {
                Text(details.title)
                    .font(.title3.weight(.semibold))
                    .lineLimit(3)
                    .textSelection(.enabled)
                HStack(spacing: 8) {
                    statusPill(item.isProcessed ? "Processed" : "Unprocessed", tint: item.isProcessed ? .green : .blue)
                    statusPill(item.queueStatus.compactTitle, tint: .secondary)
                }
                if let seriesName = details.seriesName {
                    Text(seriesName)
                        .font(.callout)
                        .foregroundStyle(.secondary)
                        .lineLimit(2)
                        .textSelection(.enabled)
                }
            }
            Spacer(minLength: 0)
        }
    }

    @ViewBuilder
    private var coverImage: some View {
        if let url = remoteURL(details.imageURL) {
            AsyncImage(url: url) { phase in
                switch phase {
                case let .success(image):
                    image
                        .resizable()
                        .scaledToFill()
                case .failure:
                    fallbackCover
                case .empty:
                    ProgressView()
                @unknown default:
                    fallbackCover
                }
            }
            .frame(width: 92, height: 92)
            .background(Color.secondary.opacity(0.08), in: RoundedRectangle(cornerRadius: 8))
            .clipShape(RoundedRectangle(cornerRadius: 8))
        } else {
            fallbackCover
        }
    }

    private var fallbackCover: some View {
        Image(systemName: "dot.radiowaves.left.and.right")
            .font(.system(size: 30, weight: .semibold))
            .foregroundStyle(.secondary)
            .frame(width: 92, height: 92)
            .background(Color.secondary.opacity(0.08), in: RoundedRectangle(cornerRadius: 8))
    }

    private func statusPill(_ title: String, tint: Color) -> some View {
        Text(title)
            .font(.caption.weight(.semibold))
            .foregroundStyle(tint)
            .padding(.horizontal, 9)
            .padding(.vertical, 4)
            .background(tint.opacity(0.12), in: Capsule())
    }

    private var metadataGrid: some View {
        VStack(alignment: .leading, spacing: 9) {
            detailRow("Channel", details.seriesName)
            detailRow("Source", details.sourceName)
            detailRow("Published", details.publishedAt)
            detailRow("Duration", details.duration)
            detailRow("Episode Link", details.sourceURL)
            detailRow("Feed", details.seriesURL)
            detailRow("Audio", details.audioURL)
            detailRow("GUID", details.guid)
        }
        .textSelection(.enabled)
        .padding(14)
        .background(Color.secondary.opacity(0.06), in: RoundedRectangle(cornerRadius: 8))
    }

    @ViewBuilder
    private func detailRow(_ title: String, _ value: String?) -> some View {
        if let value = clean(value) {
            HStack(alignment: .firstTextBaseline, spacing: 12) {
                Text(title)
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(.secondary)
                    .frame(width: 92, alignment: .leading)
                Text(value)
                    .font(.callout)
                    .lineLimit(3)
                    .truncationMode(.middle)
                Spacer(minLength: 0)
            }
        }
    }

    private var descriptionSection: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("Description")
                .font(.headline)
            Text(clean(details.description) ?? "No description from feed.")
                .font(.callout)
                .foregroundStyle(clean(details.description) == nil ? .secondary : .primary)
                .lineSpacing(3)
                .textSelection(.enabled)
        }
    }

    private var footer: some View {
        HStack(spacing: 8) {
            Button {
                copyPrimaryURLToPasteboard()
            } label: {
                Label("Copy Link", systemImage: "link")
            }
            .disabled(clean(details.primaryURL) == nil)
            Spacer()
            Button {
                dismiss()
            } label: {
                Label("Close", systemImage: "xmark")
            }
            .keyboardShortcut(.cancelAction)
        }
    }

    private func copyPrimaryURLToPasteboard() {
        guard let url = clean(details.primaryURL) else { return }
        NSPasteboard.general.clearContents()
        NSPasteboard.general.setString(url, forType: .string)
    }

    private func clean(_ value: String?) -> String? {
        let trimmed = value?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
        return trimmed.isEmpty ? nil : trimmed
    }

    private func remoteURL(_ value: String?) -> URL? {
        guard let text = clean(value), let url = URL(string: text), ["http", "https"].contains(url.scheme?.lowercased()) else {
            return nil
        }
        return url
    }
}
