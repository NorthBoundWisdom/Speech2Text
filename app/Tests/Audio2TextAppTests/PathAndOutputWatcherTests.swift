@testable import Audio2TextApp
import Audio2TextCore
import XCTest

final class PathAndOutputWatcherTests: XCTestCase {
    func testSanitizedSlugKeepsChineseAndCollapsesSeparators() {
        XCTAssertEqual(PathTools.sanitizedSlug(" 咖啡时间：揭秘 / 一杯? "), "咖啡时间-揭秘-一杯")
    }

    func testDateFolderUsesMonthAndDay() throws {
        var calendar = Calendar(identifier: .gregorian)
        calendar.timeZone = try XCTUnwrap(TimeZone(secondsFromGMT: 0))
        let date = Date(timeIntervalSince1970: 1_779_840_000) // 2026-05-27 UTC

        XCTAssertEqual(PathTools.dateFolder(for: date, calendar: calendar), "0527")
    }

    func testOutputDirectoryUsesDataOutputRootForProcessAudio() {
        let dataRoot = URL(fileURLWithPath: "/data")
        let audio = dataRoot.appendingPathComponent("materials/0528/show/show.m4a")

        XCTAssertEqual(
            OutputWatcher.outputDirectory(forAudio: audio, dataRoot: dataRoot).path,
            "/data/work/0528/show"
        )
    }

    func testSnapshotReadsRunJsonOnceForDisplayRunAndCloudStatus() throws {
        let root = URL(fileURLWithPath: NSTemporaryDirectory())
            .appendingPathComponent(UUID().uuidString)
        let output = root.appendingPathComponent("work")
        let runURL = output.appendingPathComponent("run.json")
        try writeJSON(
            [
                "success": true,
                "chunks": [],
                "chunk_status_counts": [
                    "transcribed": 0,
                    "transcribed_after_cache_mismatch": 0,
                    "skipped_existing": 0,
                ],
                "cloud": [
                    "summary_state": "failed",
                    "error": "timeout",
                ],
            ],
            to: runURL
        )
        var runReads = 0
        OutputWatcher.jsonReadObserver = { observedURL in
            if observedURL.standardizedFileURL.path == runURL.standardizedFileURL.path {
                runReads += 1
            }
        }
        defer { OutputWatcher.jsonReadObserver = nil }

        let snapshot = OutputWatcher.snapshot(outputDirectory: output)

        XCTAssertEqual(runReads, 1)
        XCTAssertEqual(snapshot.runStatus, "done")
        XCTAssertEqual(snapshot.cloudStatus, "failed")
        XCTAssertEqual(snapshot.cloudMessage, "timeout")
        XCTAssertTrue(snapshot.runText.contains("\"success\" : true"))
    }

    func testContentTabDisplayOrderShowsReaderTabsOnly() {
        XCTAssertEqual(ContentTab.displayOrder, [.metadata, .summary, .transcript])
        XCTAssertEqual(ContentTab.metadata.title, "Overview")
        XCTAssertEqual(ContentTab.summary.title, "Summary")
        XCTAssertEqual(ContentTab.transcript.title, "Transcript")
    }

    func testSnapshotPrefersSummaryOverTranscript() throws {
        let root = URL(fileURLWithPath: NSTemporaryDirectory())
            .appendingPathComponent(UUID().uuidString)
        let output = root.appendingPathComponent("work")
        let documents = root.appendingPathComponent("Audio2TextLibrary/episodes/episode/documents")
        try FileManager.default.createDirectory(at: documents, withIntermediateDirectories: true)
        try "summary body".write(to: documents.appendingPathComponent("summary.md"), atomically: true, encoding: .utf8)
        try "transcript body".write(to: documents.appendingPathComponent("transcript.md"), atomically: true, encoding: .utf8)

        let snapshot = OutputWatcher.snapshot(outputDirectory: output, documentsDirectory: documents)

        XCTAssertEqual(snapshot.preferredSummaryText, "summary body")
        XCTAssertEqual(snapshot.summarySource, "summary.md")
        XCTAssertEqual(snapshot.summaryURL?.path, documents.appendingPathComponent("summary.md").path)
    }

    func testSnapshotPrefersRootSummaryBeforeCloudSummary() throws {
        let root = URL(fileURLWithPath: NSTemporaryDirectory())
            .appendingPathComponent(UUID().uuidString)
        let output = root.appendingPathComponent("work")
        let documents = root.appendingPathComponent("Audio2TextLibrary/episodes/episode/documents")
        let cloud = output.appendingPathComponent("cloud")
        try FileManager.default.createDirectory(at: cloud, withIntermediateDirectories: true)
        try FileManager.default.createDirectory(at: documents, withIntermediateDirectories: true)
        try "library summary".write(to: documents.appendingPathComponent("summary.md"), atomically: true, encoding: .utf8)
        try "cloud summary".write(to: cloud.appendingPathComponent("summary.md"), atomically: true, encoding: .utf8)

        let snapshot = OutputWatcher.snapshot(outputDirectory: output, documentsDirectory: documents)

        XCTAssertEqual(snapshot.summaryText, "library summary")
        XCTAssertEqual(snapshot.summaryURL?.path, documents.appendingPathComponent("summary.md").path)
    }

