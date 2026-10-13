import AppKit
import Foundation

enum SRTExportState: Equatable {
    case idle
    case running
    case success(URL)
    case failure(String)

    var isRunning: Bool {
        if case .running = self {
            return true
        }
        return false
    }
}

struct SRTExportResultPayload: Decodable {
    let success: Bool
    let results: [SRTExportResultItem]
}

struct SRTExportResultItem: Decodable {
    let success: Bool
    let srtPath: String?
    let error: String?

    enum CodingKeys: String, CodingKey {
        case success
        case srtPath = "srt_path"
        case error
    }
}

typealias SRTExportRunner = (
    _ executable: URL,
    _ arguments: [String],
    _ currentDirectory: URL,
    _ environment: [String: String],
    _ onOutput: @escaping @MainActor (String) -> Void
) async throws -> ProcessResult

typealias SRTRuntimeProvider = () throws -> RuntimeContext

@MainActor
final class SRTExportController: ObservableObject {
    @Published var selectedFile: URL?
    @Published var overwrite = false
    @Published var state: SRTExportState = .idle
    @Published var logText = ""

    private let settingsStore: AppSettingsStore
    private let environment: [String: String]
    private let runner: SRTExportRunner
    private let runtimeProvider: SRTRuntimeProvider

    init(
        settingsStore: AppSettingsStore = .live(),
        environment: [String: String] = ProcessInfo.processInfo.environment,
        runtimeProvider: SRTRuntimeProvider? = nil,
        runner: SRTExportRunner? = nil
    ) {
        self.settingsStore = settingsStore
        self.environment = environment
        self.runtimeProvider = runtimeProvider ?? { try RuntimeManager.context(environment: environment) }
        if let runner {
            self.runner = runner
        } else {
            let processRunner = ProcessRunner()
            self.runner = { executable, arguments, currentDirectory, environment, onOutput in
                try await processRunner.run(
                    executable: executable,
                    arguments: arguments,
                    currentDirectory: currentDirectory,
                    environment: environment,
                    onOutput: onOutput
                )
            }
        }
    }

    var canExport: Bool {
        selectedFile != nil && !state.isRunning
    }

    var successURL: URL? {
        if case let .success(url) = state {
            return url
        }
        return nil
    }

    func reset() {
        selectedFile = nil
        overwrite = false
        state = .idle
        logText = ""
    }

    func chooseFile() {
        let panel = NSOpenPanel()
        panel.canChooseFiles = true
        panel.canChooseDirectories = false
        panel.allowsMultipleSelection = false
        panel.allowedContentTypes = [.audio, .movie, .video]
        if panel.runModal() == .OK {
            selectedFile = panel.url
            state = .idle
            logText = ""
        }
    }

    func revealOutput() {
        guard let successURL else { return }
        NSWorkspace.shared.activateFileViewerSelecting([successURL])
    }

    func export() {
        guard let selectedFile else { return }
        state = .running
        logText = ""
        Task {
            await runExport(input: selectedFile)
        }
    }

    private func runExport(input: URL) async {
        do {
            let runtime = try runtimeProvider()
            let settings = settingsStore.load(environment: runtime.environment)
            let arguments = buildArguments(input: input, settings: settings)
            appendLog("$ \(runtime.cli.path) \(arguments.joined(separator: " "))\n")
            let result = try await runner(
                runtime.cli,
                arguments,
                runtime.workingDirectory,
                commandEnvironment(runtime: runtime, settings: settings),
                appendLog
            )
            let outputURL = try parseOutputURL(result.output)
            state = .success(outputURL)
            appendLog("\nSRT: \(outputURL.path)\n")
        } catch {
            let message = error.localizedDescription
            state = .failure(message)
            appendLog("\nERROR: \(message)\n")
        }
    }

    func buildArguments(input: URL, settings: AppSettings) -> [String] {
        return AtotServiceClient.srt(
            input: input,
            sourceLanguages: settings.transcriptionLanguages,
            overwrite: overwrite,
            json: true
        )
    }

    private func commandEnvironment(runtime: RuntimeContext, settings _: AppSettings) -> [String: String] {
        runtime.environment
    }

    private func parseOutputURL(_ output: String) throws -> URL {
        let payload = try parsePayload(output)
        guard payload.success, let first = payload.results.first, first.success, let path = first.srtPath else {
            let reason = payload.results.first?.error ?? "SRT export failed."
            throw AppError.processFailed(command: "srt", code: 1, output: reason)
        }
        return URL(fileURLWithPath: path)
    }

    private func parsePayload(_ output: String) throws -> SRTExportResultPayload {
        let jsonText = output.trimmingCharacters(in: .whitespacesAndNewlines)
        let decoder = JSONDecoder()
        if let payload = try? decoder.decode(SRTExportResultPayload.self, from: Data(jsonText.utf8)) {
            return payload
        }
        for index in jsonText.indices.reversed() where jsonText[index] == "{" {
            let candidate = String(jsonText[index...])
            if let payload = try? decoder.decode(SRTExportResultPayload.self, from: Data(candidate.utf8)) {
                return payload
            }
        }
        return try decoder.decode(SRTExportResultPayload.self, from: Data(jsonText.utf8))
    }

    private func appendLog(_ text: String) {
        logText += text
    }
}
