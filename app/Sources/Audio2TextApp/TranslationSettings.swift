import Foundation

enum TranslationBackend: String, CaseIterable, Identifiable {
    case cloud
    case local

    var id: String {
        rawValue
    }
}

struct TranslationSettings: Equatable {
    static let defaultTargetLanguage = "zh"
    static let defaultLocalModelAlias = "nllb-200-distilled-600m"

    var enabled: Bool = false
    var backend: TranslationBackend = .cloud
    var targetLanguage: String = defaultTargetLanguage
    var localModelAlias: String = defaultLocalModelAlias
}

struct LocalASRProfile: Identifiable, Equatable {
    let name: String
    let title: String

    var id: String {
        name
    }

    static let defaultName = "balanced_zh_podcast"
    static let all: [LocalASRProfile] = [
        LocalASRProfile(name: "fast", title: "Fast"),
        LocalASRProfile(name: "balanced_zh_podcast", title: "Balanced"),
        LocalASRProfile(name: "quality_zh_podcast", title: "Quality"),
        LocalASRProfile(name: "repair_strict", title: "Repair"),
    ]
}
