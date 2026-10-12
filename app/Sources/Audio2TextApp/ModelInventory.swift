import Foundation

struct LocalASRModel: Identifiable, Equatable {
    let alias: String
    let title: String
    let note: String
    let files: [ModelDownloadFile]

    var id: String {
        alias
    }

    var relativeDirectory: String {
        files.first?.relativePath.split(separator: "/").dropFirst().dropLast().joined(separator: "/") ?? alias
    }

    static let defaultAlias = "large-v3-turbo"
    static var all: [LocalASRModel] {
        ModelInventoryLoader.loadProductionModels()
    }

    static func model(for alias: String) -> LocalASRModel {
        all.first { $0.alias == alias } ?? all[0]
    }

    static func anyModel(for alias: String) -> LocalASRModel {
        ModelInventoryLoader.loadAllModels().first { $0.alias == alias } ?? model(for: alias)
    }
}

struct ModelDownloadFile: Identifiable, Equatable {
    let name: String
    let relativePath: String
    let url: String

    var id: String {
        relativePath
    }

    var pathUnderModelRoot: String {
        relativePath.hasPrefix("model/") ? String(relativePath.dropFirst("model/".count)) : relativePath
    }
}

private struct ModelInventoryPayload: Decodable {
    let models: [ModelInventoryEntry]
}

private struct ModelInventoryEntry: Decodable {
    let name: String
    let aliases: [String]
    let note: String
    let production: Bool
    let requiredFiles: [ModelInventoryRequiredFile]

    enum CodingKeys: String, CodingKey {
        case name
        case aliases
        case note
        case production
        case requiredFiles = "required_files"
    }
}

private struct ModelInventoryRequiredFile: Decodable {
    let path: String
    let url: String
}

enum ModelInventoryLoader {
    static func loadAllModels(bundle: Bundle = .main) -> [LocalASRModel] {
        loadModels(bundle: bundle, productionOnly: false)
    }

    static func loadProductionModels(bundle: Bundle = .main) -> [LocalASRModel] {
        loadModels(bundle: bundle, productionOnly: true)
    }

    private static func loadModels(bundle: Bundle, productionOnly: Bool) -> [LocalASRModel] {
        guard
            let url = AppPaths.modelInventoryURL(bundle: bundle),
            let data = try? Data(contentsOf: url),
            let inventory = try? JSONDecoder().decode(ModelInventoryPayload.self, from: data)
        else {
            return fallbackModels()
        }
        let models = inventory.models
            .filter { !productionOnly || $0.production }
            .map { entry in
                let alias = entry.aliases.first ?? entry.name
                return LocalASRModel(
                    alias: alias,
                    title: title(for: alias),
                    note: entry.note,
                    files: entry.requiredFiles.map {
                        ModelDownloadFile(
                            name: URL(fileURLWithPath: $0.path).lastPathComponent,
                            relativePath: $0.path,
                            url: $0.url
                        )
                    }
                )
            }
        return sortForPicker(models.isEmpty ? fallbackModels() : models)
    }

    private static func title(for alias: String) -> String {
        alias
            .split(separator: "-")
            .map { part in
                let text = String(part)
                if text.lowercased() == "v3" { return "v3" }
                if text.lowercased() == "q4" { return "Q4" }
                return text.prefix(1).uppercased() + text.dropFirst()
            }
            .joined(separator: " ")
    }

    private static func sortForPicker(_ models: [LocalASRModel]) -> [LocalASRModel] {
        models.sorted { lhs, rhs in
            if lhs.alias == LocalASRModel.defaultAlias { return true }
            if rhs.alias == LocalASRModel.defaultAlias { return false }
            return lhs.alias.localizedStandardCompare(rhs.alias) == .orderedAscending
        }
    }

    private static func fallbackModels() -> [LocalASRModel] {
        [
            LocalASRModel(
                alias: LocalASRModel.defaultAlias,
                title: "Large v3 Turbo",
                note: "Recommended default for Chinese podcasts.",
                files: [
                    ModelDownloadFile(
                        name: "config.json",
                        relativePath: "model/whisper-large-v3-turbo/config.json",
                        url: "https://huggingface.co/mlx-community/whisper-large-v3-turbo/resolve/main/config.json?download=true"
                    ),
                    ModelDownloadFile(
                        name: "weights.safetensors",
                        relativePath: "model/whisper-large-v3-turbo/weights.safetensors",
                        url: "https://huggingface.co/mlx-community/whisper-large-v3-turbo/resolve/main/weights.safetensors?download=true"
                    ),
                ]
            ),
        ]
    }
}
