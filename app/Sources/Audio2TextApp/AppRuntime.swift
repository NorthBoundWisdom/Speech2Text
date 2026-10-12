import Foundation

struct RuntimeContext: Equatable {
    let dataRoot: URL
    let workingDirectory: URL
    let cli: URL
    let environment: [String: String]
}

enum AppPaths {
    static func dataRoot(environment _: [String: String] = ProcessInfo.processInfo.environment) -> URL {
        if isAppStoreDistribution() {
            let support = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first
                ?? FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent("Library/Application Support")
            return support
                .appendingPathComponent("Audio2Text", isDirectory: true)
                .appendingPathComponent("SpeechToTextData", isDirectory: true)
                .standardizedFileURL
        }
        return FileManager.default.homeDirectoryForCurrentUser
            .appendingPathComponent("Documents")
            .appendingPathComponent("SpeechToTextData")
            .standardizedFileURL
    }

    static func isAppStoreDistribution(bundle: Bundle = .main) -> Bool {
        (bundle.object(forInfoDictionaryKey: "ATOTDistribution") as? String) == "app-store"
    }

    static func modelRoot(dataRoot: URL = dataRoot()) -> URL {
        dataRoot.appendingPathComponent("model")
    }

    static func envRoot(dataRoot: URL = dataRoot()) -> URL {
        dataRoot.appendingPathComponent("env")
    }

    static func cacheRoot(dataRoot: URL = dataRoot()) -> URL {
        dataRoot.appendingPathComponent("cache")
    }

    static func materialsRoot(dataRoot: URL = dataRoot()) -> URL {
        dataRoot.appendingPathComponent("materials")
    }

    static func workRoot(dataRoot: URL = dataRoot()) -> URL {
        dataRoot.appendingPathComponent("work")
    }

    static func defaultLibraryRoot() -> URL {
        FileManager.default.homeDirectoryForCurrentUser
            .appendingPathComponent("Library")
            .appendingPathComponent("Mobile Documents")
            .appendingPathComponent("com~apple~CloudDocs")
            .appendingPathComponent("Audio2Text", isDirectory: true)
            .appendingPathComponent("Audio2TextLibrary", isDirectory: true)
            .standardizedFileURL
    }

    static func localLibraryRoot(dataRoot: URL = dataRoot()) -> URL {
        dataRoot.appendingPathComponent("Audio2TextLibrary", isDirectory: true)
    }

    static func libraryRoot(storage: String, iCloudRoot: String, localRoot: String, dataRoot: URL = dataRoot()) -> URL {
        let normalizedStorage = storage.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
        if normalizedStorage == "local" {
            let trimmed = localRoot.trimmingCharacters(in: .whitespacesAndNewlines)
            return trimmed.isEmpty ? localLibraryRoot(dataRoot: dataRoot) : normalizedLibraryRoot(expandedFileURL(trimmed))
        }
        let trimmed = iCloudRoot.trimmingCharacters(in: .whitespacesAndNewlines)
        return trimmed.isEmpty ? defaultLibraryRoot() : normalizedLibraryRoot(expandedFileURL(trimmed))
    }

    static func normalizedLibraryRoot(_ url: URL) -> URL {
        url.lastPathComponent == "Audio2TextLibrary"
            ? url.standardizedFileURL
            : url.appendingPathComponent("Audio2TextLibrary", isDirectory: true).standardizedFileURL
    }

    private static func expandedFileURL(_ path: String) -> URL {
        if path == "~" {
            return FileManager.default.homeDirectoryForCurrentUser
        }
        if path.hasPrefix("~/") {
            return FileManager.default.homeDirectoryForCurrentUser
                .appendingPathComponent(String(path.dropFirst(2)), isDirectory: true)
        }
        return URL(fileURLWithPath: path, isDirectory: true)
    }

    static func processRoot(dataRoot: URL = dataRoot()) -> URL {
        materialsRoot(dataRoot: dataRoot)
    }

    static func outputRoot(dataRoot: URL = dataRoot()) -> URL {
        workRoot(dataRoot: dataRoot)
    }

