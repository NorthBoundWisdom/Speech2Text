import AppKit
import Combine
import Foundation
#if canImport(Network)
    import Network
#endif

@MainActor
final class AppStore: ObservableObject {
    @Published var settings: AppSettings
    @Published var diagnostics: AppDiagnosticsReport
    @Published var isSettingsPresented = false
    @Published var isInputPanelPresented = false
    @Published var isSRTExportPanelPresented = false
    @Published var isNewGroupPanelPresented = false
    @Published var settingsMessage = ""
    @Published var configInspection: ConfigInspectionPayload?
    @Published var isTestingCloud = false
    @Published var isLoadingConfigInspection = false
    @Published var isInstallingRuntime = false
    @Published private(set) var cloudStartupStatus: ProcessingTaskStatus?
    @Published var job: JobController
    @Published var srtExport: SRTExportController
    @Published private var verifiedCloudSettingsSignature: String?
    @Published private var failedCloudSettingsSignature: String?

    private let settingsStore: AppSettingsStore
    private let environment: [String: String]
    private let networkConnectivityTest: () async throws -> Void
    private let cloudConnectionTest: (AppSettings) async throws -> Void
    private var cloudStartupCheckID = UUID()
    private var cancellables: Set<AnyCancellable> = []

    init(
        settingsStore: AppSettingsStore = .live(),
        environment: [String: String] = ProcessInfo.processInfo.environment,
        networkConnectivityTest: @escaping () async throws -> Void = NetworkConnectivityTester.test,
        cloudConnectionTest: @escaping (AppSettings) async throws -> Void = CloudConnectionTester.test,
        runsStartupCloudPreflight: Bool = true
    ) {
        self.settingsStore = settingsStore
        self.environment = environment
        self.networkConnectivityTest = networkConnectivityTest
        self.cloudConnectionTest = cloudConnectionTest
        let loadedSettings = settingsStore.load(environment: environment)
        settings = loadedSettings
        settingsMessage = loadedSettings.configurationError
        let dataRoot = AppPaths.dataRoot(environment: environment)
        AppLogger.shared.configure(dataRoot: dataRoot)
        AppLogger.shared.log(
            .info,
            category: "app",
            event: "app_start",
            message: "SonaFolio app store initialized",
            fields: ["data_root": dataRoot.path],
            dataRoot: dataRoot
        )
        let importedCrashReports = CrashReportScanner.scan(dataRoot: dataRoot)
        AppLogger.shared.log(
            .info,
            category: "crash",
            event: "crash_report_scan_complete",
            message: "Crash report scan completed",
            fields: ["new_reports": "\(importedCrashReports.count)"],
            dataRoot: dataRoot
        )
        let inspectedDiagnostics = AppDiagnostics.inspect(settings: loadedSettings, environment: environment)
        diagnostics = inspectedDiagnostics
        AppLogger.shared.log(
            .info,
            category: "diagnostics",
            event: "diagnostics_inspected",
            message: "Diagnostics inspected",
            fields: [
                "item_count": "\(inspectedDiagnostics.items.count)",
                "blocking_count": "\(inspectedDiagnostics.blockingIssues.count)",
            ],
            dataRoot: dataRoot
        )
        job = JobController(settingsStore: settingsStore)
        srtExport = SRTExportController(settingsStore: settingsStore, environment: environment)
        job.objectWillChange.sink { [weak self] _ in
            self?.objectWillChange.send()
        }
        .store(in: &cancellables)
        job.$hidesReadLibraryItems
            .removeDuplicates()
            .sink { [weak self] hidesReadItems in
                guard let self, self.settings.hideReadItems != hidesReadItems else { return }
                self.settings.hideReadItems = hidesReadItems
            }
            .store(in: &cancellables)
        srtExport.objectWillChange.sink { [weak self] _ in
            self?.objectWillChange.send()
        }
        .store(in: &cancellables)
        if runsStartupCloudPreflight {
            runStartupCloudPreflight()
        }
    }

    static func makeLive() -> AppStore {
        AppStore()
    }

    var selectedLibraryItem: ProcessLibraryItem? {
        guard let id = job.selectedLibraryItemID else { return nil }
        return job.libraryItems.first { $0.id == id }
    }

    func showImportPanel() {
        AppLogger.shared.log(.info, category: "ui", event: "import_panel_open", message: "Import panel opened")
        job.resetImportDraft()
        isInputPanelPresented = true
    }

    func showSRTExportPanel() {
        AppLogger.shared.log(.info, category: "ui", event: "srt_export_panel_open", message: "SRT export panel opened")
        srtExport.reset()
        isSRTExportPanelPresented = true
    }

