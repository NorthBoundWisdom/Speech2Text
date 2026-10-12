import AppKit
@testable import Audio2TextApp
import SwiftUI
import XCTest

final class AppSettingsTests: XCTestCase {
    func testCloudSettingsDoesNotReadEnvironmentOverrides() {
        XCTAssertEqual(CloudSettings.defaultAPIBase, "")
        XCTAssertEqual(CloudSettings.load(environment: [:]).model, "gpt-5.4-mini")

        let settings = CloudSettings.load(
            environment: [
                "ATOT_CLOUD_API_BASE": "https://api.example/v1",
                "ATOT_CLOUD_MODEL": "kimi-test",
                "ATOT_CLOUD_API_KEY": "sk-123456",
            ]
        )

        XCTAssertEqual(settings.apiBase, CloudSettings.defaultAPIBase)
        XCTAssertEqual(settings.apiBase, "")
        XCTAssertEqual(settings.model, "gpt-5.4-mini")
        XCTAssertFalse(settings.isConfigured)
        XCTAssertNil(settings.environment(over: [:])["ATOT_CLOUD_API_KEY"])
        XCTAssertFalse(settings.redactedDescription.contains("sk-123456"))
    }

    func testCloudConfigurationRequiresEndpointAndAPIKey() {
        var cloudSettings = CloudSettings.load(environment: [:])
        cloudSettings.apiKey = "test-key"
        XCTAssertFalse(cloudSettings.isConfigured)

        cloudSettings.apiBase = "https://api.example/v1"
        XCTAssertTrue(cloudSettings.isConfigured)

        var appSettings = AppSettings()
        appSettings.apiKey = "test-key"
        XCTAssertFalse(appSettings.isCloudConfigured)

        appSettings.apiBase = "https://api.example/v1"
        XCTAssertTrue(appSettings.isCloudConfigured)
    }

    func testAppSettingsDefaultsToCloudTranslationDisabled() {
        let dataRoot = URL(fileURLWithPath: NSTemporaryDirectory()).appendingPathComponent(UUID().uuidString)
        let store = AppSettingsStore(dataRoot: dataRoot, credentials: MemoryCloudCredentials())

        let settings = store.load(environment: [:])

        XCTAssertEqual(AppSettings().cloudModel, "gpt-5.4-mini")
        XCTAssertEqual(settings.cloudModel, "gpt-5.4-mini")
        XCTAssertEqual(settings.cloudModelOptions.first, "gpt-5.4-mini")
        XCTAssertEqual(store.cloudSettings(environment: [:]).model, "gpt-5.4-mini")
        XCTAssertFalse(settings.translation.enabled)
        XCTAssertEqual(settings.translation.backend, .cloud)
        XCTAssertEqual(settings.translation.targetLanguage, "zh")
        XCTAssertEqual(settings.translation.localModelAlias, "nllb-200-distilled-600m")
        XCTAssertEqual(settings.readingStyle, .default)
        XCTAssertEqual(settings.libraryStorage, "icloud")
        XCTAssertEqual(settings.libraryICloudRoot, "")
        XCTAssertEqual(settings.libraryLocalRoot, "")
        XCTAssertFalse(settings.hideReadItems)
    }

