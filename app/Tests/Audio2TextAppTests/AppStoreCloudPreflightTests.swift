@testable import Audio2TextApp
import Audio2TextCore
import XCTest

final class AppStoreCloudPreflightTests: XCTestCase {
    @MainActor
    func testDefaultAgentWorkflowDoesNotRequireKeyOrRunCloudChecks() async throws {
        let dataRoot = URL(fileURLWithPath: NSTemporaryDirectory()).appendingPathComponent(UUID().uuidString)
        let settingsStore = AppSettingsStore(dataRoot: dataRoot, credentials: MemoryCloudCredentials())
        let networkChecks = AsyncCallCounter()
        let keyChecks = AsyncCallCounter()
        let appStore = AppStore(
            settingsStore: settingsStore,
            environment: ["PATH": ""],
            networkConnectivityTest: { await networkChecks.increment() },
            cloudConnectionTest: { _ in await keyChecks.increment() }
        )
        await Task.yield()
        XCTAssertNil(appStore.cloudStartupStatus)
        XCTAssertFalse(appStore.isCloudConnectionFailed(for: appStore.settings))
        XCTAssertNil(ProcessSidebarView(store: appStore).cloudAPIKeyWarningDetail)
        let networkCount = await networkChecks.value()
        let keyCount = await keyChecks.value()
        XCTAssertEqual(networkCount, 0)
        XCTAssertEqual(keyCount, 0)
    }

    @MainActor
    func testAppStoreLoadsSettingsAndDiagnostics() throws {
        let dataRoot = URL(fileURLWithPath: NSTemporaryDirectory()).appendingPathComponent(UUID().uuidString)
        let store = AppSettingsStore(dataRoot: dataRoot, credentials: MemoryCloudCredentials())
        try FileManager.default.createDirectory(at: dataRoot, withIntermediateDirectories: true)
        try """
        [workflow]
        default_cloud_summary = true
        [cloud]
        api_base = "https://api.example/v1"
        api_key = "key"
        model = "model-x"
        """.write(to: dataRoot.appendingPathComponent("config.toml"), atomically: true, encoding: .utf8)

        let appStore = AppStore(
            settingsStore: store,
            environment: ["PATH": ""],
            runsStartupCloudPreflight: false
        )

        XCTAssertEqual(appStore.settings.apiKey, "key")
        XCTAssertFalse(appStore.diagnostics.items.isEmpty)
    }

    @MainActor
    func testReadFilterPreferenceSyncsToAppStoreSettings() {
        let dataRoot = URL(fileURLWithPath: NSTemporaryDirectory()).appendingPathComponent(UUID().uuidString)
        let store = AppSettingsStore(dataRoot: dataRoot, credentials: MemoryCloudCredentials())
        let appStore = AppStore(
            settingsStore: store,
            environment: ["PATH": ""],
            runsStartupCloudPreflight: false
        )

        XCTAssertFalse(appStore.settings.hideReadItems)

        appStore.job.setHidesReadLibraryItems(true)

        XCTAssertTrue(appStore.settings.hideReadItems)
        XCTAssertTrue(store.load(environment: [:]).hideReadItems)
    }

    @MainActor
    func testCloudConnectionCheckRecordsSuccessWithoutSaving() async throws {
        let dataRoot = URL(fileURLWithPath: NSTemporaryDirectory()).appendingPathComponent(UUID().uuidString)
        let store = AppSettingsStore(dataRoot: dataRoot, credentials: MemoryCloudCredentials())
        let appStore = AppStore(
            settingsStore: store,
            environment: ["PATH": ""],
            cloudConnectionTest: { settings in
                guard settings.apiKey == "valid-key" else {
                    throw URLError(.userAuthenticationRequired)
                }
            },
            runsStartupCloudPreflight: false
        )
        var draft = appStore.settings
        draft.apiBase = "https://api.example/v1"
        draft.cloudModel = "model-x"
        draft.apiKey = "valid-key"

        appStore.testCloudConnection(draft)

        try await waitForCondition("cloud check succeeds") {
            appStore.isCloudConnectionVerified(for: draft)
        }
        XCTAssertEqual(appStore.settingsMessage, "Cloud connection succeeded. Click Save to persist settings.")
        XCTAssertTrue(appStore.isCloudConnectionVerified(for: draft))
        XCTAssertFalse(appStore.isCloudConnectionFailed(for: draft))
    }

