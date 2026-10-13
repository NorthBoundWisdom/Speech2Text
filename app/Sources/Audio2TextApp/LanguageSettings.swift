import Foundation

struct LanguageOption: Identifiable {
    let id: String
    let title: String

    static let all: [LanguageOption] = [
        .init(id: "zh", title: "Chinese / Mandarin"), .init(id: "en", title: "English"),
        .init(id: "ja", title: "Japanese"), .init(id: "ko", title: "Korean"),
        .init(id: "yue", title: "Cantonese"), .init(id: "de", title: "German"),
        .init(id: "fr", title: "French"), .init(id: "es", title: "Spanish"),
        .init(id: "ru", title: "Russian"), .init(id: "pt", title: "Portuguese"),
        .init(id: "it", title: "Italian"), .init(id: "ar", title: "Arabic"),
        .init(id: "hi", title: "Hindi"), .init(id: "vi", title: "Vietnamese"),
        .init(id: "th", title: "Thai"), .init(id: "id", title: "Indonesian")
    ]

    static func normalize(_ codes: [String]) throws -> [String] {
        let aliases = ["jp": "ja", "cn": "zh", "mandarin": "zh", "chinese": "zh",
                       "japanese": "ja", "english": "en", "korean": "ko", "cantonese": "yue"]
        let normalized = codes.map { code in
            let value = code.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
            return aliases[value] ?? value
        }
        if normalized.contains(where: { ["", "auto", "detect"].contains($0) }) { return [] }
        guard normalized.allSatisfy({ code in all.contains(where: { $0.id == code }) }) else {
            throw AppError.invalidImportOutput("Unsupported language code in settings.")
        }
        return normalized.reduce(into: []) { if !$0.contains($1) { $0.append($1) } }
    }
}