    func testAppSettingsStorePersistsNonSecretConfigCredentialAndTranslationSettings() throws {
        let dataRoot = URL(fileURLWithPath: NSTemporaryDirectory()).appendingPathComponent(UUID().uuidString)
        let store = AppSettingsStore(dataRoot: dataRoot, credentials: MemoryCloudCredentials())
        var settings = AppSettings()
        settings.localASRModel = "small-4bit"
        settings.localASRProfile = "quality_zh_podcast"
        settings.apiBase = "https://api.example/v1"
        settings.cloudModel = "model-x"
        settings.summaryPrompt = "自定义总结提示词"
        settings.titlePrompt = "自定义标题提示词"
        settings.apiKey = "secret-key"
        settings.translation = TranslationSettings(
            enabled: true,
            backend: .local,
            targetLanguage: "zh",
            localModelAlias: "custom-local-translator"
        )
        settings.workflowDefaultCloudSummary = true
        settings.workflowLocalOnly = true
        settings.workflowChunking = "fixed"
        settings.workflowChunkLength = "900"
        settings.workflowOverlap = "12"
        settings.libraryStorage = "local"
        settings.libraryLocalRoot = "/tmp/audio2text-library"
        settings.hideReadItems = true
        settings.readingStyle = ReadingStyleSettings(
            textSize: .xxLarge,
            lineSpacing: .spacious,
            contentWidth: .standard,
            fontDesign: .serif
        )
        try store.save(settings, environment: [:])

        let loaded = store.load(environment: [:])

        XCTAssertEqual(loaded.localASRModel, "small-4bit")
        XCTAssertEqual(loaded.localASRProfile, "quality_zh_podcast")
        XCTAssertEqual(loaded.apiBase, "https://api.example/v1")
        XCTAssertEqual(loaded.cloudModel, "model-x")
        XCTAssertEqual(loaded.summaryPrompt, "自定义总结提示词")
        XCTAssertEqual(loaded.titlePrompt, "自定义标题提示词")
        XCTAssertEqual(loaded.apiKey, "secret-key")
        XCTAssertTrue(loaded.isCloudConfigured)
        XCTAssertEqual(
            loaded.cloudModelOptions,
            ["gpt-5.4-mini", "gpt-5.4", "gpt-5.5", "gpt-5.6-sol", "gpt-5.6-terra", "gpt-5.6-luna"]
        )
        XCTAssertTrue(loaded.translation.enabled)
        XCTAssertEqual(loaded.translation.backend, .local)
        XCTAssertEqual(loaded.translation.targetLanguage, "zh")
        XCTAssertEqual(loaded.translation.localModelAlias, "custom-local-translator")
        XCTAssertTrue(loaded.workflowDefaultCloudSummary)
        XCTAssertTrue(loaded.workflowLocalOnly)
        XCTAssertEqual(loaded.workflowChunking, "fixed")
        XCTAssertEqual(loaded.workflowChunkLength, "900")
        XCTAssertEqual(loaded.workflowOverlap, "12")
        XCTAssertEqual(loaded.libraryStorage, "local")
        XCTAssertEqual(loaded.libraryLocalRoot, "/tmp/audio2text-library")
        XCTAssertTrue(loaded.hideReadItems)
        XCTAssertEqual(loaded.readingStyle.textSize, .xxLarge)
        XCTAssertEqual(loaded.readingStyle.lineSpacing, .spacious)
        XCTAssertEqual(loaded.readingStyle.contentWidth, .standard)
        XCTAssertEqual(loaded.readingStyle.fontDesign, .serif)
        let config = try String(contentsOf: dataRoot.appendingPathComponent("config.toml"), encoding: .utf8)
        XCTAssertTrue(config.contains("model = \"model-x\""))
        XCTAssertTrue(config.contains("api_base = \"https://api.example/v1\""))
        XCTAssertFalse(config.contains("secret-key"))
        XCTAssertTrue(config.contains("api_key_store = \"system\""))
        XCTAssertFalse(config.contains("auth_mode"))
        XCTAssertFalse(config.contains("wire_api"))
        XCTAssertTrue(config.contains("asr_model = \"small-4bit\""))
        XCTAssertTrue(config.contains("asr_profile = \"quality_zh_podcast\""))
        XCTAssertTrue(config.contains("summary_prompt = \"自定义总结提示词\""))
        XCTAssertTrue(config.contains("backend = \"local\""))
        XCTAssertTrue(config.contains("default_cloud_summary = true"))
        XCTAssertTrue(config.contains("local_only = true"))
        XCTAssertTrue(config.contains("chunking = \"fixed\""))
        XCTAssertTrue(config.contains("chunk_length = \"900\""))
        XCTAssertTrue(config.contains("[library]"))
        XCTAssertTrue(config.contains("storage = \"local\""))
        XCTAssertTrue(config.contains("local_root = \"/tmp/audio2text-library\""))
        XCTAssertTrue(config.contains("reading_text_size = \"xxlarge\""))
        XCTAssertTrue(config.contains("reading_line_spacing = \"spacious\""))
        XCTAssertTrue(config.contains("reading_content_width = \"standard\""))
        XCTAssertTrue(config.contains("reading_font = \"serif\""))
        XCTAssertTrue(config.contains("hide_read_items = true"))
        XCTAssertTrue(config.contains("model_options = [\"gpt-5.4-mini\", \"gpt-5.4\", \"gpt-5.5\", \"gpt-5.6-sol\", \"gpt-5.6-terra\", \"gpt-5.6-luna\"]"))
    }

