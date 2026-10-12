import Foundation
#if canImport(Audio2TextCore)
    import Audio2TextCore
#endif

struct XiaoyuzhouImportPayload: Decodable {
    let episodeDir: String
    let audioPath: String
    let audioURL: String?
    let title: String
    let downloaded: Bool?
    let reusedExisting: Bool?

    enum CodingKeys: String, CodingKey {
        case episodeDir = "episode_dir"
        case audioPath = "audio_path"
        case audioURL = "audio_url"
        case title
        case downloaded
        case reusedExisting = "reused_existing"
    }
}

enum LinkCheckStatus: Equatable {
    case idle
    case checking
    case valid(url: String, title: String)
    case invalid(String)
}
