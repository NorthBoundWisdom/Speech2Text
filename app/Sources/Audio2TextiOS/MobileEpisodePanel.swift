import SwiftUI
#if canImport(Audio2TextCore)
    import Audio2TextCore
#endif

struct MobileEpisodePanel: View {
    private static let episodeListAnimation = Animation.easeInOut(duration: 0.22)
    private static var episodeRowTransition: AnyTransition {
        .asymmetric(
            insertion: .move(edge: .top).combined(with: .opacity),
            removal: .move(edge: .top).combined(with: .opacity)
        )
    }

    enum HeaderDisplayMode {
        case column
        case systemNavigation
    }

    @ObservedObject var store: MobileLibraryViewModel
    let sections: [MobileEpisodeSection]
    let selectedEpisodeID: String?
    var selectedSubscriptionID: String? = nil
    let selectedSource: LibrarySidebarSource
    let selectedSourceTitle: String
    var isSourcePanelVisible = true
    var hidesReadItems = false
    var canToggleHidingReadItems = false
    var onToggleSourcePanel: (() -> Void)?
    let onSelectEpisode: (LibraryEpisode) -> Void
    var onSelectSubscription: ((LibrarySubscription) -> Void)?
    let onAddSubscription: () -> Void
    let onMarkEpisodeRead: (LibraryEpisode) -> Void
    let onToggleEpisodeStar: (LibraryEpisode) -> Void
    let onToggleHidingReadItems: () -> Void
    let onArchiveEpisode: (LibraryEpisode) -> Void
    let onDeleteEpisode: (LibraryEpisode) -> Void
    let onMoveEpisode: (LibraryEpisode, String) -> Void
    let onCopyEpisodeLink: (LibraryEpisode) -> Void
    let onRefreshSubscription: (LibrarySubscription) -> Void
    let onFetchSubscriptionHistory: (LibrarySubscription) -> Void
    let onDeleteSubscription: (LibrarySubscription) -> Void
    let onCopySubscriptionLink: (LibrarySubscription) -> Void
    var headerDisplayMode: HeaderDisplayMode = .column
    var onBack: (() -> Void)?