    static func logsRoot(dataRoot: URL = dataRoot()) -> URL {
        cacheRoot(dataRoot: dataRoot).appendingPathComponent("logs")
    }

    static func toolsRoot(dataRoot: URL = dataRoot()) -> URL {
        cacheRoot(dataRoot: dataRoot).appendingPathComponent("tools")
    }

    static func cliExecutable(bundle: Bundle = .main) -> URL {
        if let executable = bundle.executableURL {
            return executable
                .deletingLastPathComponent()
                .appendingPathComponent("Audio2TextCli")
        }
        return URL(fileURLWithPath: FileManager.default.currentDirectoryPath)
            .appendingPathComponent("Audio2TextCli")
    }

    static func envPython(dataRoot: URL = dataRoot()) -> URL {
        envRoot(dataRoot: dataRoot).appendingPathComponent("bin/python")
    }

    static func runtimeWheelURL(bundle: Bundle = .main) -> URL? {
        bundle.urls(forResourcesWithExtension: "whl", subdirectory: nil)?
            .filter { $0.lastPathComponent.hasPrefix("audio2text_local-") }
            .sorted { $0.lastPathComponent > $1.lastPathComponent }
            .first
    }

    static func modelInventoryURL(bundle: Bundle = .main) -> URL? {
        if let bundled = bundle.url(forResource: "model_inventory", withExtension: "json") {
            return bundled
        }
        let current = URL(fileURLWithPath: FileManager.default.currentDirectoryPath)
        for relative in [
            "src/atot/data/model_inventory.json",
            "../src/atot/data/model_inventory.json",
            "../../src/atot/data/model_inventory.json",
        ] {
            let candidate = current.appendingPathComponent(relative).standardizedFileURL
            if FileManager.default.fileExists(atPath: candidate.path) {
                return candidate
            }
        }
        return nil
    }

    static func workingDirectory(dataRoot: URL = dataRoot()) -> URL {
        cacheRoot(dataRoot: dataRoot)
    }

    static func environment(dataRoot _: URL = dataRoot(), over base: [String: String] = ProcessInfo.processInfo.environment) -> [String: String] {
        base
    }

    static func outputDirectory(forAudio audioURL: URL, dataRoot: URL = dataRoot()) -> URL {
        let processRoot = materialsRoot(dataRoot: dataRoot).standardizedFileURL
        let audioDirectory = audioURL.deletingLastPathComponent().standardizedFileURL
        let processPath = processRoot.path
        let directoryPath = audioDirectory.path
        if directoryPath == processPath || directoryPath.hasPrefix(processPath + "/") {
            let relative = String(directoryPath.dropFirst(processPath.count)).trimmingCharacters(in: CharacterSet(charactersIn: "/"))
            return relative.isEmpty
                ? workRoot(dataRoot: dataRoot)
                : workRoot(dataRoot: dataRoot).appendingPathComponent(relative)
        }
        return workRoot(dataRoot: dataRoot).appendingPathComponent(PathTools.sanitizedSlug(audioURL.deletingPathExtension().lastPathComponent))
    }
}

enum RuntimeManager {
    static func context(
        environment: [String: String] = ProcessInfo.processInfo.environment,
        bundle: Bundle = .main
    ) throws -> RuntimeContext {
        let dataRoot = AppPaths.dataRoot(environment: environment)
        try ensureDirectories(dataRoot: dataRoot)
        try ensureRuntime(dataRoot: dataRoot, environment: environment, bundle: bundle)
        let cli = AppPaths.cliExecutable(bundle: bundle)
        guard FileManager.default.isExecutableFile(atPath: cli.path) else {
            throw AppError.cliNotFound(cli)
        }
        return RuntimeContext(
            dataRoot: dataRoot,
            workingDirectory: AppPaths.workingDirectory(dataRoot: dataRoot),
            cli: cli,
            environment: AppPaths.environment(dataRoot: dataRoot, over: environment)
        )
    }

