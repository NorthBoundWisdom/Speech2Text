import Foundation

enum AppLogLevel: String {
    case debug
    case info
    case warning
    case error
}

struct CrashReportRecord: Codable, Equatable {
    let id: String
    let fileName: String
    let originalPath: String
    let cachedPath: String
    let modifiedAt: String
    let discoveredAt: String
}

private struct CrashReportIndex: Codable {
    var reports: [CrashReportRecord]
}

struct LogCleanupResult: Equatable {
    let deletedFiles: Int
    let deletedDirectories: Int
}

final class AppLogger {
    static let shared = AppLogger()

    private let lock = NSLock()
    private var configuredDataRoot: URL?
    private let fileManager: FileManager
    private let now: () -> Date

    init(
        dataRoot: URL? = nil,
        fileManager: FileManager = .default,
        now: @escaping () -> Date = Date.init
    ) {
        configuredDataRoot = dataRoot
        self.fileManager = fileManager
        self.now = now
    }

    func configure(dataRoot: URL) {
        lock.lock()
        configuredDataRoot = dataRoot
        lock.unlock()
        do {
            try fileManager.createDirectory(at: AppPaths.logsRoot(dataRoot: dataRoot), withIntermediateDirectories: true)
            resetCurrentLog(dataRoot: dataRoot)
            cleanup(dataRoot: dataRoot)
        } catch {
            NSLog("Audio2Text AppLogger configure failed: \(error.localizedDescription)")
        }
    }

    func latestLogURL(dataRoot: URL? = nil) -> URL {
        let root = dataRoot ?? resolvedDataRoot()
        return AppPaths.logsRoot(dataRoot: root).appendingPathComponent("app-current.log")
    }

    func log(
        _ level: AppLogLevel = .info,
        category: String,
        event: String,
        message: String = "",
        fields: [String: String] = [:],
        dataRoot explicitDataRoot: URL? = nil
    ) {
        let timestamp = now()
        let dataRoot = explicitDataRoot ?? resolvedDataRoot()
        let logsRoot = AppPaths.logsRoot(dataRoot: dataRoot)
        do {
            lock.lock()
            defer { lock.unlock() }
            try fileManager.createDirectory(at: logsRoot, withIntermediateDirectories: true)
            let line = try encodedLine(
                timestamp: timestamp,
                level: level,
                category: category,
                event: event,
                message: message,
                fields: fields
            )
            append(line, to: logsRoot.appendingPathComponent("app-current.log"))
            append(line, to: logsRoot.appendingPathComponent("app-\(dayStamp(timestamp)).log"))
        } catch {
            NSLog("Audio2Text AppLogger write failed: \(error.localizedDescription)")
        }
    }

    func cleanup(
        dataRoot: URL? = nil,
        keepDays: Int = 30,
        maxBytes: Int64 = 50 * 1024 * 1024
    ) {
        let root = dataRoot ?? resolvedDataRoot()
        let logsRoot = AppPaths.logsRoot(dataRoot: root)
        guard let enumerator = fileManager.enumerator(
            at: logsRoot,
            includingPropertiesForKeys: [.isRegularFileKey, .contentModificationDateKey, .fileSizeKey],
            options: [.skipsHiddenFiles]
        ) else {
            return
        }

        let cutoff = now().addingTimeInterval(TimeInterval(-keepDays * 86400))
        var files: [(url: URL, modified: Date, size: Int64)] = []
        for case let url as URL in enumerator {
            guard isRegularFile(url) else { continue }
            let modified = modificationDate(url) ?? .distantPast
            let size = fileSize(url)
            if shouldPreserveDuringCleanup(url, logsRoot: logsRoot) {
                files.append((url, modified, size))
                continue
            }
            if modified < cutoff {
                try? fileManager.removeItem(at: url)
            } else {
                files.append((url, modified, size))
            }
        }

        var total = files.reduce(Int64(0)) { $0 + $1.size }
        guard total > maxBytes else { return }
        for file in files
            .filter({ !shouldPreserveDuringCleanup($0.url, logsRoot: logsRoot) })
            .sorted(by: { $0.modified < $1.modified })
        {
            try? fileManager.removeItem(at: file.url)
            total -= file.size
            if total <= maxBytes {
                break
            }
        }
    }

