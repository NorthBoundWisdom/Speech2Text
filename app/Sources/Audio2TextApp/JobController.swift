import Foundation
#if canImport(Audio2TextCore)
    import Audio2TextCore
#endif

@MainActor
final class JobController: ObservableObject {
    @Published var inputMode: InputMode = .xiaoyuzhou
    @Published var urlText: String = "" {
        didSet {
            if oldValue != urlText {
                linkCheckStatus = .idle
            }
        }
    }

    @Published var selectedFile: URL?
    @Published var localImportMode: LocalImportMode = .copy
    @Published var linkCheckStatus: LinkCheckStatus = .idle
    @Published var stage: JobStage = .idle
    @Published var message: String = ""
    @Published var logText: String = ""
    @Published var metadataText: String = "No metadata is available."
    @Published var snapshot = OutputSnapshot()
    @Published var selectedTab: ContentTab = .metadata
    @Published var progressFraction: Double = 0.0 {
        didSet {
            updateBatchProgressFromCurrentItem()
        }
    }

    @Published var persistentLogPath: String = ""
    @Published var libraryItems: [ProcessLibraryItem] = [] {
        didSet { markLibrarySidebarDerivedStateDirty() }
    }

    @Published var librarySections: [ProcessLibrarySection] = [] {
        didSet { markLibrarySidebarDerivedStateDirty() }
    }

    @Published var subscriptions: [PodcastSubscriptionItem] = [] {
        didSet { markLibrarySidebarDerivedStateDirty() }
    }

    @Published var subscriptionURLText: String = ""
    @Published var subscriptionGroupName: String = ProcessLibrary.defaultGroupName
    @Published var isAddingSubscription = false
    @Published var isRefreshingSubscriptions = false
    @Published var subscriptionRefreshTaskStatus: ProcessingTaskStatus?
    @Published var selectedLibraryItemID: String?
    @Published var selectedSubscriptionID: String?
    @Published var selectedGroupName: String = ProcessLibrary.defaultGroupName
    @Published var selectedSidebarSource: SidebarSource = .library {
        didSet { markLibrarySidebarDerivedStateDirty() }
    }

    @Published var unprocessedQueueFilter: AppQueueStatus? {
        didSet { markLibrarySidebarDerivedStateDirty() }
    }

    @Published var hidesReadLibraryItems = false {
        didSet { markLibrarySidebarDerivedStateDirty() }
    }

    @Published var batchProgress: BatchProcessingProgress?
    @Published var isBatchStopRequested = false
    @Published var summaryRequestStatus: SummaryRequestStatus?
    @Published var processingTaskStatus: ProcessingTaskStatus?
    @Published var cloudProcessingTaskStatus: ProcessingTaskStatus?
    @Published var processingReport: ProcessingReport?
    @Published var isRefreshingLibrary = false
    @Published var libraryRefreshMessage = ""
    @Published var librarySyncStatus = LibrarySyncStatus.unavailable()

    let runner: any ProcessRunning
    let logStore = LogStore()
    let settingsStore: AppSettingsStore
    let runtimeProvider: () throws -> RuntimeContext
    let cloudPrepareChunkMinutes = "30"
    var currentTask: Task<Void, Never>?
    var watcherTask: Task<Void, Never>?
    var libraryLoadTask: Task<Void, Never>?
    var libraryLoadGeneration = 0
    var activeBatchTotal = 0
    var activeBatchCompleted = 0
    var activeBatchCurrentTitle = ""
    var activeBatchTaskKind: ProcessingTaskKind?
    var summaryRequestStatusClearTask: Task<Void, Never>?
    var summaryRequestStatusGeneration = 0
    var subscriptionRefreshStatusClearTask: Task<Void, Never>?
    var subscriptionRefreshStatusGeneration = 0
    var pendingSummarySaveURL: URL?
    var pendingSummarySaveText: String?
    var summarySaveTask: Task<Void, Never>?
    var localLibraryMutationSyncingUntil: Date?
    var localLibraryMutationSyncDetail = "本地资料修改正在同步。"
    var librarySidebarDerivedStateIsDirty = true
    var cachedLibrarySidebarState = LibrarySidebarState(items: [])
    var cachedVisibleLibraryItems: [ProcessLibraryItem] = []
    var cachedSubscriptionDetailSnapshots: [String: SubscriptionDetailSnapshot] = [:]
    var cachedSubscriptionDetailSnapshotVersion = 0
    lazy var backgroundSummaryQueue = BackgroundSummaryQueue(
        runner: { [weak self] job, outputHandler in
            guard let self else { return }
            try await self.runBackgroundSummaryCommand(job, onOutput: outputHandler)
        },
        eventHandler: { [weak self] event in
            self?.handleBackgroundSummaryQueueEvent(event)
        }
    )

    init(
        settingsStore: AppSettingsStore = .live(),
        runner: any ProcessRunning = ProcessRunner(),
        runtimeProvider: @escaping () throws -> RuntimeContext = { try RuntimeManager.context() },
        loadsLibrarySynchronously: Bool = false
    ) {
        self.settingsStore = settingsStore
        self.runner = runner
        self.runtimeProvider = runtimeProvider
        hidesReadLibraryItems = settingsStore.load(includeAPIKey: false).hideReadItems
        if loadsLibrarySynchronously {
            loadLibrarySynchronously()
        } else {
            refreshLibraryInBackground()
        }
    }

    deinit {
        currentTask?.cancel()
        watcherTask?.cancel()
        libraryLoadTask?.cancel()
        summaryRequestStatusClearTask?.cancel()
        subscriptionRefreshStatusClearTask?.cancel()
        summarySaveTask?.cancel()
    }
}
