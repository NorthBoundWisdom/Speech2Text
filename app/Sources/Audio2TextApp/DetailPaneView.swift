import SwiftUI

struct DetailPaneView: View {
    @ObservedObject var controller: JobController
    let readingStyle: ReadingStyleSettings

    init(controller: JobController, readingStyle: ReadingStyleSettings = .default) {
        self.controller = controller
        self.readingStyle = readingStyle
    }

    var body: some View {
        if case .subscriptions = controller.selectedSidebarSource {
            SubscriptionDetailView(controller: controller, state: controller.subscriptionDetailViewState)
                .equatable()
        } else {
            VStack(alignment: .leading, spacing: 0) {
                detailContent
            }
        }
    }

    @ViewBuilder
    private var detailContent: some View {
        if let item = controller.selectedLibraryItem, !item.isProcessed {
            UnprocessedDetailPaneView(controller: controller, item: item, readingStyle: readingStyle)
        } else if controller.selectedTab == .summary {
            SummaryPaneView(controller: controller, readingStyle: readingStyle)
        } else if controller.selectedTab == .repair {
            RepairPaneView(controller: controller, readingStyle: readingStyle)
        } else if controller.selectedTab == .glossary {
            GlossaryEditorPaneView(controller: controller, readingStyle: readingStyle)
        } else if controller.selectedTab == .metadata {
            IntroPaneView(controller: controller, text: selectedText, readingStyle: readingStyle)
        } else {
            SimpleMarkdownView(text: selectedText, style: readingStyle)
        }
    }

    private var selectedText: String {
        switch controller.selectedTab {
        case .metadata:
            return controller.metadataText
        case .transcript:
            return controller.snapshot.transcriptText.isEmpty
                ? "Transcript is not available yet."
                : controller.snapshot.transcriptText
        case .summary:
            return controller.snapshot.summaryText
        case .repair:
            return controller.snapshot.repairText
        case .glossary:
            return controller.snapshot.glossaryText
        case .log:
            return logText
        }
    }

    private var logText: String {
        var sections: [String] = []
        let stage = controller.stage.rawValue
        let progress = Int((min(1.0, max(0.0, controller.progressFraction)) * 100).rounded())
        sections.append("""
        # Status

        - Stage: \(stage)
        - Progress: \(progress)%
        - Message: \(controller.message.isEmpty ? "None" : controller.message)
        """)

        if let selectedFile = controller.selectedFile {
            sections.append("""
            # Current item

            - Audio: \(selectedFile.path)
            - Output: \(controller.snapshot.outputDirectory?.path ?? "None")
            """)
        }

        if !controller.persistentLogPath.isEmpty {
            sections.append("""
            # Log file

            \(controller.persistentLogPath)
            """)
        }

        let liveLog = controller.logText.trimmingCharacters(in: .whitespacesAndNewlines)
        if !liveLog.isEmpty {
            sections.append("""
            # Live Log

            ```text
            \(liveLog)
            ```
            """)
        }

        if !controller.snapshot.runText.isEmpty {
            sections.append("""
            # Run

            ```json
            \(controller.snapshot.runText)
            ```
            """)
        }

        if !controller.snapshot.qaText.isEmpty {
            sections.append("""
            # QA

            \(controller.snapshot.qaText)
            """)
        }

        return sections.joined(separator: "\n\n")
    }
}
