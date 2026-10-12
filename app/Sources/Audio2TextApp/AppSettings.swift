import Foundation

struct AppSettings: Equatable {
    var configurationError: String = ""
    static let defaultSummaryPrompt = """
    请只基于输入的中文播客转写稿生成结构化 Markdown 总结，不要补充外部事实。
    第一行必须是“# <具体中文总结标题>”，标题要基于本期内容生成；不要写成“播客结构化总结”、“中文播客摘要”、“Summary”或目录名如 work。
    请覆盖：主要内容、核心观点、关键要点、重要名词（较生僻的请给出解释）、结论、金句提炼。
    直接输出最终 Markdown，不要输出思考过程。
    """
    static let defaultTitlePrompt = """
    请只基于输入的中文播客摘要生成一个适合列表显示的中文短标题，不要补充外部事实。
    必须输出成“主要嘉宾：一句话观点”格式；如果没有明确单一嘉宾，才允许输出成“主题：一句话观点”格式。
    风格要像播客标题，而不是章节名、关键词列表或抽象名词堆砌。
    正例：罗永浩：情绪稳定很重要
    正例：郑植：创作要走现实路
    反例：情绪稳定与表达
    反例：郑植创作现实路
    反例：AI 时代的表达
    要求：
    1. 标题里必须有一个明确的人名或主题短语放在冒号前。
    2. 冒号后必须是一个完整观点、判断、态度或冲突，不要只写名词。
    3. 尽量点明本期最有记忆点的一句话观点，而不是泛泛概括。
    4. 控制在10到20个汉字。
    5. 使用中文冒号“：”。
    6. 不要使用书名号、引号、括号、序号、解释文字。
    直接只输出标题本身。
    """

    var localASRModel: String = LocalASRModel.defaultAlias
    var localASRProfile: String = LocalASRProfile.defaultName
    var apiBase: String = CloudConfigFile.defaultBaseURL
    var cloudModel: String = CloudConfigFile.defaultModel
    var summaryPrompt: String = AppSettings.defaultSummaryPrompt
    var titlePrompt: String = AppSettings.defaultTitlePrompt
    var apiKey: String = ""
    var cloudTimeout: String = CloudConfigFile.defaultCloudTimeout
    var cloudTemperature: String = CloudConfigFile.defaultCloudTemperature
    var cloudMaxTokens: String = CloudConfigFile.defaultCloudMaxTokens
    var cloudModelOptions: [String] = CloudConfigFile.defaultModelOptions
    var translation: TranslationSettings = .init()
    var workflowDefaultCloudSummary: Bool = false
    var workflowLocalOnly: Bool = false
    var workflowChunking: String = "auto"
    var workflowChunkLength: String = "1200"
    var workflowOverlap: String = "10"
    var libraryStorage: String = "icloud"
    var libraryICloudRoot: String = ""
    var libraryLocalRoot: String = ""
    var readingStyle: ReadingStyleSettings = .default
    var hideReadItems: Bool = false

    var isCloudConfigured: Bool {
        !apiBase.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
            && !apiKey.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
    }

    var resolvedLibraryRoot: URL {
        AppPaths.libraryRoot(storage: libraryStorage, iCloudRoot: libraryICloudRoot, localRoot: libraryLocalRoot)
    }
}
