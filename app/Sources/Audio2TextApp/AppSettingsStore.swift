import Foundation
#if canImport(Audio2TextCore)
    import Audio2TextCore
#endif

struct AppSettingsStore {
    var dataRootOverride: URL?
    var credentials: any CloudCredentialStore

    init(dataRoot: URL? = nil, credentials: any CloudCredentialStore = KeychainCloudCredentialStore()) {
        dataRootOverride = dataRoot
        self.credentials = credentials
    }

    static func live() -> AppSettingsStore {
        AppSettingsStore()
    }

    func load(
        environment _: [String: String] = ProcessInfo.processInfo.environment,
        includeAPIKey: Bool = true
    ) -> AppSettings {
        appSettings(from: loadConfig(includeAPIKey: includeAPIKey), includeAPIKey: includeAPIKey)
    }

    static func supportedLocalASRModel(_ value: String?) -> String {
        guard let value else {
            return LocalASRModel.defaultAlias
        }
        let supported = Set(LocalASRModel.all.map(\.alias))
        return supported.contains(value) ? value : LocalASRModel.defaultAlias
    }

    func save(
        _ settings: AppSettings,
        environment _: [String: String] = ProcessInfo.processInfo.environment
    ) throws {
        if !settings.configurationError.isEmpty && settings.apiKey.isEmpty {
            throw AppError.invalidImportOutput(settings.configurationError)
        }
        try cloudConfig(from: settings).write(to: resolvedDataRoot(), credentials: credentials)
    }

    func cloudSettings(environment: [String: String] = ProcessInfo.processInfo.environment) -> CloudSettings {
        let settings = load(environment: environment)
        return CloudSettings(
            apiBase: settings.apiBase,
            configurationError: settings.configurationError,
            model: settings.cloudModel,
            apiKey: settings.apiKey,
            timeout: settings.cloudTimeout,
            temperature: settings.cloudTemperature,
            maxTokens: settings.cloudMaxTokens,
            summaryPrompt: settings.summaryPrompt,
            titlePrompt: settings.titlePrompt
        )
    }

    func libraryRoot(environment: [String: String] = ProcessInfo.processInfo.environment) -> URL {
        let settings = load(environment: environment, includeAPIKey: false)
        return AppPaths.libraryRoot(
            storage: settings.libraryStorage,
            iCloudRoot: settings.libraryICloudRoot,
            localRoot: settings.libraryLocalRoot,
            dataRoot: resolvedDataRoot()
        )
    }

    func dataRoot() -> URL {
        resolvedDataRoot()
    }

    func ensureCloudConfigFile(
        environment _: [String: String] = ProcessInfo.processInfo.environment,
        fileManager: FileManager = .default
    ) throws -> URL {
        let dataRoot = resolvedDataRoot()
        let url = CloudConfigFile.configURL(dataRoot: dataRoot)
        if !fileManager.fileExists(atPath: url.path) {
            try fileManager.createDirectory(at: dataRoot, withIntermediateDirectories: true)
            try CloudConfigFile.template().write(to: url, atomically: true, encoding: .utf8)
            try fileManager.setAttributes([.posixPermissions: 0o600], ofItemAtPath: url.path)
        }
        return url
    }

    private func loadConfig(includeAPIKey: Bool) -> CloudConfigFile {
        do {
            return try CloudConfigFile.load(dataRoot: resolvedDataRoot(), credentials: credentials,
                                            includeAPIKey: includeAPIKey)
        } catch {
            var file = (try? CloudConfigFile.load(dataRoot: resolvedDataRoot(), credentials: credentials,
                                                   includeAPIKey: false)) ?? CloudConfigFile()
            file.configurationError = error.localizedDescription
            return file
        }
    }

