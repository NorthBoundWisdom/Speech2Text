import SwiftUI

struct GlossaryEditorPaneView: View {
    @ObservedObject var controller: JobController
    let readingStyle: ReadingStyleSettings
    @State private var term = ""
    @State private var category = "technical_terms"
    @State private var jsonDraft = ""
    @State private var loadedOutputURL: URL?

    private let categories = ["technical_terms", "people", "organizations", "titles"]

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            header
            Divider()
            HSplitView {
                SimpleMarkdownView(text: suggestionsText, style: readingStyle)
                    .frame(minWidth: 280, maxWidth: .infinity, maxHeight: .infinity)
                TextEditor(text: jsonBinding)
                    .font(.system(.body, design: .monospaced))
                    .frame(minWidth: 280, maxWidth: .infinity, maxHeight: .infinity)
                    .padding(8)
            }
        }
        .onAppear { loadDraft(force: true) }
        .onChange(of: controller.snapshot.outputDirectory) { _ in loadDraft(force: true) }
        .onChange(of: controller.snapshot.episodeGlossaryText) { _ in loadDraft(force: false) }
    }

    private var header: some View {
        HStack(spacing: 8) {
            TextField("Term", text: $term)
                .textFieldStyle(.roundedBorder)
                .frame(width: 180)
            Picker("", selection: $category) {
                ForEach(categories, id: \.self) { value in
                    Text(value).tag(value)
                }
            }
            .labelsHidden()
            .frame(width: 170)
            Button {
                controller.addGlossaryTerm(term, category: category)
                term = ""
                loadDraft(force: true)
            } label: {
                Image(systemName: "plus")
            }
            .help("Add term")
            .disabled(term.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
            Button {
                controller.disableGlossaryTerm(term)
                term = ""
                loadDraft(force: true)
            } label: {
                Image(systemName: "nosign")
            }
            .help("Disable term")
            .disabled(term.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
            Spacer()
            Button {
                controller.saveEpisodeGlossaryJSON(jsonDraft)
                loadDraft(force: true)
            } label: {
                Image(systemName: "square.and.arrow.down")
            }
            .help("Save glossary JSON")
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 8)
    }

    private var suggestionsText: String {
        let text = controller.snapshot.glossaryText.trimmingCharacters(in: .whitespacesAndNewlines)
        return text.isEmpty ? "# Glossary\n\nNo glossary suggestions are available." : text
    }

    private var jsonBinding: Binding<String> {
        Binding(get: { jsonDraft }, set: { jsonDraft = $0 })
    }

    private func loadDraft(force: Bool) {
        guard force || loadedOutputURL != controller.snapshot.outputDirectory else { return }
        let current = controller.snapshot.episodeGlossaryText.trimmingCharacters(in: .whitespacesAndNewlines)
        jsonDraft = current.isEmpty ? "{\n  \"technical_terms\" : []\n}" : current
        loadedOutputURL = controller.snapshot.outputDirectory
    }
}