    func reload() {
        settings = settingsStore.load(environment: environment)
        diagnostics = AppDiagnostics.inspect(settings: settings, environment: environment)
        job.refreshLibraryInBackground()
        AppLogger.shared.log(
            .info,
            category: "diagnostics",
            event: "diagnostics_reloaded",
            message: "Diagnostics reloaded",
            fields: [
                "item_count": "\(diagnostics.items.count)",
                "blocking_count": "\(diagnostics.blockingIssues.count)",
            ]
        )
    }

    func refreshConfigInspection() {
        isLoadingConfigInspection = true
        let dataRoot = AppPaths.dataRoot(environment: environment)
        let runner = ProcessRunner()
        Task {
            do {
                let result = try await runner.run(
                    executable: AppPaths.cliExecutable(),
                    arguments: AtotServiceClient.configInspect(),
                    currentDirectory: AppPaths.workingDirectory(dataRoot: dataRoot),
                    environment: AppPaths.environment(dataRoot: dataRoot, over: environment),
                    onOutput: { _ in }
                )
                let payload = try JSONDecoder().decode(ConfigInspectionPayload.self, from: Data(result.output.utf8))
                await MainActor.run {
                    self.configInspection = payload
                    self.isLoadingConfigInspection = false
                }
            } catch {
                await MainActor.run {
                    self.configInspection = nil
                    self.isLoadingConfigInspection = false
                    self.settingsMessage = "Config sources unavailable: \(error.localizedDescription)"
                }
            }
        }
    }

    @discardableResult
    func saveSettings(_ newSettings: AppSettings) -> Bool {
        do {
            try settingsStore.save(newSettings, environment: environment)
            settings = newSettings
            settingsMessage = "Settings saved"
            AppLogger.shared.log(
                .info,
                category: "settings",
                event: "settings_saved",
                message: "Settings saved",
                fields: [
                    "local_asr_model": newSettings.localASRModel,
                    "api_base": newSettings.apiBase,
                    "cloud_model": newSettings.cloudModel,
                ]
            )
            reload()
            runStartupCloudPreflight()
            return true
        } catch {
            settingsMessage = error.localizedDescription
            AppLogger.shared.log(.error, category: "settings", event: "settings_save_failed", message: error.localizedDescription)
            return false
        }
    }

    func testCloudConnection(_ draft: AppSettings) {
        let checkedDraft = draft
        let signatureDraft = checkedDraft
        isTestingCloud = true
        verifiedCloudSettingsSignature = nil
        failedCloudSettingsSignature = nil
        settingsMessage = "Testing cloud connection..."
        setCloudStartupStatus(
            title: "Cloud API Key Check",
            detail: "Checking API key...",
            fraction: 0.70,
            state: .running
        )
        AppLogger.shared.log(
            .info,
            category: "settings",
            event: "cloud_connection_test_start",
            message: "Testing cloud summary connection",
            fields: ["api_base": checkedDraft.apiBase, "cloud_model": checkedDraft.cloudModel]
        )
        Task {
            do {
                try await cloudConnectionTest(checkedDraft)
                await MainActor.run {
                    self.verifiedCloudSettingsSignature = Self.cloudSettingsSignature(signatureDraft)
                    self.failedCloudSettingsSignature = nil
                    self.cloudStartupStatus = nil
                    self.settingsMessage = "Cloud connection succeeded. Click Save to persist settings."
                    self.isTestingCloud = false
                    AppLogger.shared.log(.info, category: "settings", event: "cloud_connection_test_success", message: "Cloud connection test succeeded")
                }
            } catch {
                await MainActor.run {
                    self.verifiedCloudSettingsSignature = nil
                    self.failedCloudSettingsSignature = Self.cloudSettingsSignature(signatureDraft)
                    self.setCloudStartupStatus(
                        title: "Cloud API Key Check Failed",
                        detail: self.cloudPreflightFailureDetail(error),
                        fraction: 1.0,
                        state: .failure
                    )
                    self.settingsMessage = "Cloud connection failed: \(error.localizedDescription)"
                    self.isTestingCloud = false
                    AppLogger.shared.log(.error, category: "settings", event: "cloud_connection_test_failed", message: error.localizedDescription)
                }
            }
        }
    }

