import Foundation

struct OutputSnapshot: Equatable {
    var outputDirectory: URL?
    var summaryText: String = ""
    var summarySource: String = ""
    var summaryURL: URL?
    var transcriptText: String = ""
    var qaText: String = ""
    var reviewText: String = ""
    var repairText: String = ""
    var glossaryText: String = ""
    var episodeGlossaryText: String = ""
    var runText: String = ""
    var qaStatus: String = "missing"
    var runStatus: String = "missing"
    var chunkProgress: String = "0/0"
    var completedChunks: Int = 0
    var totalChunks: Int = 0
    var diskUsageBytes: Int = 0
    var progressFraction: Double = 0.0
    var cloudStatus: String = "missing"
    var cloudStage: String = ""
    var cloudChunkProgress: String = "0/0"
    var cloudCompletedChunks: Int = 0
    var cloudTotalChunks: Int = 0
    var cloudFailedChunks: Int = 0
    var cloudProgressFraction: Double = 0.0
    var cloudMessage: String = ""

    var preferredSummaryText: String {
        if !summaryText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            return summaryText
        }
        if !transcriptText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            return transcriptText
        }
        return "No summary or transcript is available yet."
    }
}

enum OutputWatcher {
    #if DEBUG
        static var jsonReadObserver: ((URL) -> Void)?
    #endif

    static func outputDirectory(forAudio audioURL: URL, dataRoot: URL = AppPaths.dataRoot()) -> URL {
        AppPaths.outputDirectory(forAudio: audioURL, dataRoot: dataRoot)
    }

    static func snapshot(outputDirectory: URL?, documentsDirectory: URL? = nil) -> OutputSnapshot {
        guard let outputDirectory else {
            return OutputSnapshot()
        }
        var snapshot = OutputSnapshot(outputDirectory: outputDirectory)
        let documentsDirectory = documentsDirectory
        let summaryCandidates = [
            documentsDirectory?.appendingPathComponent("summary.md"),
        ].compactMap { $0 }
        let transcriptCandidates = [
            documentsDirectory?.appendingPathComponent("transcript.md"),
            outputDirectory.appendingPathComponent("transcript.readable.md"),
        ].compactMap { $0 }
        snapshot.summaryText = firstExistingText(
            summaryCandidates,
            source: &snapshot.summarySource,
            sourceURL: &snapshot.summaryURL
        )
        snapshot.transcriptText = firstExistingText(transcriptCandidates)
        snapshot.qaText = readText(outputDirectory.appendingPathComponent("qa.md"))
        snapshot.reviewText = readText(outputDirectory.appendingPathComponent("review.md"))
        snapshot.repairText = repairMarkdown(outputDirectory: outputDirectory)
        snapshot.glossaryText = firstExistingText(
            [
                outputDirectory.appendingPathComponent("cloud/glossary_editor_items.md"),
                outputDirectory.appendingPathComponent("cloud/glossary_suggestions.md"),
                outputDirectory.appendingPathComponent("glossary.effective.json"),
            ]
        )
        snapshot.episodeGlossaryText = prettyJSON(outputDirectory.appendingPathComponent("episode_glossary.json"))
        let runFile = jsonFile(outputDirectory.appendingPathComponent("run.json"))
        snapshot.runText = runFile.prettyText
        snapshot.diskUsageBytes = directorySize(outputDirectory) + (documentsDirectory.map { directorySize($0) } ?? 0)
        applyRunStatus(to: &snapshot, outputDirectory: outputDirectory, run: runFile.object)
        applyEventProgress(to: &snapshot, outputDirectory: outputDirectory)
        applyQAStatus(to: &snapshot, outputDirectory: outputDirectory)
        applyCloudStatus(to: &snapshot, outputDirectory: outputDirectory, run: runFile.object)
        return snapshot
    }

    static func libraryListSnapshot(outputDirectory: URL?, documentsDirectory: URL? = nil) -> OutputSnapshot {
        guard let outputDirectory else {
            return OutputSnapshot()
        }
        var snapshot = OutputSnapshot(outputDirectory: outputDirectory)
        let transcriptCandidates = [
            documentsDirectory?.appendingPathComponent("transcript.md"),
            outputDirectory.appendingPathComponent("transcript.readable.md"),
        ].compactMap { $0 }
        if transcriptCandidates.contains(where: isExistingNonEmptyFile) {
            snapshot.transcriptText = "available"
        }
        let runObject = jsonObjectOnly(outputDirectory.appendingPathComponent("run.json"))
        applyRunStatus(to: &snapshot, outputDirectory: outputDirectory, run: runObject)
        applyEventProgress(to: &snapshot, outputDirectory: outputDirectory)
        applyQAStatus(to: &snapshot, outputDirectory: outputDirectory)
        return snapshot
    }

