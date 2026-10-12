import SwiftUI

struct UnprocessedDetailPaneView: View {
    @ObservedObject var controller: JobController
    let item: ProcessLibraryItem
    let readingStyle: ReadingStyleSettings

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            header
            Divider()
            SimpleMarkdownView(
                text: ProcessLibrary.unprocessedDetailText(for: item, metadataText: controller.metadataText),
                style: readingStyle
            )
        }
    }

    private var header: some View {
        HStack(spacing: 10) {
            VStack(alignment: .leading, spacing: 2) {
                Text(item.title)
                    .font(.headline)
                    .lineLimit(1)
                Text("\(item.status) · \(item.queueStatus.compactTitle)")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .lineLimit(1)
            }
            Spacer()
            if item.canDownloadAudio {
                Label("Remote audio", systemImage: "icloud.and.arrow.down")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            } else if item.isAudioPresent {
                Label("Audio ready", systemImage: "waveform")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 9)
    }
}
