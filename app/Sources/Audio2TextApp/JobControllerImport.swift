import Foundation
#if canImport(Audio2TextCore)
    import Audio2TextCore
#endif

extension JobController {
    func runLinkCheck(url: String) async {
        do {
            let runtime = try runtimeProvider()
            let payload = try await checkXiaoyuzhouLink(url, runtime: runtime)
            guard let audioURL = payload.audioURL, let mediaURL = URL(string: audioURL) else {
                throw AppError.invalidImportOutput("Import metadata did not include an audio URL.")
            }
            try await verifyDownloadableMediaURL(mediaURL)
            linkCheckStatus = .valid(url: url, title: payload.title)
            message = "Link is valid"
            logEvent(category: "import", event: "link_check_succeeded", message: "Link check succeeded", fields: ["host": URL(string: url)?.host ?? ""])
        } catch {
            linkCheckStatus = .invalid(error.localizedDescription)
            message = error.localizedDescription
            logError(category: "import", event: "link_check_failed", error: error, fields: ["host": URL(string: url)?.host ?? ""])
        }
    }

    func runImportOnly() async {
        stage = .idle
        message = ""
        logText = ""
        metadataText = "No metadata is available."
        snapshot = OutputSnapshot()
        progressFraction = 0.0
        persistentLogPath = ""

        do {
            let audioURL: URL
            switch inputMode {
            case .xiaoyuzhou:
                let runtime = try runtimeProvider()
                let plannedAudioURL = try await importXiaoyuzhou(runtime: runtime, download: false)
                selectedFile = plannedAudioURL
                await refreshLibraryAndWait()
                if let item = libraryItems.first(where: { $0.audioURL.path == plannedAudioURL.path }) {
                    selectLibraryItem(item)
                }
                audioURL = try await importXiaoyuzhou(runtime: runtime, download: true)
            case .localFile:
                let dataRoot = settingsStore.dataRoot()
                try RuntimeManager.ensureDirectories(dataRoot: dataRoot)
                audioURL = try importLocal(dataRoot: dataRoot)
            }
            selectedFile = audioURL
            await refreshLibraryAndWait()
            if let item = libraryItems.first(where: { $0.audioURL.path == audioURL.path }) {
                selectLibraryItem(item)
            }
            stage = .completed
            progressFraction = 1.0
            message = "Imported"
            logEvent(category: "import", event: "import_only_completed", message: "Import-only job completed", fields: ["audio": audioURL.lastPathComponent])
        } catch {
            stage = .failed
            message = error.localizedDescription
            appendLog("\nERROR: \(error.localizedDescription)\n")
            logError(category: "import", event: "import_only_failed", error: error)
            await refreshLibraryAndWait()
        }
    }

    func runAudioRestore(for item: ProcessLibraryItem) async {
        stopWatching()
        selectLibraryItem(item)
        stage = .importing
        progressFraction = 0.05
        message = "Restoring audio"
        do {
            try await restoreAudioFile(for: item)
            progressFraction = 1.0
            stage = .completed
            message = "Audio restored"
            await refreshLibraryAndWait()
            if let restored = libraryItems.first(where: { $0.id == item.id }) {
                selectLibraryItem(restored)
            }
            logEvent(category: "import", event: "audio_restore_completed", message: "Audio restored", fields: ["item_id": item.id])
        } catch {
            stage = .failed
            message = error.localizedDescription
            appendLog("\nERROR: \(error.localizedDescription)\n")
            logError(category: "import", event: "audio_restore_failed", error: error, fields: ["item_id": item.id])
            await refreshLibraryAndWait()
        }
    }

    func runAudioDownload(for item: ProcessLibraryItem) async {
        stopWatching()
        selectLibraryItem(item)
        stage = .importing
        progressFraction = 0.05
        message = "Downloading audio"
        do {
            try await restoreAudioFile(for: item)
            progressFraction = 1.0
            stage = .completed
            message = "Audio downloaded"
            await refreshLibraryAndWait()
            if let downloaded = libraryItems.first(where: { $0.id == item.id }) {
                selectLibraryItem(downloaded)
            }
            logEvent(category: "import", event: "audio_download_completed", message: "Audio downloaded", fields: ["item_id": item.id])
        } catch {
            stage = .failed
            message = error.localizedDescription
            appendLog("\nERROR: \(error.localizedDescription)\n")
            logError(category: "import", event: "audio_download_failed", error: error, fields: ["item_id": item.id])
            await refreshLibraryAndWait()
        }
    }