    var body: some View {
        VStack(spacing: 0) {
            if headerDisplayMode == .column {
                columnHeader
                MobileColumnDivider(axis: .horizontal)
            }

            List {
                if isSubscriptionsSource {
                    ForEach(store.subscriptions) { subscription in
                        MobileSubscriptionRow(
                            subscription: subscription,
                            isRefreshing: store.isRefreshing,
                            onRefresh: onRefreshSubscription,
                            onFetchHistory: onFetchSubscriptionHistory,
                            onDelete: onDeleteSubscription,
                            onCopyLink: onCopySubscriptionLink
                        )
                        .contentShape(Rectangle())
                        .onTapGesture {
                            onSelectSubscription?(subscription)
                        }
                        .listRowBackground(subscriptionRowBackground(for: subscription))
                    }
                } else {
                    ForEach(sections) { section in
                        Section {
                            episodeRows(section.episodes)
                        } header: {
                            if showsSectionHeaders {
                                Text(section.title)
                            }
                        }
                    }
                }
            }
            .listStyle(.plain)
            .scrollContentBackground(.hidden)
            .animation(Self.episodeListAnimation, value: visibleEpisodeIDs)
            .overlay {
                if isEmpty {
                    MobileAdaptiveEmptyState(
                        title: emptyTitle,
                        message: emptyMessage,
                        systemImage: emptySystemImage
                    )
                    .padding(.horizontal, 24)
                }
            }
            .refreshable {
                store.load()
            }
        }
        .background(Color.mobileContentBackground)
        .navigationTitle(headerDisplayMode == .systemNavigation ? selectedSourceTitle : "")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            if headerDisplayMode == .systemNavigation {
                ToolbarItemGroup(placement: .topBarTrailing) {
                    if canToggleHidingReadItems {
                        readFilterButton
                    }

                    if isSubscriptionsSource {
                        MobileIconButton(
                            systemName: "plus",
                            label: "Add Subscription",
                            isDisabled: store.libraryRoot == nil || store.isRefreshing,
                            action: onAddSubscription
                        )
                    }
                }
            }
        }
    }

    private var readFilterButton: some View {
        MobileIconButton(
            systemName: readFilterSystemName,
            label: readFilterLabel,
            action: onToggleHidingReadItems
        )
    }

    private var readFilterSystemName: String {
        hidesReadItems ? "line.3.horizontal.decrease.circle.fill" : "line.3.horizontal.decrease.circle"
    }

    private var readFilterLabel: String {
        hidesReadItems ? "显示已读" : "隐藏已读"
    }

    private var columnHeader: some View {
        VStack(alignment: .leading, spacing: 9) {
            HStack(spacing: 10) {
                if let onBack {
                    MobileInlineBackButton(action: onBack)
                }

                VStack(alignment: .leading, spacing: 2) {
                    Text(selectedSourceTitle)
                        .font(.title3.bold())
                        .lineLimit(1)
                    Text(countLabel)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                Spacer()

                if canToggleHidingReadItems {
                    readFilterButton
                }

                if let onToggleSourcePanel {
                    MobileIconButton(
                        systemName: "sidebar.left",
                        label: isSourcePanelVisible ? "Hide Left Panel" : "Show Left Panel",
                        action: onToggleSourcePanel
                    )
                }

                if isSubscriptionsSource {
                    MobileIconButton(
                        systemName: "plus",
                        label: "Add Subscription",
                        isDisabled: store.libraryRoot == nil || store.isRefreshing,
                        action: onAddSubscription
                    )
                }
            }
        }
        .padding(.horizontal, 16)
        .padding(.top, onBack == nil ? 12 : 8)
        .padding(.bottom, 8)
    }

    private var documentCount: Int {
        sections.reduce(0) { $0 + $1.episodes.count }
    }

    private var isEmpty: Bool {
        isSubscriptionsSource ? store.subscriptions.isEmpty : documentCount == 0
    }

    private var isSubscriptionsSource: Bool {
        if case .subscriptions = selectedSource {
            return true
        }
        return false
    }

    private var countLabel: String {
        isSubscriptionsSource ? "\(store.subscriptions.count) subscriptions" : "\(documentCount) documents"
    }

    private var showsSectionHeaders: Bool {
        sections.count > 1
    }

    private var visibleEpisodeIDs: [String] {
        sections.flatMap { section in
            section.episodes.map(\.id)
        }
    }

    private var emptyTitle: String {
        isSubscriptionsSource ? "No Subscriptions" : (store.episodes.isEmpty ? mobileEmptyStateTitle(for: store) : "No Matching Documents")
    }

    private var emptyMessage: String {
        if isSubscriptionsSource {
            return "Add a subscription to create metadata-only episode records."
        }
        return store.episodes.isEmpty ? mobileEmptyStateMessage(for: store) : "Try another source."
    }

    private var emptySystemImage: String {
        isSubscriptionsSource ? "dot.radiowaves.left.and.right" : (store.episodes.isEmpty ? mobileEmptyStateSystemImage(for: store) : "tray")
    }

    private func rowBackground(for episode: LibraryEpisode) -> Color {
        episode.id == selectedEpisodeID ? Color.accentColor.opacity(0.12) : Color.clear
    }

    private func subscriptionRowBackground(for subscription: LibrarySubscription) -> Color {
        subscription.id == selectedSubscriptionID ? Color.accentColor.opacity(0.12) : Color.clear
    }

    private func episodeRows(_ episodes: [LibraryEpisode]) -> some View {
        ForEach(episodes) { episode in
            Button {
                onSelectEpisode(episode)
            } label: {
                EpisodeRow(episode: episode)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .contentShape(Rectangle())
            }
            .buttonStyle(.plain)
            .contextMenu {
                episodeContextMenu(for: episode)
            }
            .swipeActions(edge: .leading, allowsFullSwipe: false) {
                Button {
                    onMarkEpisodeRead(episode)
                } label: {
                    Label(episode.isRead ? "Unread" : "Read", systemImage: episode.isRead ? "circle" : "checkmark.circle")
                }
                .tint(.blue)

                Button {
                    onToggleEpisodeStar(episode)
                } label: {
                    Label(episode.isStarred ? "Unstar" : "Star", systemImage: episode.isStarred ? "star.slash" : "star")
                }
                .tint(.yellow)
            }
            .swipeActions(edge: .trailing, allowsFullSwipe: false) {
                Button(role: .destructive) {
                    onDeleteEpisode(episode)
                } label: {
                    Label("Delete", systemImage: "trash")
                }

                Button {
                    onArchiveEpisode(episode)
                } label: {
                    Label(episode.isArchived ? "Unarchive" : "Archive", systemImage: episode.isArchived ? "tray.and.arrow.up" : "archivebox")
                }
                .tint(.orange)
            }
            .listRowBackground(rowBackground(for: episode))
            .transition(Self.episodeRowTransition)
        }
    }

    @ViewBuilder
    private func episodeContextMenu(for episode: LibraryEpisode) -> some View {
        Button {
            onMarkEpisodeRead(episode)
        } label: {
            Label(episode.isRead ? "Mark as Unread" : "Mark as Read", systemImage: episode.isRead ? "circle" : "checkmark.circle")
        }

        Button {
            onToggleEpisodeStar(episode)
        } label: {
            Label(episode.isStarred ? "Unstar" : "Star", systemImage: episode.isStarred ? "star.slash" : "star")
        }

        Menu {
            ForEach(store.availableGroupNames, id: \.self) { groupName in
                if groupName == LibrarySidebarItem.normalizedGroupName(episode.appGroup) {
                    Button {} label: {
                        Label(groupName, systemImage: "checkmark")
                    }
                    .disabled(true)
                } else {
                    Button(groupName) {
                        onMoveEpisode(episode, groupName)
                    }
                }
            }
        } label: {
            Label("Move to Group", systemImage: "folder")
        }

        Button {
            onArchiveEpisode(episode)
        } label: {
            Label(episode.isArchived ? "Unarchive" : "Archive", systemImage: episode.isArchived ? "tray.and.arrow.up" : "archivebox")
        }

        Button {
            onCopyEpisodeLink(episode)
        } label: {
            Label("Copy Link", systemImage: "link")
        }

        Divider()

        Button(role: .destructive) {
            onDeleteEpisode(episode)
        } label: {
            Label("Delete Episode", systemImage: "trash")
        }
    }
}

