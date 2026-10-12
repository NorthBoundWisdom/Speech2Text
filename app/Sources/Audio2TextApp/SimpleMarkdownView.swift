// Audio2Text-iOS shared source

import SwiftUI

struct MarkdownBlock: Identifiable, Equatable {
    enum Kind: Equatable {
        case heading(Int)
        case paragraph
        case bullet
        case code
        case table(MarkdownTable)
        case blank
    }

    let id: Int
    let kind: Kind
    let text: String
}

struct MarkdownTable: Equatable {
    let header: [String]
    let rows: [[String]]

    var columnCount: Int {
        max(header.count, rows.map(\.count).max() ?? 0)
    }

    func cells(for row: [String]) -> [String] {
        let count = columnCount
        guard row.count < count else { return Array(row.prefix(count)) }
        return row + Array(repeating: "", count: count - row.count)
    }

    func cells(inColumn index: Int) -> [String] {
        guard index >= 0, index < columnCount else { return [] }
        let headerCell = index < header.count ? header[index] : ""
        return [headerCell] + rows.map { cells(for: $0)[index] }
    }
}

enum SimpleMarkdown {
    static func blocks(from text: String) -> [MarkdownBlock] {
        let lines = text.split(separator: "\n", omittingEmptySubsequences: false).map(String.init)
        var blocks: [MarkdownBlock] = []
        var inCode = false
        var index = 0

        while index < lines.count {
            let line = lines[index]
            let trimmed = line.trimmingCharacters(in: .whitespaces)
            if trimmed.hasPrefix("```") {
                inCode.toggle()
                index += 1
                continue
            }
            if inCode {
                blocks.append(MarkdownBlock(id: index, kind: .code, text: line))
            } else if trimmed.isEmpty {
                blocks.append(MarkdownBlock(id: index, kind: .blank, text: ""))
            } else if let heading = headingBlock(trimmed, id: index) {
                blocks.append(heading)
            } else if let table = tableBlock(lines: lines, startIndex: index) {
                blocks.append(MarkdownBlock(id: index, kind: .table(table.table), text: ""))
                index = table.nextIndex
                continue
            } else if trimmed.hasPrefix("- ") || trimmed.hasPrefix("* ") {
                blocks.append(MarkdownBlock(id: index, kind: .bullet, text: String(trimmed.dropFirst(2))))
            } else {
                blocks.append(MarkdownBlock(id: index, kind: .paragraph, text: line))
            }
            index += 1
        }
        return blocks
    }

    private static func headingBlock(_ line: String, id: Int) -> MarkdownBlock? {
        for level in 1 ... 4 {
            let prefix = String(repeating: "#", count: level) + " "
            if line.hasPrefix(prefix) {
                return MarkdownBlock(id: id, kind: .heading(level), text: String(line.dropFirst(prefix.count)))
            }
        }
        return nil
    }

    private static func tableBlock(lines: [String], startIndex: Int) -> (table: MarkdownTable, nextIndex: Int)? {
        guard startIndex + 1 < lines.count else { return nil }
        let header = pipeCells(from: lines[startIndex])
        guard header.count >= 2, isTableSeparator(lines[startIndex + 1], expectedColumns: header.count) else {
            return nil
        }
        var rows: [[String]] = []
        var index = startIndex + 2
        while index < lines.count {
            let line = lines[index]
            let trimmed = line.trimmingCharacters(in: .whitespaces)
            guard !trimmed.isEmpty, trimmed.contains("|") else { break }
            rows.append(pipeCells(from: line))
            index += 1
        }
        return (MarkdownTable(header: header, rows: rows), index)
    }

    private static func isTableSeparator(_ line: String, expectedColumns: Int) -> Bool {
        let cells = pipeCells(from: line)
        guard cells.count == expectedColumns else { return false }
        return cells.allSatisfy { cell in
            let trimmed = cell.trimmingCharacters(in: .whitespaces)
            guard trimmed.count >= 3 else { return false }
            let stripped = trimmed.trimmingCharacters(in: CharacterSet(charactersIn: ":"))
            return stripped.count >= 3 && stripped.allSatisfy { $0 == "-" }
        }
    }

    private static func pipeCells(from line: String) -> [String] {
        var value = line.trimmingCharacters(in: .whitespaces)
        if value.hasPrefix("|") {
            value.removeFirst()
        }
        if value.hasSuffix("|") {
            value.removeLast()
        }
        return value.split(separator: "|", omittingEmptySubsequences: false)
            .map { String($0).trimmingCharacters(in: .whitespaces) }
    }

