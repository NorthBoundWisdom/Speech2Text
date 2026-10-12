import SwiftUI

struct RepairPaneView: View {
    @ObservedObject var controller: JobController
    let readingStyle: ReadingStyleSettings

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            header
            Divider()
            SimpleMarkdownView(text: repairText, style: readingStyle)
        }
    }

    private var header: some View {
        HStack(spacing: 10) {
            Text(repairStatus)
                .font(.caption)
                .foregroundStyle(.secondary)
                .lineLimit(1)
            Spacer()
            Button {
                controller.runRepairForSelectedItem()
            } label: {
                Image(systemName: "wrench.and.screwdriver")
            }
            .help("Run local repair")
            .disabled(!controller.canRunRepair(for: controller.selectedLibraryItem))
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 8)
    }

    private var repairText: String {
        var sections: [String] = []
        if !controller.snapshot.qaText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            sections.append("""
            # QA

            \(controller.snapshot.qaText)
            """)
        }
        sections.append(controller.snapshot.repairText)
        return sections.joined(separator: "\n\n")
    }

    private var repairStatus: String {
        if controller.stage.isRunning {
            return controller.message.isEmpty ? "Running" : controller.message
        }
        return controller.snapshot.qaStatus == "fail" ? "QA needs review" : "Repair artifacts"
    }
}
