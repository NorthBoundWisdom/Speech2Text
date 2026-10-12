import Foundation
#if canImport(Audio2TextCore)
    import Audio2TextCore
#endif

struct CloudConfigFile: Equatable {
    static let defaultBaseURL = CloudModelDefaults.defaultAPIBase
    static let defaultModelOptions = CloudModelDefaults.defaultModelOptions
    static let defaultModel = CloudModelDefaults.defaultModel
    static let defaultCloudTimeout = "360"
    static let defaultCloudTemperature = "1"
    static let defaultCloudMaxTokens = "8192"

    var configurationError: String = ""
    var apiKeyStore: String = ""
    var model: String = defaultModel
    var baseURL: String = defaultBaseURL
    var apiKey: String = ""
    var modelOptions: [String] = defaultModelOptions
    var localASRModel: String = LocalASRModel.defaultAlias
    var localASRProfile: String = LocalASRProfile.defaultName
    var summaryPrompt: String = AppSettings.defaultSummaryPrompt
    var titlePrompt: String = AppSettings.defaultTitlePrompt
    var cloudTimeout: String = defaultCloudTimeout
    var cloudTemperature: String = defaultCloudTemperature
    var cloudMaxTokens: String = defaultCloudMaxTokens
    var translationEnabled: Bool = false
    var translationBackend: String = TranslationBackend.cloud.rawValue
    var translationTargetLanguage: String = TranslationSettings.defaultTargetLanguage
    var translationLocalModelAlias: String = TranslationSettings.defaultLocalModelAlias
    var workflowDefaultCloudSummary: Bool = false
    var workflowLocalOnly: Bool = false
    var workflowChunking: String = "auto"
    var workflowChunkLength: String = "1200"
    var workflowOverlap: String = "10"
    var libraryStorage: String = "icloud"
    var libraryICloudRoot: String = ""
    var libraryLocalRoot: String = ""
    var readingTextSize: String = ReadingStyleSettings.default.textSize.rawValue
    var readingLineSpacing: String = ReadingStyleSettings.default.lineSpacing.rawValue
    var readingContentWidth: String = ReadingStyleSettings.default.contentWidth.rawValue
    var readingFont: String = ReadingStyleSettings.default.fontDesign.rawValue
    var hideReadItems: Bool = false

    static func configURL(dataRoot: URL) -> URL {
        dataRoot.appendingPathComponent("config.toml")
    }

    static func load(
        dataRoot: URL,
        fileManager: FileManager = .default,
        credentials: any CloudCredentialStore = KeychainCloudCredentialStore(),
        includeAPIKey: Bool = true
    ) throws -> CloudConfigFile {
        let url = configURL(dataRoot: dataRoot)
        guard fileManager.fileExists(atPath: url.path) else {
            return CloudConfigFile()
        }
        let text = try String(contentsOf: url, encoding: .utf8)
        var file = try parse(text)
        if !includeAPIKey {
            file.apiKey = ""
            return file
        }
        let account = url.standardizedFileURL.resolvingSymlinksInPath().path
        if !file.apiKey.isEmpty {
            try credentials.save(file.apiKey, account: account)
            var section = ""
            var migrated: [String] = []
            for line in text.components(separatedBy: .newlines) {
                let trimmed = line.trimmingCharacters(in: .whitespacesAndNewlines)
                if trimmed.hasPrefix("[") && trimmed.hasSuffix("]") { section = trimmed }
                let key = trimmed.split(separator: "=", maxSplits: 1).first?.trimmingCharacters(in: .whitespacesAndNewlines)
                if section == "[cloud]" && key == "api_key_store" { continue }
                if section == "[cloud]" && key == "api_key" {
                    migrated.append("api_key = \"\"")
                    migrated.append("api_key_store = \"system\"")
                } else { migrated.append(line) }
            }
            try migrated.joined(separator: "\n").write(to: url, atomically: true, encoding: .utf8)
            try fileManager.setAttributes([.posixPermissions: 0o600], ofItemAtPath: url.path)
            file.apiKeyStore = "system"
        } else if file.apiKeyStore == "system" {
            guard let key = try credentials.load(account: account) else {
                throw AppError.invalidImportOutput("Cloud credential is missing from Keychain.")
            }
            file.apiKey = key
        } else if !file.apiKeyStore.isEmpty {
            throw AppError.invalidImportOutput("Unsupported cloud credential store.")
        }
        return file
    }