    func testAppSettingsStoreLoadDoesNotRewriteCompleteConfig() throws {
        let dataRoot = URL(fileURLWithPath: NSTemporaryDirectory()).appendingPathComponent(UUID().uuidString)
        let store = AppSettingsStore(dataRoot: dataRoot, credentials: MemoryCloudCredentials())
        var settings = AppSettings()
        settings.apiKey = "stable-key"
        try store.save(settings, environment: [:])
        let configURL = dataRoot.appendingPathComponent("config.toml")
        let markerDate = Date(timeIntervalSince1970: 1_700_000_000)
        try FileManager.default.setAttributes([.modificationDate: markerDate], ofItemAtPath: configURL.path)

        _ = store.load(environment: [:])
        guard let after = try FileManager.default.attributesOfItem(atPath: configURL.path)[.modificationDate] as? Date else {
            XCTFail("Expected config.toml modification date")
            return
        }

        XCTAssertEqual(after.timeIntervalSince1970, markerDate.timeIntervalSince1970, accuracy: 0.001)
    }

    func testAppSettingsStoreFallsBackFromInvalidReadingStyleConfig() throws {
        let dataRoot = URL(fileURLWithPath: NSTemporaryDirectory()).appendingPathComponent(UUID().uuidString)
        let store = AppSettingsStore(dataRoot: dataRoot, credentials: MemoryCloudCredentials())
        try FileManager.default.createDirectory(at: dataRoot, withIntermediateDirectories: true)
        try """
        [ui]
        reading_text_size = "enormous"
        reading_line_spacing = "airy"
        reading_content_width = "paperback"
        reading_font = "fantasy"
        """.write(to: dataRoot.appendingPathComponent("config.toml"), atomically: true, encoding: .utf8)

        let settings = store.load(environment: [:])

        XCTAssertEqual(settings.readingStyle, .default)
    }

    func testAppSettingsStoreReadsCloudSettingsFromCloudSection() throws {
        let dataRoot = URL(fileURLWithPath: NSTemporaryDirectory()).appendingPathComponent(UUID().uuidString)
        let store = AppSettingsStore(dataRoot: dataRoot, credentials: MemoryCloudCredentials())
        let copiedStore = store
        try FileManager.default.createDirectory(at: dataRoot, withIntermediateDirectories: true)
        try """
        [cloud]
        api_base = "https://api.example/v1"
        api_key = "stored-key"
        model = "model-x"
        """.write(to: dataRoot.appendingPathComponent("config.toml"), atomically: true, encoding: .utf8)

        XCTAssertEqual(store.cloudSettings(environment: [:]).apiKey, "stored-key")
        XCTAssertEqual(store.cloudSettings(environment: [:]).apiBase, "https://api.example/v1")
        XCTAssertEqual(store.cloudSettings(environment: [:]).model, "model-x")
        XCTAssertEqual(store.cloudSettings(environment: [:]).titlePrompt, AppSettings.defaultTitlePrompt)
        XCTAssertEqual(
            store.load(environment: [:]).cloudModelOptions,
            ["gpt-5.4-mini", "gpt-5.4", "gpt-5.5", "gpt-5.6-sol", "gpt-5.6-terra", "gpt-5.6-luna"]
        )
        XCTAssertEqual(copiedStore.cloudSettings(environment: [:]).apiKey, "stored-key")
        XCTAssertEqual(copiedStore.cloudSettings(environment: [:]).titlePrompt, AppSettings.defaultTitlePrompt)
    }

    func testAppSettingsStoreLoadWithoutAPIKeyUsesEmptyString() {
        let dataRoot = URL(fileURLWithPath: NSTemporaryDirectory()).appendingPathComponent(UUID().uuidString)
        let store = AppSettingsStore(dataRoot: dataRoot, credentials: MemoryCloudCredentials())

        let settings = store.load(environment: [:], includeAPIKey: false)

        XCTAssertEqual(settings.apiKey, "")
    }