    func restoreAudioFile(for item: ProcessLibraryItem) async throws {
        if let mediaURL = item.remoteAudioURL {
            try await downloadMedia(from: mediaURL, to: item.audioURL)
            return
        }
        let originalURL: URL
        var scopedAccess = false
        if let bookmark = item.originalBookmark {
            var isStale = false
            originalURL = try URL(
                resolvingBookmarkData: bookmark,
                options: [.withSecurityScope],
                relativeTo: nil,
                bookmarkDataIsStale: &isStale
            )
            scopedAccess = originalURL.startAccessingSecurityScopedResource()
        } else if let originalPath = item.originalPath {
            originalURL = URL(fileURLWithPath: originalPath)
        } else {
            throw AppError.fileCopyFailed("No recoverable audio source is available.")
        }
        defer {
            if scopedAccess {
                originalURL.stopAccessingSecurityScopedResource()
            }
        }
        guard ProcessLibrary.isExistingNonEmptyFile(originalURL) else {
            throw AppError.fileCopyFailed("Original local file is unavailable.")
        }
        try FileManager.default.createDirectory(at: item.audioURL.deletingLastPathComponent(), withIntermediateDirectories: true)
        if FileManager.default.fileExists(atPath: item.audioURL.path) {
            try FileManager.default.removeItem(at: item.audioURL)
        }
        try FileManager.default.copyItem(at: originalURL, to: item.audioURL)
    }

    func importXiaoyuzhou(runtime: RuntimeContext, download: Bool) async throws -> URL {
        let url = urlText.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !url.isEmpty else { throw AppError.missingURL }
        guard url.contains("xiaoyuzhoufm.com/episode/") else { throw AppError.unsupportedURL(url) }

        stage = .importing
        progressFraction = download ? max(progressFraction, 0.08) : 0.03
        message = download ? "Downloading episode audio" : "Importing episode metadata"
        logEvent(category: "import", event: "xiaoyuzhou_import_started", message: message, fields: ["download": "\(download)", "host": URL(string: url)?.host ?? ""])
        let processRoot = AppPaths.processRoot(dataRoot: runtime.dataRoot)
        let arguments = AtotServiceClient.importXiaoyuzhou(
            url: url,
            processDirectory: processRoot,
            download: download
        )
        appendLog("$ \(runtime.cli.path) \(arguments.joined(separator: " "))\n")
        let result = try await runner.run(
            executable: runtime.cli,
            arguments: arguments,
            currentDirectory: runtime.workingDirectory,
            environment: runtime.environment,
            onOutput: appendLog
        )
        guard let payload = parseImportPayload(result.output) else {
            throw AppError.invalidImportOutput(result.output)
        }
        let downloadStatus = payload.reusedExisting == true
            ? "reused existing audio"
            : payload.downloaded == false ? "audio already present" : "downloaded audio"
        try writeSelectedGroupTag(episodeDirectory: URL(fileURLWithPath: payload.episodeDir))
        await refreshLibraryAndWait()
        appendLog("\nImported: \(payload.title) (\(downloadStatus))\n")
        logEvent(category: "import", event: "xiaoyuzhou_import_completed", message: downloadStatus, fields: ["title": payload.title, "download": "\(download)"])
        return URL(fileURLWithPath: payload.audioPath)
    }

