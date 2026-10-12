import Foundation
#if canImport(Audio2TextCore)
    import Audio2TextCore
#endif

@MainActor
extension JobController {
    func conciseFailureReason(_ error: Error) -> String {
        if case let AppError.processFailed(_, code, output) = error {
            return processFailureSummary(exitCode: code, output: output)
        }
        return shortStatusMessage(error.localizedDescription)
    }

    private func processFailureSummary(exitCode: Int32, output: String) -> String {
        let lines = output
            .components(separatedBy: .newlines)
            .map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }
            .filter { !$0.isEmpty }
        let preferredLine = lines.last { line in
            line.localizedCaseInsensitiveContains("ERROR")
                || line.localizedCaseInsensitiveContains("failed")
                || line.localizedCaseInsensitiveContains("Status: FAIL")
        } ?? lines.last
        if let preferredLine {
            return shortStatusMessage("Command failed (\(exitCode)): \(preferredLine)")
        }
        return "Command failed (\(exitCode))"
    }

    func validateCloudCommandResult(
        _ result: ProcessResult,
        outputDirectory: URL,
        requiredArtifact: String,
        missingArtifactMessage: String,
        includeChunkFailures: Bool = false
    ) throws {
        if let payload = jsonObjectFromCommandOutput(result.output) {
            try validateCloudPayload(
                payload,
                rawOutput: result.output,
                outputDirectory: outputDirectory,
                includeChunkFailures: includeChunkFailures
            )
        }
        let artifactURL = outputDirectory.appendingPathComponent(requiredArtifact)
        guard ProcessLibrary.isExistingNonEmptyFile(artifactURL) else {
            throw AppError.cloudSummaryFailed(
                enrichedCloudFailureMessage(
                    missingArtifactMessage,
                    outputDirectory: outputDirectory,
                    includeChunkFailures: includeChunkFailures
                )
            )
        }
    }

    private func validateCloudPayload(
        _ payload: [String: Any],
        rawOutput: String,
        outputDirectory: URL,
        includeChunkFailures: Bool
    ) throws {
        if let ok = payload["ok"] as? Bool, !ok {
            throw AppError.cloudSummaryFailed(
                cloudSummaryFailureMessage(
                    from: rawOutput,
                    outputDirectory: outputDirectory,
                    includeChunkFailures: includeChunkFailures
                )
            )
        }
        if let success = payload["success"] as? Bool, !success {
            throw AppError.cloudSummaryFailed(
                cloudSummaryFailureMessage(
                    from: rawOutput,
                    outputDirectory: outputDirectory,
                    includeChunkFailures: includeChunkFailures
                )
            )
        }
        if let result = payload["result"] as? [String: Any],
           let success = result["success"] as? Bool,
           !success
        {
            throw AppError.cloudSummaryFailed(
                cloudSummaryFailureMessage(
                    from: rawOutput,
                    outputDirectory: outputDirectory,
                    includeChunkFailures: includeChunkFailures
                )
            )
        }
    }

    func cloudSummaryFailureMessage(
        from output: String,
        outputDirectory: URL? = nil,
        includeChunkFailures: Bool = false
    ) -> String {
        if let payload = jsonObjectFromCommandOutput(output),
           let message = errorMessage(from: payload)
        {
            return enrichedCloudFailureMessage(message, outputDirectory: outputDirectory, includeChunkFailures: includeChunkFailures)
        }
        let lines = output
            .components(separatedBy: .newlines)
            .map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }
            .filter { !$0.isEmpty }
        if let errorLine = lines.last(where: { $0.localizedCaseInsensitiveContains("ERROR:") }) {
            let message = String(errorLine.replacingOccurrences(of: "ERROR:", with: "").trimmingCharacters(in: .whitespacesAndNewlines).prefix(300))
            return enrichedCloudFailureMessage(message, outputDirectory: outputDirectory, includeChunkFailures: includeChunkFailures)
        }
        if let lastLine = lines.last {
            return enrichedCloudFailureMessage(String(lastLine.prefix(300)), outputDirectory: outputDirectory, includeChunkFailures: includeChunkFailures)
        }
        return enrichedCloudFailureMessage(
            "The cloud service returned no usable result. Check the key, model, base URL, and network connection.",
            outputDirectory: outputDirectory,
            includeChunkFailures: includeChunkFailures
        )
    }

    private func jsonObjectFromCommandOutput(_ output: String) -> [String: Any]? {
        if let direct = jsonObject(from: output) {
            return direct
        }
        guard
            let start = output.firstIndex(of: "{"),
            let end = output.lastIndex(of: "}"),
            start <= end
        else {
            return nil
        }
        return jsonObject(from: String(output[start ... end]))
    }

    private func jsonObject(from text: String) -> [String: Any]? {
        guard let data = text.data(using: .utf8) else { return nil }
        return (try? JSONSerialization.jsonObject(with: data)) as? [String: Any]
    }

    private func errorMessage(from payload: [String: Any]) -> String? {
        if let error = payload["error"] as? [String: Any] {
            return stringValue(error["message"])
                ?? stringValue(error["detail"])
                ?? stringValue(error["type"])
        }
        if let result = payload["result"] as? [String: Any] {
            return errorMessage(from: result)
        }
        return stringValue(payload["message"])
            ?? stringValue(payload["detail"])
            ?? stringValue(payload["reason"])
    }

    private func enrichedCloudFailureMessage(
        _ message: String,
        outputDirectory: URL?,
        includeChunkFailures: Bool
    ) -> String {
        let trimmed = message.trimmingCharacters(in: .whitespacesAndNewlines)
        guard
            includeChunkFailures,
            let outputDirectory,
            let chunkFailure = failedCloudChunkSummary(outputDirectory: outputDirectory)
        else {
            return shortStatusMessage(trimmed)
        }
        guard !chunkFailure.reason.isEmpty else {
            return shortStatusMessage(trimmed)
        }
        if trimmed.localizedCaseInsensitiveContains(chunkFailure.reason) {
            return shortStatusMessage(trimmed)
        }
        let includesFailedFileName = chunkFailure.fileNames.contains { trimmed.contains($0) }
        let filePart = includesFailedFileName ? "" : " (\(chunkFailure.compactFileList))"
        let base = trimmed.isEmpty ? "Cloud chunk summaries failed" : trimmed
        return shortStatusMessage("\(chunkFailure.reason) - \(base)\(filePart)")
    }

    private struct CloudChunkFailureSummary {
        let fileNames: [String]
        let reason: String

        var compactFileList: String {
            let shown = fileNames.prefix(3)
            var value = shown.joined(separator: ", ")
            let remaining = fileNames.count - shown.count
            if remaining > 0 {
                value += " +\(remaining)"
            }
            return value
        }
    }

    private func failedCloudChunkSummary(outputDirectory: URL) -> CloudChunkFailureSummary? {
        let chunkDirectory = outputDirectory.appendingPathComponent("cloud/chunk_summaries")
        let fileURLs = ((try? FileManager.default.contentsOfDirectory(
            at: chunkDirectory,
            includingPropertiesForKeys: nil,
            options: [.skipsHiddenFiles]
        )) ?? [])
            .filter { $0.pathExtension == "json" && $0.lastPathComponent.hasPrefix("chunk_") && $0.lastPathComponent.hasSuffix(".summary.json") }
            .sorted { $0.lastPathComponent.localizedStandardCompare($1.lastPathComponent) == .orderedAscending }
        var failedFiles: [String] = []
        var failureReason = ""
        for fileURL in fileURLs {
            guard
                let data = try? Data(contentsOf: fileURL),
                let payload = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
                let success = payload["success"] as? Bool,
                !success
            else {
                continue
            }
            failedFiles.append(fileURL.lastPathComponent)
            if failureReason.isEmpty {
                failureReason = failedCloudChunkReason(from: payload)
            }
        }
        guard !failedFiles.isEmpty else { return nil }
        return CloudChunkFailureSummary(fileNames: failedFiles, reason: failureReason)
    }

    private func failedCloudChunkReason(from payload: [String: Any]) -> String {
        if let retry = payload["retry"] as? [String: Any] {
            if let reason = stringValue(retry["error"]) {
                return reason
            }
            if let attempts = retry["attempts"] as? [[String: Any]] {
                for attempt in attempts.reversed() {
                    if let reason = stringValue(attempt["error"]) {
                        return reason
                    }
                }
            }
        }
        return stringValue(payload["error"])
            ?? stringValue(payload["message"])
            ?? stringValue(payload["reason"])
            ?? ""
    }

    private func stringValue(_ value: Any?) -> String? {
        guard let value else { return nil }
        let text = String(describing: value).trimmingCharacters(in: .whitespacesAndNewlines)
        return text.isEmpty ? nil : text
    }
}