    static func inlineAttributedString(_ text: String) -> AttributedString {
        if let attributed = try? AttributedString(
            markdown: text,
            options: AttributedString.MarkdownParsingOptions(interpretedSyntax: .inlineOnlyPreservingWhitespace)
        ) {
            return attributed
        }
        return AttributedString(text)
    }
}

struct SimpleMarkdownView: View {
    private static let contentPadding: CGFloat = 14

    let blocks: [MarkdownBlock]
    let style: ReadingStyleSettings

    init(text: String, style: ReadingStyleSettings = .default) {
        blocks = SimpleMarkdown.blocks(from: text)
        self.style = style
    }

    init(blocks: [MarkdownBlock], style: ReadingStyleSettings = .default) {
        self.blocks = blocks
        self.style = style
    }

    var body: some View {
        GeometryReader { proxy in
            let availableWidth = max(proxy.size.width - (Self.contentPadding * 2), 0)
            let contentWidth = style.contentWidth.resolvedWidth(for: availableWidth)
            ScrollView {
                SimpleMarkdownContentView(blocks: blocks, style: style)
                    .frame(width: contentWidth, alignment: .leading)
                    .padding(Self.contentPadding)
                    .frame(maxWidth: .infinity, alignment: .center)
            }
        }
    }
}

struct SimpleMarkdownContentView: View {
    let blocks: [MarkdownBlock]
    let style: ReadingStyleSettings

    @State private var availableWidth: CGFloat = 0

    init(text: String, style: ReadingStyleSettings = .default) {
        blocks = SimpleMarkdown.blocks(from: text)
        self.style = style
    }

    init(blocks: [MarkdownBlock], style: ReadingStyleSettings = .default) {
        self.blocks = blocks
        self.style = style
    }

