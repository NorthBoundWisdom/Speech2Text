@testable import Audio2TextApp
import Audio2TextCore
import XCTest

final class AppLoggingTests: XCTestCase {
    func testApplicationInstanceLockBlocksSecondOwnerUntilReleased() throws {
        let dataRoot = URL(fileURLWithPath: NSTemporaryDirectory())
            .appendingPathComponent(UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: dataRoot) }

        var firstLock: ApplicationInstanceLock? = try XCTUnwrap(
            ApplicationInstanceLock.acquire(dataRoot: dataRoot, processID: 101)
        )
        let lockFileURL = try XCTUnwrap(firstLock?.lockFileURL)

        XCTAssertNil(try ApplicationInstanceLock.acquire(dataRoot: dataRoot, processID: 202))
        XCTAssertEqual(try String(contentsOf: lockFileURL, encoding: .utf8), "101\n")

        firstLock = nil
        let secondLock = try XCTUnwrap(ApplicationInstanceLock.acquire(dataRoot: dataRoot, processID: 202))
        XCTAssertEqual(try String(contentsOf: lockFileURL, encoding: .utf8), "202\n")
        _ = secondLock
    }

    func testAppLoggerWritesCurrentAndDailyLogsAndRedactsSecrets() throws {
        let dataRoot = URL(fileURLWithPath: NSTemporaryDirectory())
            .appendingPathComponent(UUID().uuidString)
        let fixedDate = Date(timeIntervalSince1970: 1_779_840_000)
        let logger = AppLogger(dataRoot: dataRoot, now: { fixedDate })

        logger.log(
            .info,
            category: "settings",
            event: "saved",
            message: "Bearer sk-secret-token",
            fields: ["api_key": "sk-123", "model": "kimi"]
        )

        let current = try readText(AppPaths.logsRoot(dataRoot: dataRoot).appendingPathComponent("app-current.log"))
        let daily = try readText(AppPaths.logsRoot(dataRoot: dataRoot).appendingPathComponent("app-20260527.log"))
        XCTAssertEqual(current, daily)
        XCTAssertTrue(current.contains(#""event":"saved""#))
        XCTAssertTrue(current.contains(#""api_key":"****""#))
        XCTAssertTrue(current.contains("Bearer ****"))
        XCTAssertFalse(current.contains("sk-123"))
        XCTAssertFalse(current.contains("sk-secret-token"))
    }

    func testAppLoggerRetentionRemovesOldLogsAndCapsLogSize() throws {
        let dataRoot = URL(fileURLWithPath: NSTemporaryDirectory())
            .appendingPathComponent(UUID().uuidString)
        let logsRoot = AppPaths.logsRoot(dataRoot: dataRoot)
        try FileManager.default.createDirectory(at: logsRoot, withIntermediateDirectories: true)
        let now = Date(timeIntervalSince1970: 1_779_840_000)
        let old = logsRoot.appendingPathComponent("app-20240101.log")
        let recentA = logsRoot.appendingPathComponent("job-a.log")
        let recentB = logsRoot.appendingPathComponent("job-b.log")
        try Data(repeating: 1, count: 10).write(to: old)
        try Data(repeating: 2, count: 40).write(to: recentA)
        try Data(repeating: 3, count: 40).write(to: recentB)
        try FileManager.default.setAttributes(
            [.modificationDate: now.addingTimeInterval(-40 * 86400)],
            ofItemAtPath: old.path
        )
        try FileManager.default.setAttributes(
            [.modificationDate: now.addingTimeInterval(-60)],
            ofItemAtPath: recentA.path
        )
        try FileManager.default.setAttributes(
            [.modificationDate: now],
            ofItemAtPath: recentB.path
        )
        let logger = AppLogger(dataRoot: dataRoot, now: { now })

        logger.cleanup(dataRoot: dataRoot, keepDays: 30, maxBytes: 50)

        XCTAssertFalse(FileManager.default.fileExists(atPath: old.path))
        XCTAssertFalse(FileManager.default.fileExists(atPath: recentA.path))
        XCTAssertTrue(FileManager.default.fileExists(atPath: recentB.path))
    }

    func testAppLoggerConfigureResetsCurrentLogForCurrentRun() throws {
        let dataRoot = URL(fileURLWithPath: NSTemporaryDirectory())
            .appendingPathComponent(UUID().uuidString)
        let logsRoot = AppPaths.logsRoot(dataRoot: dataRoot)
        try FileManager.default.createDirectory(at: logsRoot, withIntermediateDirectories: true)
        let current = logsRoot.appendingPathComponent("app-current.log")
        try "old run".write(to: current, atomically: true, encoding: .utf8)
        let logger = AppLogger(dataRoot: dataRoot)

        logger.configure(dataRoot: dataRoot)

        XCTAssertEqual(try readText(current), "")
    }

    func testAppLoggerDeleteHistoricalLogsKeepsCurrentRunLog() throws {
        let dataRoot = URL(fileURLWithPath: NSTemporaryDirectory())
            .appendingPathComponent(UUID().uuidString)
        let logsRoot = AppPaths.logsRoot(dataRoot: dataRoot)
        let crashRoot = logsRoot.appendingPathComponent("crash-reports")
        try FileManager.default.createDirectory(at: crashRoot, withIntermediateDirectories: true)
        let current = logsRoot.appendingPathComponent("app-current.log")
        let daily = logsRoot.appendingPathComponent("app-20260527.log")
        let job = logsRoot.appendingPathComponent("job-20260527-120000.log")
        let crash = crashRoot.appendingPathComponent("Audio2TextApp.crash")
        try "current run".write(to: current, atomically: true, encoding: .utf8)
        try "daily".write(to: daily, atomically: true, encoding: .utf8)
        try "job".write(to: job, atomically: true, encoding: .utf8)
        try "crash".write(to: crash, atomically: true, encoding: .utf8)
        let logger = AppLogger(dataRoot: dataRoot)

        let result = logger.deleteHistoricalLogs(dataRoot: dataRoot)

        XCTAssertEqual(result.deletedFiles, 3)
        XCTAssertEqual(try readText(current), "current run")
        XCTAssertFalse(FileManager.default.fileExists(atPath: daily.path))
        XCTAssertFalse(FileManager.default.fileExists(atPath: job.path))
        XCTAssertFalse(FileManager.default.fileExists(atPath: crash.path))
        XCTAssertFalse(FileManager.default.fileExists(atPath: crashRoot.path))
    }

    func testCrashReportScannerCopiesNewCrashReportsOnce() throws {
        let root = URL(fileURLWithPath: NSTemporaryDirectory())
            .appendingPathComponent(UUID().uuidString)
        let dataRoot = root.appendingPathComponent("data")
        let diagnosticRoot = root.appendingPathComponent("DiagnosticReports")
        try FileManager.default.createDirectory(at: diagnosticRoot, withIntermediateDirectories: true)
        let crash = diagnosticRoot.appendingPathComponent("SonaFolio_2026-05-27.crash")
        let ips = diagnosticRoot.appendingPathComponent("SonaFolio-2026-05-28.ips")
        let hyphenatedIPS = diagnosticRoot.appendingPathComponent("Audio2TextApp-2026-05-29-234749.ips")
        let ignored = diagnosticRoot.appendingPathComponent("OtherApp_2026-05-28.crash")
        try "crash".write(to: crash, atomically: true, encoding: .utf8)
        try "ips".write(to: ips, atomically: true, encoding: .utf8)
        try "hyphenated ips".write(to: hyphenatedIPS, atomically: true, encoding: .utf8)
        try "ignored".write(to: ignored, atomically: true, encoding: .utf8)
        let logger = AppLogger(dataRoot: dataRoot, now: { Date(timeIntervalSince1970: 1_779_840_000) })

        let first = CrashReportScanner.scan(
            dataRoot: dataRoot,
            diagnosticReportsURL: diagnosticRoot,
            logger: logger,
            now: Date(timeIntervalSince1970: 1_779_840_000)
        )
        let second = CrashReportScanner.scan(
            dataRoot: dataRoot,
            diagnosticReportsURL: diagnosticRoot,
            logger: logger,
            now: Date(timeIntervalSince1970: 1_779_840_100)
        )

        XCTAssertEqual(
            first.map(\.fileName).sorted(),
            ["Audio2TextApp-2026-05-29-234749.ips", "SonaFolio-2026-05-28.ips", "SonaFolio_2026-05-27.crash"]
        )
        XCTAssertTrue(second.isEmpty)
        XCTAssertTrue(FileManager.default.fileExists(atPath: first[0].cachedPath))
        XCTAssertTrue(FileManager.default.fileExists(atPath: first[1].cachedPath))
        let index = try readText(CrashReportScanner.indexURL(dataRoot: dataRoot))
        XCTAssertTrue(index.contains("SonaFolio_2026-05-27.crash"))
        XCTAssertTrue(index.contains("Audio2TextApp-2026-05-29-234749.ips"))
        let appLog = try readText(AppPaths.logsRoot(dataRoot: dataRoot).appendingPathComponent("app-current.log"))
        XCTAssertEqual(appLog.components(separatedBy: "crash_report_found").count - 1, 3)
    }

    @MainActor
    func testLogStoreMirrorsFallbackAndOutputLogs() throws {
        let dataRoot = URL(fileURLWithPath: NSTemporaryDirectory())
            .appendingPathComponent(UUID().uuidString)
        let output = dataRoot.appendingPathComponent("work/0527/show")
        let store = LogStore()

        store.start(dataRoot: dataRoot)
        store.append("before attach\n")
        store.attach(outputDirectory: output)
        store.append("after attach\n")

        let fallback = try readText(XCTUnwrap(store.fallbackURL))
        let mirror = try readText(XCTUnwrap(store.outputURL))
        XCTAssertTrue(fallback.contains("before attach"))
        XCTAssertTrue(fallback.contains("after attach"))
        XCTAssertTrue(mirror.contains("before attach"))
        XCTAssertTrue(mirror.contains("after attach"))
    }
}