    func installRuntime() {
        isInstallingRuntime = true
        settingsMessage = "Installing Python environment and dependencies..."
        let dataRoot = AppPaths.dataRoot(environment: environment)
        AppLogger.shared.log(.info, category: "runtime", event: "runtime_install_requested", message: "Runtime install requested", dataRoot: dataRoot)
        Task {
            do {
                try RuntimeManager.ensureDirectories(dataRoot: dataRoot)
                try RuntimeManager.ensureRuntime(dataRoot: dataRoot, environment: environment)
                await MainActor.run {
                    self.settingsMessage = "Python environment is ready"
                    self.isInstallingRuntime = false
                    AppLogger.shared.log(.info, category: "runtime", event: "runtime_install_ready", message: "Runtime install finished", dataRoot: dataRoot)
                    self.reload()
                }
            } catch {
                await MainActor.run {
                    self.settingsMessage = "Runtime install failed: \(error.localizedDescription)"
                    self.isInstallingRuntime = false
                    AppLogger.shared.log(.error, category: "runtime", event: "runtime_install_failed", message: error.localizedDescription, dataRoot: dataRoot)
                    self.reload()
                }
            }
        }
    }

    func showSettings() {
        settings = settingsStore.load(environment: environment)
        AppLogger.shared.log(.info, category: "settings", event: "settings_opened", message: "Settings opened")
        isSettingsPresented = true
    }

    func revealLogs() {
        let dataRoot = AppPaths.dataRoot(environment: environment)
        let logsRoot = AppPaths.logsRoot(dataRoot: dataRoot)
        try? FileManager.default.createDirectory(at: logsRoot, withIntermediateDirectories: true)
        AppLogger.shared.log(
            .info,
            category: "logs",
            event: "logs_revealed",
            message: "Logs folder revealed",
            fields: ["path": logsRoot.path],
            dataRoot: dataRoot
        )
        NSWorkspace.shared.open(logsRoot)
    }

    func openCloudConfig() {
        do {
            let url = try settingsStore.ensureCloudConfigFile(environment: environment)
            AppLogger.shared.log(
                .info,
                category: "settings",
                event: "cloud_config_opened",
                message: "Cloud config file opened",
                fields: ["path": url.path],
                dataRoot: AppPaths.dataRoot(environment: environment)
            )
            NSWorkspace.shared.open(url)
        } catch {
            settingsMessage = "Could not open config.toml: \(error.localizedDescription)"
            AppLogger.shared.log(
                .error,
                category: "settings",
                event: "cloud_config_open_failed",
                message: error.localizedDescription,
                dataRoot: AppPaths.dataRoot(environment: environment)
            )
        }
    }

    func deleteHistoricalLogs() {
        let dataRoot = AppPaths.dataRoot(environment: environment)
        let result = AppLogger.shared.deleteHistoricalLogs(dataRoot: dataRoot)
        AppLogger.shared.log(
            .info,
            category: "logs",
            event: "logs_deleted",
            message: "Historical logs deleted",
            fields: [
                "deleted_files": "\(result.deletedFiles)",
                "deleted_directories": "\(result.deletedDirectories)",
            ],
            dataRoot: dataRoot
        )
        settingsMessage = "Deleted \(result.deletedFiles) historical log files"
        diagnostics = AppDiagnostics.inspect(settings: settings, environment: environment)
    }
}

