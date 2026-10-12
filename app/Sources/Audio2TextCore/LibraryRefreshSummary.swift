import Foundation

public struct LibraryRefreshError: Equatable {
    public let title: String
    public let message: String

    public init(title: String, message: String) {
        self.title = title
        self.message = message
    }
}

public struct LibraryRefreshSummary: Equatable {
    public private(set) var refreshedSubscriptionCount: Int
    public private(set) var failedSubscriptionCount: Int
    public private(set) var writtenEpisodeCount: Int
    public private(set) var reusedMetadataEpisodeCount: Int
    public private(set) var skippedAvailableEpisodeCount: Int
    public private(set) var tombstoneSkippedEpisodeCount: Int
    public private(set) var errors: [LibraryRefreshError]

    public init(
        refreshedSubscriptionCount: Int = 0,
        failedSubscriptionCount: Int = 0,
        writtenEpisodeCount: Int = 0,
        reusedMetadataEpisodeCount: Int = 0,
        skippedAvailableEpisodeCount: Int = 0,
        tombstoneSkippedEpisodeCount: Int = 0,
        errors: [LibraryRefreshError] = []
    ) {
        self.refreshedSubscriptionCount = refreshedSubscriptionCount
        self.failedSubscriptionCount = failedSubscriptionCount
        self.writtenEpisodeCount = writtenEpisodeCount
        self.reusedMetadataEpisodeCount = reusedMetadataEpisodeCount
        self.skippedAvailableEpisodeCount = skippedAvailableEpisodeCount
        self.tombstoneSkippedEpisodeCount = tombstoneSkippedEpisodeCount
        self.errors = errors
    }

    public mutating func recordSuccess(_ result: LibraryWriteResult) {
        refreshedSubscriptionCount += 1
        writtenEpisodeCount += result.writtenEpisodeCount
        reusedMetadataEpisodeCount += result.reusedMetadataEpisodeCount
        skippedAvailableEpisodeCount += result.skippedAvailableEpisodeCount
        tombstoneSkippedEpisodeCount += result.tombstoneSkippedEpisodeCount
    }

    public mutating func recordFailure(title: String, message: String) {
        failedSubscriptionCount += 1
        errors.append(LibraryRefreshError(title: title, message: message))
    }

    public var metadataCountText: String {
        "\(writtenEpisodeCount) new, \(reusedMetadataEpisodeCount) refreshed, \(skippedAvailableEpisodeCount) processed kept, \(tombstoneSkippedEpisodeCount) deleted skipped"
    }

    public var refreshAllStatusText: String {
        let refreshed = "Refreshed \(refreshedSubscriptionCount) subscription\(refreshedSubscriptionCount == 1 ? "" : "s"): \(metadataCountText)."
        guard failedSubscriptionCount > 0 else {
            return refreshed
        }
        let failureDetails = errors
            .map { "\($0.title): \($0.message)" }
            .joined(separator: "; ")
        return "\(refreshed) Failed \(failedSubscriptionCount) subscription\(failedSubscriptionCount == 1 ? "" : "s"): \(failureDetails)"
    }
}