    var body: some View {
        LazyVStack(alignment: .leading, spacing: 4) {
            ForEach(blocks) { block in
                blockView(block, availableWidth: availableWidth)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .textSelection(.enabled)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(widthReader)
        .onPreferenceChange(SimpleMarkdownContentWidthKey.self) { width in
            availableWidth = width
        }
    }

    @ViewBuilder
    private func blockView(_ block: MarkdownBlock, availableWidth: CGFloat) -> some View {
        switch block.kind {
        case let .heading(level):
            Text(SimpleMarkdown.inlineAttributedString(block.text))
                .font(style.headingFont(level))
                .fontWeight(.semibold)
                .fixedSize(horizontal: false, vertical: true)
                .padding(.top, level == 1 ? 10 : 6)
                .padding(.bottom, 2)
        case .paragraph:
            Text(SimpleMarkdown.inlineAttributedString(block.text))
                .font(style.bodyFont)
                .lineSpacing(style.lineSpacing.points)
                .fixedSize(horizontal: false, vertical: true)
        case .bullet:
            HStack(alignment: .top, spacing: 8) {
                Text("•")
                    .font(style.bulletFont)
                Text(SimpleMarkdown.inlineAttributedString(block.text))
                    .font(style.bodyFont)
                    .lineSpacing(style.lineSpacing.points)
                    .fixedSize(horizontal: false, vertical: true)
            }
        case .code:
            Text(block.text)
                .font(style.codeFont)
                .lineSpacing(style.lineSpacing.points)
                .fixedSize(horizontal: false, vertical: true)
        case let .table(table):
            MarkdownTableView(table: table, availableWidth: availableWidth, style: style)
        case .blank:
            Spacer(minLength: style.lineSpacing.blankSpacing)
        }
    }
}

private struct SimpleMarkdownContentWidthKey: PreferenceKey {
    static var defaultValue: CGFloat = 0

    static func reduce(value: inout CGFloat, nextValue: () -> CGFloat) {
        value = nextValue()
    }
}

private var widthReader: some View {
    GeometryReader { proxy in
        Color.clear.preference(key: SimpleMarkdownContentWidthKey.self, value: proxy.size.width)
    }
}

struct MarkdownTableLayout: Equatable {
    static let minimumColumnWidth: CGFloat = 120

    let columnWidths: [CGFloat]
    let availableWidth: CGFloat

    init(table: MarkdownTable, availableWidth: CGFloat) {
        self.availableWidth = availableWidth
        columnWidths = Self.columnWidths(for: table, availableWidth: availableWidth)
    }

    var columnCount: Int {
        columnWidths.count
    }

    var tableWidth: CGFloat {
        if columnCount == 2, availableWidth > 0 {
            return availableWidth
        }
        return max(availableWidth, columnWidths.reduce(0, +))
    }

    private static func columnWidths(for table: MarkdownTable, availableWidth: CGFloat) -> [CGFloat] {
        let columnCount = table.columnCount
        guard columnCount > 0 else { return [] }

        if let fixedTwoColumnWidths = fixedTwoColumnWidths(for: table, availableWidth: availableWidth) {
            return fixedTwoColumnWidths
        }

        let minimumWidths = Array(repeating: Self.minimumColumnWidth, count: columnCount)
        let minimumTotalWidth = minimumWidths.reduce(0, +)
        let targetWidth = max(availableWidth, minimumTotalWidth)
        let extraWidth = targetWidth - minimumTotalWidth
        guard extraWidth > 0 else { return minimumWidths }

        let scores = columnScores(for: table)
        let maximumWidth = targetWidth * maximumColumnShare(for: columnCount)
        var widths = minimumWidths
        var remainingWidth = extraWidth
        var adjustableColumns = Set(widths.indices)

        while remainingWidth > 0.5, !adjustableColumns.isEmpty {
            let totalScore = adjustableColumns.reduce(CGFloat.zero) { partial, index in
                partial + max(scores[index], 0.1)
            }
            guard totalScore > 0 else { break }

            let batchWidth = remainingWidth
            var consumedWidth: CGFloat = 0
            var cappedColumns: [Int] = []

            for index in adjustableColumns.sorted() {
                let share = max(scores[index], 0.1) / totalScore
                let proposedWidth = widths[index] + batchWidth * share
                let cappedWidth = min(proposedWidth, maximumWidth)
                consumedWidth += cappedWidth - widths[index]
                widths[index] = cappedWidth
                if cappedWidth >= maximumWidth - 0.5 {
                    cappedColumns.append(index)
                }
            }

            remainingWidth -= consumedWidth
            if cappedColumns.isEmpty {
                break
            }
            cappedColumns.forEach { adjustableColumns.remove($0) }
        }

        if remainingWidth > 0.5, !widths.isEmpty {
            let fallbackWidth = remainingWidth / CGFloat(widths.count)
            for index in widths.indices {
                widths[index] += fallbackWidth
            }
        }
        return widths
    }

    private static func fixedTwoColumnWidths(for table: MarkdownTable, availableWidth: CGFloat) -> [CGFloat]? {
        guard table.columnCount == 2 else { return nil }
        let targetWidth = availableWidth > 0 ? availableWidth : (Self.minimumColumnWidth * 3)
        let firstWidth = targetWidth / 3
        let secondWidth = targetWidth - firstWidth
        return [firstWidth, secondWidth]
    }

    private static func columnScores(for table: MarkdownTable) -> [CGFloat] {
        (0 ..< table.columnCount).map { index in
            let units = table.cells(inColumn: index).map(displayUnits(for:))
            let longest = units.max() ?? 0
            let average = units.reduce(0, +) / CGFloat(max(units.count, 1))
            let headerUnits = displayUnits(for: index < table.header.count ? table.header[index] : "")
            return max(1, min(longest, 30) * 0.72 + min(average, 18) * 0.28 + min(headerUnits, 12) * 0.2)
        }
    }

    private static func maximumColumnShare(for columnCount: Int) -> CGFloat {
        switch columnCount {
        case 0 ... 1:
            return 1
        case 2:
            return 0.68
        case 3:
            return 0.5
        case 4:
            return 0.42
        default:
            return 0.36
        }
    }

    private static func displayUnits(for text: String) -> CGFloat {
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return 1 }
        return trimmed.unicodeScalars.reduce(CGFloat.zero) { partial, scalar in
            partial + scalarDisplayUnit(scalar)
        }
    }

    private static func scalarDisplayUnit(_ scalar: Unicode.Scalar) -> CGFloat {
        if CharacterSet.whitespacesAndNewlines.contains(scalar) {
            return 0.35
        }
        if scalar.properties.isIdeographic || isWideCJKScalar(scalar) {
            return 1.8
        }
        if CharacterSet.uppercaseLetters.contains(scalar) {
            return 1.05
        }
        if CharacterSet.lowercaseLetters.contains(scalar) || CharacterSet.decimalDigits.contains(scalar) {
            return 0.95
        }
        if CharacterSet.punctuationCharacters.contains(scalar) || CharacterSet.symbols.contains(scalar) {
            return 0.55
        }
        return 1
    }

    private static func isWideCJKScalar(_ scalar: Unicode.Scalar) -> Bool {
        switch scalar.value {
        case 0x2E80 ... 0x2FDF, // CJK Radicals Supplement, Kangxi Radicals
             0x2FF0 ... 0x30FF, // Ideographic Description, Hiragana, Katakana
             0x3100 ... 0x312F, // Bopomofo
             0x3190 ... 0x31EF, // Kanbun, Bopomofo Extended, CJK Strokes
             0x3400 ... 0x4DBF, // CJK Unified Ideographs Extension A
             0x4E00 ... 0x9FFF, // CJK Unified Ideographs
             0xAC00 ... 0xD7AF, // Hangul Syllables
             0xF900 ... 0xFAFF, // CJK Compatibility Ideographs
             0xFE10 ... 0xFE6F, // Vertical forms, CJK compatibility forms
             0xFF01 ... 0xFF60, // Fullwidth ASCII variants
             0xFFE0 ... 0xFFE6:
            return true
        default:
            return false
        }
    }
}

private struct MarkdownTableView: View {
    let table: MarkdownTable
    let availableWidth: CGFloat
    let style: ReadingStyleSettings

