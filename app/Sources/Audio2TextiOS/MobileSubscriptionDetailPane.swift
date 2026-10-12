import SwiftUI
#if canImport(Audio2TextCore)
    import Audio2TextCore
#endif

struct MobileSubscriptionDetailPane: View {
    let subscription: LibrarySubscription?
    let episodes: [LibraryEpisode]
    let isRefreshing: Bool
    let onRefresh: (LibrarySubscription) -> Void
    let onFetchHistory: (LibrarySubscription) -> Void
    let onDelete: (LibrarySubscription) -> Void
    let onCopyLink: (LibrarySubscription) -> Void

    var body: some View {
        Group {
            if let subscription {
                VStack(alignment: .leading, spacing: 0) {
                    header(subscription)
                    MobileColumnDivider(axis: .horizontal)
                    ScrollView {
                        VStack(alignment: .leading, spacing: 18) {
                            stats
                            episodesSection
                            metadataSection(subscription)
                        }
                        .frame(maxWidth: 760, alignment: .leading)
                        .frame(maxWidth: .infinity, alignment: .center)
                        .padding(.horizontal, 20)
                        .padding(.vertical, 18)
                    }
                }
            } else {
                MobileAdaptiveEmptyState(
                    title: "No Subscription",
                    message: "Select a subscription to inspect its episodes and feed metadata.",
                    systemImage: "dot.radiowaves.left.and.right"
                )
                .padding(.horizontal, 24)
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Color.mobileReaderBackground)
    }

    private func header(_ subscription: LibrarySubscription) -> some View {
        HStack(alignment: .center, spacing: 10) {
            VStack(alignment: .leading, spacing: 3) {
                Text(subscription.source ?? "Subscription")
                    .font(.subheadline.weight(.semibold))
                    .foregroundStyle(.secondary)
                    .lineLimit(1)
                Text(subscription.title)
                    .font(.title2.bold())
                    .lineLimit(2)
                    .fixedSize(horizontal: false, vertical: true)
            }
            .frame(maxWidth: .infinity, alignment: .leading)

            HStack(spacing: 4) {
                MobileReaderActionButton(title: "Copy", systemName: "link") {
                    onCopyLink(subscription)
                }
                MobileReaderActionButton(
                    title: "Refresh",
                    systemName: "arrow.clockwise",
                    isDisabled: isRefreshing
                ) {
                    onRefresh(subscription)
                }
                MobileReaderActionButton(
                    title: "History",
                    systemName: "clock.arrow.circlepath",
                    isDisabled: isRefreshing
                ) {
                    onFetchHistory(subscription)
                }
                MobileReaderActionButton(
                    title: "Remove",
                    systemName: "trash",
                    role: .destructive,
                    isDisabled: isRefreshing
                ) {
                    onDelete(subscription)
                }
            }
        }
        .padding(.horizontal, 20)
        .padding(.top, 16)
        .padding(.bottom, 12)
    }

    private var stats: some View {
        HStack(spacing: 10) {
            MobileSubscriptionStat(value: "\(episodes.count)", label: "Episodes", tint: .primary)
            MobileSubscriptionStat(value: "\(episodes.filter { !$0.hasSyncedDocuments }.count)", label: "Metadata", tint: .blue)
            MobileSubscriptionStat(value: "\(episodes.filter(\.hasSyncedDocuments).count)", label: "Ready", tint: .green)
        }
    }

    private var episodesSection: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("Current Episodes")
                .font(.headline)
            if episodes.isEmpty {
                Label("No episodes imported for this subscription yet.", systemImage: "tray")
                    .font(.callout)
                    .foregroundStyle(.secondary)
                    .padding(.vertical, 8)
            } else {
                VStack(spacing: 8) {
                    ForEach(episodes) { episode in
                        EpisodeRow(episode: episode)
                            .padding(.horizontal, 12)
                            .padding(.vertical, 8)
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .background(Color.mobileSearchBackground, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
                    }
                }
            }
        }
    }

    private func metadataSection(_ subscription: LibrarySubscription) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("Channel Metadata")
                .font(.headline)
            VStack(alignment: .leading, spacing: 9) {
                metadataRow(title: "Source", value: mobileClean(subscription.source) ?? "Unknown")
                metadataRow(title: "Group", value: mobileClean(subscription.groupName) ?? LibrarySidebarState.defaultGroupName)
                metadataRow(title: "Feed", value: subscriptionDisplayURL(subscription))
                metadataRow(title: "Created", value: mobileClean(subscription.createdAt) ?? "None")
                metadataRow(title: "Last Checked", value: mobileClean(subscription.lastCheckedAt) ?? "None")
            }
            .padding(14)
            .background(Color.mobileSearchBackground, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
        }
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

    private func subscriptionDisplayURL(_ subscription: LibrarySubscription) -> String {
        mobileClean(subscription.feedURL) ?? mobileClean(subscription.url) ?? "No URL"
    }
}

private struct MobileSubscriptionStat: View {
    let value: String
    let label: String
    let tint: Color

    var body: some View {
        VStack(alignment: .leading, spacing: 3) {
            Text(value)
                .font(.title3.weight(.semibold).monospacedDigit())
                .foregroundStyle(tint)
            Text(label)
                .font(.caption)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(12)
        .background(Color.mobileSearchBackground, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
    }
}