    static func ensureDirectories(dataRoot: URL) throws {
        for url in [
            AppPaths.materialsRoot(dataRoot: dataRoot),
            AppPaths.workRoot(dataRoot: dataRoot),
            AppPaths.modelRoot(dataRoot: dataRoot),
            AppPaths.envRoot(dataRoot: dataRoot),
            AppPaths.cacheRoot(dataRoot: dataRoot),
            AppPaths.logsRoot(dataRoot: dataRoot),
            AppPaths.toolsRoot(dataRoot: dataRoot),
        ] {
            try FileManager.default.createDirectory(at: url, withIntermediateDirectories: true)
        }
    }

    static func runtimeStatus(dataRoot: URL, environment: [String: String] = ProcessInfo.processInfo.environment) -> Bool {
        let python = AppPaths.envPython(dataRoot: dataRoot)
        guard FileManager.default.isExecutableFile(atPath: python.path) else { return false }
        guard commandSucceeds(
            python,
            arguments: ["-m", "atot.cli", "models", "--json"],
            dataRoot: dataRoot,
            environment: environment
        ) else {
            return false
        }
        return commandOutputContains(
            python,
            arguments: ["-m", "atot.cli", "exec", "cloud", "summarize", "--help"],
            dataRoot: dataRoot,
            environment: environment,
            text: "--stream-summary"
        )
    }

    private static func commandSucceeds(
        _ executable: URL,
        arguments: [String],
        dataRoot: URL,
        environment: [String: String]
    ) -> Bool {
        commandOutput(executable, arguments: arguments, dataRoot: dataRoot, environment: environment)?.status == 0
    }

    private static func commandOutputContains(
        _ executable: URL,
        arguments: [String],
        dataRoot: URL,
        environment: [String: String],
        text: String
    ) -> Bool {
        guard let result = commandOutput(executable, arguments: arguments, dataRoot: dataRoot, environment: environment) else {
            return false
        }
        return result.status == 0 && result.output.contains(text)
    }

    private static func commandOutput(
        _ executable: URL,
        arguments: [String],
        dataRoot: URL,
        environment: [String: String]
    ) -> (status: Int32, output: String)? {
        let process = Process()
        process.executableURL = executable
        process.arguments = arguments
        process.currentDirectoryURL = AppPaths.workingDirectory(dataRoot: dataRoot)
        process.environment = AppPaths.environment(dataRoot: dataRoot, over: environment)
        let pipe = Pipe()
        process.standardOutput = pipe
        process.standardError = pipe
        do {
            try process.run()
            process.waitUntilExit()
            let data = pipe.fileHandleForReading.readDataToEndOfFile()
            return (process.terminationStatus, String(data: data, encoding: .utf8) ?? "")
        } catch {
            return nil
        }
    }

    static func ensureRuntime(
        dataRoot: URL,
        environment: [String: String] = ProcessInfo.processInfo.environment,
        bundle: Bundle = .main
    ) throws {
        AppLogger.shared.log(
            .info,
            category: "runtime",
            event: "runtime_check_start",
            message: "Checking bundled Python runtime",
            dataRoot: dataRoot
        )
        if runtimeStatus(dataRoot: dataRoot, environment: environment) {
            AppLogger.shared.log(
                .info,
                category: "runtime",
                event: "runtime_check_ready",
                message: "Python runtime is ready",
                dataRoot: dataRoot
            )
            return
        }
        if AppPaths.isAppStoreDistribution(bundle: bundle) {
            AppLogger.shared.log(
                .error,
                category: "runtime",
                event: "runtime_install_blocked_app_store",
                message: "App Store builds do not install Python runtime code after launch",
                dataRoot: dataRoot
            )
            throw AppError.bundledRuntimeNotFound
        }
        guard let wheel = AppPaths.runtimeWheelURL(bundle: bundle) else {
            AppLogger.shared.log(
                .error,
                category: "runtime",
                event: "runtime_install_failed",
                message: "Bundled runtime wheel is missing",
                dataRoot: dataRoot
            )
            throw AppError.bundledRuntimeNotFound
        }
        AppLogger.shared.log(
            .info,
            category: "runtime",
            event: "runtime_install_start",
            message: "Installing bundled Python runtime",
            fields: ["wheel": wheel.lastPathComponent],
            dataRoot: dataRoot
        )
        let python = AppPaths.envPython(dataRoot: dataRoot)
        var createdEnvironment = false
        if !FileManager.default.isExecutableFile(atPath: python.path) {
            try runSystemPython(["-m", "venv", AppPaths.envRoot(dataRoot: dataRoot).path])
            createdEnvironment = true
        }
        if createdEnvironment {
            try runPython(python, ["-m", "pip", "install", "-U", "pip"], dataRoot: dataRoot, environment: environment)
        }
        try runPython(python, ["-m", "pip", "install", wheel.path], dataRoot: dataRoot, environment: environment)
        try runPython(
            python,
            ["-m", "pip", "install", "--force-reinstall", "--no-deps", wheel.path],
            dataRoot: dataRoot,
            environment: environment
        )
        try? FileManager.default.removeItem(
            at: AppPaths.envRoot(dataRoot: dataRoot).appendingPathComponent("bin/atot")
        )
        AppLogger.shared.log(
            .info,
            category: "runtime",
            event: "runtime_install_finish",
            message: "Python runtime install completed",
            fields: ["created_environment": "\(createdEnvironment)"],
            dataRoot: dataRoot
        )
    }