    @MainActor
    func testCloudConnectionCheckRecordsFailureWithoutSaving() async throws {
        let dataRoot = URL(fileURLWithPath: NSTemporaryDirectory()).appendingPathComponent(UUID().uuidString)
        let store = AppSettingsStore(dataRoot: dataRoot, credentials: MemoryCloudCredentials())
        try FileManager.default.createDirectory(at: dataRoot, withIntermediateDirectories: true)
        try """
        [workflow]
        default_cloud_summary = true
        [cloud]
        api_base = "https://api.example/v1"
        api_key = "old-key"
        model = "model-x"
        """.write(to: dataRoot.appendingPathComponent("config.toml"), atomically: true, encoding: .utf8)
        let appStore = AppStore(
            settingsStore: store,
            environment: ["PATH": ""],
            cloudConnectionTest: { _ in
                throw URLError(.userAuthenticationRequired)
            },
            runsStartupCloudPreflight: false
        )
        var draft = appStore.settings
        draft.apiKey = "bad-key"

        appStore.testCloudConnection(draft)

        try await waitForCondition("failed validation completes") {
            appStore.isCloudConnectionFailed(for: draft)
        }
        XCTAssertEqual(appStore.settings.apiKey, "old-key")
        XCTAssertTrue(appStore.settingsMessage.contains("Cloud connection failed"))
        XCTAssertFalse(appStore.isCloudConnectionVerified(for: draft))
        XCTAssertTrue(appStore.isCloudConnectionFailed(for: draft))
    }

    @MainActor
    func testCloudConnectionCheckUsesConfiguredCloudSettings() async throws {
        let dataRoot = URL(fileURLWithPath: NSTemporaryDirectory()).appendingPathComponent(UUID().uuidString)
        let store = AppSettingsStore(dataRoot: dataRoot, credentials: MemoryCloudCredentials())
        try FileManager.default.createDirectory(at: dataRoot, withIntermediateDirectories: true)
        try """
        [workflow]
        default_cloud_summary = true
        [cloud]
        api_base = "https://api.example/v1"
        api_key = "api-key-value"
        model = "model-x"
        """.write(to: dataRoot.appendingPathComponent("config.toml"), atomically: true, encoding: .utf8)

        var capturedSettings: AppSettings?
        let appStore = AppStore(
            settingsStore: store,
            environment: ["PATH": ""],
            cloudConnectionTest: { settings in
                capturedSettings = settings
            },
            runsStartupCloudPreflight: false
        )

        appStore.testCloudConnection(appStore.settings)

        try await waitForCondition("cloud check finishes") {
            appStore.isCloudConnectionVerified(for: appStore.settings)
        }
        XCTAssertEqual(capturedSettings?.apiKey, "api-key-value")
        XCTAssertEqual(capturedSettings?.apiBase, "https://api.example/v1")
        XCTAssertEqual(capturedSettings?.cloudModel, "model-x")
    }

    @MainActor
    func testStartupCloudPreflightReportsNetworkFailureBeforeKeyCheck() async throws {
        let dataRoot = URL(fileURLWithPath: NSTemporaryDirectory()).appendingPathComponent(UUID().uuidString)
        let store = AppSettingsStore(dataRoot: dataRoot, credentials: MemoryCloudCredentials())
        try FileManager.default.createDirectory(at: dataRoot, withIntermediateDirectories: true)
        try """
        [workflow]
        default_cloud_summary = true
        [cloud]
        api_base = "https://api.example/v1"
        api_key = "api-key-value"
        model = "model-x"
        """.write(to: dataRoot.appendingPathComponent("config.toml"), atomically: true, encoding: .utf8)
        let keyChecks = AsyncCallCounter()

        let appStore = AppStore(
            settingsStore: store,
            environment: ["PATH": ""],
            networkConnectivityTest: {
                throw NetworkConnectivityError.unavailable
            },
            cloudConnectionTest: { _ in
                await keyChecks.increment()
            }
        )

        try await waitForCondition("startup network failure is reported") {
            appStore.cloudStartupStatus?.title == "Cloud Network Check Failed"
        }
        XCTAssertEqual(appStore.cloudStartupStatus?.state, .failure)
        XCTAssertTrue(appStore.cloudStartupStatus?.detail.contains("Network connection is unavailable") == true)
        let keyCheckCount = await keyChecks.value()
        XCTAssertEqual(keyCheckCount, 0)
    }

