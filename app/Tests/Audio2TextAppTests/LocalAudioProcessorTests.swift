@testable import Audio2TextApp
import XCTest

@MainActor
final class LocalAudioProcessorTests: XCTestCase {
    func testQAFailureReturnsWarningResultWithoutFailingLocalProcessing() async throws {
        let runner = FakeLocalProcessRunner(failingMethod: "qa")
        let processor = LocalAudioProcessor(runner: runner)
        let root = URL(fileURLWithPath: NSTemporaryDirectory()).appendingPathComponent(UUID().uuidString)
        let runtime = RuntimeContext(
            dataRoot: root,
            workingDirectory: root.appendingPathComponent("cache"),
            cli: root.appendingPathComponent("Audio2TextCli"),
            environment: ["ATOT_TEST": "1"]
        )
        let audioURL = root.appendingPathComponent("episode.m4a")
        let outputDirectory = root.appendingPathComponent("work/episode")
        var outputText = ""
        var events: [String] = []

        let result = try await processor.run(
            audioURL: audioURL,
            outputDirectory: outputDirectory,
            runtime: runtime,
            onOutput: { outputText.append($0) },
            onEvent: { event in
                switch event {
                case .willTranscribe:
                    events.append("transcribe")
                case .willRunQA:
                    events.append("qa")
                case let .qaFailed(code, output):
                    events.append("qa_failed:\(code):\(output)")
                }
            }
        )

        XCTAssertEqual(result, LocalProcessingResult(qaPassed: false, didTranscribe: true))
        XCTAssertEqual(runner.methods, ["transcribe", "qa"])
        XCTAssertEqual(events, ["transcribe", "qa", "qa_failed:2:Status: FAIL\nNeeds review"])
        XCTAssertTrue(outputText.contains("ran transcribe"))
        XCTAssertFalse(outputText.contains("ran qa"))
    }
}

private final class FakeLocalProcessRunner: ProcessRunning {
    private let failingMethod: String?
    private(set) var methods: [String] = []

    init(failingMethod: String? = nil) {
        self.failingMethod = failingMethod
    }

    func run(
        executable _: URL,
        arguments: [String],
        currentDirectory _: URL,
        environment _: [String: String]?,
        onOutput: @escaping @MainActor (String) -> Void
    ) async throws -> ProcessResult {
        let method = serviceMethod(arguments) ?? "unknown"
        methods.append(method)
        if method == failingMethod {
            throw AppError.processFailed(command: method, code: 2, output: "Status: FAIL\nNeeds review")
        }
        await onOutput("ran \(method)\n")
        return ProcessResult(code: 0, output: "ok")
    }

    private func serviceMethod(_ arguments: [String]) -> String? {
        guard
            let index = arguments.firstIndex(of: "--request-json"),
            arguments.indices.contains(index + 1),
            let data = arguments[index + 1].data(using: .utf8),
            let request = try? JSONSerialization.jsonObject(with: data) as? [String: Any]
        else {
            return nil
        }
        return request["method"] as? String
    }
}