    func testSnapshotReadsCanonicalTimestampedTranscriptForTranscriptTab() throws {
        let root = URL(fileURLWithPath: NSTemporaryDirectory())
            .appendingPathComponent(UUID().uuidString)
        let output = root.appendingPathComponent("work")
        let documents = root.appendingPathComponent("Audio2TextLibrary/episodes/episode/documents")
        try FileManager.default.createDirectory(at: documents, withIntermediateDirectories: true)
        try "[00:00:01 -> 00:00:03] timed transcript".write(
            to: documents.appendingPathComponent("transcript.md"),
            atomically: true,
            encoding: .utf8
        )

        let snapshot = OutputWatcher.snapshot(outputDirectory: output, documentsDirectory: documents)

        XCTAssertEqual(snapshot.transcriptText, "[00:00:01 -> 00:00:03] timed transcript")
    }

    func testSnapshotReadsRepairArtifacts() throws {
        let root = URL(fileURLWithPath: NSTemporaryDirectory())
            .appendingPathComponent(UUID().uuidString)
        let repair = root.appendingPathComponent("work/repair")
        try FileManager.default.createDirectory(at: repair, withIntermediateDirectories: true)
        try #"{"windows":[{"id":"repair-window-0001"}]}"#.write(
            to: repair.appendingPathComponent("repair_plan.json"),
            atomically: true,
            encoding: .utf8
        )
        try "### Before\n\n坏\n\n### After\n\n好\n".write(
            to: repair.appendingPathComponent("diff_001.md"),
            atomically: true,
            encoding: .utf8
        )

        let snapshot = OutputWatcher.snapshot(outputDirectory: root.appendingPathComponent("work"))