    @discardableResult
    func deleteHistoricalLogs(dataRoot: URL? = nil) -> LogCleanupResult {
        let root = dataRoot ?? resolvedDataRoot()
        let logsRoot = AppPaths.logsRoot(dataRoot: root)
        let currentLogURL = logsRoot.appendingPathComponent("app-current.log").standardizedFileURL
        guard let enumerator = fileManager.enumerator(
            at: logsRoot,
            includingPropertiesForKeys: [.isRegularFileKey, .isDirectoryKey],
            options: [.skipsHiddenFiles]
        ) else {
            return LogCleanupResult(deletedFiles: 0, deletedDirectories: 0)
        }

        var deletedFiles = 0
        var directories: [URL] = []
        for case let url as URL in enumerator {
            let standardizedURL = url.standardizedFileURL
            if standardizedURL == currentLogURL {
                continue
            }
            if isDirectory(url) {
                directories.append(url)
                continue
            }
            do {
                try fileManager.removeItem(at: url)
                deletedFiles += 1
            } catch {
                NSLog("Audio2Text AppLogger log cleanup failed: \(error.localizedDescription)")
            }
        }

        var deletedDirectories = 0
        for directory in directories.sorted(by: { $0.path.count > $1.path.count }) {
            if (try? fileManager.contentsOfDirectory(atPath: directory.path).isEmpty) == true {
                do {
                    try fileManager.removeItem(at: directory)
                    deletedDirectories += 1
                } catch {
                    NSLog("Audio2Text AppLogger directory cleanup failed: \(error.localizedDescription)")
                }
            }
        }
        return LogCleanupResult(deletedFiles: deletedFiles, deletedDirectories: deletedDirectories)
    }

    static func redacted(_ value: String, key: String = "") -> String {
        let lowerKey = key.lowercased()
        if lowerKey.contains("key")
            || lowerKey.contains("token")
            || lowerKey.contains("secret")
            || lowerKey.contains("authorization")
            || lowerKey.contains("password")
        {
            return "****"
        }
        var text = value
        text = text.replacingOccurrences(
            of: #"(?i)(api[_-]?key|token|authorization|secret|password)=([^\s&]+)"#,
            with: "$1=****",
            options: .regularExpression
        )
        text = text.replacingOccurrences(
            of: #"(?i)(Bearer\s+)[A-Za-z0-9._~+/=-]+"#,
            with: "$1****",
            options: .regularExpression
        )
        text = text.replacingOccurrences(
            of: #"sk-[A-Za-z0-9._-]{8,}"#,
            with: "sk-****",
            options: .regularExpression
        )
        if text.count > 1000 {
            return String(text.prefix(1000)) + "...(truncated)"
        }
        return text
    }

    private func encodedLine(
        timestamp: Date,
        level: AppLogLevel,
        category: String,
        event: String,
        message: String,
        fields: [String: String]
    ) throws -> String {
        var object: [String: Any] = [
            "time": isoString(timestamp),
            "level": level.rawValue,
            "category": category,
            "event": event,
            "message": Self.redacted(message, key: "message"),
        ]
        if !fields.isEmpty {
            object["fields"] = fields.reduce(into: [String: String]()) { partial, pair in
                partial[pair.key] = Self.redacted(pair.value, key: pair.key)
            }
        }
        let data = try JSONSerialization.data(withJSONObject: object, options: [.sortedKeys])
        return (String(data: data, encoding: .utf8) ?? "{}") + "\n"
    }

    private func resolvedDataRoot() -> URL {
        lock.lock()
        let root = configuredDataRoot
        lock.unlock()
        return root ?? AppPaths.dataRoot()
    }

