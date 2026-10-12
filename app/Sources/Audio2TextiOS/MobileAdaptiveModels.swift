import SwiftUI
#if canImport(Audio2TextCore)
    import Audio2TextCore
#endif

struct MobileEpisodeSection: Equatable, Identifiable {
    let title: String
    let episodes: [LibraryEpisode]

    var id: String {
        title
    }
}

enum MobileReaderSection: String, CaseIterable, Identifiable {
    case intro
    case summary
    case transcript

    var id: String {
        rawValue
    }

    var title: String {
        switch self {
        case .intro:
            return "Overview"
        case .summary:
            return "Summary"
        case .transcript:
            return "Transcript"
        }
    }

    var documentName: String? {
        switch self {
        case .intro:
            return nil
        case .summary:
            return "summary.md"
        case .transcript:
            return "transcript.md"
        }
    }
}