extension AppStore {
    func runStartupCloudPreflight() {
        let checkedSettings = settings
        let signature = Self.cloudSettingsSignature(checkedSettings)
        let checkID = UUID()
        cloudStartupCheckID = checkID
        verifiedCloudSettingsSignature = nil
        failedCloudSettingsSignature = nil
        guard checkedSettings.workflowDefaultCloudSummary && !checkedSettings.workflowLocalOnly else {
            cloudStartupStatus = nil
            return
        }
        guard checkedSettings.isCloudConfigured else {
            failedCloudSettingsSignature = signature
            setCloudStartupStatus(
                title: "Cloud API Key Missing",
                detail: "Configure an API key before cloud summary.",
                fraction: 1.0,
                state: .warning
            )
            AppLogger.shared.log(
                .warning,
                category: "settings",
                event: "cloud_startup_key_missing",
                message: "Cloud startup preflight skipped network check because the API key is missing"
            )
            return
        }
        setCloudStartupStatus(
            title: "Cloud Network Check",
            detail: "Checking network connectivity...",
            fraction: 0.20,
            state: .running
        )
        AppLogger.shared.log(
            .info,
            category: "settings",
            event: "cloud_startup_preflight_started",
            message: "Cloud startup preflight started",
            fields: ["api_base": checkedSettings.apiBase, "cloud_model": checkedSettings.cloudModel]
        )

        Task {
            do {
                try await networkConnectivityTest()
            } catch {
                await MainActor.run {
                    guard self.isCurrentCloudStartupCheck(checkID, signature: signature) else { return }
                    self.verifiedCloudSettingsSignature = nil
                    self.failedCloudSettingsSignature = nil
                    self.setCloudStartupStatus(
                        title: "Cloud Network Check Failed",
                        detail: self.cloudPreflightFailureDetail(error),
                        fraction: 1.0,
                        state: .failure
                    )
                    AppLogger.shared.log(
                        .error,
                        category: "settings",
                        event: "cloud_startup_network_failed",
                        message: error.localizedDescription
                    )
                }
                return
            }

            await MainActor.run {
                guard self.isCurrentCloudStartupCheck(checkID, signature: signature) else { return }
                self.setCloudStartupStatus(
                    title: "Cloud API Key Check",
                    detail: "Checking API key...",
                    fraction: 0.70,
                    state: .running
                )
            }

            do {
                try await cloudConnectionTest(checkedSettings)
                await MainActor.run {
                    guard self.isCurrentCloudStartupCheck(checkID, signature: signature) else { return }
                    self.verifiedCloudSettingsSignature = signature
                    self.failedCloudSettingsSignature = nil
                    self.cloudStartupStatus = nil
                    AppLogger.shared.log(.info, category: "settings", event: "cloud_startup_preflight_success", message: "Cloud startup preflight succeeded")
                }
            } catch {
                await MainActor.run {
                    guard self.isCurrentCloudStartupCheck(checkID, signature: signature) else { return }
                    self.verifiedCloudSettingsSignature = nil
                    self.failedCloudSettingsSignature = signature
                    self.setCloudStartupStatus(
                        title: "Cloud API Key Check Failed",
                        detail: self.cloudPreflightFailureDetail(error),
                        fraction: 1.0,
                        state: .failure
                    )
                    AppLogger.shared.log(.error, category: "settings", event: "cloud_startup_key_failed", message: error.localizedDescription)
                }
            }
        }
    }

    func isCloudConnectionVerified(for settings: AppSettings) -> Bool {
        verifiedCloudSettingsSignature == Self.cloudSettingsSignature(settings)
    }

    func isCloudConnectionFailed(for settings: AppSettings) -> Bool {
        failedCloudSettingsSignature == Self.cloudSettingsSignature(settings)
    }

    private func setCloudStartupStatus(title: String, detail: String, fraction: Double, state: ProcessingTaskState) {
        cloudStartupStatus = ProcessingTaskStatus(
            kind: .cloud,
            id: "cloud-startup-preflight",
            title: title,
            itemTitle: "",
            detail: detail,
            fraction: fraction,
            state: state
        )
    }

    private func isCurrentCloudStartupCheck(_ checkID: UUID, signature: String) -> Bool {
        cloudStartupCheckID == checkID && Self.cloudSettingsSignature(settings) == signature
    }

    private func cloudPreflightFailureDetail(_ error: Error) -> String {
        let message = error.localizedDescription.trimmingCharacters(in: .whitespacesAndNewlines)
        return message.isEmpty ? "Check network and cloud settings." : message
    }

    private static func cloudSettingsSignature(_ settings: AppSettings) -> String {
        [
            settings.apiBase,
            settings.cloudModel,
            settings.apiKey,
        ]
        .map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }
        .joined(separator: "\u{1F}")
    }
}

enum NetworkConnectivityTester {
    static func test() async throws {
        #if canImport(Network)
            try await withCheckedThrowingContinuation { (continuation: CheckedContinuation<Void, Error>) in
                let monitor = NWPathMonitor()
                let queue = DispatchQueue(label: "com.audio2text.cloud-network-check")
                let state = NetworkConnectivityContinuation(monitor: monitor, continuation: continuation)

                monitor.pathUpdateHandler = { path in
                    switch path.status {
                    case .satisfied:
                        state.finish(.success(()))
                    case .unsatisfied, .requiresConnection:
                        state.finish(.failure(NetworkConnectivityError.unavailable))
                    @unknown default:
                        state.finish(.failure(NetworkConnectivityError.unavailable))
                    }
                }
                monitor.start(queue: queue)
                queue.asyncAfter(deadline: .now() + 5) {
                    state.finish(.failure(NetworkConnectivityError.timedOut))
                }
            }
        #else
            return
        #endif
    }
}

