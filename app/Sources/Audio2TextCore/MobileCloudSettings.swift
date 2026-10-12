import Foundation

public enum CloudModelDefaults {
    public static let defaultAPIBase = ""
    public static let defaultModelOptions = [
        "gpt-5.4-mini",
        "gpt-5.4",
        "gpt-5.5",
        "gpt-5.6-sol",
        "gpt-5.6-terra",
        "gpt-5.6-luna",
    ]
    public static let defaultModel = defaultModelOptions[0]
}

public struct MobileCloudSettings: Equatable {
    public var apiBase: String
    public var apiKey: String
    public var model: String

    public init(
        apiBase: String = CloudModelDefaults.defaultAPIBase,
        apiKey: String = "",
        model: String = CloudModelDefaults.defaultModel
    ) {
        self.apiBase = apiBase
        self.apiKey = apiKey
        self.model = model
    }

    public var isConfigured: Bool {
        !apiBase.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
            && !apiKey.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
    }
}

public struct MobileCloudSettingsStore {
    public static let apiBaseKey = "mobile.cloud.apiBase"
    public static let apiKeyKey = "mobile.cloud.apiKey"
    public static let modelKey = "mobile.cloud.model"

    private let defaults: UserDefaults
    private let credentials: any CloudCredentialStore
    private let account: String

    public init(
        defaults: UserDefaults = .standard,
        credentials: any CloudCredentialStore = KeychainCloudCredentialStore(),
        account: String = "mobile.cloud.apiKey"
    ) {
        self.defaults = defaults
        self.credentials = credentials
        self.account = account
    }

    public func load() throws -> MobileCloudSettings {
        if let legacy = defaults.string(forKey: Self.apiKeyKey), !legacy.isEmpty {
            try credentials.save(legacy.trimmingCharacters(in: .whitespacesAndNewlines), account: account)
            defaults.removeObject(forKey: Self.apiKeyKey)
        }
        return MobileCloudSettings(
            apiBase: defaults.string(forKey: Self.apiBaseKey) ?? CloudModelDefaults.defaultAPIBase,
            apiKey: try credentials.load(account: account) ?? "",
            model: normalizedModel(defaults.string(forKey: Self.modelKey))
        )
    }

    public func save(_ settings: MobileCloudSettings) throws {
        try credentials.save(settings.apiKey.trimmingCharacters(in: .whitespacesAndNewlines), account: account)
        defaults.removeObject(forKey: Self.apiKeyKey)
        defaults.set(settings.apiBase.trimmingCharacters(in: .whitespacesAndNewlines), forKey: Self.apiBaseKey)
        defaults.set(normalizedModel(settings.model), forKey: Self.modelKey)
    }

    public func delete() throws {
        try credentials.save("", account: account)
        defaults.removeObject(forKey: Self.apiBaseKey)
        defaults.removeObject(forKey: Self.apiKeyKey)
        defaults.removeObject(forKey: Self.modelKey)
    }

    private func normalizedModel(_ value: String?) -> String {
        let trimmed = value?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
        return trimmed.isEmpty ? CloudModelDefaults.defaultModel : trimmed
    }

}
