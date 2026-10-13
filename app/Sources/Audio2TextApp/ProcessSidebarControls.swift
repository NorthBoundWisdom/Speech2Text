import SwiftUI
#if canImport(Audio2TextCore)
    import Audio2TextCore
#endif

struct LibrarySyncStatusCard: View {
    let status: LibrarySyncStatus
    var showsFullDetails = false
    let refresh: () -> Void

    var body: some View {
        Button(action: refresh) {
            VStack(alignment: .leading, spacing: 5) {
                HStack(alignment: .top, spacing: 8) {
                    Image(systemName: systemImage)
                        .font(.system(size: 13, weight: .semibold))
                        .frame(width: 18, height: 18)
                        .foregroundStyle(tint)
                        .fixedSize()
                    Text("Library Sync")
                        .font(.system(size: 12, weight: .semibold))
                        .fixedSize(horizontal: false, vertical: true)
                    Spacer(minLength: 0)
                    Image(systemName: "arrow.clockwise")
                        .font(.system(size: 10, weight: .semibold))
                        .frame(width: 18, height: 18)
                        .foregroundStyle(tint)
                        .fixedSize()
                }
                Text(status.title)
                    .font(.system(size: 11, weight: .semibold))
                    .fixedSize(horizontal: false, vertical: true)
                    .accessibilityIdentifier("application.status.sync.title")
                Text(status.detail)
                    .font(.system(size: 11))
                    .foregroundStyle(.secondary)
                    .lineLimit(showsFullDetails ? nil : 3)
                    .fixedSize(horizontal: false, vertical: true)
                if status.state == .syncing, let progress = status.progress {
                    ProgressView(value: min(1, max(0, progress)))
                        .progressViewStyle(.linear)
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .foregroundStyle(Color.primary)
            .padding(10)
            .background(tint.opacity(0.08), in: RoundedRectangle(cornerRadius: 7))
        }
        .buttonStyle(.plain)
        .help(status.detail + " Click to refresh library status.")
        .accessibilityLabel("Library sync: \(status.title)")
        .accessibilityHint("Refresh library status. " + status.detail)
        .accessibilityIdentifier("application.status.sync")
    }

    private var systemImage: String {
        switch status.state {
        case .syncing: return "arrow.triangle.2.circlepath.icloud"
        case .offline: return "wifi.slash"
        case .synced: return "checkmark.icloud.fill"
        }
    }

    private var tint: Color {
        switch status.state {
        case .syncing: return .blue
        case .offline: return .orange
        case .synced: return .green
        }
    }
}

struct ProcessActivityIndicator: View {
    let progress: Double

    var body: some View {
        TimelineView(.animation) { timeline in
            let seconds = timeline.date.timeIntervalSinceReferenceDate
            HStack(spacing: 4) {
                Image(systemName: "arrow.triangle.2.circlepath")
                    .font(.system(size: 11, weight: .semibold))
                    .rotationEffect(.degrees(seconds.truncatingRemainder(dividingBy: 1.2) / 1.2 * 360))
                Text("\(percent)%")
                    .font(.caption2.monospacedDigit())
            }
            .foregroundStyle(.secondary)
            .padding(.horizontal, 6)
            .padding(.vertical, 2)
            .background(
                Capsule()
                    .fill(Color.secondary.opacity(0.12))
            )
            .accessibilityLabel("Processing \(percent) percent")
        }
        .fixedSize()
    }

    private var percent: Int {
        Int((min(1.0, max(0.0, progress)) * 100).rounded())
    }
}

struct ProcessedItemContentIcon: View {
    let hasTranscript: Bool
    let hasFile: Bool

    var body: some View {
        HStack(spacing: 3) {
            if hasFile {
                Image(systemName: "waveform")
                    .accessibilityLabel("Audio available")
            }
            if hasTranscript {
                Image(systemName: "doc.text")
                    .accessibilityLabel("Transcript available")
            }
        }
        .font(.system(size: 11, weight: .medium))
        .foregroundStyle(.secondary)
        .frame(width: 28, height: 28, alignment: .center)
    }
}
