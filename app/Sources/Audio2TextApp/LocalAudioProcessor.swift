import Foundation

struct LocalProcessingResult: Equatable {
    let qaPassed: Bool
    let didTranscribe: Bool

    var taskState: ProcessingTaskState {
        qaPassed ? .success : .warning
    }
}

enum LocalAudioProcessingEvent {
    case willTranscribe(arguments: [String])
    case willRunQA(arguments: [String])
    case qaFailed(code: Int32, output: String)
}

struct LocalAudioProcessor {
    let runner: any ProcessRunning

    func run(
        audioURL: URL,
        outputDirectory: URL,
        runtime: RuntimeContext,
        onOutput: @escaping @MainActor (String) -> Void,
        onEvent: @MainActor (LocalAudioProcessingEvent) -> Void
    ) async throws -> LocalProcessingResult {
        let transcribeArguments = AtotServiceClient.transcribe(
            audioURL: audioURL,
            jobDirectory: outputDirectory
        )
        await onEvent(.willTranscribe(arguments: transcribeArguments))
        _ = try await runner.run(
            executable: runtime.cli,
            arguments: transcribeArguments,
            currentDirectory: runtime.workingDirectory,
            environment: runtime.environment,
            onOutput: onOutput
        )

        let qaArguments = AtotServiceClient.qa(outputDirectory: outputDirectory)
        await onEvent(.willRunQA(arguments: qaArguments))
        do {
            _ = try await runner.run(
                executable: runtime.cli,
                arguments: qaArguments,
                currentDirectory: runtime.workingDirectory,
                environment: runtime.environment,
                onOutput: onOutput
            )
            return LocalProcessingResult(qaPassed: true, didTranscribe: true)
        } catch let AppError.processFailed(_, code, output) {
            await onEvent(.qaFailed(code: code, output: output))
            return LocalProcessingResult(qaPassed: false, didTranscribe: true)
        }
    }
}