    private static func runSystemPython(_ arguments: [String]) throws {
        let candidates = ["/opt/homebrew/bin/python3", "/usr/local/bin/python3", "/usr/bin/python3"]
        guard let executable = candidates.first(where: { FileManager.default.isExecutableFile(atPath: $0) }) else {
            throw AppError.runtimeInstallFailed("python3 was not found")
        }
        try run(URL(fileURLWithPath: executable), arguments, dataRoot: nil, environment: [:])
    }

    private static func runPython(_ python: URL, _ arguments: [String], dataRoot: URL, environment: [String: String]) throws {
        try run(python, arguments, dataRoot: dataRoot, environment: environment)
    }

    private static func run(_ executable: URL, _ arguments: [String], dataRoot: URL?, environment: [String: String]) throws {
        let process = Process()
        process.executableURL = executable
        process.arguments = arguments
        let command = ([executable.path] + arguments).joined(separator: " ")
        let startedAt = Date()
        AppLogger.shared.log(
            .info,
            category: "runtime",
            event: "runtime_command_start",
            message: "Starting runtime command",
            fields: [
                "executable": executable.lastPathComponent,
                "argument_count": "\(arguments.count)",
                "command": AppLogger.redacted(command),
            ],
            dataRoot: dataRoot
        )
        if let dataRoot {
            process.currentDirectoryURL = AppPaths.workingDirectory(dataRoot: dataRoot)
            process.environment = AppPaths.environment(dataRoot: dataRoot, over: environment)
        }
        let pipe = Pipe()
        process.standardOutput = pipe
        process.standardError = pipe
        try process.run()
        process.waitUntilExit()
        let data = pipe.fileHandleForReading.readDataToEndOfFile()
        let output = String(data: data, encoding: .utf8) ?? ""
        guard process.terminationStatus == 0 else {
            AppLogger.shared.log(
                .error,
                category: "runtime",
                event: "runtime_command_failed",
                message: "Runtime command failed",
                fields: [
                    "executable": executable.lastPathComponent,
                    "exit_code": "\(process.terminationStatus)",
                    "duration_seconds": String(format: "%.3f", Date().timeIntervalSince(startedAt)),
                    "summary": AppLogger.redacted(output),
                ],
                dataRoot: dataRoot
            )
            throw AppError.runtimeInstallFailed(output)
        }
        AppLogger.shared.log(
            .info,
            category: "runtime",
            event: "runtime_command_finish",
            message: "Runtime command completed",
            fields: [
                "executable": executable.lastPathComponent,
                "exit_code": "\(process.terminationStatus)",
                "duration_seconds": String(format: "%.3f", Date().timeIntervalSince(startedAt)),
            ],
            dataRoot: dataRoot
        )
    }
}
