@testable import Audio2TextApp
import XCTest

final class ProcessingModelsTests: XCTestCase {
    func testProcessingWorkflowTitlesReflectCloudConfiguration() {
        XCTAssertEqual(
            ProcessingWorkflow.transcribeAndSummarize.actionTitle(isCloudConfigured: true),
            "转写并总结"
        )
        XCTAssertEqual(
            ProcessingWorkflow.transcribeAndSummarize.actionTitle(isCloudConfigured: false),
            "转写并总结（未配置）"
        )
        XCTAssertEqual(
            ProcessingWorkflow.transcribeAndSummarize.actionTitle(reprocess: true, isCloudConfigured: true),
            "重新转写并总结"
        )
        XCTAssertEqual(
            ProcessingWorkflow.transcribeAndSummarize.actionTitle(reprocess: true, isCloudConfigured: false),
            "重新转写并总结（未配置）"
        )
        XCTAssertEqual(ProcessingWorkflow.localOnly.actionTitle(), "仅本地转写")
        XCTAssertEqual(ProcessingWorkflow.localOnly.actionTitle(reprocess: true), "仅重新本地转写")
    }
}
