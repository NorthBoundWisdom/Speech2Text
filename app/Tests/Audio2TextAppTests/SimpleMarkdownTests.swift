@testable import Audio2TextApp
import Audio2TextCore
import XCTest

final class SimpleMarkdownTests: XCTestCase {
    func testSimpleMarkdownParsesCommonBlocks() {
        let markdown = """
        # Title

        Paragraph with **bold** text.
        - item
        ```json
        {"ok": true}
        ```
        """

        let blocks = SimpleMarkdown.blocks(from: markdown)

        XCTAssertEqual(blocks.map(\.kind), [.heading(1), .blank, .paragraph, .bullet, .code])
        XCTAssertEqual(blocks.last?.text, #"{"ok": true}"#)
    }

    func testSimpleMarkdownKeepsStreamingOpenCodeFenceContent() {
        let markdown = """
        # Streaming

        ```json
        {"partial": true}
        """

        let blocks = SimpleMarkdown.blocks(from: markdown)

        XCTAssertEqual(blocks.map(\.kind), [.heading(1), .blank, .code])
        XCTAssertEqual(blocks.last?.text, #"{"partial": true}"#)
    }

    func testSimpleMarkdownParsesPipeTables() {
        let markdown = """
        | 项目 | 状态 | 说明 |
        | --- | :---: | --- |
        | Summary | **完成** | 支持 Markdown |
        | Transcript | 待处理 | 保留文本 |

        next paragraph
        """

        let blocks = SimpleMarkdown.blocks(from: markdown)

        XCTAssertEqual(blocks.map(\.kind), [
            .table(
                MarkdownTable(
                    header: ["项目", "状态", "说明"],
                    rows: [
                        ["Summary", "**完成**", "支持 Markdown"],
                        ["Transcript", "待处理", "保留文本"],
                    ]
                )
            ),
            .blank,
            .paragraph,
        ])
    }

    func testMarkdownTableLayoutExpandsBalancedColumnsToAvailableWidth() {
        let layout = MarkdownTableLayout(
            table: MarkdownTable(
                header: ["A", "B", "C"],
                rows: [
                    ["One", "Two", "Three"],
                    ["Alpha", "Beta", "Gamma"],
                ]
            ),
            availableWidth: 900
        )

        XCTAssertEqual(layout.tableWidth, 900, accuracy: 0.001)
        XCTAssertEqual(layout.columnWidths.count, 3)
        XCTAssertEqual(layout.columnWidths.reduce(0, +), 900, accuracy: 0.001)
        XCTAssertLessThan(abs(layout.columnWidths[0] - 300), 40)
        XCTAssertLessThan(abs(layout.columnWidths[1] - 300), 40)
        XCTAssertLessThan(abs(layout.columnWidths[2] - 300), 40)
    }

    func testMarkdownTableLayoutKeepsMinimumColumnWidthWhenWindowIsNarrow() {
        let layout = MarkdownTableLayout(
            table: MarkdownTable(
                header: ["A", "B", "C"],
                rows: [["1", "2", "3"]]
            ),
            availableWidth: 240
        )

        XCTAssertEqual(layout.tableWidth, 360, accuracy: 0.001)
        XCTAssertEqual(layout.columnWidths, [120, 120, 120])
    }

    func testMarkdownTableLayoutBiasesWidthTowardLongDescriptionColumns() {
        let layout = MarkdownTableLayout(
            table: MarkdownTable(
                header: ["名词", "解释"],
                rows: [
                    ["ADHD", "注意力缺陷多动障碍，特征包括拖延、注意力分散、难以坚持长期项目。"],
                    ["过度利他基因", "对想利的对象会超出实际必要程度付出的基因特质。"],
                ]
            ),
            availableWidth: 900
        )

        XCTAssertEqual(layout.tableWidth, 900, accuracy: 0.001)
        XCTAssertEqual(layout.columnWidths.reduce(0, +), 900, accuracy: 0.001)
        XCTAssertEqual(layout.columnWidths.count, 2)
        XCTAssertEqual(layout.columnWidths[0], 300, accuracy: 0.001)
        XCTAssertEqual(layout.columnWidths[1], 600, accuracy: 0.001)
    }

    func testMarkdownTableLayoutUsesMinimumWidthForNarrowTwoColumnTables() {
        let layout = MarkdownTableLayout(
            table: MarkdownTable(
                header: ["名词", "解释"],
                rows: [["A", "B"]]
            ),
            availableWidth: 240
        )

        XCTAssertEqual(layout.tableWidth, 240, accuracy: 0.001)
        XCTAssertEqual(layout.columnWidths[0], 80, accuracy: 0.001)
        XCTAssertEqual(layout.columnWidths[1], 160, accuracy: 0.001)
    }

    func testReadingTextSizeMapsToExpectedFontSizes() {
        XCTAssertEqual(ReadingTextSize.small.bodyFontSize, 14)
        XCTAssertEqual(ReadingTextSize.medium.bodyFontSize, 16)
        XCTAssertEqual(ReadingTextSize.large.bodyFontSize, 18)
        XCTAssertEqual(ReadingTextSize.xLarge.bodyFontSize, 21)
        XCTAssertEqual(ReadingTextSize.xxLarge.bodyFontSize, 24)
        XCTAssertEqual(ReadingTextSize.large.headingFontSize(1), 26)
        XCTAssertEqual(ReadingTextSize.large.headingFontSize(3), 21)
        XCTAssertEqual(ReadingTextSize.large.codeFontSize, 17)
    }

    func testReadingContentWidthMapsToMaximumReadableWidths() {
        XCTAssertEqual(ReadingContentWidth.compact.resolvedWidth(for: 1200), 680)
        XCTAssertEqual(ReadingContentWidth.standard.resolvedWidth(for: 1200), 820)
        XCTAssertEqual(ReadingContentWidth.wide.resolvedWidth(for: 1200), 1040)
        XCTAssertEqual(ReadingContentWidth.full.resolvedWidth(for: 1200), 1200)
        XCTAssertEqual(ReadingContentWidth.standard.resolvedWidth(for: 640), 640)
    }
}
