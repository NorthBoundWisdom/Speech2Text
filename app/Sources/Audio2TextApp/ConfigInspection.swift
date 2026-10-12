import Foundation

struct ConfigInspectionPayload: Decodable, Equatable {
    var path: String
    var effective: [String: [String: JSONValue]]
    var layers: ConfigInspectionLayers
    var entries: [ConfigInspectionEntry]
}

struct ConfigInspectionLayers: Decodable, Equatable {
    var builtInDefaults: ConfigInspectionLayer
    var userConfig: ConfigInspectionLayer

    enum CodingKeys: String, CodingKey {
        case builtInDefaults = "built_in_defaults"
        case userConfig = "user_config"
    }
}

struct ConfigInspectionLayer: Decodable, Equatable {
    var name: String
    var enabled: Bool
    var description: String
    var path: String?
    var keys: [String]?
}

struct ConfigInspectionEntry: Decodable, Equatable, Identifiable {
    var key: String
    var value: JSONValue
    var redacted: Bool
    var source: String
    var rawKey: String
    var editable: Bool
    var isDefault: Bool

    var id: String {
        key
    }

    enum CodingKeys: String, CodingKey {
        case key
        case value
        case redacted
        case source
        case rawKey = "raw_key"
        case editable
        case isDefault = "is_default"
    }
}

enum JSONValue: Decodable, Equatable {
    case null
    case bool(Bool)
    case number(Double)
    case string(String)
    case array([JSONValue])
    case object([String: JSONValue])

    init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        if container.decodeNil() {
            self = .null
        } else if let value = try? container.decode(Bool.self) {
            self = .bool(value)
        } else if let value = try? container.decode(Double.self) {
            self = .number(value)
        } else if let value = try? container.decode(String.self) {
            self = .string(value)
        } else if let value = try? container.decode([JSONValue].self) {
            self = .array(value)
        } else {
            self = try .object(container.decode([String: JSONValue].self))
        }
    }

    var displayString: String {
        switch self {
        case .null:
            return "null"
        case let .bool(value):
            return value ? "true" : "false"
        case let .number(value):
            return value.rounded() == value ? String(Int(value)) : String(value)
        case let .string(value):
            return value.isEmpty ? "\"\"" : value
        case let .array(values):
            return values.map(\.displayString).joined(separator: ", ")
        case let .object(values):
            return values.keys.sorted().joined(separator: ", ")
        }
    }
}
