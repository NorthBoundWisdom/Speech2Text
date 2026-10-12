import Foundation
import Audio2TextCore

final class MemoryCloudCredentials: CloudCredentialStore {
    var values: [String: String] = [:]
    var fails = false
    func load(account: String) throws -> String? {
        if fails { throw CredentialStorageError(status: -1) }
        return values[account]
    }
    func save(_ value: String, account: String) throws {
        if fails { throw CredentialStorageError(status: -1) }
        values[account] = value.isEmpty ? nil : value
    }
}
