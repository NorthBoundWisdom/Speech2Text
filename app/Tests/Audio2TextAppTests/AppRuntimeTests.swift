@testable import Audio2TextApp
import XCTest

final class AppRuntimeTests: XCTestCase {
    func testRuntimeContextUsesDataRootWithoutRepository() {
        let dataRoot = URL(fileURLWithPath: "/tmp/audio2text-data")
        let context = RuntimeContext(
            dataRoot: dataRoot,
            workingDirectory: dataRoot.appendingPathComponent("cache"),
            cli: URL(fileURLWithPath: "/Applications/Audio2Text.app/Contents/MacOS/Audio2TextCli"),
            environment: AppPaths.environment(dataRoot: dataRoot, over: [:])
        )

        XCTAssertEqual(context.workingDirectory.path, "/tmp/audio2text-data/cache")
        XCTAssertEqual(context.cli.lastPathComponent, "Audio2TextCli")
        XCTAssertNil(context.environment["ATOT_DATA_ROOT"])
    }

    func testAudio2TextCliLauncherDetectsOnlyCliExecutableName() {
        XCTAssertTrue(Audio2TextCliLauncher.isCliInvocation(arguments: [
            "/Applications/Audio2Text.app/Contents/MacOS/Audio2TextCli",
            "--help",
        ]))
        XCTAssertFalse(Audio2TextCliLauncher.isCliInvocation(arguments: [
            "/Applications/Audio2Text.app/Contents/MacOS/Audio2Text",
            "--help",
        ]))
        XCTAssertFalse(Audio2TextCliLauncher.isCliInvocation(arguments: []))
    }

    func testAudio2TextCliLauncherBuildsPythonModuleArguments() {
        XCTAssertEqual(
            Audio2TextCliLauncher.pythonModuleArguments(from: ["exec", "srt", "/tmp/clip.mp4", "--language", "zh"]),
            ["-m", "atot.cli", "exec", "srt", "/tmp/clip.mp4", "--language", "zh"]
        )
    }

    func testDefaultModelDownloadPathsStayUnderModelRoot() {
        let dataRoot = URL(fileURLWithPath: "/tmp/audio2text-data")
        let model = LocalASRModel.model(for: LocalASRModel.defaultAlias)

        XCTAssertEqual(model.files.map(\.pathUnderModelRoot), [
            "whisper-large-v3-turbo/config.json",
            "whisper-large-v3-turbo/weights.safetensors",
        ])
        XCTAssertEqual(
            AppPaths.modelRoot(dataRoot: dataRoot).appendingPathComponent(model.files[1].pathUnderModelRoot).path,
            "/tmp/audio2text-data/model/whisper-large-v3-turbo/weights.safetensors"
        )
    }

    func testLibraryRootDefaultsToVisibleICloudDriveFolder() {
        let root = AppPaths.libraryRoot(
            storage: "icloud",
            iCloudRoot: "",
            localRoot: "",
            dataRoot: URL(fileURLWithPath: "/tmp/audio2text-data")
        )

        XCTAssertEqual(root.lastPathComponent, "Audio2TextLibrary")
        XCTAssertTrue(root.path.contains("/Library/Mobile Documents/com~apple~CloudDocs/Audio2Text/Audio2TextLibrary"))
    }

    func testLibraryRootUsesCustomLocalFolderAndExpandsHome() {
        XCTAssertEqual(
            AppPaths.libraryRoot(
                storage: "local",
                iCloudRoot: "",
                localRoot: "/tmp/audio2text-library",
                dataRoot: URL(fileURLWithPath: "/tmp/audio2text-data")
            ).path,
            "/tmp/audio2text-library/Audio2TextLibrary"
        )
        XCTAssertEqual(
            AppPaths.libraryRoot(
                storage: "local",
                iCloudRoot: "",
                localRoot: "~/Audio2TextLibraryRoot",
                dataRoot: URL(fileURLWithPath: "/tmp/audio2text-data")
            ).path,
            FileManager.default.homeDirectoryForCurrentUser
                .appendingPathComponent("Audio2TextLibraryRoot/Audio2TextLibrary")
                .path
        )
    }

    func testModelInventoryLoadsProductionModelsFromRepositorySource() {
        let aliases = LocalASRModel.all.map(\.alias)

        XCTAssertEqual(aliases, [LocalASRModel.defaultAlias, "small-4bit"])
        XCTAssertFalse(aliases.contains("large-v3"))
        XCTAssertFalse(aliases.contains("tiny"))
        XCTAssertFalse(aliases.contains("mlx-qwen3-asr-0.6b"))
    }

    func testModelInventoryCanResolveTranslationModelWithoutAddingItToASRPicker() {
        let asrAliases = LocalASRModel.all.map(\.alias)
        let translationModel = LocalASRModel.anyModel(for: TranslationSettings.defaultLocalModelAlias)

        XCTAssertFalse(asrAliases.contains(TranslationSettings.defaultLocalModelAlias))
        XCTAssertEqual(translationModel.alias, TranslationSettings.defaultLocalModelAlias)
        XCTAssertEqual(translationModel.files.map(\.name), [
            "config.json",
            "generation_config.json",
            "pytorch_model.bin",
            "sentencepiece.bpe.model",
            "special_tokens_map.json",
            "tokenizer.json",
            "tokenizer_config.json",
        ])
    }
}
