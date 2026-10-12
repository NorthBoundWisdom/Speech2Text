import Foundation

struct BatchLocalProcessingOutcome {
    let succeeded: Bool
    let shouldQueueSummary: Bool
    let reason: String
    let taskState: ProcessingTaskState
}
