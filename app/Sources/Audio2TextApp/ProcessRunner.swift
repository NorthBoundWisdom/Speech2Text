import Foundation

struct ProcessResult {
    let code: Int32
    let output: String
}

final class LockedOutput: @unchecked Sendable {
    private let lock = NSLock()
    private var data = Data()

    func append(_ newData: Data) {
        lock.lock()
        data.append(newData)
        lock.unlock()
    }

    func stringValue() -> String {
        lock.lock()
        let copy = data
        lock.unlock()
        return String(data: copy, encoding: .utf8) ?? ""
    }
}

protocol ProcessRunning {
    func run(
        executable: URL,
        arguments: [String],
        currentDirectory: URL,
        environment: [String: String]?,
        onOutput: @escaping @MainActor (String) -> Void
    ) async throws -> ProcessResult
}

final class ProcessRunner: ProcessRunning {
    func run(
        executable: URL,
        arguments: [String],
        currentDirectory: URL,
        environment: [String: String]? = nil,
        onOutput: @escaping @MainActor (String) -> Void
    ) async throws -> ProcessResult {
        let process = Process()
        process.executableURL = executable
        process.arguments = arguments
        process.currentDirectoryURL = currentDirectory
        process.environment = environment

        let pipe = Pipe()
        process.standardOutput = pipe
        process.standardError = pipe

        let output = LockedOutput()
        let command = ([executable.path] + arguments).joined(separator: " ")
        let startedAt = Date()
        AppLogger.shared.log(
            .info,
            category: "process",
            event: "process_start",
            message: "Starting external command",
            fields: [
                "executable": executable.lastPathComponent,
                "argument_count": "\(arguments.count)",
                "command": AppLogger.redacted(command),
            ]
        )

        pipe.fileHandleForReading.readabilityHandler = { handle in
            let data = handle.availableData
            guard !data.isEmpty else { return }
            output.append(data)
            if let text = String(data: data, encoding: .utf8) {
                Task { @MainActor in
                    onOutput(text)
                }
            }
        }

        try process.run()

        return try await withCheckedThrowingContinuation { continuation in
            process.terminationHandler = { finished in
                pipe.fileHandleForReading.readabilityHandler = nil
                let trailing = pipe.fileHandleForReading.availableData
                if !trailing.isEmpty {
                    output.append(trailing)
                    if let text = String(data: trailing, encoding: .utf8) {
                        Task { @MainActor in
                            onOutput(text)
                        }
                    }
                }
                let outputText = output.stringValue()
                let result = ProcessResult(code: finished.terminationStatus, output: outputText)
                let duration = String(format: "%.3f", Date().timeIntervalSince(startedAt))
                if finished.terminationStatus == 0 {
                    AppLogger.shared.log(
                        .info,
                        category: "process",
                        event: "process_finish",
                        message: "External command completed",
                        fields: [
                            "executable": executable.lastPathComponent,
                            "exit_code": "\(finished.terminationStatus)",
                            "duration_seconds": duration,
                        ]
                    )
                    continuation.resume(returning: result)
                } else {
                    AppLogger.shared.log(
                        .error,
                        category: "process",
                        event: "process_failed",
                        message: "External command failed",
                        fields: [
                            "executable": executable.lastPathComponent,
                            "exit_code": "\(finished.terminationStatus)",
                            "duration_seconds": duration,
                            "summary": AppLogger.redacted(outputText),
                        ]
                    )
                    continuation.resume(
                        throwing: AppError.processFailed(
                            command: command,
                            code: finished.terminationStatus,
                            output: outputText
                        )
                    )
                }
            }
        }
    }
}
