import SwiftUI
#if canImport(Audio2TextCore)
    import Audio2TextCore
#endif

private struct MobileReaderDocumentLoadID: Hashable {
    let episodeID: String
    let libraryRootPath: String
    let documentSignature: String
}

private struct MobileReaderDocumentReference: Equatable {
    let name: String
    let path: String
}

private struct MobileReadableTextBlock: Equatable, Identifiable {
    let id: Int
    let text: String

    static func blocks(from text: String, maxCharacters: Int = 900) -> [MobileReadableTextBlock] {
        let normalized = text
            .replacingOccurrences(of: "\r\n", with: "\n")
            .replacingOccurrences(of: "\r", with: "\n")
        let lines = normalized.components(separatedBy: "\n")
        var rawBlocks: [String] = []
        var currentLines: [String] = []
        var currentLength = 0

        func flushCurrent() {
            let block = currentLines
                .joined(separator: "\n")
                .trimmingCharacters(in: .whitespacesAndNewlines)
            if !block.isEmpty {
                rawBlocks.append(block)
            }
            currentLines.removeAll(keepingCapacity: true)
            currentLength = 0
        }

        func appendLongLine(_ line: String) {
            var start = line.startIndex
            while start < line.endIndex {
                let end = line.index(start, offsetBy: maxCharacters, limitedBy: line.endIndex) ?? line.endIndex
                rawBlocks.append(String(line[start ..< end]))
                start = end
            }
        }

        for line in lines {
            if line.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                flushCurrent()
                continue
            }
            if line.count > maxCharacters {
                flushCurrent()
                appendLongLine(line)
                continue
            }
            let additionalLength = currentLines.isEmpty ? line.count : line.count + 1
            if !currentLines.isEmpty, currentLength + additionalLength > maxCharacters {
                flushCurrent()
            }
            currentLines.append(line)
            currentLength += additionalLength
        }
        flushCurrent()

        return rawBlocks.enumerated().map { index, text in
            MobileReadableTextBlock(id: index, text: text)
        }
    }
}

private struct MobileReaderDocumentContent: Equatable {
    let text: String
    let isEmpty: Bool
    let blocks: [MobileReadableTextBlock]
    let markdownBlocks: [MarkdownBlock]

    init(text: String, rendersMarkdown: Bool) {
        self.text = text
        isEmpty = text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
        blocks = MobileReadableTextBlock.blocks(from: text)
        markdownBlocks = rendersMarkdown ? SimpleMarkdown.blocks(from: text) : []
    }
}

private struct MobileReaderDocumentCache: Equatable {
    let episodeID: String
    let libraryRootPath: String
    let documents: [String: MobileReaderDocumentContent]
    let missingNames: Set<String>

    static var empty: MobileReaderDocumentCache {
        MobileReaderDocumentCache(
            episodeID: "",
            libraryRootPath: "",
            documents: [:],
            missingNames: []
        )
    }

    static func empty(episodeID: String, libraryRootPath: String) -> MobileReaderDocumentCache {
        MobileReaderDocumentCache(
            episodeID: episodeID,
            libraryRootPath: libraryRootPath,
            documents: [:],
            missingNames: []
        )
    }

    func content(named name: String) -> MobileReaderDocumentContent? {
        documents[name]
    }

    func hasLoaded(named name: String) -> Bool {
        documents[name] != nil || missingNames.contains(name)
    }

    static func load(
        episodeID: String,
        libraryRootPath: String,
        documents references: [MobileReaderDocumentReference],
        requestedNames: [String]
    ) -> MobileReaderDocumentCache {
        let root = URL(fileURLWithPath: libraryRootPath, isDirectory: true)
        let referenceByName = Dictionary(uniqueKeysWithValues: references.map { ($0.name, $0) })
        var contents: [String: MobileReaderDocumentContent] = [:]
        var missing: Set<String> = []

        for name in requestedNames {
            guard let reference = referenceByName[name] else {
                missing.insert(name)
                continue
            }
            let url = root
                .appendingPathComponent("episodes/\(episodeID)", isDirectory: true)
                .appendingPathComponent(reference.path)
            guard let text = try? String(contentsOf: url, encoding: .utf8) else {
                missing.insert(name)
                continue
            }
            let content = MobileReaderDocumentContent(
                text: text,
                rendersMarkdown: name == MobileReaderSection.summary.documentName
            )
            if content.isEmpty {
                missing.insert(name)
            } else {
                contents[name] = content
            }
        }

        return MobileReaderDocumentCache(
            episodeID: episodeID,
            libraryRootPath: libraryRootPath,
            documents: contents,
            missingNames: missing
        )
    }
}