    private func append(_ line: String, to url: URL) {
        guard let data = line.data(using: .utf8) else { return }
        if fileManager.fileExists(atPath: url.path), let handle = try? FileHandle(forWritingTo: url) {
            defer { try? handle.close() }
            _ = try? handle.seekToEnd()
            try? handle.write(contentsOf: data)
        } else {
            try? data.write(to: url, options: .atomic)
        }
    }

    private func dayStamp(_ date: Date) -> String {
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.dateFormat = "yyyyMMdd"
        return formatter.string(from: date)
    }

    private func isoString(_ date: Date) -> String {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return formatter.string(from: date)
    }

    private func isRegularFile(_ url: URL) -> Bool {
        (try? url.resourceValues(forKeys: [.isRegularFileKey]).isRegularFile) == true
    }

    private func isDirectory(_ url: URL) -> Bool {
        (try? url.resourceValues(forKeys: [.isDirectoryKey]).isDirectory) == true
    }

    private func modificationDate(_ url: URL) -> Date? {
        try? url.resourceValues(forKeys: [.contentModificationDateKey]).contentModificationDate
    }

    private func fileSize(_ url: URL) -> Int64 {
        let size = try? url.resourceValues(forKeys: [.fileSizeKey]).fileSize
        return Int64(size ?? 0)
    }

    private func shouldPreserveDuringCleanup(_ url: URL, logsRoot: URL) -> Bool {
        url.standardizedFileURL == logsRoot.appendingPathComponent("app-current.log").standardizedFileURL
            || url.lastPathComponent == "index.json"
    }

    private func resetCurrentLog(dataRoot: URL) {
        let currentLogURL = AppPaths.logsRoot(dataRoot: dataRoot).appendingPathComponent("app-current.log")
        try? Data().write(to: currentLogURL, options: .atomic)
    }
}

enum CrashReportScanner {
    static func scan(
        dataRoot: URL,
        diagnosticReportsURL: URL = FileManager.default.homeDirectoryForCurrentUser
            .appendingPathComponent("Library/Logs/DiagnosticReports"),
        logger: AppLogger = .shared,
        now: Date = Date(),
        fileManager: FileManager = .default
    ) -> [CrashReportRecord] {
        let crashRoot = AppPaths.logsRoot(dataRoot: dataRoot).appendingPathComponent("crash-reports")
        do {
            try fileManager.createDirectory(at: crashRoot, withIntermediateDirectories: true)
        } catch {
            logger.log(.error, category: "crash", event: "crash_report_scan_failed", message: error.localizedDescription, dataRoot: dataRoot)
            return []
        }

        var index = loadIndex(from: indexURL(dataRoot: dataRoot), fileManager: fileManager)
        let knownIDs = Set(index.reports.map(\.id))
        let candidates = crashReportCandidates(in: diagnosticReportsURL, fileManager: fileManager)
        var imported: [CrashReportRecord] = []

        for sourceURL in candidates {
            guard let recordID = reportID(for: sourceURL, fileManager: fileManager), !knownIDs.contains(recordID) else {
                continue
            }
            let cachedURL = uniqueCacheURL(for: sourceURL, in: crashRoot, fileManager: fileManager)
            do {
                try fileManager.copyItem(at: sourceURL, to: cachedURL)
                let record = CrashReportRecord(
                    id: recordID,
                    fileName: sourceURL.lastPathComponent,
                    originalPath: sourceURL.path,
                    cachedPath: cachedURL.path,
                    modifiedAt: isoString(modificationDate(sourceURL, fileManager: fileManager) ?? now),
                    discoveredAt: isoString(now)
                )
                index.reports.append(record)
                imported.append(record)
                logger.log(
                    .error,
                    category: "crash",
                    event: "crash_report_found",
                    message: "Imported macOS crash report",
                    fields: [
                        "file_name": record.fileName,
                        "modified_at": record.modifiedAt,
                        "original_path": record.originalPath,
                        "cached_path": record.cachedPath,
                    ],
                    dataRoot: dataRoot
                )
            } catch {
                logger.log(
                    .error,
                    category: "crash",
                    event: "crash_report_import_failed",
                    message: error.localizedDescription,
                    fields: ["file_name": sourceURL.lastPathComponent],
                    dataRoot: dataRoot
                )
            }
        }

        saveIndex(index, to: indexURL(dataRoot: dataRoot), fileManager: fileManager)
        return imported
    }

