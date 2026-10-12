import Foundation
import Security

public protocol CloudCredentialStore {
    func load(account: String) throws -> String?
    func save(_ value: String, account: String) throws
}

public struct KeychainCloudCredentialStore: CloudCredentialStore {
    public static let service = "org.audio2text.cloud"
    public init() {}

    private func query(_ account: String) -> [String: Any] {
        [kSecClass as String: kSecClassGenericPassword,
         kSecAttrService as String: Self.service,
         kSecAttrAccount as String: account]
    }

    public func load(account: String) throws -> String? {
        var request = query(account)
        request[kSecReturnData as String] = true
        request[kSecMatchLimit as String] = kSecMatchLimitOne
        var result: CFTypeRef?
        let status = SecItemCopyMatching(request as CFDictionary, &result)
        if status == errSecItemNotFound { return nil }
        guard status == errSecSuccess, let data = result as? Data,
              let value = String(data: data, encoding: .utf8) else {
            throw CredentialStorageError(status: status)
        }
        return value
    }

    public func save(_ value: String, account: String) throws {
        let request = query(account)
        if value.isEmpty {
            let status = SecItemDelete(request as CFDictionary)
            guard status == errSecSuccess || status == errSecItemNotFound else {
                throw CredentialStorageError(status: status)
            }
            return
        }
        let attributes = [kSecValueData as String: Data(value.utf8)]
        let status = SecItemUpdate(request as CFDictionary, attributes as CFDictionary)
        if status == errSecItemNotFound {
            var item = request.merging(attributes) { _, new in new }
            #if os(iOS)
                item[kSecAttrAccessible as String] = kSecAttrAccessibleWhenUnlockedThisDeviceOnly
            #endif
            let added = SecItemAdd(item as CFDictionary, nil)
            guard added == errSecSuccess else { throw CredentialStorageError(status: added) }
        } else if status != errSecSuccess {
            throw CredentialStorageError(status: status)
        }
    }
}

public struct CredentialStorageError: LocalizedError {
    public let status: OSStatus
    public init(status: OSStatus) { self.status = status }
    public var errorDescription: String? {
        "Cloud credential storage failed (Keychain status \(status)). Unlock Keychain and retry."
    }
}
