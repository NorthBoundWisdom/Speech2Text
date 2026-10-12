import Foundation
#if canImport(Audio2TextCore)
    import Audio2TextCore
#endif

@MainActor
extension JobController {
    func startWatching(outputDirectory: URL) {
        stopWatching()
        watcherTask = Task { [weak self] in
            while !Task.isCancelled {
                try? await Task.sleep(nanoseconds: 1_000_000_000)
                await MainActor.run {
                    guard let self else { return }
                    let runningSnapshot = self.libraryListSnapshotForOutputDirectory(outputDirectory)
                    if self.snapshot.outputDirectory?.standardizedFileURL.path == outputDirectory.standardizedFileURL.path {
                        self.snapshot = runningSnapshot
                    }
                    self.updateProgress(from: runningSnapshot, defaultValue: 0.15)
                    self.updateSelectedLibraryItemDetails(from: runningSnapshot, outputDirectory: outputDirectory)
                }
            }
        }
    }

    func stopWatching() {
        watcherTask?.cancel()
        watcherTask = nil
    }

    func appendLog(_ text: String) {
        logText.append(text)
        logStore.append(text)
    }

    func logEvent(
        _ level: AppLogLevel = .info,
        category: String = "job",
        event: String,
        message: String = "",
        fields: [String: String] = [:]
    ) {
        AppLogger.shared.log(level, category: category, event: event, message: message, fields: fields)
    }

    func logError(
        category: String = "job",
        event: String,
        error: Error,
        fields: [String: String] = [:]
    ) {
        var merged = fields
        merged["error_type"] = "\(type(of: error))"
        AppLogger.shared.log(
            .error,
            category: category,
            event: event,
            message: error.localizedDescription,
            fields: merged
        )
    }

    func updateProgress(from source: OutputSnapshot? = nil, defaultValue: Double) {
        let source = source ?? snapshot
        if source.progressFraction > 0 {
            progressFraction = source.progressFraction
        } else {
            progressFraction = max(progressFraction, defaultValue)
        }
    }
}
