import SwiftUI
#if canImport(Audio2TextCore)
    import Audio2TextCore
#endif

struct MobileSourcePanel: View {
    enum TitleDisplayMode {
        case system
        case large
        case compact
    }

    @ObservedObject var store: MobileLibraryViewModel
    let sidebarState: LibrarySidebarState
    let selectedSource: LibrarySidebarSource
    @Binding var isShowingSettings: Bool
    let onSelectSource: (LibrarySidebarSource) -> Void
    let titleDisplayMode: TitleDisplayMode

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            MobileSourceHeader(
                store: store,
                isShowingSettings: $isShowingSettings,
                titleDisplayMode: titleDisplayMode
            )

            ScrollView {
                LazyVStack(alignment: .leading, spacing: 5) {
                    ForEach(sidebarState.smartFeedRows) { item in
                        MobileSourceRow(
                            item: item,
                            isSelected: item.source == selectedSource
                        ) {
                            onSelectSource(item.source)
                        }
                    }

                    HStack(spacing: 8) {
                        Text("Folders")
                            .font(.caption.weight(.semibold))
                            .foregroundStyle(.secondary)
                        Spacer()
                    }
                    .padding(.horizontal, 6)
                    .padding(.top, 14)
                    .padding(.bottom, 2)

                    ForEach(sidebarState.folderRows()) { item in
                        MobileSourceRow(
                            item: item,
                            isSelected: item.source == selectedSource
                        ) {
                            onSelectSource(item.source)
                        }
                    }
                }
                .padding(.horizontal, 10)
                .padding(.vertical, 10)
            }
            .refreshable {
                store.load()
            }

            MobileAdaptiveStatusFooter(store: store)
                .padding(.horizontal, 10)
                .padding(.bottom, 10)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
        .background(Color.mobilePanelBackground)
        .navigationTitle(titleDisplayMode == .system ? "Audio2Text" : "")
        .navigationBarTitleDisplayMode(titleDisplayMode == .system ? .large : .inline)
        .toolbar {
            if titleDisplayMode == .system {
                ToolbarItemGroup(placement: .topBarTrailing) {
                    MobileSyncStatusIconButton(status: store.displayedLibrarySyncStatus) {
                        store.refreshSyncStatus()
                    }

                    MobileIconButton(systemName: "gearshape", label: "Settings") {
                        isShowingSettings = true
                    }
                }
            }
        }
    }
}

private struct MobileSourceHeader: View {
    @ObservedObject var store: MobileLibraryViewModel
    @Binding var isShowingSettings: Bool
    let titleDisplayMode: MobileSourcePanel.TitleDisplayMode

    var body: some View {
        VStack(alignment: .leading, spacing: titleDisplayMode == .system ? 0 : 14) {
            if titleDisplayMode != .system {
                HStack(alignment: .center, spacing: 12) {
                    Text("Audio2Text")
                        .font(titleDisplayMode == .large ? .largeTitle.bold() : .title2.bold())
                        .lineLimit(1)
                        .minimumScaleFactor(0.8)

                    Spacer(minLength: 8)

                    MobileSyncStatusIconButton(status: store.displayedLibrarySyncStatus) {
                        store.refreshSyncStatus()
                    }

                    MobileIconButton(systemName: "gearshape", label: "Settings") {
                        isShowingSettings = true
                    }
                }
            }

            HStack(spacing: 14) {
                MobileMetricPill(value: store.episodes.count, label: "Episodes")
                MobileMetricPill(value: store.episodes.filter(\.hasSyncedDocuments).count, label: "Ready")
                MobileMetricPill(value: store.subscriptions.count, label: "Feeds")
            }
        }
        .padding(.horizontal, 16)
        .padding(.top, headerTopPadding)
        .padding(.bottom, titleDisplayMode == .system ? 8 : 12)
        .background(Color.mobilePanelBackground)
    }

    private var headerTopPadding: CGFloat {
        switch titleDisplayMode {
        case .system:
            return 8
        case .large:
            return 28
        case .compact:
            return 14
        }
    }
}

private struct MobileSyncStatusIconButton: View {
    let status: LibrarySyncStatus
    let refresh: () -> Void

    var body: some View {
        Button(action: refresh) {
            Image(systemName: mobileSyncStatusSystemImage(for: status.state))
                .font(.system(size: 15, weight: .semibold))
                .foregroundStyle(mobileSyncStatusTint(for: status.state))
                .frame(width: 30, height: 30)
                .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .accessibilityLabel("同步状态：\(status.title)")
        .accessibilityHint(status.detail)
    }
}

struct MobileSyncStatusPill: View {
    let status: LibrarySyncStatus
    let refresh: () -> Void

    var body: some View {
        Button(action: refresh) {
            HStack(spacing: 8) {
                Image(systemName: mobileSyncStatusSystemImage(for: status.state))
                    .font(.system(size: 14, weight: .semibold))
                    .frame(width: 18)
                VStack(alignment: .leading, spacing: 1) {
                    Text(status.title)
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(.primary)
                        .lineLimit(1)
                    Text(status.detail)
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                        .lineLimit(1)
                        .truncationMode(.middle)
                }
                Spacer(minLength: 6)
            }
            .foregroundStyle(mobileSyncStatusTint(for: status.state))
            .padding(.horizontal, 10)
            .padding(.vertical, 8)
            .background(Color.mobileSearchBackground, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
        }
        .buttonStyle(.plain)
        .accessibilityLabel("同步状态：\(status.title)")
        .accessibilityHint(status.detail)
    }
}

private func mobileSyncStatusSystemImage(for state: LibrarySyncStatus.State) -> String {
    switch state {
    case .syncing:
        return "arrow.triangle.2.circlepath.icloud"
    case .offline:
        return "wifi.slash"
    case .synced:
        return "checkmark.icloud.fill"
    }
}

private func mobileSyncStatusTint(for state: LibrarySyncStatus.State) -> Color {
    switch state {
    case .syncing:
        return .blue
    case .offline:
        return .orange
    case .synced:
        return .green
    }
}

private struct MobileMetricPill: View {
    let value: Int
    let label: String

    var body: some View {
        VStack(alignment: .leading, spacing: 1) {
            Text("\(value)")
                .font(.headline.weight(.semibold))
            Text(label)
                .font(.caption2)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }
}

private struct MobileSourceRow: View {
    let item: LibrarySidebarRow
    let isSelected: Bool
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack(spacing: 11) {
                Image(systemName: item.systemImage)
                    .font(.system(size: 16, weight: .semibold))
                    .foregroundStyle(isSelected ? Color.accentColor : .secondary)
                    .frame(width: 24, height: 24)

                VStack(alignment: .leading, spacing: 2) {
                    Text(item.title)
                        .font(.callout.weight(.semibold))
                        .foregroundStyle(.primary)
                        .lineLimit(1)
                }

                Spacer(minLength: 8)

                Text("\(item.count)")
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(.secondary)
                    .padding(.horizontal, 7)
                    .padding(.vertical, 3)
                    .background(Color.secondary.opacity(0.12), in: Capsule())
            }
            .padding(.horizontal, 10)
            .frame(maxWidth: .infinity, minHeight: 46, alignment: .leading)
            .background(
                RoundedRectangle(cornerRadius: 8, style: .continuous)
                    .fill(isSelected ? Color.accentColor.opacity(0.14) : Color.clear)
            )
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .accessibilityAddTraits(isSelected ? .isSelected : [])
    }
}
