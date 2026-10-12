import Foundation
#if canImport(Audio2TextCore)
    import Audio2TextCore
#endif

enum AppError: LocalizedError, Equatable {
    case cliNotFound(URL)
    case bundledRuntimeNotFound
    case runtimeInstallFailed(String)
    case missingURL
    case unsupportedURL(String)
    case missingLocalFile
    case processFailed(command: String, code: Int32, output: String)
    case invalidImportOutput(String)
    case fileCopyFailed(String)
    case missingCloudAPIKey
    case cloudConnectionFailed(Int, String)
    case cloudSummaryFailed(String)
    case cloudTitleFailed(String)

    var errorDescription: String? {
        switch self {
        case let .cliNotFound(url):
            return "Missing CLI executable: \(url.path)"
        case .bundledRuntimeNotFound:
            return "Audio2Text runtime package is missing from the app bundle."
        case let .runtimeInstallFailed(output):
            return "Could not install Audio2Text runtime:\n\(output)"
        case .missingURL:
            return "Enter a Xiaoyuzhou episode URL."
        case let .unsupportedURL(value):
            return "Only Xiaoyuzhou episode URLs are supported in URL mode: \(value)"
        case .missingLocalFile:
            return "Choose a local audio file."
        case let .processFailed(command, code, output):
            return "Command failed (\(code)): \(command)\n\(output)"
        case let .invalidImportOutput(output):
            return "Could not parse import output:\n\(output)"
        case let .fileCopyFailed(message):
            return message
        case .missingCloudAPIKey:
            return "缺少云服务 API Key。请在系统菜单 Settings 中配置 Cloud Model 的 API Key 并保存。"
        case let .cloudConnectionFailed(status, body):
            return "Cloud API returned HTTP \(status): \(body.prefix(300))"
        case let .cloudSummaryFailed(message):
            return "云总结生成失败：\(message)"
        case let .cloudTitleFailed(message):
            return "云标题生成失败：\(message)"
        }
    }
}

enum InputMode: String, CaseIterable, Identifiable {
    case xiaoyuzhou
    case localFile

    var id: String {
        rawValue
    }

    var title: String {
        switch self {
        case .xiaoyuzhou: return "链接模式"
        case .localFile: return "选择文件"
        }
    }
}

enum JobStage: String {
    case idle
    case importing
    case copying
    case transcribing
    case qa
    case summarizing
    case refreshing
    case completed
    case failed

    var title: String {
        switch self {
        case .idle: return "Idle"
        case .importing: return "Importing"
        case .copying: return "Copying"
        case .transcribing: return "Transcribing"
        case .qa: return "QA"
        case .summarizing: return "Summarizing"
        case .refreshing: return "Refreshing"
        case .completed: return "Completed"
        case .failed: return "Failed"
        }
    }

    var isRunning: Bool {
        switch self {
        case .importing, .copying, .transcribing, .qa, .summarizing, .refreshing:
            return true
        case .idle, .completed, .failed:
            return false
        }
    }
}

enum ContentTab: String, CaseIterable, Identifiable {
    case metadata
    case transcript
    case summary
    case repair
    case glossary
    case log

    var id: String {
        rawValue
    }

    static let displayOrder: [ContentTab] = [.metadata, .summary, .transcript]
    static let unprocessedDisplayOrder: [ContentTab] = [.metadata]

    var title: String {
        switch self {
        case .metadata: return "简介"
        case .transcript: return "转写"
        case .summary: return "摘要"
        case .repair: return "Repair"
        case .glossary: return "Glossary"
        case .log: return "Log"
        }
    }
}

typealias SidebarSmartFeed = LibrarySidebarSmartFeed
typealias SidebarSource = LibrarySidebarSource

enum PathTools {
    static func sanitizedSlug(_ value: String, maxLength: Int = 80) -> String {
        let trimmed = value.trimmingCharacters(in: .whitespacesAndNewlines)
        let scalars = trimmed.unicodeScalars.map { scalar -> Character in
            if CharacterSet.alphanumerics.contains(scalar) || isCJK(scalar) {
                return Character(scalar)
            }
            return "-"
        }
        let collapsed = String(scalars)
            .replacingOccurrences(of: "-+", with: "-", options: .regularExpression)
            .trimmingCharacters(in: CharacterSet(charactersIn: "-. "))
        let fallback = collapsed.isEmpty ? "audio" : collapsed
        return String(fallback.prefix(maxLength))
    }

    private static func isCJK(_ scalar: UnicodeScalar) -> Bool {
        (0x3400 ... 0x4DBF).contains(Int(scalar.value))
            || (0x4E00 ... 0x9FFF).contains(Int(scalar.value))
    }

    static func dateFolder(for date: Date, calendar: Calendar = .current) -> String {
        let components = calendar.dateComponents([.month, .day], from: date)
        let month = components.month ?? 1
        let day = components.day ?? 1
        return String(format: "%02d%02d", month, day)
    }
}
