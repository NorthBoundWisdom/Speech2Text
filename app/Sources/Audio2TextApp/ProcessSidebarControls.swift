import SwiftUI
#if canImport(Audio2TextCore)
    import Audio2TextCore
#endif

struct LibrarySyncStatusBadge: View {
    let status: LibrarySyncStatus
    let refresh: () -> Void

    var body: some View {
        Button(action: refresh) {
            HStack(spacing: 5) {
                Image(systemName: systemImage)
                    .font(.system(size: 11, weight: .semibold))
                Text(status.title)
                    .font(.system(size: 11, weight: .semibold))
                    .lineLimit(1)
                    .minimumScaleFactor(0.75)
            }
            .foregroundStyle(tint)
            .padding(.horizontal, 7)
            .frame(height: 20)
            .background(tint.opacity(0.10), in: RoundedRectangle(cornerRadius: 6, style: .continuous))
        }
        .buttonStyle(.plain)
        .help(status.detail)
        .accessibilityLabel("同步状态：\(status.title)")
        .accessibilityHint(status.detail)
    }

    private var systemImage: String {
        switch status.state {
        case .syncing:
            return "arrow.triangle.2.circlepath.icloud"
        case .offline:
            return "wifi.slash"
        case .synced:
            return "checkmark.icloud.fill"
        }
    }

    private var tint: Color {
        switch status.state {
        case .syncing:
            return .blue
        case .offline:
            return .orange
        case .synced:
            return .green
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