    private func appSettings(from config: CloudConfigFile, includeAPIKey: Bool) -> AppSettings {
        AppSettings(
            configurationError: config.configurationError,
            localASRModel: config.localASRModel,
            localASRProfile: config.localASRProfile,
            apiBase: config.baseURL,
            cloudModel: config.model,
            summaryPrompt: config.summaryPrompt,
            titlePrompt: config.titlePrompt,
            apiKey: includeAPIKey ? config.apiKey : "",
            cloudTimeout: config.cloudTimeout,
            cloudTemperature: config.cloudTemperature,
            cloudMaxTokens: config.cloudMaxTokens,
            cloudModelOptions: config.modelOptions,
            translation: TranslationSettings(
                enabled: config.translationEnabled,
                backend: TranslationBackend(rawValue: config.translationBackend) ?? .cloud,
                targetLanguage: config.translationTargetLanguage,
                localModelAlias: config.translationLocalModelAlias
            ),
            workflowDefaultCloudSummary: config.workflowDefaultCloudSummary,
            workflowLocalOnly: config.workflowLocalOnly,
            workflowChunking: config.workflowChunking,
            workflowChunkLength: config.workflowChunkLength,
            workflowOverlap: config.workflowOverlap,
            libraryStorage: config.libraryStorage,
            libraryICloudRoot: config.libraryICloudRoot,
            libraryLocalRoot: config.libraryLocalRoot,
            readingStyle: ReadingStyleSettings(
                textSize: ReadingTextSize(rawValue: config.readingTextSize) ?? ReadingStyleSettings.default.textSize,
                lineSpacing: ReadingLineSpacing(rawValue: config.readingLineSpacing) ?? ReadingStyleSettings.default.lineSpacing,
                contentWidth: ReadingContentWidth(rawValue: config.readingContentWidth) ?? ReadingStyleSettings.default.contentWidth,
                fontDesign: ReadingFontDesign(rawValue: config.readingFont) ?? ReadingStyleSettings.default.fontDesign
            ),
            hideReadItems: config.hideReadItems
        )
    }

    private func cloudConfig(from settings: AppSettings) -> CloudConfigFile {
        let model = trimmed(settings.cloudModel)
        return CloudConfigFile(
            model: model.isEmpty ? CloudConfigFile.defaultModel : model,
            baseURL: trimmed(settings.apiBase),
            apiKey: trimmed(settings.apiKey),
            modelOptions: settings.cloudModelOptions.isEmpty ? CloudConfigFile.defaultModelOptions : settings.cloudModelOptions,
            localASRModel: Self.supportedLocalASRModel(settings.localASRModel),
            localASRProfile: supportedLocalASRProfile(settings.localASRProfile),
            summaryPrompt: settings.summaryPrompt,
            titlePrompt: settings.titlePrompt,
            cloudTimeout: nonEmpty(settings.cloudTimeout) ?? CloudConfigFile.defaultCloudTimeout,
            cloudTemperature: nonEmpty(settings.cloudTemperature) ?? CloudConfigFile.defaultCloudTemperature,
            cloudMaxTokens: nonEmpty(settings.cloudMaxTokens) ?? CloudConfigFile.defaultCloudMaxTokens,
            translationEnabled: settings.translation.enabled,
            translationBackend: settings.translation.backend.rawValue,
            translationTargetLanguage: settings.translation.targetLanguage,
            translationLocalModelAlias: settings.translation.localModelAlias,
            workflowDefaultCloudSummary: settings.workflowDefaultCloudSummary,
            workflowLocalOnly: settings.workflowLocalOnly,
            workflowChunking: supportedWorkflowChunking(settings.workflowChunking),
            workflowChunkLength: nonEmpty(settings.workflowChunkLength) ?? "1200",
            workflowOverlap: nonEmpty(settings.workflowOverlap) ?? "10",
            libraryStorage: supportedLibraryStorage(settings.libraryStorage),
            libraryICloudRoot: normalizedLibraryRoot(settings.libraryICloudRoot),
            libraryLocalRoot: normalizedLibraryRoot(settings.libraryLocalRoot),
            readingTextSize: settings.readingStyle.textSize.rawValue,
            readingLineSpacing: settings.readingStyle.lineSpacing.rawValue,
            readingContentWidth: settings.readingStyle.contentWidth.rawValue,
            readingFont: settings.readingStyle.fontDesign.rawValue,
            hideReadItems: settings.hideReadItems
        )
    }

    private func supportedLocalASRProfile(_ value: String?) -> String {
        guard let value else {
            return LocalASRProfile.defaultName
        }
        return LocalASRProfile.all.contains(where: { $0.name == value }) ? value : LocalASRProfile.defaultName
    }

    private func supportedWorkflowChunking(_ value: String) -> String {
        ["auto", "fixed", "smart"].contains(value) ? value : "auto"
    }

    private func supportedLibraryStorage(_ value: String) -> String {
        let normalized = value.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
        return ["icloud", "local"].contains(normalized) ? normalized : "icloud"
    }

    private func normalizedLibraryRoot(_ value: String) -> String {
        value.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    private func resolvedDataRoot() -> URL {
        dataRootOverride ?? AppPaths.dataRoot()
    }

    private func trimmed(_ value: String) -> String {
        value.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    private func nonEmpty(_ value: String?) -> String? {
        guard let value else { return nil }
        let normalized = trimmed(value)
        return normalized.isEmpty ? nil : normalized
    }
}