    private static func firstExistingText(_ urls: [URL], source: inout String, sourceURL: inout URL?) -> String {
        for url in urls {
            let text = readText(url)
            if !text.isEmpty {
                source = url.lastPathComponent
                sourceURL = url
                return text
            }
        }
        return ""
    }

    private static func firstExistingText(_ urls: [URL]) -> String {
        var ignored = ""
        var ignoredURL: URL?
        return firstExistingText(urls, source: &ignored, sourceURL: &ignoredURL)
    }

    private static func readText(_ url: URL) -> String {
        (try? String(contentsOf: url, encoding: .utf8)) ?? ""
    }

    private static func jsonObject(_ url: URL) -> [String: Any]? {
        jsonFile(url).object
    }

    private static func jsonObjectOnly(_ url: URL) -> [String: Any]? {
        #if DEBUG
            jsonReadObserver?(url)
        #endif
        guard
            let data = try? Data(contentsOf: url),
            let object = try? JSONSerialization.jsonObject(with: data) as? [String: Any]
        else {
            return nil
        }
        return object
    }

    private struct JSONFile {
        let object: [String: Any]?
        let prettyText: String
    }

    private static func jsonFile(_ url: URL) -> JSONFile {
        #if DEBUG
            jsonReadObserver?(url)
        #endif
        guard
            let data = try? Data(contentsOf: url),
            let object = try? JSONSerialization.jsonObject(with: data) as? [String: Any]
        else {
            return JSONFile(object: nil, prettyText: "")
        }
        let pretty = (try? JSONSerialization.data(withJSONObject: object, options: [.prettyPrinted, .sortedKeys]))
            .flatMap { String(data: $0, encoding: .utf8) } ?? ""
        return JSONFile(object: object, prettyText: pretty)
    }

    private static func directorySize(_ url: URL) -> Int {
        guard let enumerator = FileManager.default.enumerator(at: url, includingPropertiesForKeys: [.fileSizeKey]) else {
            return 0
        }
        var total = 0
        for case let fileURL as URL in enumerator {
            total += (try? fileURL.resourceValues(forKeys: [.fileSizeKey]).fileSize) ?? 0
        }
        return total
    }

    private static func isExistingNonEmptyFile(_ url: URL) -> Bool {
        guard
            let attributes = try? FileManager.default.attributesOfItem(atPath: url.path),
            let type = attributes[.type] as? FileAttributeType,
            type == .typeRegular,
            let size = attributes[.size] as? NSNumber
        else {
            return false
        }
        return size.int64Value > 0
    }

    private static func prettyJSON(_ url: URL) -> String {
        jsonFile(url).prettyText
    }

    private static func repairMarkdown(outputDirectory: URL) -> String {
        var sections = ["# Repair"]
        let planText = prettyJSON(outputDirectory.appendingPathComponent("repair/repair_plan.json"))
        if !planText.isEmpty {
            sections.append("""
            ## Plan

            ```json
            \(planText)
            ```
            """)
        }
        if let latestRun = latestFile(in: outputDirectory.appendingPathComponent("repair"), prefix: "repair_run_", suffix: ".json") {
            let runText = prettyJSON(latestRun)
            if !runText.isEmpty {
                sections.append("""
                ## Latest Run

                ```json
                \(runText)
                ```
                """)
            }
        }
        if let latestDiff = latestFile(in: outputDirectory.appendingPathComponent("repair"), prefix: "diff_", suffix: ".md") {
            let diffText = readText(latestDiff)
            if !diffText.isEmpty {
                sections.append("""
                ## Latest Diff

                \(diffText)
                """)
            }
        }
        if sections.count == 1 {
            sections.append("No repair artifacts are available.")
        }
        return sections.joined(separator: "\n\n")
    }

    private static func latestFile(in directory: URL, prefix: String, suffix: String) -> URL? {
        let urls = (try? FileManager.default.contentsOfDirectory(
            at: directory,
            includingPropertiesForKeys: [.contentModificationDateKey]
        )) ?? []
        return urls
            .filter { $0.lastPathComponent.hasPrefix(prefix) && $0.lastPathComponent.hasSuffix(suffix) }
            .sorted { lhs, rhs in
                lhs.lastPathComponent.localizedStandardCompare(rhs.lastPathComponent) == .orderedDescending
            }
            .first
    }