    func testAppSettingsStoreSaveUpdatesCloudAPIKey() throws {
        let dataRoot = URL(fileURLWithPath: NSTemporaryDirectory()).appendingPathComponent(UUID().uuidString)
        let store = AppSettingsStore(dataRoot: dataRoot, credentials: MemoryCloudCredentials())
        try FileManager.default.createDirectory(at: dataRoot, withIntermediateDirectories: true)
        try """
        [cloud]
        api_base = "https://api.example/v1"
        model = "model-x"
        api_key = "old-key"
        """.write(to: dataRoot.appendingPathComponent("config.toml"), atomically: true, encoding: .utf8)

        XCTAssertEqual(store.cloudSettings(environment: [:]).apiKey, "old-key")
        var settings = AppSettings()
        settings.apiBase = "https://api.example/v1"
        settings.cloudModel = "model-x"
        settings.apiKey = "new-key"
        try store.save(settings, environment: [:])

        XCTAssertEqual(store.cloudSettings(environment: [:]).apiKey, "new-key")
        let config = try String(contentsOf: dataRoot.appendingPathComponent("config.toml"), encoding: .utf8)
        XCTAssertFalse(config.contains("new-key"))
        XCTAssertTrue(config.contains("api_key_store = \"system\""))
    }

    func testAppSettingsStoreKeepsAPIKeyOutOfConfig() throws {
        let dataRoot = URL(fileURLWithPath: NSTemporaryDirectory()).appendingPathComponent(UUID().uuidString)
        let store = AppSettingsStore(dataRoot: dataRoot, credentials: MemoryCloudCredentials())
        try FileManager.default.createDirectory(at: dataRoot, withIntermediateDirectories: true)
        try """
        [cloud]
        api_base = "https://api.example/v1"
        model = "model-x"
        api_key = "sk-secret-real-value"
        """.write(to: dataRoot.appendingPathComponent("config.toml"), atomically: true, encoding: .utf8)

        var settings = store.load(environment: [:])
        settings.apiBase = "https://api.changed/v1"
        settings.apiKey = "literal-****-value"
        try store.save(settings, environment: [:])

        let loaded = store.load(environment: [:])
        XCTAssertEqual(loaded.apiBase, "https://api.changed/v1")
        XCTAssertEqual(loaded.apiKey, "literal-****-value")
        let config = try String(contentsOf: dataRoot.appendingPathComponent("config.toml"), encoding: .utf8)
        XCTAssertFalse(config.contains("literal-****-value"))
        XCTAssertTrue(config.contains("api_key_store = \"system\""))
        XCTAssertFalse(config.contains("api_key = \"sk-secret-real-value\""))
    }

    func testAppSettingsStoreKeepsSavedCloudModelWhenEnvironmentHasOldModel() throws {
        let dataRoot = URL(fileURLWithPath: NSTemporaryDirectory()).appendingPathComponent(UUID().uuidString)
        let store = AppSettingsStore(dataRoot: dataRoot, credentials: MemoryCloudCredentials())
        let environment = [
            "ATOT_CLOUD_MODEL": "gpt-5.4",
        ]
        var settings = AppSettings()
        settings.cloudModel = "gpt-5.4-mini"

        try store.save(settings, environment: environment)
        let loaded = store.load(environment: environment)

        XCTAssertEqual(loaded.cloudModel, "gpt-5.4-mini")
        let config = try String(contentsOf: dataRoot.appendingPathComponent("config.toml"), encoding: .utf8)
        XCTAssertTrue(config.contains("model = \"gpt-5.4-mini\""))
    }

    func testEnsureCloudConfigFileCreatesTemplate() throws {
        let dataRoot = URL(fileURLWithPath: NSTemporaryDirectory()).appendingPathComponent(UUID().uuidString)
        let store = AppSettingsStore(dataRoot: dataRoot, credentials: MemoryCloudCredentials())

        let url = try store.ensureCloudConfigFile(environment: [:])

        XCTAssertEqual(url, dataRoot.appendingPathComponent("config.toml"))
        let text = try String(contentsOf: url, encoding: .utf8)
        XCTAssertTrue(text.contains("[cloud]"))
        XCTAssertTrue(text.contains("api_base = \"\""))
        XCTAssertTrue(text.contains("model = \"gpt-5.4-mini\""))
        XCTAssertTrue(text.contains("api_key = \"\""))
        XCTAssertFalse(text.contains("auth_mode"))
        XCTAssertFalse(text.contains("wire_api"))
        XCTAssertTrue(text.contains("[local]"))
        XCTAssertTrue(text.contains("[translation]"))
        XCTAssertTrue(text.contains("[workflow]"))
        XCTAssertTrue(text.contains("[library]"))
        XCTAssertTrue(text.contains("storage = \"icloud\""))
        XCTAssertTrue(text.contains("icloud_root = \"\""))
        XCTAssertTrue(text.contains("local_root = \"\""))
        XCTAssertTrue(text.contains("[ui]"))
        XCTAssertTrue(text.contains("reading_text_size = \"large\""))
        XCTAssertTrue(text.contains("reading_line_spacing = \"comfortable\""))
        XCTAssertTrue(text.contains("reading_content_width = \"full\""))
        XCTAssertTrue(text.contains("reading_font = \"system\""))
        XCTAssertTrue(text.contains("hide_read_items = false"))
        XCTAssertTrue(text.contains("model_options = [\"gpt-5.4-mini\", \"gpt-5.4\", \"gpt-5.5\", \"gpt-5.6-sol\", \"gpt-5.6-terra\", \"gpt-5.6-luna\"]"))
    }