    var body: some View {
        let layout = MarkdownTableLayout(table: table, availableWidth: availableWidth)
        Group {
            if table.columnCount == 2 {
                tableContent(layout: layout)
                    .frame(maxWidth: .infinity, alignment: .leading)
            } else {
                ScrollView(.horizontal, showsIndicators: true) {
                    tableContent(layout: layout)
                }
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(.vertical, 6)
    }

    private func tableContent(layout: MarkdownTableLayout) -> some View {
        VStack(alignment: .leading, spacing: 0) {
            MarkdownTableRowView(
                cells: table.cells(for: table.header),
                columnWidths: layout.columnWidths,
                isHeader: true,
                style: style
            )
            ForEach(Array(table.rows.enumerated()), id: \.offset) { index, row in
                MarkdownTableRowView(
                    cells: table.cells(for: row),
                    columnWidths: layout.columnWidths,
                    isHeader: false,
                    rowIndex: index,
                    style: style
                )
            }
        }
        .frame(width: layout.tableWidth, alignment: .leading)
        .background(
            RoundedRectangle(cornerRadius: 10)
                .fill(Color.secondary.opacity(0.05))
        )
        .clipShape(RoundedRectangle(cornerRadius: 10))
        .overlay(
            RoundedRectangle(cornerRadius: 10)
                .stroke(Color.secondary.opacity(0.18), lineWidth: 1)
        )
    }
}

private struct MarkdownTableRowView: View {
    let cells: [String]
    let columnWidths: [CGFloat]
    let isHeader: Bool
    let rowIndex: Int
    let style: ReadingStyleSettings

    init(cells: [String], columnWidths: [CGFloat], isHeader: Bool, rowIndex: Int = 0, style: ReadingStyleSettings) {
        self.cells = cells
        self.columnWidths = columnWidths
        self.isHeader = isHeader
        self.rowIndex = rowIndex
        self.style = style
    }

    var body: some View {
        HStack(alignment: .top, spacing: 0) {
            ForEach(Array(cells.enumerated()), id: \.offset) { index, cell in
                MarkdownTableCellView(
                    text: cell,
                    columnWidth: index < columnWidths.count ? columnWidths[index] : MarkdownTableLayout.minimumColumnWidth,
                    isHeader: isHeader,
                    style: style
                )
            }
        }
        .background(rowBackgroundColor)
        .overlay(rowGridOverlay.allowsHitTesting(false))
    }

    private var rowBackgroundColor: Color {
        if isHeader {
            return Color.secondary.opacity(0.16)
        }
        return rowIndex.isMultiple(of: 2) ? Color.secondary.opacity(0.035) : Color.clear
    }

    private var rowGridOverlay: some View {
        ZStack(alignment: .leading) {
            Rectangle()
                .stroke(Color.secondary.opacity(0.12), lineWidth: 0.5)
            ForEach(dividerOffsets, id: \.self) { offset in
                Rectangle()
                    .fill(Color.secondary.opacity(0.12))
                    .frame(width: 0.5)
                    .offset(x: offset)
            }
        }
    }

    private var dividerOffsets: [CGFloat] {
        var offsets: [CGFloat] = []
        var runningWidth: CGFloat = 0
        for width in columnWidths.dropLast() {
            runningWidth += width
            offsets.append(runningWidth)
        }
        return offsets
    }
}

private struct MarkdownTableCellView: View {
    let text: String
    let columnWidth: CGFloat
    let isHeader: Bool
    let style: ReadingStyleSettings

    var body: some View {
        Text(SimpleMarkdown.inlineAttributedString(text))
            .font(style.tableFont(isHeader: isHeader))
            .lineSpacing(style.lineSpacing.points)
            .multilineTextAlignment(.leading)
            .fixedSize(horizontal: false, vertical: true)
            .padding(.horizontal, 12)
            .padding(.vertical, 8)
            .frame(width: columnWidth, alignment: .topLeading)
    }
}