private struct MobileSubscriptionRow: View {
    let subscription: LibrarySubscription
    let isRefreshing: Bool
    let onRefresh: (LibrarySubscription) -> Void
    let onFetchHistory: (LibrarySubscription) -> Void
    let onDelete: (LibrarySubscription) -> Void
    let onCopyLink: (LibrarySubscription) -> Void

    var body: some View {
        HStack(alignment: .center, spacing: 12) {
            Image(systemName: "dot.radiowaves.left.and.right")
                .font(.body)
                .foregroundStyle(.purple)
                .frame(width: 24, height: 28)

            VStack(alignment: .leading, spacing: 4) {
                Text(subscription.title)
                    .font(.headline)
                    .foregroundStyle(.primary)
                    .lineLimit(2)
                Text(subscription.feedURL ?? subscription.url ?? "No URL")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .lineLimit(1)
            }
        }
        .padding(.vertical, 4)
        .contextMenu {
            subscriptionContextMenu
        }
        .swipeActions(edge: .leading, allowsFullSwipe: false) {
            Button {
                onCopyLink(subscription)
            } label: {
                Label("Copy Link", systemImage: "link")
            }
            .tint(.blue)
        }
        .swipeActions(edge: .trailing, allowsFullSwipe: false) {
            Button(role: .destructive) {
                onDelete(subscription)
            } label: {
                Label("Remove", systemImage: "trash")
            }
            .disabled(isRefreshing)

            Button {
                onRefresh(subscription)
            } label: {
                Label("Refresh", systemImage: "arrow.clockwise")
            }
            .tint(.green)
            .disabled(isRefreshing)
        }
    }

    @ViewBuilder
    private var subscriptionContextMenu: some View {
        Button {
            onRefresh(subscription)
        } label: {
            Label("Refresh Subscription", systemImage: "arrow.clockwise")
        }
        .disabled(isRefreshing)

        Button {
            onFetchHistory(subscription)
        } label: {
            Label("Fetch Full History", systemImage: "clock.arrow.circlepath")
        }
        .disabled(isRefreshing)

        Button {
            onCopyLink(subscription)
        } label: {
            Label("Copy Link", systemImage: "link")
        }

        Divider()

        Button(role: .destructive) {
            onDelete(subscription)
        } label: {
            Label("Remove Subscription", systemImage: "trash")
        }
        .disabled(isRefreshing)
    }
}

private struct MobileEpisodeOverviewRow: View {
    let episodeCount: Int
    let subscriptionCount: Int
    let availableCount: Int

    var body: some View {
        HStack(spacing: 12) {
            Image(systemName: "waveform")
                .font(.title3)
                .foregroundStyle(.blue)
                .frame(width: 24)
            VStack(alignment: .leading, spacing: 2) {
                Text("\(episodeCount) Episodes")
                    .font(.headline)
                Text("\(availableCount) ready to read · \(subscriptionCount) subscriptions")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
        .padding(.vertical, 3)
    }
}