    static func parse(_ text: String) throws -> CloudConfigFile {
        var file = CloudConfigFile()
        var section = ""

        for rawLine in text.components(separatedBy: .newlines) {
            let line = rawLine.trimmingCharacters(in: .whitespacesAndNewlines)
            if line.isEmpty || line.hasPrefix("#") {
                continue
            }
            if line.hasPrefix("[") && line.hasSuffix("]") {
                section = String(line.dropFirst().dropLast())
                continue
            }
            guard let separator = line.firstIndex(of: "=") else {
                continue
            }
            let key = line[..<separator].trimmingCharacters(in: .whitespacesAndNewlines)
            let valueText = line[line.index(after: separator)...].trimmingCharacters(in: .whitespacesAndNewlines)

            if section == "local" {
                switch key {
                case "asr_model":
                    file.localASRModel = try parseQuotedTOMLString(valueText)
                case "asr_profile":
                    file.localASRProfile = try parseQuotedTOMLString(valueText)
                default:
                    break
                }
            } else if section == "cloud" {
                switch key {
                case "api_base":
                    file.baseURL = try parseQuotedTOMLString(valueText)
                case "api_key_store":
                    file.apiKeyStore = try parseQuotedTOMLString(valueText)
                case "api_key":
                    file.apiKey = try parseQuotedTOMLString(valueText)
                case "model":
                    file.model = try parseQuotedTOMLString(valueText)
                case "model_options":
                    file.modelOptions = try parseQuotedTOMLStringArray(valueText)
                case "timeout":
                    file.cloudTimeout = try parseTOMLScalarString(valueText)
                case "temperature":
                    file.cloudTemperature = try parseTOMLScalarString(valueText)
                case "max_tokens":
                    file.cloudMaxTokens = try parseTOMLScalarString(valueText)
                case "summary_prompt":
                    file.summaryPrompt = try parseQuotedTOMLString(valueText)
                case "title_prompt":
                    file.titlePrompt = try parseQuotedTOMLString(valueText)
                default:
                    break
                }
            } else if section == "translation" {
                switch key {
                case "enabled":
                    file.translationEnabled = try parseTOMLBool(valueText)
                case "backend":
                    file.translationBackend = try parseQuotedTOMLString(valueText)
                case "target_language":
                    file.translationTargetLanguage = try parseQuotedTOMLString(valueText)
                case "local_model_alias":
                    file.translationLocalModelAlias = try parseQuotedTOMLString(valueText)
                default:
                    break
                }
            } else if section == "workflow" {
                switch key {
                case "default_cloud_summary":
                    file.workflowDefaultCloudSummary = try parseTOMLBool(valueText)
                case "local_only":
                    file.workflowLocalOnly = try parseTOMLBool(valueText)
                case "chunking":
                    file.workflowChunking = try parseQuotedTOMLString(valueText)
                case "chunk_length":
                    file.workflowChunkLength = try parseTOMLScalarString(valueText)
                case "overlap":
                    file.workflowOverlap = try parseTOMLScalarString(valueText)
                default:
                    break
                }
            } else if section == "library" {
                switch key {
                case "storage":
                    file.libraryStorage = try parseQuotedTOMLString(valueText)
                case "icloud_root":
                    file.libraryICloudRoot = try parseQuotedTOMLString(valueText)
                case "local_root":
                    file.libraryLocalRoot = try parseQuotedTOMLString(valueText)
                default:
                    break
                }
            } else if section == "ui" {
                switch key {
                case "reading_text_size":
                    file.readingTextSize = try parseQuotedTOMLString(valueText)
                case "reading_line_spacing":
                    file.readingLineSpacing = try parseQuotedTOMLString(valueText)
                case "reading_content_width":
                    file.readingContentWidth = try parseQuotedTOMLString(valueText)
                case "reading_font":
                    file.readingFont = try parseQuotedTOMLString(valueText)
                case "hide_read_items":
                    file.hideReadItems = try parseTOMLBool(valueText)
                default:
                    break
                }
            }
        }

        if file.model.isEmpty {
            file.model = defaultModel
        }
        if file.modelOptions.isEmpty {
            file.modelOptions = defaultModelOptions
        }
        file.localASRModel = AppSettingsStore.supportedLocalASRModel(file.localASRModel)
        if !LocalASRProfile.all.contains(where: { $0.name == file.localASRProfile }) {
            file.localASRProfile = LocalASRProfile.defaultName
        }
        if TranslationBackend(rawValue: file.translationBackend) == nil {
            file.translationBackend = TranslationBackend.cloud.rawValue
        }
        if file.translationTargetLanguage.isEmpty {
            file.translationTargetLanguage = TranslationSettings.defaultTargetLanguage
        }
        if file.translationLocalModelAlias.isEmpty {
            file.translationLocalModelAlias = TranslationSettings.defaultLocalModelAlias
        }
        if !["auto", "fixed", "smart"].contains(file.workflowChunking) {
            file.workflowChunking = "auto"
        }
        if file.workflowChunkLength.isEmpty {
            file.workflowChunkLength = "1200"
        }
        if file.workflowOverlap.isEmpty {
            file.workflowOverlap = "10"
        }
        if !["icloud", "local"].contains(file.libraryStorage) {
            file.libraryStorage = "icloud"
        }
        if ReadingTextSize(rawValue: file.readingTextSize) == nil {
            file.readingTextSize = ReadingStyleSettings.default.textSize.rawValue
        }
        if ReadingLineSpacing(rawValue: file.readingLineSpacing) == nil {
            file.readingLineSpacing = ReadingStyleSettings.default.lineSpacing.rawValue
        }
        if ReadingContentWidth(rawValue: file.readingContentWidth) == nil {
            file.readingContentWidth = ReadingStyleSettings.default.contentWidth.rawValue
        }
        if ReadingFontDesign(rawValue: file.readingFont) == nil {
            file.readingFont = ReadingStyleSettings.default.fontDesign.rawValue
        }
        return file
    }

