import Foundation
#if canImport(Audio2TextCore)
    import Audio2TextCore
#endif

@MainActor
extension JobController {
    func addGlossaryTerm(_ term: String, category: String) {
        let clean = term.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !clean.isEmpty else { return }
        updateEpisodeGlossary { glossary in
            var values = glossary[category] as? [String] ?? []
            if !values.contains(clean) {
                values.append(clean)
            }
            glossary[category] = values.sorted()
        }
    }

    func saveEpisodeGlossaryJSON(_ text: String) {
        guard let outputDirectory = snapshot.outputDirectory else {
            message = "No output directory is selected"
            return
        }
        guard let data = text.data(using: .utf8),
              (try? JSONSerialization.jsonObject(with: data)) is [String: Any]
        else {
            message = "Glossary JSON is invalid"
            return
        }
        do {
            let url = outputDirectory.appendingPathComponent("episode_glossary.json")
            try FileManager.default.createDirectory(at: url.deletingLastPathComponent(), withIntermediateDirectories: true)
            try data.write(to: url, options: .atomic)
            snapshot = snapshotForOutputDirectory(outputDirectory)
            message = "Glossary saved"
        } catch {
            message = error.localizedDescription
            logError(category: "glossary", event: "episode_glossary_save_failed", error: error)
        }
    }

    func disableGlossaryTerm(_ term: String) {
        let clean = term.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !clean.isEmpty else { return }
        updateEpisodeGlossary { glossary in
            var disabled = glossary["disabled_terms"] as? [String] ?? []
            if !disabled.contains(clean) {
                disabled.append(clean)
            }
            glossary["disabled_terms"] = disabled.sorted()
        }
    }

    private func updateEpisodeGlossary(_ mutate: (inout [String: Any]) -> Void) {
        guard let outputDirectory = snapshot.outputDirectory else {
            message = "No output directory is selected"
            return
        }
        let url = outputDirectory.appendingPathComponent("episode_glossary.json")
        var glossary: [String: Any] = [:]
        if let data = try? Data(contentsOf: url),
           let object = try? JSONSerialization.jsonObject(with: data) as? [String: Any]
        {
            glossary = object
        }
        mutate(&glossary)
        do {
            let data = try JSONSerialization.data(withJSONObject: glossary, options: [.prettyPrinted, .sortedKeys])
            try FileManager.default.createDirectory(at: url.deletingLastPathComponent(), withIntermediateDirectories: true)
            try data.write(to: url, options: .atomic)
            snapshot = snapshotForOutputDirectory(outputDirectory)
            message = "Glossary updated"
        } catch {
            message = error.localizedDescription
            logError(category: "glossary", event: "episode_glossary_update_failed", error: error)
        }
    }
}