#if canImport(Network)
    private final class NetworkConnectivityContinuation: @unchecked Sendable {
        private let lock = NSLock()
        private var didFinish = false
        private let monitor: NWPathMonitor
        private let continuation: CheckedContinuation<Void, Error>

        init(monitor: NWPathMonitor, continuation: CheckedContinuation<Void, Error>) {
            self.monitor = monitor
            self.continuation = continuation
        }

        func finish(_ result: Result<Void, Error>) {
            lock.lock()
            guard !didFinish else {
                lock.unlock()
                return
            }
            didFinish = true
            lock.unlock()
            monitor.pathUpdateHandler = nil
            monitor.cancel()
            continuation.resume(with: result)
        }
    }
#endif

enum NetworkConnectivityError: LocalizedError, Equatable {
    case unavailable
    case timedOut

    var errorDescription: String? {
        switch self {
        case .unavailable:
            return "Network connection is unavailable."
        case .timedOut:
            return "Network check timed out."
        }
    }
}

enum CloudConnectionTester {
    static func test(settings: AppSettings) async throws {
        if !settings.configurationError.isEmpty && settings.apiKey.isEmpty {
            throw AppError.invalidImportOutput(settings.configurationError)
        }
        guard settings.isCloudConfigured else {
            throw AppError.missingCloudAPIKey
        }
        let endpoint = settings.apiBase.trimmingCharacters(in: .whitespacesAndNewlines)
            .trimmingCharacters(in: CharacterSet(charactersIn: "/"))
            + "/responses"
        guard let url = URL(string: endpoint) else {
            throw URLError(.badURL)
        }
        let model = settings.cloudModel.trimmingCharacters(in: .whitespacesAndNewlines)
        let payload = buildPayload(model: model)
        let headers = buildHeaders(apiKey: settings.apiKey)
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.timeoutInterval = Double(CloudSettings.defaultTimeout) ?? 60
        headers.forEach { request.addValue($0.value, forHTTPHeaderField: $0.key) }
        request.httpBody = try JSONSerialization.data(withJSONObject: payload)
        let (data, response) = try await URLSession.shared.data(for: request)
        guard let http = response as? HTTPURLResponse else {
            throw URLError(.badServerResponse)
        }
        let body = String(data: data, encoding: .utf8) ?? ""
        guard (200 ..< 300).contains(http.statusCode) else {
            throw AppError.cloudConnectionFailed(http.statusCode, body)
        }
        try validateResponsesAPIResponse(data, statusCode: http.statusCode)
    }

    private static func buildPayload(model: String) -> [String: Any] {
        let maxTokens = Int(CloudSettings.defaultMaxTokens.trimmingCharacters(in: .whitespacesAndNewlines))
            ?? Int(CloudSettings.defaultMaxTokens)!
        return [
            "model": model,
            "input": [
                ["role": "system", "content": "Return only the final answer."],
                ["role": "user", "content": "Reply in one sentence: connection test"],
            ],
            "max_output_tokens": maxTokens,
            "temperature": Double(CloudSettings.defaultTemperature) ?? 1.0,
            "store": false,
        ]
    }

    private static func buildHeaders(apiKey: String) -> [String: String] {
        ["Authorization": "Bearer \(apiKey)", "Content-Type": "application/json"]
    }

    private static func validateResponsesAPIResponse(_ data: Data, statusCode: Int) throws {
        guard let object = try JSONSerialization.jsonObject(with: data) as? [String: Any] else {
            throw AppError.cloudConnectionFailed(statusCode, "Cloud response did not include a JSON object.")
        }
        if let outputText = object["output_text"] as? String, !outputText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            return
        }
        if
            let output = object["output"] as? [[String: Any]],
            let text = extractResponsesText(output: output),
            !text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
        {
            return
        }
        if
            let incompleteDetails = object["incomplete_details"] as? [String: Any],
            String(describing: incompleteDetails["reason"] ?? "") == "max_output_tokens"
        {
            throw AppError.cloudConnectionFailed(
                statusCode,
                "Cloud response reached the token limit before producing final content. Increase Max Tokens."
            )
        }
        throw AppError.cloudConnectionFailed(statusCode, "Cloud responses API did not include textual output.")
    }

    private static func extractResponsesText(output: [[String: Any]]) -> String? {
        for item in output {
            guard let contentItems = item["content"] as? [[String: Any]] else {
                continue
            }
            for content in contentItems {
                if let text = content["text"] as? String, !text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                    return text
                }
                if
                    let textObject = content["text"] as? [String: Any],
                    let value = textObject["value"] as? String,
                    !value.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
                {
                    return value
                }
            }
        }
        return nil
    }
}
