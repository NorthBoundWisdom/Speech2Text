import Foundation

enum DiagnosticSeverity: String {
    case ok
    case warning
    case error
}

struct DiagnosticItem: Identifiable, Equatable {
    let id: String
    let title: String
    let detail: String
    let severity: DiagnosticSeverity
}

struct AppDiagnosticsReport: Equatable {
    var dataRoot: URL?
    var items: [DiagnosticItem]

    var blockingIssues: [DiagnosticItem] {
        items.filter { $0.severity == .error }
    }

    var isReadyForProcessing: Bool {
        blockingIssues.isEmpty
    }

    func item(_ id: String) -> DiagnosticItem? {
        items.first { $0.id == id }
    }
}

enum AppDiagnostics {
    static func inspect(
        settings: AppSettings,
        fileManager: FileManager = .default,
        environment: [String: String] = ProcessInfo.processInfo.environment
    ) -> AppDiagnosticsReport {
        var items: [DiagnosticItem] = []
        let dataRoot = AppPaths.dataRoot(environment: environment)
        let cli = AppPaths.cliExecutable()
        let cliReady = fileManager.isExecutableFile(atPath: cli.path)
        let runtimeReady = RuntimeManager.runtimeStatus(dataRoot: dataRoot, environment: environment)
        let cliAndRuntimeReady = cliReady && runtimeReady
        let appStoreDistribution = AppPaths.isAppStoreDistribution()
        items.append(
            DiagnosticItem(
                id: "cli",
                title: "Audio2TextCli",
                detail: cliAndRuntimeReady
                    ? "\(cli.path) is ready."
                    : !cliReady
                    ? "Audio2TextCli is missing from the app bundle: \(cli.path)."
                    : appStoreDistribution
                    ? "Runtime is missing. App Store builds must include a ready bundled runtime and will not install code after launch."
                    : "Runtime is missing or stale. The app will repair it from its bundled package.",
                severity: cliAndRuntimeReady ? .ok : appStoreDistribution ? .error : .warning
            )
        )

        let selectedModel = LocalASRModel.model(for: settings.localASRModel)
        let missingModelFiles = selectedModel.files.filter {
            !fileManager.fileExists(
                atPath: AppPaths.modelRoot(dataRoot: dataRoot).appendingPathComponent($0.pathUnderModelRoot).path
            )
        }
        items.append(
            DiagnosticItem(
                id: "model-\(selectedModel.alias)",
                title: "ASR Model",
                detail: missingModelFiles.isEmpty
                    ? "\(selectedModel.alias) local model files are present."
                    : "Missing model files under \(AppPaths.modelRoot(dataRoot: dataRoot).path): \(missingModelFiles.map(\.relativePath).joined(separator: ", ")).",
                severity: missingModelFiles.isEmpty ? .ok : .error
            )
        )

        let ffmpegAvailable = commandExists("ffmpeg", environment: environment)
        let ffprobeAvailable = commandExists("ffprobe", environment: environment)
        items.append(
            DiagnosticItem(
                id: "ffmpeg",
                title: "Audio Tools",
                detail: ffmpegAvailable && ffprobeAvailable
                    ? "ffmpeg and ffprobe are available."
                    : "ffmpeg/ffprobe are missing. Install ffmpeg or use macOS-supported WAV inputs only.",
                severity: ffmpegAvailable && ffprobeAvailable ? .ok : .warning
            )
        )

        items.append(
            DiagnosticItem(
                id: "cloud",
                title: "Cloud Summary",
                detail: cloudSummaryDetail(settings),
                severity: settings.configurationError.isEmpty ? .ok : .error
            )
        )

        let latestLog = AppLogger.shared.latestLogURL(dataRoot: dataRoot)
        let crashCount = CrashReportScanner.recentCrashReportCount(dataRoot: dataRoot)
        items.append(
            DiagnosticItem(
                id: "logs",
                title: "Logs",
                detail: "Latest app log: \(latestLog.path). Recent crash reports: \(crashCount).",
                severity: .ok
            )
        )

        return AppDiagnosticsReport(dataRoot: dataRoot, items: items)
    }

    private static func cloudSummaryDetail(_ settings: AppSettings) -> String {
        if !settings.configurationError.isEmpty { return settings.configurationError }
        let hasKey = !settings.apiKey.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
        if hasKey {
            return "\(settings.cloudModel) @ \(settings.apiBase)"
        }
        return "Cloud summary is optional and is currently not configured."
    }

    private static func commandExists(_ name: String, environment: [String: String]) -> Bool {
        let dataRoot = AppPaths.dataRoot(environment: environment)
        var candidates = [
            AppPaths.toolsRoot(dataRoot: dataRoot).appendingPathComponent("bin/\(name)").path,
            AppPaths.toolsRoot(dataRoot: dataRoot).appendingPathComponent("ffmpeg/bin/\(name)").path,
        ]
        if !AppPaths.isAppStoreDistribution() {
            candidates.append(contentsOf: [
                "/opt/homebrew/bin/\(name)",
                "/usr/local/bin/\(name)",
                "/usr/bin/\(name)",
            ])
        }
        if candidates.contains(where: { FileManager.default.isExecutableFile(atPath: $0) }) {
            return true
        }
        if AppPaths.isAppStoreDistribution() {
            return false
        }
        let path = environment["PATH"] ?? ""
        return path.split(separator: ":").contains { directory in
            FileManager.default.isExecutableFile(atPath: "\(directory)/\(name)")
        }
    }
}