struct MobileReaderPane: View {
    enum HeaderDisplayMode {
        case column
        case systemNavigation
    }

    let episode: LibraryEpisode?
    let libraryRoot: URL?
    @Binding var section: MobileReaderSection
    @Binding var readingStyle: ReadingStyleSettings
    let onMarkEpisodeRead: (LibraryEpisode) -> Void
    let onToggleEpisodeStar: (LibraryEpisode) -> Void
    let onArchiveEpisode: (LibraryEpisode) -> Void
    let onDeleteEpisode: (LibraryEpisode) -> Void
    var headerDisplayMode: HeaderDisplayMode = .column
    var onBack: (() -> Void)?

    var body: some View {
        Group {
            if let episode {
                MobileEpisodeReader(
                    episode: episode,
                    libraryRoot: libraryRoot,
                    section: $section,
                    readingStyle: $readingStyle,
                    onMarkEpisodeRead: onMarkEpisodeRead,
                    onToggleEpisodeStar: onToggleEpisodeStar,
                    onArchiveEpisode: onArchiveEpisode,
                    onDeleteEpisode: onDeleteEpisode,
                    headerDisplayMode: headerDisplayMode,
                    onBack: onBack
                )
            } else {
                MobileAdaptiveEmptyState(
                    title: "No Episode",
                    message: "Select an episode to read synced content.",
                    systemImage: "doc.text"
                )
                .padding(.horizontal, 24)
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Color.mobileReaderBackground)
    }
}

private struct MobileEpisodeReader: View {
    let episode: LibraryEpisode
    let libraryRoot: URL?
    @Binding var section: MobileReaderSection
    @Binding var readingStyle: ReadingStyleSettings
    let onMarkEpisodeRead: (LibraryEpisode) -> Void
    let onToggleEpisodeStar: (LibraryEpisode) -> Void
    let onArchiveEpisode: (LibraryEpisode) -> Void
    let onDeleteEpisode: (LibraryEpisode) -> Void
    let headerDisplayMode: MobileReaderPane.HeaderDisplayMode
    var onBack: (() -> Void)?

    @State private var documentCache = MobileReaderDocumentCache.empty
    @State private var isLoadingDocuments = false

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            if headerDisplayMode == .column {
                columnHeader
            } else {
                sectionPicker
                    .padding(.horizontal, 16)
                    .padding(.vertical, 8)
            }

            MobileColumnDivider(axis: .horizontal)

