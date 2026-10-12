@testable import Audio2TextApp
import AppKit
import SwiftUI
import XCTest

final class LibraryWorkspaceLayoutTests: XCTestCase {
    @MainActor
    func testNarrowWorkspaceKeepsColumnsInsideViewport() throws {
        try assertWorkspaceFits(width: 980)
    }

    @MainActor
    func testWideWorkspaceKeepsColumnsInsideViewport() throws {
        try assertWorkspaceFits(width: 1280)
        try assertWorkspaceFits(width: 1640)
    }

    @MainActor
    func testWorkspaceWithoutSourceColumnUsesRemainingWidth() throws {
        try assertWorkspaceFits(width: 980, showsSourceColumn: false)
    }

    @MainActor
    private func assertWorkspaceFits(width: CGFloat, showsSourceColumn: Bool = true) throws {
        let measurements = LayoutMeasurements()
        let workspace = LibraryWorkspaceShell(
            showsSourceColumn: showsSourceColumn,
            sourceColumnWidth: 270,
            listColumnWidth: 340,
            sourceColumnMinimumWidth: 230,
            listColumnMinimumWidth: 280
        ) {
            Text("Subscriptions")
                .frame(maxWidth: .infinity, maxHeight: .infinity)
                .background(LayoutProbe(name: "source", measurements: measurements))
        } listColumn: {
            Text("Library")
                .frame(maxWidth: .infinity, maxHeight: .infinity)
                .background(LayoutProbe(name: "list", measurements: measurements))
        } detailColumn: {
            VStack(spacing: 0) {
                LibraryWorkspaceDetailHeader {
                    Picker("", selection: .constant(0)) {
                        Text("简介").tag(0)
                        Text("摘要").tag(1)
                        Text("转写").tag(2)
                    }
                    .pickerStyle(.segmented)
                    .labelsHidden()
                }
                .background(LayoutProbe(name: "header", measurements: measurements))
                SimpleMarkdownView(text: """
                # 中文播客：一个需要在窄阅读区域自动换行的长标题

                - 来源：Podcast RSS
                - 链接：[https://example.com/\(String(repeating: "long-path/", count: 30))](https://example.com/\(String(repeating: "long-path/", count: 30)))

                ## 节目介绍

                \(String(repeating: "这段较长的中文正文用于验证阅读区在不同窗口宽度下自然换行，保持内容完整可读。", count: 8))
                """)
            }
            .background(LayoutProbe(name: "detail", measurements: measurements))
        }
        .coordinateSpace(name: "workspace")

        let hosting = NSHostingView(rootView: workspace)
        let window = NSWindow(
            contentRect: NSRect(x: 0, y: 0, width: width, height: 680),
            styleMask: [.borderless], backing: .buffered, defer: false
        )
        window.contentView = hosting
        defer { window.contentView = nil }
        hosting.layoutSubtreeIfNeeded()
        let deadline = Date().addingTimeInterval(1)
        let expectedMeasurements = showsSourceColumn ? 4 : 3
        while measurements.frames.count < expectedMeasurements, Date() < deadline {
            RunLoop.main.run(until: Date().addingTimeInterval(0.01))
            hosting.layoutSubtreeIfNeeded()
        }

        if showsSourceColumn {
            let source = try XCTUnwrap(measurements.frames["source"])
            XCTAssertEqual(source.minX, 0, accuracy: 1)
            XCTAssertEqual(source.width, 270, accuracy: 1)
        }
        let list = try XCTUnwrap(measurements.frames["list"])
        XCTAssertEqual(list.minX, showsSourceColumn ? 271 : 0, accuracy: 1)
        XCTAssertEqual(list.width, 340, accuracy: 1)
        let detail = try XCTUnwrap(measurements.frames["detail"])
        XCTAssertEqual(detail.minX, showsSourceColumn ? 612 : 341, accuracy: 1)
        XCTAssertEqual(detail.maxX, width, accuracy: 1)
        let header = try XCTUnwrap(measurements.frames["header"])
        XCTAssertEqual(header.minX, detail.minX, accuracy: 1)
        XCTAssertEqual(header.maxX, detail.maxX, accuracy: 1)

        if let snapshotDirectory = ProcessInfo.processInfo.environment["ATOT_LAYOUT_SNAPSHOT_DIR"] {
            let directory = URL(fileURLWithPath: snapshotDirectory, isDirectory: true)
            try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
            let bitmap = try XCTUnwrap(hosting.bitmapImageRepForCachingDisplay(in: hosting.bounds))
            hosting.cacheDisplay(in: hosting.bounds, to: bitmap)
            let png = try XCTUnwrap(bitmap.representation(using: .png, properties: [:]))
            try png.write(to: directory.appendingPathComponent("workspace-\(Int(width))-\(showsSourceColumn).png"))
        }
    }
}

private final class LayoutMeasurements {
    var frames: [String: CGRect] = [:]
}

private struct LayoutProbe: View {
    let name: String
    let measurements: LayoutMeasurements

    var body: some View {
        GeometryReader { proxy in
            Color.clear
                .preference(key: WorkspaceFramesKey.self, value: [name: proxy.frame(in: .named("workspace"))])
        }
        .onPreferenceChange(WorkspaceFramesKey.self) { measurements.frames.merge($0) { _, new in new } }
    }
}

private struct WorkspaceFramesKey: PreferenceKey {
    static var defaultValue: [String: CGRect] = [:]

    static func reduce(value: inout [String: CGRect], nextValue: () -> [String: CGRect]) {
        value.merge(nextValue()) { _, new in new }
    }
}
