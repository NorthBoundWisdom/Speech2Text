import Foundation

enum Audio2TextCliLauncher {
    static let executableName = "Audio2TextCli"

    static func isCliInvocation(arguments: [String] = CommandLine.arguments) -> Bool {
        guard let executable = arguments.first else { return false }
        return URL(fileURLWithPath: executable).lastPathComponent == executableName
    }

    static func runIfRequested(
        arguments: [String] = CommandLine.arguments,
        environment: [String: String] = ProcessInfo.processInfo.environment,
        bundle: Bundle = .main
    ) -> Int32? {
        guard isCliInvocation(arguments: arguments) else { return nil }
        do {
            let runtime = try RuntimeManager.context(environment: environment, bundle: bundle)
            return try runPythonModule(arguments: Array(arguments.dropFirst()), runtime: runtime)
        } catch {
            writeStandardError("\(error.localizedDescription)\n")
            return 1
        }
    }

    static func pythonModuleArguments(from cliArguments: [String]) -> [String] {
        ["-m", "atot.cli"] + cliArguments
    }

    private static func runPythonModule(arguments: [String], runtime: RuntimeContext) throws -> Int32 {
        let process = Process()
        process.executableURL = AppPaths.envPython(dataRoot: runtime.dataRoot)
        process.arguments = pythonModuleArguments(from: arguments)
        process.currentDirectoryURL = runtime.workingDirectory
        process.environment = runtime.environment

        let stdout = Pipe()
        let stderr = Pipe()
        process.standardOutput = stdout
        process.standardError = stderr
        stdout.fileHandleForReading.readabilityHandler = { handle in
            let data = handle.availableData
            if !data.isEmpty {
                FileHandle.standardOutput.write(data)
            }
        }
        stderr.fileHandleForReading.readabilityHandler = { handle in
            let data = handle.availableData
            if !data.isEmpty {
                FileHandle.standardError.write(data)
            }
        }
        defer {
            stdout.fileHandleForReading.readabilityHandler = nil
            stderr.fileHandleForReading.readabilityHandler = nil
        }

        try process.run()
        process.waitUntilExit()
        flush(stdout.fileHandleForReading, to: .standardOutput)
        flush(stderr.fileHandleForReading, to: .standardError)
        return process.terminationStatus
    }

    private static func flush(_ handle: FileHandle, to output: FileHandle) {
        let data = handle.availableData
        if !data.isEmpty {
            output.write(data)
        }
    }

    private static func writeStandardError(_ text: String) {
        guard let data = text.data(using: .utf8) else { return }
        FileHandle.standardError.write(data)
    }
}