    func write(to dataRoot: URL, fileManager: FileManager = .default,
               credentials: any CloudCredentialStore = KeychainCloudCredentialStore()) throws {
        let url = Self.configURL(dataRoot: dataRoot)
        try fileManager.createDirectory(at: dataRoot, withIntermediateDirectories: true)
        let text = try serialized()
        try credentials.save(apiKey, account: url.standardizedFileURL.resolvingSymlinksInPath().path)
        try text.write(to: url, atomically: true, encoding: .utf8)
        try fileManager.setAttributes([.posixPermissions: 0o600], ofItemAtPath: url.path)
    }

    func serialized() throws -> String {
        try [
            "[local]",
            "asr_model = \(quotedTOMLString(localASRModel))",
            "asr_profile = \(quotedTOMLString(localASRProfile))",
            "",
            "[cloud]",
            "api_base = \(quotedTOMLString(baseURL))",
            "api_key = \"\"",
            "api_key_store = \(quotedTOMLString(apiKey.isEmpty ? "" : "system"))",
            "model = \(quotedTOMLString(model))",
            "timeout = \(quotedTOMLString(cloudTimeout))",
            "temperature = \(quotedTOMLString(cloudTemperature))",
            "max_tokens = \(quotedTOMLString(cloudMaxTokens))",
            "model_options = \(quotedTOMLStringArray(modelOptions))",
            "summary_prompt = \(quotedTOMLString(summaryPrompt))",
            "title_prompt = \(quotedTOMLString(titlePrompt))",
            "",
            "[translation]",
            "enabled = \(translationEnabled ? "true" : "false")",
            "backend = \(quotedTOMLString(translationBackend))",
            "target_language = \(quotedTOMLString(translationTargetLanguage))",
            "local_model_alias = \(quotedTOMLString(translationLocalModelAlias))",
            "",
            "[workflow]",
            "default_cloud_summary = \(workflowDefaultCloudSummary ? "true" : "false")",
            "local_only = \(workflowLocalOnly ? "true" : "false")",
            "chunking = \(quotedTOMLString(workflowChunking))",
            "chunk_length = \(quotedTOMLString(workflowChunkLength))",
            "overlap = \(quotedTOMLString(workflowOverlap))",
            "",
            "[library]",
            "storage = \(quotedTOMLString(libraryStorage))",
            "icloud_root = \(quotedTOMLString(libraryICloudRoot))",
            "local_root = \(quotedTOMLString(libraryLocalRoot))",
            "",
            "[ui]",
            "language = \"zh\"",
            "theme = \"system\"",
            "reading_text_size = \(quotedTOMLString(readingTextSize))",
            "reading_line_spacing = \(quotedTOMLString(readingLineSpacing))",
            "reading_content_width = \(quotedTOMLString(readingContentWidth))",
            "reading_font = \(quotedTOMLString(readingFont))",
            "hide_read_items = \(hideReadItems ? "true" : "false")",
            "no_alt_screen = false",
            "",
        ]
        .joined(separator: "\n")
    }

