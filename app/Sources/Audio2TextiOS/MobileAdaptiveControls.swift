import SwiftUI
#if canImport(Audio2TextCore)
    import Audio2TextCore
#endif

struct MobileReaderActionButton: View {
    let title: String
    let systemName: String
    var role: ButtonRole?
    var isDisabled = false
    let action: () -> Void

    var body: some View {
        Button(role: role, action: action) {
            VStack(spacing: 2) {
                Image(systemName: systemName)
                    .font(.system(size: 15, weight: .semibold))
                Text(title)
                    .font(.caption2.weight(.medium))
            }
            .frame(width: 42, height: 40)
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .foregroundStyle(foregroundStyle)
        .disabled(isDisabled)
        .accessibilityLabel(title)
    }

    private var foregroundStyle: Color {
        if isDisabled {
            return Color.secondary.opacity(0.45)
        }
        if role == .destructive {
            return Color.red
        }
        return Color.primary
    }
}

struct MobileInlineBackButton: View {
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            Image(systemName: "chevron.left")
                .font(.system(size: 17, weight: .semibold))
                .frame(width: 38, height: 38)
                .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .accessibilityLabel("Back")
    }
}

struct MobileIconButton: View {
    let systemName: String
    let label: String
    var isDisabled = false
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            Image(systemName: systemName)
                .font(.system(size: 17, weight: .semibold))
                .frame(width: 34, height: 34)
                .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .foregroundStyle(isDisabled ? Color.secondary.opacity(0.45) : Color.primary)
        .disabled(isDisabled)
        .accessibilityLabel(label)
    }
}

struct MobileAdaptiveStatusFooter: View {
    @ObservedObject var store: MobileLibraryViewModel

    var body: some View {
        Group {
            if store.isRefreshing {
                Label("Refreshing", systemImage: "arrow.clockwise")
                    .font(.footnote)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(.horizontal, 10)
                    .padding(.vertical, 8)
                    .background(Color.mobileSearchBackground, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
            } else if !store.statusMessage.isEmpty {
                Text(store.statusMessage)
                    .font(.footnote)
                    .foregroundStyle(.secondary)
                    .lineLimit(3)
                    .fixedSize(horizontal: false, vertical: true)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(.horizontal, 10)
                    .padding(.vertical, 8)
                    .background(Color.mobileSearchBackground, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
            }
        }
    }
}

struct MobileAdaptiveEmptyState: View {
    let title: String
    let message: String
    let systemImage: String

    var body: some View {
        VStack(spacing: 12) {
            Image(systemName: systemImage)
                .font(.system(size: 38, weight: .regular))
                .foregroundStyle(.secondary)
            Text(title)
                .font(.title3.bold())
                .multilineTextAlignment(.center)
            Text(message)
                .font(.callout)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
                .fixedSize(horizontal: false, vertical: true)
        }
        .frame(maxWidth: 360)
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}

struct MobileColumnDivider: View {
    enum Axis {
        case vertical
        case horizontal
    }

    var axis: Axis = .vertical

    var body: some View {
        Rectangle()
            .fill(Color.mobileDivider)
            .frame(
                width: axis == .vertical ? 1 : nil,
                height: axis == .horizontal ? 1 : nil
            )
    }
}

@MainActor
func mobileEmptyStateTitle(for store: MobileLibraryViewModel) -> String {
    store.libraryRoot == nil ? "Library Unavailable" : "No Documents"
}

@MainActor
func mobileEmptyStateMessage(for store: MobileLibraryViewModel) -> String {
    if store.libraryRoot == nil {
        return "Choose your Audio2TextLibrary folder in Settings."
    }
    return store.statusMessage.isEmpty ? "No synced Audio2Text library was found." : store.statusMessage
}

@MainActor
func mobileEmptyStateSystemImage(for store: MobileLibraryViewModel) -> String {
    store.libraryRoot == nil ? "folder" : "tray"
}

func mobileDateLabel(for episode: LibraryEpisode) -> String {
    mobileClean(episode.localPublishedAt ?? episode.publishedAt) ?? "No date"
}

func mobileClean(_ value: String?) -> String? {
    guard let value else { return nil }
    let trimmed = value.trimmingCharacters(in: .whitespacesAndNewlines)
    return trimmed.isEmpty ? nil : trimmed
}

extension Color {
    static var mobileShellBackground: Color {
        Color(.systemGroupedBackground)
    }

    static var mobilePanelBackground: Color {
        Color(.secondarySystemGroupedBackground)
    }

    static var mobileContentBackground: Color {
        Color(.systemGroupedBackground)
    }

    static var mobileReaderBackground: Color {
        Color(.systemBackground)
    }

    static var mobileSearchBackground: Color {
        Color(.tertiarySystemGroupedBackground)
    }

    static var mobileDivider: Color {
        Color(.separator)
    }
}