    func importLocal(dataRoot: URL) throws -> URL {
        guard let selectedFile else { throw AppError.missingLocalFile }
        stage = .copying
        progressFraction = 0.05
        message = localImportMode == .copy ? "Copying local audio into data cache" : "Referencing local audio"
        let importer = LocalAudioImporter(dataRoot: dataRoot, libraryRoot: settingsStore.libraryRoot(), groupName: selectedGroupName)
        let audio = try importer.importAudio(selectedFile, mode: localImportMode)
        appendLog("Imported local audio: \(audio.path)\n")
        logEvent(category: "import", event: "local_import_completed", message: "Local audio imported", fields: ["file_name": selectedFile.lastPathComponent, "group": selectedGroupName, "mode": localImportMode.rawValue])
        return audio
    }

    private func checkXiaoyuzhouLink(_ url: String, runtime: RuntimeContext) async throws -> XiaoyuzhouImportPayload {
        let checkRoot = FileManager.default.temporaryDirectory
            .appendingPathComponent("Audio2TextLinkCheck-\(UUID().uuidString)")
        defer { try? FileManager.default.removeItem(at: checkRoot) }
        let arguments = AtotServiceClient.importXiaoyuzhou(
            url: url,
            processDirectory: checkRoot,
            download: false
        )
        appendLog("$ \(runtime.cli.path) \(arguments.joined(separator: " "))\n")
        let result = try await runner.run(
            executable: runtime.cli,
            arguments: arguments,
            currentDirectory: runtime.workingDirectory,
            environment: runtime.environment,
            onOutput: appendLog
        )
        guard let payload = parseImportPayload(result.output) else {
            throw AppError.invalidImportOutput(result.output)
        }
        return payload
    }

    private func writeSelectedGroupTag(episodeDirectory: URL) throws {
        let metadataURL = episodeDirectory.appendingPathComponent("episode.json")
        guard
            let data = try? Data(contentsOf: metadataURL),
            var object = try? JSONSerialization.jsonObject(with: data) as? [String: Any]
        else {
            return
        }
        let groupName = ProcessLibrary.pathComponent(forGroupName: selectedGroupName)
        object["app_group"] = groupName
        let updated = try JSONSerialization.data(withJSONObject: object, options: [.prettyPrinted, .sortedKeys])
        try updated.write(to: metadataURL, options: .atomic)
        try LibraryWriter.upsertGroup(groupName, in: settingsStore.libraryRoot())
    }

    private func verifyDownloadableMediaURL(_ url: URL) async throws {
        var request = URLRequest(url: url)
        request.httpMethod = "HEAD"
        request.timeoutInterval = 15
        let (_, response) = try await URLSession.shared.data(for: request)
        guard let http = response as? HTTPURLResponse, (200 ..< 400).contains(http.statusCode) else {
            throw AppError.fileCopyFailed("Could not verify media download URL.")
        }
    }

    private func downloadMedia(from url: URL, to destination: URL) async throws {
        var request = URLRequest(url: url)
        request.setValue("SonaFolio/1.0", forHTTPHeaderField: "User-Agent")
        let (temporaryURL, response) = try await URLSession.shared.download(for: request)
        guard let http = response as? HTTPURLResponse, (200 ..< 400).contains(http.statusCode) else {
            throw AppError.fileCopyFailed("Audio download failed.")
        }
        try FileManager.default.createDirectory(at: destination.deletingLastPathComponent(), withIntermediateDirectories: true)
        if FileManager.default.fileExists(atPath: destination.path) {
            try FileManager.default.removeItem(at: destination)
        }
        try FileManager.default.moveItem(at: temporaryURL, to: destination)
        guard ProcessLibrary.isExistingNonEmptyFile(destination) else {
            throw AppError.fileCopyFailed("Downloaded audio is empty.")
        }
    }

    private func parseImportPayload(_ output: String) -> XiaoyuzhouImportPayload? {
        guard let data = output.data(using: .utf8) else { return nil }
        if let payload = try? JSONDecoder().decode(XiaoyuzhouImportPayload.self, from: data) {
            return payload
        }
        guard
            let start = output.firstIndex(of: "{"),
            let end = output.lastIndex(of: "}")
        else {
            return nil
        }
        let jsonText = String(output[start ... end])
        return try? JSONDecoder().decode(XiaoyuzhouImportPayload.self, from: Data(jsonText.utf8))
    }
}