        XCTAssertTrue(snapshot.repairText.contains("repair-window-0001"))
        XCTAssertTrue(snapshot.repairText.contains("### After"))
    }

    func testSnapshotReadsGlossaryEditorArtifacts() throws {
        let root = URL(fileURLWithPath: NSTemporaryDirectory())
            .appendingPathComponent(UUID().uuidString)
        let output = root.appendingPathComponent("work")
        try FileManager.default.createDirectory(
            at: output.appendingPathComponent("cloud"),
            withIntermediateDirectories: true
        )
        try "# Glossary\n\n| Term | Category |\n| --- | --- |\n| API | technical_terms |\n".write(
            to: output.appendingPathComponent("cloud/glossary_editor_items.md"),
            atomically: true,
            encoding: .utf8
        )

        let snapshot = OutputWatcher.snapshot(outputDirectory: output)

        XCTAssertTrue(snapshot.glossaryText.contains("API"))
    }

    @MainActor
    func testEpisodeGlossaryEditorCanAddSaveAndDisableTerms() throws {
        let root = URL(fileURLWithPath: NSTemporaryDirectory())
            .appendingPathComponent(UUID().uuidString)
        let output = root.appendingPathComponent("work")
        try FileManager.default.createDirectory(at: output, withIntermediateDirectories: true)
        let controller = testJobController()
        controller.snapshot = OutputSnapshot(outputDirectory: output)

        controller.addGlossaryTerm("API", category: "technical_terms")
        controller.disableGlossaryTerm("API")
        var glossary = try readJSON(output.appendingPathComponent("episode_glossary.json"))
        XCTAssertEqual(glossary["technical_terms"] as? [String], ["API"])
        XCTAssertEqual(glossary["disabled_terms"] as? [String], ["API"])
        controller.saveEpisodeGlossaryJSON(#"{"people":["张三"]}"#)

        glossary = try readJSON(output.appendingPathComponent("episode_glossary.json"))
        XCTAssertEqual(glossary["people"] as? [String], ["张三"])
    }

    func testSnapshotReportsChunkFileProgressBeforeRunJsonExists() throws {
        let root = URL(fileURLWithPath: NSTemporaryDirectory())
            .appendingPathComponent(UUID().uuidString)
        let output = root.appendingPathComponent("work")
        let details = output
        let chunks = details.appendingPathComponent("chunks")
        try FileManager.default.createDirectory(at: chunks, withIntermediateDirectories: true)
        let manifest = """
        {"chunk_layout":{"chunks":[{"index":0},{"index":1},{"index":2}]}}
        """
        try manifest.write(to: details.appendingPathComponent("chunks_manifest.json"), atomically: true, encoding: .utf8)
        try "{}".write(to: chunks.appendingPathComponent("chunk_0000.json"), atomically: true, encoding: .utf8)
        try "{}".write(to: chunks.appendingPathComponent("chunk_0001.json"), atomically: true, encoding: .utf8)

        let snapshot = OutputWatcher.snapshot(outputDirectory: output)

        XCTAssertEqual(snapshot.runStatus, "running")
        XCTAssertEqual(snapshot.chunkProgress, "2/3")
        XCTAssertEqual(snapshot.completedChunks, 2)
        XCTAssertEqual(snapshot.totalChunks, 3)
        XCTAssertEqual(snapshot.progressFraction, 2.0 / 3.0, accuracy: 0.001)
    }

    func testSnapshotReportsRunningCloudSummaryFromLock() throws {
        let root = URL(fileURLWithPath: NSTemporaryDirectory())
            .appendingPathComponent(UUID().uuidString)
        let output = root.appendingPathComponent("work")
        let cloud = output.appendingPathComponent("cloud")
        let input = cloud.appendingPathComponent("input")
        try FileManager.default.createDirectory(at: input, withIntermediateDirectories: true)
        try #"{"text_chunks":[{"path":"chunks/chunk_0001.md"}]}"#.write(
            to: input.appendingPathComponent("manifest.json"),
            atomically: true,
            encoding: .utf8
        )
        try "pid=123\n".write(to: cloud.appendingPathComponent("summary.lock"), atomically: true, encoding: .utf8)

        let snapshot = OutputWatcher.snapshot(outputDirectory: output)

        XCTAssertEqual(snapshot.cloudStatus, "running")
        XCTAssertEqual(snapshot.cloudChunkProgress, "0/1")
        XCTAssertEqual(snapshot.cloudProgressFraction, 0.08, accuracy: 0.001)
    }

    func testSnapshotReportsFailedCloudSummaryFromFailedChunksBeforeStaleLock() throws {
        let root = URL(fileURLWithPath: NSTemporaryDirectory())
            .appendingPathComponent(UUID().uuidString)
        let output = root.appendingPathComponent("work")
        let cloud = output.appendingPathComponent("cloud")
        let input = cloud.appendingPathComponent("input")
        let chunks = cloud.appendingPathComponent("chunk_summaries")
        try FileManager.default.createDirectory(at: input, withIntermediateDirectories: true)
        try FileManager.default.createDirectory(at: chunks, withIntermediateDirectories: true)
        try #"{"text_chunks":[{"path":"chunks/chunk_0001.md"},{"path":"chunks/chunk_0002.md"}]}"#.write(
            to: input.appendingPathComponent("manifest.json"),
            atomically: true,
            encoding: .utf8
        )
        try """
        {
          "success": false,
          "retry": {
            "error": "Cloud responses API response has no text content."
          }
        }
        """.write(to: chunks.appendingPathComponent("chunk_0001.summary.json"), atomically: true, encoding: .utf8)
        try "pid=123\n".write(to: cloud.appendingPathComponent("summary.lock"), atomically: true, encoding: .utf8)

        let snapshot = OutputWatcher.snapshot(outputDirectory: output)

        XCTAssertEqual(snapshot.cloudStatus, "failed")
        XCTAssertEqual(snapshot.cloudFailedChunks, 1)
        XCTAssertEqual(snapshot.cloudChunkProgress, "0/2")
        XCTAssertEqual(snapshot.cloudMessage, "Cloud responses API response has no text content.")
        XCTAssertEqual(snapshot.cloudProgressFraction, 0.0, accuracy: 0.001)
    }

    func testSnapshotReadsEventProgressAndDiskUsage() throws {
        let root = URL(fileURLWithPath: NSTemporaryDirectory())
            .appendingPathComponent(UUID().uuidString)
        let output = root.appendingPathComponent("work")
        let details = output
        try FileManager.default.createDirectory(at: details, withIntermediateDirectories: true)
        try #"{"chunk":0,"event":"chunk","status":"transcribed","total_chunks":2}"#.write(
            to: details.appendingPathComponent("events.jsonl"),
            atomically: true,
            encoding: .utf8
        )
        try "abc".write(to: details.appendingPathComponent("transcript.timestamped.md"), atomically: true, encoding: .utf8)

        let snapshot = OutputWatcher.snapshot(outputDirectory: output)

        XCTAssertEqual(snapshot.chunkProgress, "1/2")
        XCTAssertGreaterThan(snapshot.diskUsageBytes, 0)
    }
}