            readerScrollView
        }
        .navigationTitle(headerDisplayMode == .systemNavigation ? episode.title : "")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            if headerDisplayMode == .systemNavigation {
                ToolbarItemGroup(placement: .topBarTrailing) {
                    MobileReaderTypographyMenu(style: $readingStyle)
                    readerActionsMenu
                }
            }
        }
        .task(id: documentLoadID) {
            await loadDocumentCache()
        }
    }

    private var columnHeader: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(alignment: .center, spacing: 8) {
                if let onBack {
                    MobileInlineBackButton(action: onBack)
                }

                VStack(alignment: .leading, spacing: 2) {
                    Text(episode.seriesName ?? episode.source ?? "Podcast")
                        .font(.subheadline.weight(.semibold))
                        .foregroundStyle(.secondary)
                        .lineLimit(1)
                    Text(mobileDateLabel(for: episode))
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .lineLimit(1)
                }
                .frame(maxWidth: .infinity, alignment: .leading)

                Spacer(minLength: 8)

                HStack(spacing: 4) {
                    MobileReaderTypographyMenu(style: $readingStyle)

                    MobileReaderActionButton(
                        title: "已读",
                        systemName: episode.isRead ? "checkmark.circle.fill" : "checkmark.circle"
                    ) {
                        onMarkEpisodeRead(episode)
                    }

                    MobileReaderActionButton(
                        title: "星标",
                        systemName: episode.isStarred ? "star.fill" : "star"
                    ) {
                        onToggleEpisodeStar(episode)
                    }

                    MobileReaderActionButton(
                        title: "归档",
                        systemName: episode.isArchived ? "archivebox.fill" : "archivebox"
                    ) {
                        onArchiveEpisode(episode)
                    }

                    MobileReaderActionButton(
                        title: "删除",
                        systemName: "trash",
                        role: .destructive
                    ) {
                        onDeleteEpisode(episode)
                    }
                }
            }

            Text(episode.title)
                .font(.title2.bold())
                .fixedSize(horizontal: false, vertical: true)
                .frame(maxWidth: .infinity, alignment: .leading)

            sectionPicker
        }
        .padding(.horizontal, 20)
        .padding(.top, onBack == nil ? 16 : 8)
        .padding(.bottom, 10)
    }

    private var sectionPicker: some View {
        Picker("Reader Section", selection: $section) {
            ForEach(MobileReaderSection.allCases) { item in
                Text(item.title).tag(item)
            }
        }
        .pickerStyle(.segmented)
        .labelsHidden()
    }

    private var readerScrollView: some View {
        GeometryReader { proxy in
            let horizontalPadding: CGFloat = 20
            let availableWidth = max(proxy.size.width - (horizontalPadding * 2), 0)
            let contentWidth = readingStyle.contentWidth.resolvedWidth(for: availableWidth)

            ScrollView {
                VStack(alignment: .leading, spacing: readingStyle.lineSpacing.blockSpacing) {
                    readerContent
                }
                .frame(width: contentWidth, alignment: .leading)
                .padding(.horizontal, horizontalPadding)
                .padding(.vertical, 18)
                .frame(maxWidth: .infinity, alignment: .center)
            }
        }
    }

    private var readerActionsMenu: some View {
        Menu {
            Button {
                onMarkEpisodeRead(episode)
            } label: {
                Label(episode.isRead ? "标记未读" : "标记已读", systemImage: episode.isRead ? "circle" : "checkmark.circle")
            }

            Button {
                onToggleEpisodeStar(episode)
            } label: {
                Label(episode.isStarred ? "取消星标" : "星标", systemImage: episode.isStarred ? "star.slash" : "star")
            }

            Button {
                onArchiveEpisode(episode)
            } label: {
                Label(episode.isArchived ? "取消归档" : "归档", systemImage: episode.isArchived ? "archivebox.fill" : "archivebox")
            }

            Divider()

            Button(role: .destructive) {
                onDeleteEpisode(episode)
            } label: {
                Label("删除", systemImage: "trash")
            }
        } label: {
            Image(systemName: "ellipsis.circle")
                .frame(width: 34, height: 34)
        }
        .accessibilityLabel("Episode Actions")
    }

    @ViewBuilder
    private var readerContent: some View {
        switch section {
        case .intro:
            readableText(introText)
        case .summary:
            if let content = documentContent(for: section) {
                readableMarkdown(content.markdownBlocks)
            } else if isLoadingDocument(for: section) {
                MobileDocumentLoadingView()
                    .frame(maxWidth: .infinity, alignment: .leading)
            } else {
                MobileMissingDocumentView()
                    .frame(maxWidth: .infinity, alignment: .leading)
            }
        case .transcript:
            if let content = documentContent(for: section) {
                readableText(content.blocks)
            } else if isLoadingDocument(for: section) {
                MobileDocumentLoadingView()
                    .frame(maxWidth: .infinity, alignment: .leading)
            } else {
                MobileMissingDocumentView()
                    .frame(maxWidth: .infinity, alignment: .leading)
            }
        }
    }

    private func readableText(_ text: String) -> some View {
        readableText(MobileReadableTextBlock.blocks(from: text))
    }

    private func readableText(_ blocks: [MobileReadableTextBlock]) -> some View {
        MobileReadableTextView(blocks: blocks, style: readingStyle)
    }

    private func readableMarkdown(_ blocks: [MarkdownBlock]) -> some View {
        SimpleMarkdownContentView(blocks: blocks, style: readingStyle)
    }

    private var introText: String {
        let fields = [
            episode.description,
            episode.publishedAt.map { "Published: \($0)" },
            episode.duration.map { "Duration: \($0)" },
            episode.sourceURL.map { "Source: \($0)" },
        ].compactMap { mobileClean($0) }
        return fields.isEmpty ? "No intro metadata is available." : fields.joined(separator: "\n\n")
    }

    private var documentLoadID: MobileReaderDocumentLoadID {
        MobileReaderDocumentLoadID(
            episodeID: episode.id,
            libraryRootPath: libraryRoot?.path ?? "",
            documentSignature: episode.documents
                .map { "\($0.name):\($0.path):\($0.bytes ?? -1):\($0.sha256 ?? "")" }
                .sorted()
                .joined(separator: "|")
        )
    }

    private var activeDocumentCache: MobileReaderDocumentCache? {
        guard documentCache.episodeID == episode.id,
              documentCache.libraryRootPath == (libraryRoot?.path ?? "")
        else {
            return nil
        }
        return documentCache
    }

    private func documentContent(for section: MobileReaderSection) -> MobileReaderDocumentContent? {
        guard let documentName = section.documentName else {
            return nil
        }
        return activeDocumentCache?.content(named: documentName)
    }

    private func isLoadingDocument(for section: MobileReaderSection) -> Bool {
        guard let documentName = section.documentName, libraryRoot != nil else {
            return false
        }
        if isLoadingDocuments {
            return true
        }
        guard let activeDocumentCache else {
            return true
        }
        return !activeDocumentCache.hasLoaded(named: documentName)
    }

    @MainActor
    private func loadDocumentCache() async {
        let loadID = documentLoadID
        guard !loadID.libraryRootPath.isEmpty else {
            documentCache = .empty(episodeID: loadID.episodeID, libraryRootPath: loadID.libraryRootPath)
            isLoadingDocuments = false
            return
        }

        isLoadingDocuments = true
        let references = episode.documents.map {
            MobileReaderDocumentReference(name: $0.name, path: $0.path)
        }
        let requestedNames = MobileReaderSection.allCases.compactMap(\.documentName)
        let cache = await Task.detached(priority: .userInitiated) {
            MobileReaderDocumentCache.load(
                episodeID: loadID.episodeID,
                libraryRootPath: loadID.libraryRootPath,
                documents: references,
                requestedNames: requestedNames
            )
        }.value

        guard documentLoadID == loadID else {
            return
        }
        documentCache = cache
        isLoadingDocuments = false
    }
}