    static func recentCrashReportCount(
        dataRoot: URL,
        sinceDays: Int = 30,
        now: Date = Date(),
        fileManager: FileManager = .default
    ) -> Int {
        let index = loadIndex(from: indexURL(dataRoot: dataRoot), fileManager: fileManager)
        let cutoff = now.addingTimeInterval(TimeInterval(-sinceDays * 86400))
        return index.reports.filter { record in
            guard let date = ISO8601DateFormatter().date(from: record.discoveredAt) else {
                return true
            }
            return date >= cutoff
        }.count
    }

    static func indexURL(dataRoot: URL) -> URL {
        AppPaths.logsRoot(dataRoot: dataRoot)
            .appendingPathComponent("crash-reports")
            .appendingPathComponent("index.json")
    }

    private static func crashReportCandidates(in directory: URL, fileManager: FileManager) -> [URL] {
        guard let urls = try? fileManager.contentsOfDirectory(
            at: directory,
            includingPropertiesForKeys: [.contentModificationDateKey, .fileSizeKey],
            options: [.skipsHiddenFiles]
        ) else {
            return []
        }
        return urls
            .filter { url in
                let ext = url.pathExtension.lowercased()
                let fileName = url.lastPathComponent
                return (fileName.hasPrefix("Audio2TextApp_") || fileName.hasPrefix("Audio2TextApp-"))
                    && (ext == "crash" || ext == "ips")
            }
            .sorted { lhs, rhs in
                (modificationDate(lhs, fileManager: fileManager) ?? .distantPast)
                    < (modificationDate(rhs, fileManager: fileManager) ?? .distantPast)
            }
    }

    private static func reportID(for url: URL, fileManager: FileManager) -> String? {
        guard let modified = modificationDate(url, fileManager: fileManager) else {
            return nil
        }
        let size = (try? url.resourceValues(forKeys: [.fileSizeKey]).fileSize) ?? 0
        return "\(url.path)|\(modified.timeIntervalSince1970)|\(size)"
    }

    private static func loadIndex(from url: URL, fileManager _: FileManager) -> CrashReportIndex {
        guard
            let data = try? Data(contentsOf: url),
            let decoded = try? JSONDecoder().decode(CrashReportIndex.self, from: data)
        else {
            return CrashReportIndex(reports: [])
        }
        return decoded
    }

    private static func saveIndex(_ index: CrashReportIndex, to url: URL, fileManager: FileManager) {
        do {
            try fileManager.createDirectory(at: url.deletingLastPathComponent(), withIntermediateDirectories: true)
            let data = try JSONEncoder.sortedPretty.encode(index)
            try data.write(to: url, options: .atomic)
        } catch {
            NSLog("Audio2Text crash report index write failed: \(error.localizedDescription)")
        }
    }

    private static func uniqueCacheURL(for sourceURL: URL, in crashRoot: URL, fileManager: FileManager) -> URL {
        let proposed = crashRoot.appendingPathComponent(sourceURL.lastPathComponent)
        guard fileManager.fileExists(atPath: proposed.path) else {
            return proposed
        }
        let base = sourceURL.deletingPathExtension().lastPathComponent
        let ext = sourceURL.pathExtension
        return crashRoot.appendingPathComponent("\(base)-\(UUID().uuidString.prefix(8)).\(ext)")
    }

    private static func modificationDate(_ url: URL, fileManager _: FileManager) -> Date? {
        try? url.resourceValues(forKeys: [.contentModificationDateKey]).contentModificationDate
    }

    private static func isoString(_ date: Date) -> String {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return formatter.string(from: date)
    }
}

private extension JSONEncoder {
    static var sortedPretty: JSONEncoder {
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        return encoder
    }
}
