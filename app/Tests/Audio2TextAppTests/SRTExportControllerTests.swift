@testable import Audio2TextApp
import XCTest

@MainActor
final class SRTExportControllerTests: XCTestCase {
    func testBuildsCloudTranslatedSRTCommandWithoutImporting() {
        let controller = SRTExportController()
        controller.overwrite = true
        var settings = AppSettings()
        settings.translation.enabled = true
        settings.translation.backend = .cloud

        let arguments = controller.buildArguments(
            input: URL(fileURLWithPath: "/tmp/video.mp4"),
            settings: settings
        )

        let request = serviceRequest(arguments)
        XCTAssertEqual(request["method"] as? String, "srt")
        let params = request["params"] as? [String: Any]
        XCTAssertEqual(params?["inputs"] as? [String], ["/tmp/video.mp4"])
        XCTAssertEqual(params?["languages"] as? [String], ["auto"])
        XCTAssertEqual(params?["overwrite"] as? Bool, true)
        XCTAssertFalse(arguments.contains("import-local"))
    }

    func testReportsSuccessOutputPathFromFakeRunner() async throws {
        let dataRoot = URL(fileURLWithPath: NSTemporaryDirectory()).appendingPathComponent(UUID().uuidString)
        let settingsStore = AppSettingsStore(dataRoot: dataRoot, credentials: MemoryCloudCredentials())
        let runtime = RuntimeContext(
            dataRoot: dataRoot,
            workingDirectory: dataRoot.appendingPathComponent("cache"),
            cli: URL(fileURLWithPath: "/Applications/Audio2Text.app/Contents/MacOS/Audio2TextCli"),
            environment: AppPaths.environment(dataRoot: dataRoot, over: [:])
        )
        let expectedOutput = "/tmp/video.zh.srt"
        let controller = SRTExportController(
            settingsStore: settingsStore,
            environment: [:],
            runtimeProvider: { runtime },
            runner: { _, _, _, _, onOutput in
                onOutput("running\n")
                return ProcessResult(
                    code: 0,
                    output: #"""
                    progress line
                    {"success":true,"results":[{"success":true,"srt_path":"\#(expectedOutput)"}]}
                    """#
                )
            }
        )
        var settings = AppSettings()
        settings.translation.enabled = true
        try settingsStore.save(settings, environment: [:])
        controller.selectedFile = URL(fileURLWithPath: "/tmp/video.mp4")

        controller.export()

        try await waitForSRTCondition("srt succeeds") {
            controller.successURL?.path == expectedOutput
        }
        XCTAssertTrue(controller.logText.contains("running"))
        XCTAssertTrue(controller.logText.contains(expectedOutput))
    }

    func testSurfacesProcessFailureFromFakeRunner() async throws {
        let dataRoot = URL(fileURLWithPath: NSTemporaryDirectory()).appendingPathComponent(UUID().uuidString)
        let runtime = RuntimeContext(
            dataRoot: dataRoot,
            workingDirectory: dataRoot.appendingPathComponent("cache"),
            cli: URL(fileURLWithPath: "/Applications/Audio2Text.app/Contents/MacOS/Audio2TextCli"),
            environment: AppPaths.environment(dataRoot: dataRoot, over: [:])
        )
        let controller = SRTExportController(
            environment: [:],
            runtimeProvider: { runtime },
            runner: { _, _, _, _, _ in
                throw AppError.processFailed(command: "srt", code: 1, output: "SRT already exists")
            }
        )
        controller.selectedFile = URL(fileURLWithPath: "/tmp/video.mp4")

        controller.export()

        try await waitForSRTCondition("srt fails") {
            if case let .failure(message) = controller.state {
                return message.contains("SRT already exists")
            }
            return false
        }
    }
}

private func serviceRequest(_ arguments: [String]) -> [String: Any] {
    XCTAssertEqual(arguments.first, "serve")
    XCTAssertTrue(arguments.contains("--stdio"))
    XCTAssertTrue(arguments.contains("--unwrap-result"))
    guard let index = arguments.firstIndex(of: "--request-json") else {
        XCTFail("missing --request-json")
        return [:]
    }
    let data = arguments[index + 1].data(using: .utf8)!
    return (try! JSONSerialization.jsonObject(with: data)) as! [String: Any]
}

@MainActor
private func waitForSRTCondition(
    _ description: String,
    timeout: TimeInterval = 1,
    condition: @escaping () -> Bool
) async throws {
    let deadline = Date().addingTimeInterval(timeout)
    while Date() < deadline {
        if condition() {
            return
        }
        try await Task.sleep(nanoseconds: 10_000_000)
    }
    XCTFail(description)
}
