import Foundation
#if canImport(Audio2TextCore)
    import Audio2TextCore
#endif

struct CloudSettings: Equatable {
    var apiBase: String
    var configurationError: String = ""
    var model: String
    var apiKey: String
    var timeout: String
    var temperature: String
    var maxTokens: String
    var summaryPrompt: String = AppSettings.defaultSummaryPrompt
    var titlePrompt: String = AppSettings.defaultTitlePrompt

    static let defaultAPIBase = CloudModelDefaults.defaultAPIBase
    static let defaultModel = CloudModelDefaults.defaultModel
    static let defaultTimeout = "360"
    static let defaultTemperature = "1"
    static let defaultMaxTokens = "8192"

    static func load(environment _: [String: String] = ProcessInfo.processInfo.environment) -> CloudSettings {
        return CloudSettings(
            apiBase: defaultAPIBase,
            model: defaultModel,
            apiKey: "",
            timeout: defaultTimeout,
            temperature: defaultTemperature,
            maxTokens: defaultMaxTokens,
            summaryPrompt: AppSettings.defaultSummaryPrompt,
            titlePrompt: AppSettings.defaultTitlePrompt
        )
    }

    var isConfigured: Bool {
        !apiBase.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
            && !apiKey.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
    }

    var redactedDescription: String {
        let suffix = apiKey.suffix(4)
        let keyDescription = apiKey.isEmpty ? "missing" : "****\(suffix)"
        return "\(model) @ \(apiBase) key=\(keyDescription)"
    }

    func environment(over base: [String: String] = ProcessInfo.processInfo.environment) -> [String: String] {
        base
    }

    private static func nonEmpty(_ value: String?) -> String? {
        guard let value else { return nil }
        let trimmed = value.trimmingCharacters(in: .whitespacesAndNewlines)
        return trimmed.isEmpty ? nil : trimmed
    }
}
