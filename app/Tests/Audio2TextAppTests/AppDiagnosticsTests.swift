@testable import Audio2TextApp
import Audio2TextCore
import XCTest

final class AppDiagnosticsTests: XCTestCase {
    func testDiagnosticsReportsMissingModelButCloudKeyIsOptional() {
        let report = AppDiagnostics.inspect(
            settings: AppSettings(),
            environment: ["PATH": ""]
        )

        XCTAssertFalse(report.blockingIssues.contains { $0.id == "cloud" }, "\(report.items)")
        XCTAssertEqual(report.item("cli")?.title, "Audio2TextCli")
    }
}