private struct MobileReadableTextView: View {
    let blocks: [MobileReadableTextBlock]
    let style: ReadingStyleSettings

    var body: some View {
        LazyVStack(alignment: .leading, spacing: style.lineSpacing.blockSpacing) {
            ForEach(blocks) { block in
                Text(block.text)
                    .font(style.bodyFont)
                    .lineSpacing(style.lineSpacing.points)
                    .textSelection(.enabled)
                    .fixedSize(horizontal: false, vertical: true)
                    .frame(maxWidth: .infinity, alignment: .leading)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }
}

private struct MobileReaderTypographyMenu: View {
    @Binding var style: ReadingStyleSettings

    var body: some View {
        Menu {
            Picker("文字大小", selection: textSizeBinding) {
                ForEach(ReadingTextSize.allCases) { size in
                    Text(size.title).tag(size)
                }
            }

            Picker("行距", selection: lineSpacingBinding) {
                ForEach(ReadingLineSpacing.allCases) { spacing in
                    Text(spacing.title).tag(spacing)
                }
            }

            Picker("宽度", selection: contentWidthBinding) {
                ForEach(ReadingContentWidth.allCases) { width in
                    Text(width.title).tag(width)
                }
            }

            Picker("字体", selection: fontDesignBinding) {
                ForEach(ReadingFontDesign.allCases) { font in
                    Text(font.title).tag(font)
                }
            }

            Divider()

            Button {
                style = .default
            } label: {
                Label("恢复默认", systemImage: "arrow.counterclockwise")
            }
        } label: {
            Image(systemName: "textformat.size")
                .frame(width: 34, height: 34)
        }
        .accessibilityLabel("Typography")
    }

    private var textSizeBinding: Binding<ReadingTextSize> {
        Binding(
            get: { style.textSize },
            set: { style.textSize = $0 }
        )
    }

    private var lineSpacingBinding: Binding<ReadingLineSpacing> {
        Binding(
            get: { style.lineSpacing },
            set: { style.lineSpacing = $0 }
        )
    }

    private var contentWidthBinding: Binding<ReadingContentWidth> {
        Binding(
            get: { style.contentWidth },
            set: { style.contentWidth = $0 }
        )
    }

    private var fontDesignBinding: Binding<ReadingFontDesign> {
        Binding(
            get: { style.fontDesign },
            set: { style.fontDesign = $0 }
        )
    }
}

private struct MobileDocumentLoadingView: View {
    var body: some View {
        HStack(alignment: .center, spacing: 10) {
            ProgressView()
                .controlSize(.small)
            Text("载入中")
                .font(.callout)
        }
        .foregroundStyle(.secondary)
        .padding(.vertical, 4)
    }
}

private struct MobileMissingDocumentView: View {
    var body: some View {
        HStack(alignment: .top, spacing: 10) {
            Image(systemName: "icloud.and.arrow.down")
                .font(.body)
            VStack(alignment: .leading, spacing: 3) {
                Text("需要在 Mac 上处理")
                    .font(.callout.weight(.semibold))
                Text("下载音频并生成摘要或转写后，这里会显示同步内容。")
                    .font(.caption)
            }
        }
        .foregroundStyle(.secondary)
        .padding(.vertical, 4)
    }
}
