import Darwin
import Foundation

@_silgen_name("flock")
private func systemFlock(_ fileDescriptor: CInt, _ operation: CInt) -> CInt

enum ApplicationInstanceLockError: LocalizedError {
    case cannotCreateLockDirectory(URL, underlying: Error)
    case cannotOpenLockFile(URL, errnoCode: Int32)
    case cannotWriteOwnerPID(URL, errnoCode: Int32)
    case cannotTruncateLockFile(URL, errnoCode: Int32)
    case cannotLock(URL, errnoCode: Int32)

    var errorDescription: String? {
        switch self {
        case let .cannotCreateLockDirectory(url, underlying):
            return "Cannot create application instance lock directory at \(url.path): \(underlying.localizedDescription)"
        case let .cannotOpenLockFile(url, errnoCode):
            return "Cannot open application instance lock at \(url.path): \(String(cString: strerror(errnoCode)))"
        case let .cannotWriteOwnerPID(url, errnoCode):
            return "Cannot write application instance owner PID to \(url.path): \(String(cString: strerror(errnoCode)))"
        case let .cannotTruncateLockFile(url, errnoCode):
            return "Cannot truncate application instance lock at \(url.path): \(String(cString: strerror(errnoCode)))"
        case let .cannotLock(url, errnoCode):
            return "Cannot acquire application instance lock at \(url.path): \(String(cString: strerror(errnoCode)))"
        }
    }
}

final class ApplicationInstanceLock {
    let lockFileURL: URL
    private let fileDescriptor: CInt

    private init(lockFileURL: URL, fileDescriptor: CInt) {
        self.lockFileURL = lockFileURL
        self.fileDescriptor = fileDescriptor
    }

    deinit {
        _ = systemFlock(fileDescriptor, LOCK_UN)
        Darwin.close(fileDescriptor)
    }

    static func acquire(dataRoot: URL = AppPaths.dataRoot(), processID: Int32 = getpid()) throws -> ApplicationInstanceLock? {
        let lockDirectoryURL = AppPaths.cacheRoot(dataRoot: dataRoot)
            .appendingPathComponent("locks", isDirectory: true)
            .standardizedFileURL
        let lockFileURL = lockDirectoryURL
            .appendingPathComponent("application-instance.lock", isDirectory: false)
            .standardizedFileURL
        do {
            try FileManager.default.createDirectory(
                at: lockDirectoryURL,
                withIntermediateDirectories: true
            )
        } catch {
            throw ApplicationInstanceLockError.cannotCreateLockDirectory(lockDirectoryURL, underlying: error)
        }

        let fileDescriptor = Darwin.open(lockFileURL.path, O_CREAT | O_RDWR, S_IRUSR | S_IWUSR)
        guard fileDescriptor >= 0 else {
            throw ApplicationInstanceLockError.cannotOpenLockFile(lockFileURL, errnoCode: errno)
        }

        let lockResult = systemFlock(fileDescriptor, LOCK_EX | LOCK_NB)
        guard lockResult == 0 else {
            let errnoCode = errno
            Darwin.close(fileDescriptor)
            if errnoCode == EWOULDBLOCK || errnoCode == EAGAIN {
                return nil
            }
            throw ApplicationInstanceLockError.cannotLock(lockFileURL, errnoCode: errnoCode)
        }

        do {
            try writeOwnerPID(processID, to: fileDescriptor, lockFileURL: lockFileURL)
        } catch {
            _ = systemFlock(fileDescriptor, LOCK_UN)
            Darwin.close(fileDescriptor)
            throw error
        }

        return ApplicationInstanceLock(lockFileURL: lockFileURL, fileDescriptor: fileDescriptor)
    }

    private static func writeOwnerPID(
        _ processID: Int32,
        to fileDescriptor: CInt,
        lockFileURL: URL
    ) throws {
        guard Darwin.ftruncate(fileDescriptor, 0) == 0 else {
            throw ApplicationInstanceLockError.cannotTruncateLockFile(lockFileURL, errnoCode: errno)
        }
        guard Darwin.lseek(fileDescriptor, 0, SEEK_SET) >= 0 else {
            throw ApplicationInstanceLockError.cannotWriteOwnerPID(lockFileURL, errnoCode: errno)
        }

        let data = Data("\(processID)\n".utf8)
        try data.withUnsafeBytes { rawBuffer in
            guard let baseAddress = rawBuffer.baseAddress else {
                return
            }
            var bytesWritten = 0
            while bytesWritten < data.count {
                let result = Darwin.write(
                    fileDescriptor,
                    baseAddress.advanced(by: bytesWritten),
                    data.count - bytesWritten
                )
                guard result > 0 else {
                    throw ApplicationInstanceLockError.cannotWriteOwnerPID(lockFileURL, errnoCode: errno)
                }
                bytesWritten += result
            }
        }
    }
}
