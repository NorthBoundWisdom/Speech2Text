import Foundation
#if canImport(Audio2TextCore)
    import Audio2TextCore
#endif

struct ProcessLibraryMoveResult: Equatable {
    let audioURL: URL
    let outputURL: URL
    let moved: Bool
}

struct ProcessGroupRenameResult: Equatable {
    let groupName: String
    let oldComponents: [String]
    let movedAnyDirectory: Bool
}

struct ProcessGroupDeleteResult: Equatable {
    let groupName: String
    let movedItemCount: Int
    let deleted: Bool
}

struct ProcessLibraryCleanupResult: Equatable {
    let deletedCount: Int
    let freedBytes: Int64
}

enum ProcessLibraryOperations {
    static func moveItem(
        _ item: ProcessLibraryItem,
        toGroup groupName: String,
        dataRoot _: URL
    ) throws -> ProcessLibraryMoveResult {
        let normalizedGroup = ProcessLibrary.pathComponent(forGroupName: groupName)
        guard item.groupName != normalizedGroup else {
            return ProcessLibraryMoveResult(audioURL: item.audioURL, outputURL: item.outputURL, moved: false)
        }
        try ProcessLibrary.updateGroup(normalizedGroup, for: item)
        return ProcessLibraryMoveResult(audioURL: item.audioURL, outputURL: item.outputURL, moved: true)
    }

    static func renameGroup(
        _ oldName: String,
        to newName: String,
        dataRoot: URL
    ) throws -> ProcessGroupRenameResult {
        let newPath = ProcessLibrary.pathComponent(forGroupName: newName)
        let oldPath = ProcessLibrary.pathComponent(forGroupName: oldName)
        guard oldPath != newPath else {
            return ProcessGroupRenameResult(groupName: newPath, oldComponents: [oldPath], movedAnyDirectory: false)
        }
        for item in ProcessLibrary.scan(dataRoot: dataRoot) where item.groupName == oldPath {
            try ProcessLibrary.updateGroup(newPath, for: item)
        }
        try LibraryWriter.renameGroup(oldPath, to: newPath, in: ProcessLibrary.authoritativeLibraryRoot(dataRoot: dataRoot))
        return ProcessGroupRenameResult(
            groupName: newPath,
            oldComponents: [oldPath],
            movedAnyDirectory: true
        )
    }

    static func deleteGroup(
        _ groupName: String,
        dataRoot: URL
    ) throws -> ProcessGroupDeleteResult {
        let normalizedGroup = ProcessLibrary.pathComponent(forGroupName: groupName)
        guard normalizedGroup != ProcessLibrary.defaultGroupName else {
            return ProcessGroupDeleteResult(groupName: normalizedGroup, movedItemCount: 0, deleted: false)
        }
        var movedItemCount = 0
        for item in ProcessLibrary.scan(dataRoot: dataRoot) where item.groupName == normalizedGroup {
            try ProcessLibrary.updateGroup(ProcessLibrary.defaultGroupName, for: item)
            movedItemCount += 1
        }
        try LibraryWriter.deleteGroup(normalizedGroup, in: ProcessLibrary.authoritativeLibraryRoot(dataRoot: dataRoot))
        ProcessLibrary.invalidateIndex(dataRoot: dataRoot)
        return ProcessGroupDeleteResult(groupName: normalizedGroup, movedItemCount: movedItemCount, deleted: true)
    }

    static func archiveItem(_ item: ProcessLibraryItem, dataRoot: URL? = nil) throws {
        try ProcessLibrary.updateArchive(true, for: item, dataRoot: dataRoot)
    }

    static func unarchiveItem(_ item: ProcessLibraryItem, dataRoot: URL? = nil) throws {
        try ProcessLibrary.updateArchive(false, for: item, dataRoot: dataRoot)
    }

    static func deleteItem(_ item: ProcessLibraryItem, dataRoot: URL? = nil) throws {
        try ProcessLibrary.deleteEpisode(item, dataRoot: dataRoot)
    }

    static func cleanupCache(for item: ProcessLibraryItem) throws -> ProcessLibraryCleanupResult {
        let fileManager = FileManager.default
        var deletedCount = 0
        var freedBytes: Int64 = 0

        func deleteFileIfPresent(_ url: URL) throws {
            guard fileManager.fileExists(atPath: url.path) || isSymbolicLink(url) else { return }
            let size = fileSize(url)
            try fileManager.removeItem(at: url)
            deletedCount += 1
            freedBytes += size
        }

        func deleteDirectoryIfPresent(_ url: URL) throws {
            guard fileManager.fileExists(atPath: url.path) else { return }
            let size = directorySize(url)
            try fileManager.removeItem(at: url)
            deletedCount += 1
            freedBytes += size
        }

        try deleteFileIfPresent(item.audioURL)
        try deleteFileIfPresent(item.outputURL.appendingPathComponent("prepared.wav"))
        try deleteDirectoryIfPresent(item.outputURL.appendingPathComponent("chunks"))

        for relativePath in [
            "raw.json",
            "transcript.raw.txt",
        ] {
            try deleteFileIfPresent(item.outputURL.appendingPathComponent(relativePath))
        }

        ProcessLibrary.invalidateIndex()
        return ProcessLibraryCleanupResult(deletedCount: deletedCount, freedBytes: freedBytes)
    }

    private static func isSymbolicLink(_ url: URL) -> Bool {
        guard
            let values = try? url.resourceValues(forKeys: [.isSymbolicLinkKey]),
            values.isSymbolicLink == true
        else {
            return false
        }
        return true
    }

    private static func fileSize(_ url: URL) -> Int64 {
        guard
            let attributes = try? FileManager.default.attributesOfItem(atPath: url.path),
            let size = attributes[.size] as? NSNumber
        else {
            return 0
        }
        return size.int64Value
    }

    private static func directorySize(_ url: URL) -> Int64 {
        let fileManager = FileManager.default
        guard let enumerator = fileManager.enumerator(
            at: url,
            includingPropertiesForKeys: [.fileSizeKey, .isRegularFileKey],
            options: [.skipsHiddenFiles]
        ) else {
            return 0
        }
        var total: Int64 = 0
        for case let fileURL as URL in enumerator {
            let values = try? fileURL.resourceValues(forKeys: [.fileSizeKey, .isRegularFileKey])
            if values?.isRegularFile == true {
                total += Int64(values?.fileSize ?? 0)
            }
        }
        return total
    }
}