    private static func applyRunStatus(to snapshot: inout OutputSnapshot, outputDirectory: URL, run object: [String: Any]?) {
        guard let object else {
            applyChunkFileProgress(to: &snapshot, outputDirectory: outputDirectory)
            return
        }
        if let success = object["success"] as? Bool {
            snapshot.runStatus = success ? "done" : "failed"
        } else {
            snapshot.runStatus = "running"
        }
        let chunks = object["chunks"] as? [[String: Any]] ?? []
        let counts = object["chunk_status_counts"] as? [String: Any] ?? [:]
        let completed = ["transcribed", "transcribed_after_cache_mismatch", "skipped_existing"]
            .map { counts[$0] as? Int ?? 0 }
            .reduce(0, +)
        snapshot.completedChunks = completed
        snapshot.totalChunks = chunks.count
        snapshot.chunkProgress = "\(completed)/\(chunks.count)"
        if chunks.count > 0 {
            snapshot.progressFraction = min(0.95, max(0.10, Double(completed) / Double(chunks.count)))
        }
        if snapshot.runStatus == "done" {
            snapshot.progressFraction = 1.0
        }
    }

    private static func applyChunkFileProgress(to snapshot: inout OutputSnapshot, outputDirectory: URL) {
        let manifestURL = outputDirectory.appendingPathComponent("chunks_manifest.json")
        let chunksDirectory = outputDirectory.appendingPathComponent("chunks")
        let completed = ((try? FileManager.default.contentsOfDirectory(
            at: chunksDirectory,
            includingPropertiesForKeys: nil
        )) ?? [])
            .filter { $0.pathExtension == "json" && $0.lastPathComponent.hasPrefix("chunk_") }
            .count

        var total = 0
        if
            let data = try? Data(contentsOf: manifestURL),
            let object = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
            let layout = object["chunk_layout"] as? [String: Any],
            let chunks = layout["chunks"] as? [[String: Any]]
        {
            total = chunks.count
        }
        if completed > 0 || total > 0 {
            snapshot.runStatus = "running"
            snapshot.completedChunks = completed
            snapshot.totalChunks = total
            snapshot.chunkProgress = total > 0 ? "\(completed)/\(total)" : "\(completed)/?"
            snapshot.progressFraction = total > 0 ? min(0.95, max(0.10, Double(completed) / Double(total))) : 0.10
        }
    }

    private static func applyEventProgress(to snapshot: inout OutputSnapshot, outputDirectory: URL) {
        let eventsURL = outputDirectory.appendingPathComponent("events.jsonl")
        guard let text = try? String(contentsOf: eventsURL, encoding: .utf8) else { return }
        var latestChunk: [String: Any]?
        for line in text.split(separator: "\n") {
            guard
                let data = String(line).data(using: .utf8),
                let object = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
                object["event"] as? String == "chunk"
            else {
                continue
            }
            latestChunk = object
        }
        guard let latestChunk else { return }
        let total = latestChunk["total_chunks"] as? Int ?? snapshot.totalChunks
        let current = latestChunk["chunk"] as? Int ?? -1
        let status = latestChunk["status"] as? String ?? ""
        let completed = status == "started" ? max(0, current) : max(0, current + 1)
        if total > 0 {
            snapshot.totalChunks = total
            snapshot.completedChunks = min(total, completed)
            snapshot.chunkProgress = "\(snapshot.completedChunks)/\(total)"
            if snapshot.runStatus != "done" {
                snapshot.runStatus = "running"
                snapshot.progressFraction = min(0.95, max(0.10, Double(snapshot.completedChunks) / Double(total)))
            }
        }
    }

    private static func applyQAStatus(to snapshot: inout OutputSnapshot, outputDirectory: URL) {
        let qaURL = outputDirectory.appendingPathComponent("qa.json")
        guard
            let data = try? Data(contentsOf: qaURL),
            let object = try? JSONSerialization.jsonObject(with: data) as? [String: Any]
        else {
            return
        }
        if let success = object["success"] as? Bool {
            snapshot.qaStatus = success ? "pass" : "fail"
        }
    }

