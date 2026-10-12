// Audio2Text-iOS shared source

import SwiftUI

struct ReadingStyleSettings: Equatable {
    static let `default` = ReadingStyleSettings()

    var textSize: ReadingTextSize = .large
    var lineSpacing: ReadingLineSpacing = .comfortable
    var contentWidth: ReadingContentWidth = .full
    var fontDesign: ReadingFontDesign = .system

    var bodyFont: Font {
        .system(size: textSize.bodyFontSize, weight: .regular, design: fontDesign.swiftUIDesign)
    }

    var bulletFont: Font {
        .system(size: textSize.bodyFontSize, weight: .regular, design: fontDesign.swiftUIDesign)
    }

    var codeFont: Font {
        .system(size: textSize.codeFontSize, weight: .regular, design: .monospaced)
    }

    func headingFont(_ level: Int) -> Font {
        .system(size: textSize.headingFontSize(level), weight: .semibold, design: fontDesign.swiftUIDesign)
    }

    func tableFont(isHeader: Bool) -> Font {
        .system(
            size: isHeader ? textSize.tableHeaderFontSize : textSize.tableBodyFontSize,
            weight: isHeader ? .semibold : .regular,
            design: fontDesign.swiftUIDesign
        )
    }
}

enum ReadingTextSize: String, CaseIterable, Identifiable {
    case small
    case medium
    case large
    case xLarge = "xlarge"
    case xxLarge = "xxlarge"

    var id: String {
        rawValue
    }

    var title: String {
        switch self {
        case .small: return "Small"
        case .medium: return "Medium"
        case .large: return "Large"
        case .xLarge: return "Extra Large"
        case .xxLarge: return "Extra Extra Large"
        }
    }

    var bodyFontSize: CGFloat {
        switch self {
        case .small: return 14
        case .medium: return 16
        case .large: return 18
        case .xLarge: return 21
        case .xxLarge: return 24
        }
    }

    var codeFontSize: CGFloat {
        max(12, bodyFontSize - 1)
    }

    var tableBodyFontSize: CGFloat {
        max(12, bodyFontSize - 1)
    }

    var tableHeaderFontSize: CGFloat {
        bodyFontSize
    }

    func headingFontSize(_ level: Int) -> CGFloat {
        switch level {
        case 1:
            return bodyFontSize + 8
        case 2:
            return bodyFontSize + 5
        case 3:
            return bodyFontSize + 3
        default:
            return bodyFontSize + 1
        }
    }
}

enum ReadingLineSpacing: String, CaseIterable, Identifiable {
    case compact
    case comfortable
    case spacious

    var id: String {
        rawValue
    }

    var title: String {
        switch self {
        case .compact: return "Compact"
        case .comfortable: return "Comfortable"
        case .spacious: return "Spacious"
        }
    }

    var points: CGFloat {
        switch self {
        case .compact: return 2
        case .comfortable: return 5
        case .spacious: return 8
        }
    }

    var blockSpacing: CGFloat {
        switch self {
        case .compact: return 4
        case .comfortable: return 6
        case .spacious: return 8
        }
    }

    var blankSpacing: CGFloat {
        switch self {
        case .compact: return 6
        case .comfortable: return 9
        case .spacious: return 12
        }
    }
}

enum ReadingContentWidth: String, CaseIterable, Identifiable {
    case compact
    case standard
    case wide
    case full

    var id: String {
        rawValue
    }

    var title: String {
        switch self {
        case .compact: return "Compact"
        case .standard: return "Standard"
        case .wide: return "Wide"
        case .full: return "Full"
        }
    }

    var maximumWidth: CGFloat? {
        switch self {
        case .compact: return 680
        case .standard: return 820
        case .wide: return 1040
        case .full: return nil
        }
    }

    func resolvedWidth(for availableWidth: CGFloat) -> CGFloat {
        guard let maximumWidth else {
            return availableWidth
        }
        return min(availableWidth, maximumWidth)
    }
}

enum ReadingFontDesign: String, CaseIterable, Identifiable {
    case system
    case serif
    case rounded

    var id: String {
        rawValue
    }

    var title: String {
        switch self {
        case .system: return "System"
        case .serif: return "Serif"
        case .rounded: return "Rounded"
        }
    }

    var swiftUIDesign: Font.Design {
        switch self {
        case .system: return .default
        case .serif: return .serif
        case .rounded: return .rounded
        }
    }
}
