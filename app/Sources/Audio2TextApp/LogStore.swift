import Foundation

@MainActor
final class LogStore {
    private(set) var fallbackURL: URL?
    private(set) var outputURL: URL?
    private var buffer = ""

    func start(dataRoot: URL = AppPaths.dataRoot()) {
        buffer = ""
        outputURL = nil
        let logsDirectory = AppPaths.logsRoot(dataRoot: dataRoot)
        try? FileManager.default.createDirectory(at: logsDirectory, withIntermediateDirectories: true)
        let stamp = Self.timestampForFilename()
        fallbackURL = logsDirectory.appendingPathComponent("job-\(stamp).log")
        writeHeader(to: fallbackURL)
        AppLogger.shared.log(
            .info,
            category: "job",
            event: "job_log_started",
            message: "Job log started",
            fields: ["fallback_log": fallbackURL?.path ?? ""],
            dataRoot: dataRoot
        )
    }

    func attach(outputDirectory: URL) {
        try? FileManager.default.createDirectory(at: outputDirectory, withIntermediateDirectories: true)
        outputURL = outputDirectory.appendingPathComponent("app.log")
        writeHeader(to: outputURL)
        if !buffer.isEmpty {
            appendToFile(buffer, url: outputURL)
        }
        AppLogger.shared.log(
            .info,
            category: "job",
            event: "job_log_attached",
            message: "Job log mirrored to output directory",
            fields: [
                "output_directory": outputDirectory.path,
                "output_log": outputURL?.path ?? "",
            ]
        )
    }

    func append(_ text: String) {
        buffer.append(text)
        appendToFile(text, url: fallbackURL)
        appendToFile(text, url: outputURL)
    }

    private func writeHeader(to url: URL?) {
        guard let url else { return }
        let header = "SonaFolio log started at \(ISO8601DateFormatter().string(from: Date()))\n\n"
        try? header.write(to: url, atomically: true, encoding: .utf8)
    }

    private func appendToFile(_ text: String, url: URL?) {
        guard let url, let data = text.data(using: .utf8) else { return }
        if FileManager.default.fileExists(atPath: url.path) {
            if let handle = try? FileHandle(forWritingTo: url) {
                _ = try? handle.seekToEnd()
                try? handle.write(contentsOf: data)
                try? handle.close()
            }
        } else {
            try? data.write(to: url)
        }
    }

    private static func timestampForFilename() -> String {
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.dateFormat = "yyyyMMdd-HHmmss"
        return formatter.string(from: Date())
    }
}
