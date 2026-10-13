import Foundation
@testable import Audio2TextApp
import XCTest

final class LanguageSettingsTests: XCTestCase {
    func testDefaultsAndExplicitLegacyLanguage() throws {
        XCTAssertEqual(try CloudConfigFile.parse("").transcriptionLanguages, [])
        XCTAssertEqual(try CloudConfigFile.parse("").summaryLanguage, "zh")
        XCTAssertEqual(try CloudConfigFile.parse("[local]\nlanguage = \"jp\"").transcriptionLanguages, ["ja"])
        for text in ["[local]\nlanguage = \"zh\"\nlanguages = []", "[local]\nlanguages = []\nlanguage = \"zh\""] {
            XCTAssertEqual(try CloudConfigFile.parse(text).transcriptionLanguages, [])
        }
        XCTAssertThrowsError(try CloudConfigFile.parse("[summary]\nlanguage = \"auto\""))
    }

    func testLanguagesRoundTripWithoutKeyAndPreserveOtherConfig() throws {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: root) }
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        let url = CloudConfigFile.configURL(dataRoot: root)
        try "[local]\nlanguage = \"zh\"\nbackend = \"recording\"\n[profiles.custom]\nchunk_length = 42\n".write(to: url, atomically: true, encoding: .utf8)
        let store = AppSettingsStore(dataRoot: root, credentials: MemoryCloudCredentials())
        var settings = store.load(environment: [:], includeAPIKey: false)
        XCTAssertEqual(settings.transcriptionLanguages, ["zh"])
        settings.transcriptionLanguages = ["zh", "en"]
        settings.summaryLanguage = "en"
        settings.summaryPrompt = "Keep my custom structure."
        try store.save(settings, environment: [:])
        let reloaded = store.load(environment: [:], includeAPIKey: false)
        XCTAssertEqual(reloaded.transcriptionLanguages, ["zh", "en"])
        XCTAssertEqual(reloaded.summaryLanguage, "en")
        XCTAssertEqual(reloaded.summaryPrompt, "Keep my custom structure.")
        let text = try String(contentsOf: url, encoding: .utf8)
        XCTAssertTrue(text.contains("backend = \"recording\""))
        XCTAssertTrue(text.contains("[profiles.custom]"))
        XCTAssertTrue(text.contains("chunk_length = 42"))
        XCTAssertFalse(text.contains("\nlanguage = \"zh\"\nbackend"))
    }

    func testBuiltInPromptMigrationKeepsCustomPrompt() throws {
        var file = CloudConfigFile()
        file.summaryPrompt = AppSettings.legacySummaryPrompt
        file.titlePrompt = AppSettings.legacyTitlePrompt
        let migrated = try CloudConfigFile.parse(file.serialized())
        XCTAssertEqual(migrated.summaryPrompt, AppSettings.defaultSummaryPrompt)
        XCTAssertEqual(migrated.titlePrompt, AppSettings.defaultTitlePrompt)
        file.summaryPrompt = "Custom summary structure."
        XCTAssertEqual(try CloudConfigFile.parse(file.serialized()).summaryPrompt, file.summaryPrompt)
    }

    @MainActor
    func testSRTUsesSelectedMixedLanguages() throws {
        var settings = AppSettings()
        settings.transcriptionLanguages = ["zh", "en"]
        let arguments = SRTExportController(environment: [:]).buildArguments(input: URL(fileURLWithPath: "/tmp/episode.wav"), settings: settings)
        let index = try XCTUnwrap(arguments.firstIndex(of: "--request-json"))
        let data = Data(arguments[index + 1].utf8)
        let request = try JSONSerialization.jsonObject(with: data) as! [String: Any]
        let params = request["params"] as! [String: Any]
        XCTAssertEqual(params["languages"] as? [String], ["zh", "en"])
    }
}
