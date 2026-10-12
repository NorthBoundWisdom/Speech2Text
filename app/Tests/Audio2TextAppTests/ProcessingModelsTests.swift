@testable import Audio2TextApp
import XCTest

final class ProcessingModelsTests: XCTestCase {
    func testProcessingWorkflowTitlesReflectCloudConfiguration() {
        XCTAssertEqual(
            ProcessingWorkflow.transcribeAndSummarize.actionTitle(isCloudConfigured: true),
            "Transcribe and summarize"
        )
        XCTAssertEqual(
            ProcessingWorkflow.transcribeAndSummarize.actionTitle(isCloudConfigured: false),
            "Transcribe and summarize (not configured)"
        )
        XCTAssertEqual(
            ProcessingWorkflow.transcribeAndSummarize.actionTitle(reprocess: true, isCloudConfigured: true),
            "Retranscribe and summarize"
        )
        XCTAssertEqual(
            ProcessingWorkflow.transcribeAndSummarize.actionTitle(reprocess: true, isCloudConfigured: false),
            "Retranscribe and summarize (not configured)"
        )
        XCTAssertEqual(ProcessingWorkflow.localOnly.actionTitle(), "Transcribe locally only")
        XCTAssertEqual(ProcessingWorkflow.localOnly.actionTitle(reprocess: true), "Retranscribe locally only")
    }
}