    func testEditableComboBoxSelectionCommitsSelectedModelWhenDisplayedTextIsStale() {
        var selectedModel = "gpt-5.4-mini"
        let binding = Binding<String>(
            get: { selectedModel },
            set: { selectedModel = $0 }
        )
        let coordinator = EditableComboBox.Coordinator(text: binding)
        let comboBox = NSComboBox()
        comboBox.addItems(withObjectValues: CloudConfigFile.defaultModelOptions)
        comboBox.selectItem(withObjectValue: "gpt-5.6-sol")
        comboBox.stringValue = "gpt-5.4-mini"

        coordinator.comboBoxSelectionDidChange(Notification(name: NSComboBox.selectionDidChangeNotification, object: comboBox))

        XCTAssertEqual(selectedModel, "gpt-5.6-sol")
    }

    func testAppSettingsStoreFallsBackFromUnsupportedASRModel() throws {
        let dataRoot = URL(fileURLWithPath: NSTemporaryDirectory()).appendingPathComponent(UUID().uuidString)
        let store = AppSettingsStore(dataRoot: dataRoot, credentials: MemoryCloudCredentials())
        try FileManager.default.createDirectory(at: dataRoot, withIntermediateDirectories: true)
        try """
        [local]
        asr_model = "tiny"
        """.write(to: dataRoot.appendingPathComponent("config.toml"), atomically: true, encoding: .utf8)

        let loaded = store.load(environment: [:])

        XCTAssertEqual(loaded.localASRModel, LocalASRModel.defaultAlias)
    }
}

extension AppSettingsTests {
    private func credentialTestDirectory() throws -> URL {
        let root = URL(fileURLWithPath: NSTemporaryDirectory()).appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        return root
    }

    func testCredentialMigrationPreservesUnrecognizedSettingsAndComments() throws {
        let root = try credentialTestDirectory()
        defer { try? FileManager.default.removeItem(at: root) }
        let credentials = MemoryCloudCredentials()
        let store = AppSettingsStore(dataRoot: root, credentials: credentials)
        let url = CloudConfigFile.configURL(dataRoot: root)
        try """
        # keep custom configuration
        [cloud]
        api_key = "legacy-test-key"
        [profiles.custom]
        language = "ja"
        """.write(to: url, atomically: true, encoding: .utf8)
        XCTAssertEqual(store.load().apiKey, "legacy-test-key")
        let text = try String(contentsOf: url, encoding: .utf8)
        XCTAssertFalse(text.contains("legacy-test-key"))
        XCTAssertTrue(text.contains("# keep custom configuration"))
        XCTAssertTrue(text.contains("[profiles.custom]"))
    }

    func testCredentialMigrationFailurePreservesOriginalAndReportsError() throws {
        let root = try credentialTestDirectory()
        defer { try? FileManager.default.removeItem(at: root) }
        let credentials = MemoryCloudCredentials()
        credentials.fails = true
        let store = AppSettingsStore(dataRoot: root, credentials: credentials)
        let url = CloudConfigFile.configURL(dataRoot: root)
        let original = "[cloud]\napi_key = \"legacy-test-key\"\nmodel = \"model-x\"\n"
        try original.write(to: url, atomically: true, encoding: .utf8)
        let settings = store.load()
        XCTAssertFalse(settings.configurationError.isEmpty)
        XCTAssertEqual(settings.apiKey, "")
        XCTAssertEqual(settings.cloudModel, "model-x")
        XCTAssertEqual(try String(contentsOf: url, encoding: .utf8), original)
        XCTAssertThrowsError(try store.save(settings))
    }
}
