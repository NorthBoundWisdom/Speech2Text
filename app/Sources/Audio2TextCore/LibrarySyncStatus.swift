import Foundation

public struct LibrarySyncStatus: Equatable {
    public enum State: Equatable {
        case syncing
        case offline
        case synced
    }

    public let state: State
    public let title: String
    public let detail: String
    public let checkedAt: Date
    public let scannedFileCount: Int
    public let pendingFileCount: Int
    public let errorFileCount: Int
    public let progress: Double?

    public init(
        state: State,
        title: String,
        detail: String,
        checkedAt: Date = Date(),
        scannedFileCount: Int = 0,
        pendingFileCount: Int = 0,
        errorFileCount: Int = 0,
        progress: Double? = nil
    ) {
        self.state = state
        self.title = title
        self.detail = detail
        self.checkedAt = checkedAt
        self.scannedFileCount = scannedFileCount
        self.pendingFileCount = pendingFileCount
        self.errorFileCount = errorFileCount
        self.progress = progress
    }

    public static func unavailable(_ detail: String = "无法访问同步库，请检查网络或 iCloud Drive。") -> LibrarySyncStatus {
        LibrarySyncStatus(state: .offline, title: "网络断开", detail: detail)
    }

    public static func syncing(
        _ detail: String = "资料正在同步。",
        checkedAt: Date = Date(),
        scannedFileCount: Int = 0,
        pendingFileCount: Int = 0,
        errorFileCount: Int = 0,
        progress: Double? = nil
    ) -> LibrarySyncStatus {
        LibrarySyncStatus(
            state: .syncing,
            title: "同步中",
            detail: detail,
            checkedAt: checkedAt,
            scannedFileCount: scannedFileCount,
            pendingFileCount: pendingFileCount,
            errorFileCount: errorFileCount,
            progress: progress
        )
    }
}

public enum LibrarySyncStatusProbe {
    public static func status(for libraryRoot: URL, fileManager: FileManager = .default) -> LibrarySyncStatus {
        status(for: libraryRoot, fileManager: fileManager, resourceValues: resourceValues(for:))
    }

    static func status(
        for libraryRoot: URL,
        fileManager: FileManager = .default,
        resourceValues: (URL) -> LibrarySyncResourceValues
    ) -> LibrarySyncStatus {
        var isDirectory: ObjCBool = false
        guard fileManager.fileExists(atPath: libraryRoot.path, isDirectory: &isDirectory), isDirectory.boolValue else {
            return .unavailable("无法访问同步库，请检查网络或 iCloud Drive。")
        }

        let checkedAt = Date()
        let files = syncCandidateFiles(in: libraryRoot, fileManager: fileManager)
        let urls = [libraryRoot] + files
        var sawCloudItem = false
        var sawUnknownCloudValue = false
        var pending: [String] = []
        var failures: [String] = []

        for url in urls {
            let values = resourceValues(url)
            if values.isCloudBacked == true {
                sawCloudItem = true
            } else if values.isCloudBacked == nil {
                sawUnknownCloudValue = true
            }
            if let error = values.uploadingError {
                failures.append("\(url.lastPathComponent): \(error.localizedDescription)")
            }
            if values.isUploading == true || values.isUploaded == false {
                pending.append(url.lastPathComponent)
            }
        }

        let cloudBacked = sawCloudItem || looksLikeICloudPath(libraryRoot)
        if !cloudBacked {
            return LibrarySyncStatus(
                state: .synced,
                title: "同步成功",
                detail: "当前资料已可用。",
                checkedAt: checkedAt,
                scannedFileCount: files.count,
                progress: 1
            )
        }
        if !pending.isEmpty {
            return .syncing(
                "\(pending.count) 个资料文件正在同步。",
                checkedAt: checkedAt,
                scannedFileCount: files.count,
                pendingFileCount: pending.count,
                errorFileCount: failures.count
            )
        }
        if !failures.isEmpty {
            return LibrarySyncStatus(
                state: .offline,
                title: "网络断开",
                detail: "同步暂时不可用，请检查网络或 iCloud Drive。",
                checkedAt: checkedAt,
                scannedFileCount: files.count,
                pendingFileCount: pending.count,
                errorFileCount: failures.count
            )
        }
        if sawUnknownCloudValue && files.isEmpty {
            return LibrarySyncStatus(
                state: .synced,
                title: "同步成功",
                detail: "暂无需要同步的资料。",
                checkedAt: checkedAt
            )
        }
        return LibrarySyncStatus(
            state: .synced,
            title: "同步成功",
            detail: "资料已同步完成。",
            checkedAt: checkedAt,
            scannedFileCount: files.count,
            progress: 1
        )
    }

    private static func syncCandidateFiles(in libraryRoot: URL, fileManager: FileManager) -> [URL] {
        guard let enumerator = fileManager.enumerator(
            at: libraryRoot,
            includingPropertiesForKeys: [.isRegularFileKey, .isDirectoryKey],
            options: [.skipsHiddenFiles]
        ) else {
            return []
        }
        var urls: [URL] = []
        for case let url as URL in enumerator {
            guard isPublicLibraryFile(url) else { continue }
            let values = try? url.resourceValues(forKeys: [.isRegularFileKey])
            if values?.isRegularFile == true {
                urls.append(url)
            }
        }
        return urls.sorted { $0.path.localizedStandardCompare($1.path) == .orderedAscending }
    }

    private static func isPublicLibraryFile(_ url: URL) -> Bool {
        switch url.pathExtension.lowercased() {
        case "json", "md":
            return true
        default:
            return false
        }
    }

    private static func resourceValues(for url: URL) -> LibrarySyncResourceValues {
        let keys: Set<URLResourceKey> = [
            .isUbiquitousItemKey,
            .ubiquitousItemIsUploadingKey,
            .ubiquitousItemIsUploadedKey,
            .ubiquitousItemUploadingErrorKey,
        ]
        guard let values = try? url.resourceValues(forKeys: keys) else {
            return LibrarySyncResourceValues()
        }
        return LibrarySyncResourceValues(
            isCloudBacked: values.isUbiquitousItem,
            isUploading: values.ubiquitousItemIsUploading,
            isUploaded: values.ubiquitousItemIsUploaded,
            uploadingError: values.ubiquitousItemUploadingError
        )
    }

    private static func looksLikeICloudPath(_ url: URL) -> Bool {
        let path = url.standardizedFileURL.path
        return path.contains("/Mobile Documents/") || path.contains("com~apple~CloudDocs")
    }
}

struct LibrarySyncResourceValues {
    var isCloudBacked: Bool?
    var isUploading: Bool?
    var isUploaded: Bool?
    var uploadingError: Error?
}