    static func template() -> String {
        (try? CloudConfigFile().serialized()) ?? """
        [local]
        asr_model = "\(LocalASRModel.defaultAlias)"
        asr_profile = "\(LocalASRProfile.defaultName)"

        [cloud]
        api_base = "\(defaultBaseURL)"
        api_key = ""
        model = "\(defaultModel)"
        timeout = "\(defaultCloudTimeout)"
        temperature = "\(defaultCloudTemperature)"
        max_tokens = "\(defaultCloudMaxTokens)"
        model_options = ["gpt-5.4-mini", "gpt-5.4", "gpt-5.5", "gpt-5.6-sol", "gpt-5.6-terra", "gpt-5.6-luna"]
        summary_prompt = ""
        title_prompt = ""

        [translation]
        enabled = false
        backend = "cloud"
        target_language = "zh"
        local_model_alias = "nllb-200-distilled-600m"

        [workflow]
        default_cloud_summary = false
        local_only = false
        chunking = "auto"
        chunk_length = 1200
        overlap = 10

        [library]
        storage = "icloud"
        icloud_root = ""
        local_root = ""

        [ui]
        language = "zh"
        theme = "system"
        reading_text_size = "large"
        reading_line_spacing = "comfortable"
        reading_content_width = "full"
        reading_font = "system"
        hide_read_items = false
        no_alt_screen = false
        """
    }

    private static func parseQuotedTOMLString(_ value: String) throws -> String {
        guard value.first == "\"", value.last == "\"" else {
            throw AppError.invalidImportOutput("Invalid config.toml string value.")
        }
        var result = ""
        var escaping = false
        for character in value.dropFirst().dropLast() {
            if escaping {
                switch character {
                case "n":
                    result.append("\n")
                case "t":
                    result.append("\t")
                case "\"":
                    result.append("\"")
                case "\\":
                    result.append("\\")
                default:
                    result.append(character)
                }
                escaping = false
                continue
            }
            if character == "\\" {
                escaping = true
            } else {
                result.append(character)
            }
        }
        if escaping {
            result.append("\\")
        }
        return result
    }

    private static func parseQuotedTOMLStringArray(_ value: String) throws -> [String] {
        let trimmed = value.trimmingCharacters(in: .whitespacesAndNewlines)
        guard trimmed.first == "[", trimmed.last == "]" else {
            throw AppError.invalidImportOutput("Invalid config.toml string array value.")
        }
        let body = trimmed.dropFirst().dropLast().trimmingCharacters(in: .whitespacesAndNewlines)
        if body.isEmpty {
            return []
        }
        var items: [String] = []
        var current = ""
        var inQuotes = false
        var escaping = false
        for character in body {
            if escaping {
                current.append("\\")
                current.append(character)
                escaping = false
                continue
            }
            if character == "\\" {
                escaping = true
                continue
            }
            if character == "\"" {
                inQuotes.toggle()
                current.append(character)
                continue
            }
            if character == ",", !inQuotes {
                let item = current.trimmingCharacters(in: .whitespacesAndNewlines)
                if !item.isEmpty {
                    try items.append(parseQuotedTOMLString(item))
                }
                current = ""
                continue
            }
            current.append(character)
        }
        let last = current.trimmingCharacters(in: .whitespacesAndNewlines)
        if !last.isEmpty {
            try items.append(parseQuotedTOMLString(last))
        }
        return items
    }

    private static func parseTOMLScalarString(_ value: String) throws -> String {
        if value.first == "\"", value.last == "\"" {
            return try parseQuotedTOMLString(value)
        }
        return value.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    private static func parseTOMLBool(_ value: String) throws -> Bool {
        switch value.lowercased() {
        case "true":
            return true
        case "false":
            return false
        default:
            throw AppError.invalidImportOutput("Invalid config.toml bool value.")
        }
    }

    private func quotedTOMLString(_ value: String) throws -> String {
        let escaped = value
            .replacingOccurrences(of: "\\", with: "\\\\")
            .replacingOccurrences(of: "\"", with: "\\\"")
            .replacingOccurrences(of: "\n", with: "\\n")
            .replacingOccurrences(of: "\t", with: "\\t")
        return "\"\(escaped)\""
    }

    private func quotedTOMLStringArray(_ values: [String]) throws -> String {
        let items = try values.map { try quotedTOMLString($0) }
        return "[" + items.joined(separator: ", ") + "]"
    }
}
