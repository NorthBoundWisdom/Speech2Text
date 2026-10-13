import Foundation
#if canImport(Audio2TextCore)
    import Audio2TextCore
#endif

@MainActor
extension JobController {
    func ensureCloudInputPackage(
        outputDirectory: URL,
        runtime: RuntimeContext,
        onOutput: (@MainActor (String) -> Void)? = nil
    ) async throws {
        let outputHandler = onOutput ?? appendLog
        guard !cloudInputPackageIsReady(outputDirectory: outputDirectory) else {
            outputHandler("Cloud input package is ready.\n")
            return
        }

        let arguments = AtotServiceClient.cloudPrepare(
            outputDirectory: outputDirectory,
            chunkMinutes: cloudPrepareChunkMinutes
        )
        outputHandler("\n$ \(runtime.cli.path) \(arguments.joined(separator: " "))\n")
        logEvent(
            category: "summary",
            event: "cloud_input_prepare_started",
            message: "Preparing compact cloud input package",
            fields: ["output_directory": outputDirectory.path, "chunk_minutes": cloudPrepareChunkMinutes]
        )
        do {
            _ = try await runner.run(
                executable: runtime.cli,
                arguments: arguments,
                currentDirectory: runtime.workingDirectory,
                environment: runtime.environment,
                onOutput: outputHandler
            )
        } catch let AppError.processFailed(_, code, output) {
            logEvent(
                .warning,
                event: "cloud_input_prepare_failed",
                message: "Cloud input package preparation failed",
                fields: ["output_directory": outputDirectory.path, "exit_code": "\(code)", "output": AppLogger.redacted(output)]
            )
            throw AppError.cloudSummaryFailed("Package preparation failed: \(cloudSummaryFailureMessage(from: output, outputDirectory: outputDirectory, includeChunkFailures: true))")
        }

        guard cloudInputPackageIsReady(outputDirectory: outputDirectory) else {
            throw AppError.cloudSummaryFailed("Incomplete processing package: missing manifest, transcript.for_cloud.md, or text chunks.")
        }
        outputHandler("Cloud input package prepared.\n")
        logEvent(
            category: "summary",
            event: "cloud_input_prepare_completed",
            message: "Compact cloud input package prepared",
            fields: ["output_directory": outputDirectory.path, "chunk_minutes": cloudPrepareChunkMinutes]
        )
    }

    private func cloudInputPackageIsReady(outputDirectory: URL) -> Bool {
        let inputDirectory = outputDirectory.appendingPathComponent("cloud/input")
        let transcriptURL = inputDirectory.appendingPathComponent("transcript.for_cloud.md")
        let manifestURL = inputDirectory.appendingPathComponent("manifest.json")
        guard ProcessLibrary.isExistingNonEmptyFile(transcriptURL),
              let data = try? Data(contentsOf: manifestURL),
              let manifest = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let textChunks = manifest["text_chunks"] as? [String],
              !textChunks.isEmpty
        else {
            return false
        }
        return textChunks.allSatisfy { relativePath in
            ProcessLibrary.isExistingNonEmptyFile(inputDirectory.appendingPathComponent(relativePath))
        }
    }

    func writeSummaryPromptFile(_ prompt: String, runtime: RuntimeContext) throws -> URL {
        try writeCloudPromptFile(
            prompt,
            defaultPrompt: AppSettings.defaultSummaryPrompt,
            filename: "app-summary.prompt.md",
            runtime: runtime
        )
    }

    func writeTitlePromptFile(_ prompt: String, runtime: RuntimeContext) throws -> URL {
        try writeCloudPromptFile(
            prompt,
            defaultPrompt: AppSettings.defaultTitlePrompt,
            filename: "app-title.prompt.md",
            runtime: runtime
        )
    }

    func publishTitleIfPresent(outputDirectory: URL, dataRoot: URL) throws {
        let titleURL = outputDirectory.appendingPathComponent("cloud/short_title.txt")
        guard let text = try? String(contentsOf: titleURL, encoding: .utf8) else {
            return
        }
        let title = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !title.isEmpty else {
            return
        }
        try LibraryWriter.updateTitle(
            title,
            forEpisodeID: outputDirectory.lastPathComponent,
            in: ProcessLibrary.authoritativeLibraryRoot(dataRoot: dataRoot)
        )
    }

    private func writeCloudPromptFile(
        _ prompt: String,
        defaultPrompt: String,
        filename: String,
        runtime: RuntimeContext
    ) throws -> URL {
        let text = prompt.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
            ? defaultPrompt
            : prompt
        let promptURL = AppPaths.cacheRoot(dataRoot: runtime.dataRoot)
            .appendingPathComponent(filename)
        try FileManager.default.createDirectory(at: promptURL.deletingLastPathComponent(), withIntermediateDirectories: true)
        try text.write(to: promptURL, atomically: true, encoding: .utf8)
        return promptURL
    }

}