    @MainActor
    func testStartupCloudPreflightReportsMissingAPIKeyWithoutNetworkCheck() async throws {
        let dataRoot = URL(fileURLWithPath: NSTemporaryDirectory()).appendingPathComponent(UUID().uuidString)
        let store = AppSettingsStore(dataRoot: dataRoot, credentials: MemoryCloudCredentials())
        try FileManager.default.createDirectory(at: dataRoot, withIntermediateDirectories: true)
        try "[workflow]\ndefault_cloud_summary = true\n".write(
            to: dataRoot.appendingPathComponent("config.toml"), atomically: true, encoding: .utf8
        )
        let networkChecks = AsyncCallCounter()
        let keyChecks = AsyncCallCounter()

        let appStore = AppStore(
            settingsStore: store,
            environment: ["PATH": ""],
            networkConnectivityTest: {
                await networkChecks.increment()
            },
            cloudConnectionTest: { _ in
                await keyChecks.increment()
            }
        )

        try await waitForCondition("startup missing key is reported") {
            appStore.cloudStartupStatus?.title == "Cloud API Key Missing"
        }
        XCTAssertEqual(appStore.cloudStartupStatus?.state, .warning)
        XCTAssertEqual(appStore.cloudStartupStatus?.detail, "Configure an API key before cloud summary.")
        XCTAssertTrue(appStore.isCloudConnectionFailed(for: appStore.settings))
        let networkCheckCount = await networkChecks.value()
        XCTAssertEqual(networkCheckCount, 0)
        let keyCheckCount = await keyChecks.value()
        XCTAssertEqual(keyCheckCount, 0)
    }

    @MainActor
    func testStartupCloudPreflightReportsAPIKeyFailureAfterNetworkPasses() async throws {
        let dataRoot = URL(fileURLWithPath: NSTemporaryDirectory()).appendingPathComponent(UUID().uuidString)
        let store = AppSettingsStore(dataRoot: dataRoot, credentials: MemoryCloudCredentials())
        try FileManager.default.createDirectory(at: dataRoot, withIntermediateDirectories: true)
        try """
        [workflow]
        default_cloud_summary = true
        [cloud]
        api_base = "https://api.example/v1"
        api_key = "api-key-value"
        model = "model-x"
        """.write(to: dataRoot.appendingPathComponent("config.toml"), atomically: true, encoding: .utf8)

        let appStore = AppStore(
            settingsStore: store,
            environment: ["PATH": ""],
            networkConnectivityTest: {},
            cloudConnectionTest: { _ in
                throw AppError.cloudConnectionFailed(401, "invalid key")
            }
        )

        try await waitForCondition("startup key failure is reported") {
            appStore.cloudStartupStatus?.title == "Cloud API Key Check Failed"
        }
        XCTAssertEqual(appStore.cloudStartupStatus?.state, .failure)
        XCTAssertTrue(appStore.cloudStartupStatus?.detail.contains("401") == true)
        XCTAssertTrue(appStore.isCloudConnectionFailed(for: appStore.settings))
    }

    @MainActor
    func testStartupCloudPreflightClearsStatusWhenCloudIsReady() async throws {
        let dataRoot = URL(fileURLWithPath: NSTemporaryDirectory()).appendingPathComponent(UUID().uuidString)
        let store = AppSettingsStore(dataRoot: dataRoot, credentials: MemoryCloudCredentials())
        try FileManager.default.createDirectory(at: dataRoot, withIntermediateDirectories: true)
        try """
        [workflow]
        default_cloud_summary = true
        [cloud]
        api_base = "https://api.example/v1"
        api_key = "api-key-value"
        model = "model-x"
        """.write(to: dataRoot.appendingPathComponent("config.toml"), atomically: true, encoding: .utf8)

        let appStore = AppStore(
            settingsStore: store,
            environment: ["PATH": ""],
            networkConnectivityTest: {},
            cloudConnectionTest: { _ in }
        )

        try await waitForCondition("startup cloud preflight succeeds") {
            appStore.isCloudConnectionVerified(for: appStore.settings) && appStore.cloudStartupStatus == nil
        }
    }
}

private actor AsyncCallCounter {
    private var count = 0

    func increment() {
        count += 1
    }

    func value() -> Int {
        count
    }
}