    private static func applyCloudStatus(to snapshot: inout OutputSnapshot, outputDirectory: URL, run: [String: Any]?) {
        let inputManifest = jsonObject(outputDirectory.appendingPathComponent("cloud/input/manifest.json")) ?? [:]
        let outputManifest = jsonObject(outputDirectory.appendingPathComponent("cloud/manifest.json")) ?? [:]
        let cloud = run?["cloud"] as? [String: Any] ?? [:]
        let summaryExists = FileManager.default.fileExists(
            atPath: outputDirectory.appendingPathComponent("cloud/summary.md").path
        )
        let lockExists = FileManager.default.fileExists(
            atPath: outputDirectory.appendingPathComponent("cloud/summary.lock").path
        )
        let chunkInputs = inputManifest["text_chunks"] as? [[String: Any]] ?? []
        let chunkDirectory = outputDirectory.appendingPathComponent("cloud/chunk_summaries")
        let chunkOutputs = ((try? FileManager.default.contentsOfDirectory(
            at: chunkDirectory,
            includingPropertiesForKeys: nil,
            options: [.skipsHiddenFiles]
        )) ?? [])
            .filter { $0.pathExtension == "json" && $0.lastPathComponent.hasPrefix("chunk_") && $0.lastPathComponent.hasSuffix(".summary.json") }
            .sorted { $0.lastPathComponent.localizedStandardCompare($1.lastPathComponent) == .orderedAscending }

        var completed = 0
        var failed = 0
        var failureMessage = ""
        for fileURL in chunkOutputs {
            guard let payload = jsonObject(fileURL) else { continue }
            if let success = payload["success"] as? Bool, success == false {
                failed += 1
                if failureMessage.isEmpty {
                    failureMessage = failedChunkMessage(from: payload)
                }
            } else if !payload.isEmpty {
                completed += 1
            }
        }

        let prepared = !inputManifest.isEmpty
        let state = stringValue(cloud["summary_state"])
        let stage = stringValue(cloud["summary_stage"])
        let manifestSource = stringValue(outputManifest["source"])
        var total = max(chunkInputs.count, integerValue(cloud["cloud_chunk_total"]))
        if total == 0 {
            total = chunkOutputs.count
        }

        let status: String
        if !state.isEmpty {
            status = state
        } else if !prepared {
            status = "missing"
        } else if failed > 0 && !summaryExists {
            status = "failed"
        } else if lockExists && !summaryExists {
            status = "running"
        } else if summaryExists && (failed > 0 || manifestSource == "partial_cloud") {
            status = "partial"
        } else if summaryExists {
            status = "complete"
        } else {
            status = "prepared"
        }

        snapshot.cloudStatus = status
        snapshot.cloudStage = stage
        snapshot.cloudCompletedChunks = completed
        snapshot.cloudTotalChunks = total
        snapshot.cloudFailedChunks = failed
        snapshot.cloudChunkProgress = total > 0 ? "\(completed)/\(total)" : (completed > 0 ? "\(completed)/?" : "0/0")
        let cloudError = stringValue(cloud["error"])
        let cloudReason = stringValue(cloud["reason"])
        snapshot.cloudMessage = !cloudError.isEmpty ? cloudError : (!cloudReason.isEmpty ? cloudReason : failureMessage)

        switch status {
        case "complete", "partial":
            snapshot.cloudProgressFraction = 1.0
        case "running":
            if total > 0 {
                let fractionBase = Double(completed) / Double(total)
                snapshot.cloudProgressFraction = min(0.95, max(0.08, fractionBase))
            } else {
                snapshot.cloudProgressFraction = 0.08
            }
        case "prepared":
            snapshot.cloudProgressFraction = 0.05
        default:
            snapshot.cloudProgressFraction = 0.0
        }
    }

    private static func failedChunkMessage(from payload: [String: Any]) -> String {
        if let retry = payload["retry"] as? [String: Any] {
            let retryError = stringValue(retry["error"])
            if !retryError.isEmpty {
                return retryError
            }
        }
        let error = stringValue(payload["error"])
        if !error.isEmpty {
            return error
        }
        return stringValue(payload["message"])
    }

    private static func integerValue(_ value: Any?) -> Int {
        if let number = value as? Int {
            return number
        }
        if let number = value as? Double {
            return Int(number)
        }
        if let text = value as? String, let number = Int(text) {
            return number
        }
        return 0
    }

    private static func stringValue(_ value: Any?) -> String {
        (value as? String) ?? ""
    }
}
