import AppKit
import SwiftUI
#if canImport(Audio2TextCore)
    import Audio2TextCore
#endif

extension ProcessSidebarView {
    var subscriptionsSection: some View {
        VStack(alignment: .leading, spacing: SidebarMetrics.rowSpacing) {
            subscriptionsHeader
            subscriptionsRows
        }
    }

    var subscriptionsHeader: some View {
        HStack(spacing: 8) {
            sidebarHeader("Subscriptions")
            Spacer()
            Button {
                controller.refreshAllSubscriptions()
            } label: {
                Image(systemName: "arrow.clockwise")
                    .font(.system(size: 12, weight: .medium))
                    .frame(width: 22, height: 20)
            }
            .buttonStyle(.plain)
            .foregroundStyle(.secondary)
            .help("Refresh all subscriptions")
            .disabled(controller.subscriptions.isEmpty || controller.isRefreshingSubscriptions || controller.isAddingSubscription)
            .padding(.trailing, 6)
        }
    }

    @ViewBuilder
    var subscriptionsRows: some View {
        if controller.subscriptions.isEmpty {
            Text("No subscriptions")
                .font(.system(size: SidebarMetrics.countFontSize, weight: .regular))
                .foregroundStyle(.secondary)
                .padding(.leading, 26)
                .frame(height: SidebarMetrics.itemRowHeight)
        } else {
            ForEach(controller.subscriptions) { subscription in
                subscriptionListRow(subscription)
            }
        }
    }

    func subscriptionListRow(_ subscription: PodcastSubscriptionItem) -> some View {
        let counts = controller.subscriptionItemCounts(for: subscription)
        let isSelected = controller.selectedSubscriptionID == subscription.id
        return Button {
            controller.selectSubscription(subscription)
        } label: {
            HStack(alignment: .top, spacing: 8) {
                Image(systemName: subscription.source == "xiaoyuzhou" ? "dot.radiowaves.left.and.right" : "antenna.radiowaves.left.and.right")
                    .font(.system(size: 14, weight: .semibold))
                    .foregroundStyle(isSelected ? Color.accentColor : Color.purple)
                    .frame(width: 18, height: 20)

                VStack(alignment: .leading, spacing: 3) {
                    HStack(alignment: .firstTextBaseline, spacing: 6) {
                        Text(subscription.title)
                            .font(.system(size: SidebarMetrics.titleFontSize, weight: isSelected ? .semibold : .regular))
                            .foregroundStyle(.primary)
                            .lineLimit(1)
                            .truncationMode(.tail)
                        if counts.total > 0 {
                            Text("\(counts.unprocessed)/\(counts.total)")
                                .font(.system(size: SidebarMetrics.countFontSize, weight: .semibold, design: .rounded).monospacedDigit())
                                .foregroundStyle(counts.unprocessed > 0 ? Color.blue : Color.secondary)
                                .fixedSize(horizontal: true, vertical: false)
                        }
                    }
                    HStack(spacing: 6) {
                        Label(subscription.groupName, systemImage: "folder")
                        if !subscription.lastCheckedAt.isEmpty {
                            Label(subscription.lastCheckedAt, systemImage: "clock")
                        }
                    }
                    .font(.system(size: 11, weight: .regular))
                    .foregroundStyle(.secondary)
                    .lineLimit(1)
                    Text(subscriptionDisplayURL(subscription))
                        .font(.system(size: 11, weight: .regular))
                        .foregroundStyle(.secondary)
                        .lineLimit(1)
                        .truncationMode(.middle)
                }
                Spacer(minLength: 4)
            }
            .padding(.horizontal, SidebarMetrics.rowHorizontalPadding)
            .padding(.vertical, 7)
            .background(
                RoundedRectangle(cornerRadius: SidebarMetrics.rowCornerRadius)
                    .fill(isSelected ? Color.accentColor.opacity(0.16) : Color.clear)
            )
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .contextMenu {
            Button {
                controller.refreshSubscription(subscription)
            } label: {
                Label("Refresh subscription", systemImage: "arrow.clockwise")
            }
            .disabled(controller.isRefreshingSubscriptions || controller.isAddingSubscription)

            Button {
                controller.fetchSubscriptionHistory(subscription)
            } label: {
                Label("Fetch complete history", systemImage: "clock.arrow.circlepath")
            }
            .disabled(controller.isRefreshingSubscriptions || controller.isAddingSubscription)

            Button {
                copySubscriptionURLToPasteboard(subscription)
            } label: {
                Label("Copy link", systemImage: "link")
            }

            Divider()

            Button(role: .destructive) {
                controller.removeSubscription(subscription)
            } label: {
                Label("Remove subscription", systemImage: "trash")
            }
            .disabled(controller.isRefreshingSubscriptions || controller.isAddingSubscription)
        }
    }

    func subscriptionDisplayURL(_ subscription: PodcastSubscriptionItem) -> String {
        let feedURL = subscription.feedURL.trimmingCharacters(in: .whitespacesAndNewlines)
        if !feedURL.isEmpty { return feedURL }
        let url = subscription.url.trimmingCharacters(in: .whitespacesAndNewlines)
        return url.isEmpty ? "No URL" : url
    }

    func copySubscriptionURLToPasteboard(_ subscription: PodcastSubscriptionItem) {
        let url = subscriptionDisplayURL(subscription)
        guard url != "No URL" else { return }
        let pasteboard = NSPasteboard.general
        pasteboard.clearContents()
        pasteboard.setString(url, forType: .string)
    }
}
