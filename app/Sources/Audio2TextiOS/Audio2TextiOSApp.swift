import SwiftUI
import UniformTypeIdentifiers
#if canImport(UIKit)
    import UIKit
#endif
#if canImport(Audio2TextCore)
    import Audio2TextCore
#endif

private struct MobileLibraryManifestSignature: Equatable {
    let modifiedAt: Date?
    let byteCount: Int
}

@main
struct Audio2TextiOSApp: App {
    @StateObject private var store = MobileLibraryViewModel()

    var body: some Scene {
        WindowGroup {
            MobileLibraryView(store: store)
        }
    }
}

@MainActor
final class MobileLibraryViewModel: ObservableObject {
    @Published var episodes: [LibraryEpisode] = [] {
        didSet { rebuildEpisodeCaches() }
    }

    @Published var subscriptions: [LibrarySubscription] = [] {
        didSet { rebuildSubscriptionCaches() }
    }

    @Published var groupNames: [String] = []
    @Published var selectedEpisodeID: String?
    @Published var hidesReadItems = false
    @Published var statusMessage = ""
    @Published var isRefreshing = false
    @Published private(set) var libraryRoot: URL?
    @Published private(set) var libraryLocationDescription = ""
    @Published private(set) var librarySyncStatus = LibrarySyncStatus.unavailable()

    private let libraryAccessStore = MobileLibraryAccessStore()
    private var selectedLibraryAccess: MobileLibraryAccess?
    private var lastLoadedManifestSignature: MobileLibraryManifestSignature?
    private var syncStatusRefreshTask: Task<Void, Never>?
    private var sidebarItems: [LibrarySidebarItem] = []
    private var sidebarSubscriptions: [LibrarySidebarSubscription] = []
    private var episodesByID: [String: LibraryEpisode] = [:]

    init() {
        configureInitialLibraryRoot()
        load()
    }

    var selectedEpisode: LibraryEpisode? {
        guard let selectedEpisodeID else { return nil }
        return episodes.first { $0.id == selectedEpisodeID }
    }

    var availableGroupNames: [String] {
        sidebarState(selectedSource: .library)
            .groupSections()
            .map(\.title)
    }

    var displayedLibrarySyncStatus: LibrarySyncStatus {
        guard isRefreshing else { return librarySyncStatus }
        return .syncing(
            "Library changes are syncing.",
            checkedAt: librarySyncStatus.checkedAt,
            progress: nil
        )
    }

    func sidebarState(selectedSource: LibrarySidebarSource) -> LibrarySidebarState {
        LibrarySidebarState(
            items: sidebarItems,
            subscriptions: sidebarSubscriptions,
            groupNames: groupNames + subscriptions.compactMap(\.groupName),
            selectedSidebarSource: selectedSource,
            hidesReadItems: hidesReadItems
        )
    }

    func episodeIDs(matching sidebarItems: [LibrarySidebarItem]) -> [String] {
        sidebarItems.map(\.id)
    }

    func episodes(matching sidebarItems: [LibrarySidebarItem]) -> [LibraryEpisode] {
        sidebarItems.compactMap { episodesByID[$0.id] }
    }

    func episode(forID id: String) -> LibraryEpisode? {
        episodesByID[id]
    }

    private func rebuildEpisodeCaches() {
        sidebarItems = LibrarySidebarState.items(from: episodes)
        episodesByID = Dictionary(uniqueKeysWithValues: episodes.map { ($0.id, $0) })
    }

    private func rebuildSubscriptionCaches() {
        sidebarSubscriptions = LibrarySidebarState.subscriptions(from: subscriptions)
    }

    func load() {
        guard let libraryRoot else {
            statusMessage = "Select your Audio2TextLibrary folder in Settings."
            episodes = []
            subscriptions = []
            groupNames = []
            lastLoadedManifestSignature = nil
            librarySyncStatus = .unavailable()
            return
        }
        do {
            let snapshot = try MobileLibraryStore.loadSnapshot(from: libraryRoot)
            episodes = snapshot.episodes.sorted { lhs, rhs in
                (lhs.localPublishedAt ?? lhs.publishedAt ?? "") > (rhs.localPublishedAt ?? rhs.publishedAt ?? "")
            }
            subscriptions = snapshot.subscriptions.sorted {
                $0.title.localizedStandardCompare($1.title) == .orderedAscending
            }
            groupNames = snapshot.groupNames
            lastLoadedManifestSignature = manifestSignature(for: libraryRoot)
            if let selectedEpisodeID, !episodes.contains(where: { $0.id == selectedEpisodeID }) {
                self.selectedEpisodeID = nil
            }
            statusMessage = episodes.isEmpty ? "No synced episodes yet in \(libraryLocationDescription)." : ""
            refreshSyncStatus()
        } catch {
            episodes = []
            subscriptions = []
            groupNames = []
            selectedEpisodeID = nil
            lastLoadedManifestSignature = nil
            statusMessage = "No synced SonaFolio library was found in \(libraryLocationDescription)."
            refreshSyncStatus()
        }
    }

    func refreshSyncStatus() {
        guard let libraryRoot else {
            syncStatusRefreshTask?.cancel()
            syncStatusRefreshTask = nil
            librarySyncStatus = .unavailable()
            return
        }
        syncStatusRefreshTask?.cancel()
        syncStatusRefreshTask = Task(priority: .utility) { [libraryRoot] in
            let status = await Task.detached(priority: .utility) {
                LibrarySyncStatusProbe.status(for: libraryRoot)
            }.value
            guard !Task.isCancelled, self.libraryRoot == libraryRoot else {
                return
            }
            self.librarySyncStatus = status
            self.syncStatusRefreshTask = nil
        }
    }

    func pollLibraryUpdates() async {
        while !Task.isCancelled {
            reloadIfLibraryChanged()
            try? await Task.sleep(nanoseconds: 5_000_000_000)
        }
    }

    func reloadIfLibraryChanged() {
        guard let libraryRoot else {
            refreshSyncStatus()
            return
        }
        let currentManifestSignature = manifestSignature(for: libraryRoot)
        if currentManifestSignature != lastLoadedManifestSignature {
            load()
        } else {
            refreshSyncStatus()
        }
    }

    func addSubscription(urlText: String) async {
        let trimmed = urlText.trimmingCharacters(in: .whitespacesAndNewlines)
        guard let url = URL(string: trimmed), let libraryRoot else {
            statusMessage = libraryRoot == nil ? "SonaFolio library folder is unavailable." : "Enter a valid subscription URL."
            return
        }
        isRefreshing = true
        defer { isRefreshing = false }
        do {
            let discovery = try await FeedDiscoveryService.discover(url: url, limit: 10)
            let result = try LibraryWriter.writeMetadataOnly(discovery: discovery, to: libraryRoot)
            load()
            statusMessage = "Subscription updated. \(metadataRefreshSummary(for: result))."
        } catch {
            statusMessage = error.localizedDescription
        }
    }

    func refreshSubscriptions() async {
        guard let libraryRoot else {
            statusMessage = "SonaFolio library folder is unavailable."
            return
        }
        isRefreshing = true
        defer { isRefreshing = false }
        load()
        guard !subscriptions.isEmpty else {
            statusMessage = "No subscriptions to refresh."
            return
        }
        var refreshSummary = LibraryRefreshSummary()
        for subscription in subscriptions {
            guard let url = subscription.refreshURL else {
                refreshSummary.recordFailure(title: subscription.title, message: "Subscription URL is unavailable.")
                continue
            }
            do {
                let discovery = try await FeedDiscoveryService.discover(url: url, limit: 10)
                let result = try LibraryWriter.writeMetadataOnly(
                    discovery: discovery,
                    to: libraryRoot,
                    groupName: subscription.groupName ?? "Default"
                )
                refreshSummary.recordSuccess(result)
            } catch {
                refreshSummary.recordFailure(title: subscription.title, message: error.localizedDescription)
            }
        }
        load()
        statusMessage = refreshSummary.refreshAllStatusText
    }

    func refreshSubscription(_ subscription: LibrarySubscription) async {
        guard let libraryRoot else {
            statusMessage = "SonaFolio library folder is unavailable."
            return
        }
        guard let url = subscription.refreshURL else {
            statusMessage = "Subscription URL is unavailable."
            return
        }
        isRefreshing = true
        defer { isRefreshing = false }
        do {
            let discovery = try await FeedDiscoveryService.discover(url: url, limit: 10)
            let result = try LibraryWriter.writeMetadataOnly(
                discovery: discovery,
                to: libraryRoot,
                groupName: subscription.groupName ?? "Default"
            )
            load()
            statusMessage = "Subscription refreshed. \(metadataRefreshSummary(for: result))."
        } catch {
            load()
            statusMessage = error.localizedDescription
        }
    }

    func fetchSubscriptionHistory(_ subscription: LibrarySubscription) async {
        guard let libraryRoot else {
            statusMessage = "SonaFolio library folder is unavailable."
            return
        }
        guard let url = subscription.refreshURL else {
            statusMessage = "Subscription URL is unavailable."
            return
        }
        isRefreshing = true
        defer { isRefreshing = false }
        do {
            let discovery = try await FeedDiscoveryService.discover(url: url, limit: nil)
            let result = try LibraryWriter.writeMetadataOnly(
                discovery: discovery,
                to: libraryRoot,
                groupName: subscription.groupName ?? "Default"
            )
            load()
            statusMessage = "Subscription history fetched. \(metadataRefreshSummary(for: result))."
        } catch {
            load()
            statusMessage = error.localizedDescription
        }
    }

    func deleteSubscription(_ subscription: LibrarySubscription) {
        guard let libraryRoot else {
            statusMessage = "SonaFolio library folder is unavailable."
            return
        }
        do {
            let result = try LibraryWriter.deleteSubscription(subscription, from: libraryRoot)
            load()
            statusMessage = "Subscription removed. Deleted \(result.removedMetadataOnlyEpisodeCount) metadata-only episode\(result.removedMetadataOnlyEpisodeCount == 1 ? "" : "s"); kept \(result.preservedAvailableEpisodeCount) processed."
        } catch {
            statusMessage = error.localizedDescription
        }
    }

    func deleteEpisode(_ episode: LibraryEpisode) {
        guard let libraryRoot else {
            statusMessage = "SonaFolio library folder is unavailable."
            return
        }
        do {
            try LibraryWriter.deleteEpisode(episode, from: libraryRoot)
            if selectedEpisodeID == episode.id {
                selectedEpisodeID = nil
            }
            load()
            statusMessage = "Episode deleted."
        } catch {
            statusMessage = error.localizedDescription
        }
    }

    func markEpisodeRead(_ episode: LibraryEpisode) {
        setEpisodeRead(!episode.isRead, for: episode)
    }

    func toggleHidingReadItems() {
        hidesReadItems.toggle()
    }

    func setEpisodeRead(_ isRead: Bool, for episode: LibraryEpisode) {
        guard let libraryRoot else {
            statusMessage = "SonaFolio library folder is unavailable."
            return
        }
        do {
            try LibraryWriter.updateRead(isRead, for: episode, in: libraryRoot)
            load()
            statusMessage = isRead ? "Marked as read." : "Marked as unread."
        } catch {
            statusMessage = error.localizedDescription
        }
    }

    func toggleEpisodeStar(_ episode: LibraryEpisode) {
        guard let libraryRoot else {
            statusMessage = "SonaFolio library folder is unavailable."
            return
        }
        do {
            let isStarred = !episode.isStarred
            try LibraryWriter.updateStar(isStarred, for: episode, in: libraryRoot)
            load()
            statusMessage = isStarred ? "Starred." : "Unstarred."
        } catch {
            statusMessage = error.localizedDescription
        }
    }

    func archiveEpisode(_ episode: LibraryEpisode) {
        setEpisodeArchived(!episode.isArchived, for: episode)
    }

    func setEpisodeArchived(_ isArchived: Bool, for episode: LibraryEpisode) {
        guard let libraryRoot else {
            statusMessage = "SonaFolio library folder is unavailable."
            return
        }
        do {
            try LibraryWriter.updateArchived(isArchived, for: episode, in: libraryRoot)
            load()
            statusMessage = isArchived ? "Episode archived." : "Episode unarchived."
        } catch {
            statusMessage = error.localizedDescription
        }
    }

    func moveEpisode(_ episode: LibraryEpisode, toGroup groupName: String) {
        guard let libraryRoot else {
            statusMessage = "SonaFolio library folder is unavailable."
            return
        }
        do {
            try LibraryWriter.updateGroup(groupName, for: episode, in: libraryRoot)
            load()
            statusMessage = "Moved to \(LibrarySidebarItem.normalizedGroupName(groupName))."
        } catch {
            statusMessage = error.localizedDescription
        }
    }

    func copyEpisodeLink(_ episode: LibraryEpisode) {
        guard let link = bestEpisodeLink(for: episode) else {
            statusMessage = "No link is available for this episode."
            return
        }
        copyText(link)
        statusMessage = "Episode link copied."
    }

    func copySubscriptionLink(_ subscription: LibrarySubscription) {
        guard let link = bestSubscriptionLink(for: subscription) else {
            statusMessage = "No link is available for this subscription."
            return
        }
        copyText(link)
        statusMessage = "Subscription link copied."
    }

    func useSelectedLibraryFolder(_ selectedRoot: URL) throws {
        selectedLibraryAccess = nil
        let access = try libraryAccessStore.saveSelectedRoot(selectedRoot)
        selectedLibraryAccess = access
        libraryRoot = access.libraryRoot
        libraryLocationDescription = "Selected Files Library"
        load()
    }

    func clearSelectedLibraryFolder() {
        selectedLibraryAccess = nil
        libraryAccessStore.clear()
        libraryRoot = nil
        libraryLocationDescription = "Audio2TextLibrary"
        lastLoadedManifestSignature = nil
        load()
    }

    private func metadataRefreshSummary(for result: LibraryWriteResult) -> String {
        metadataRefreshSummary(
            written: result.writtenEpisodeCount,
            reused: result.reusedMetadataEpisodeCount,
            keptProcessed: result.skippedAvailableEpisodeCount,
            skippedDeleted: result.tombstoneSkippedEpisodeCount
        )
    }

    private func metadataRefreshSummary(
        written: Int,
        reused: Int,
        keptProcessed: Int,
        skippedDeleted: Int
    ) -> String {
        "\(written) new, \(reused) refreshed, \(keptProcessed) processed kept, \(skippedDeleted) deleted skipped"
    }

    private func bestEpisodeLink(for episode: LibraryEpisode) -> String? {
        [episode.sourceURL, episode.canonicalURL, episode.audioURL]
            .compactMap(clean)
            .first
    }

    private func bestSubscriptionLink(for subscription: LibrarySubscription) -> String? {
        [subscription.feedURL, subscription.url]
            .compactMap(clean)
            .first
    }

    private func clean(_ value: String?) -> String? {
        let trimmed = value?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
        return trimmed.isEmpty ? nil : trimmed
    }

    private func copyText(_ text: String) {
        #if canImport(UIKit)
            UIPasteboard.general.string = text
        #endif
    }

    private func manifestSignature(for libraryRoot: URL) -> MobileLibraryManifestSignature? {
        let manifestURL = libraryRoot.appendingPathComponent("manifest.json")
        guard let values = try? manifestURL.resourceValues(forKeys: [
            .contentModificationDateKey,
            .fileSizeKey,
        ]) else {
            return nil
        }
        return MobileLibraryManifestSignature(
            modifiedAt: values.contentModificationDate,
            byteCount: values.fileSize ?? 0
        )
    }
}

private extension MobileLibraryViewModel {
    func configureInitialLibraryRoot() {
        if let access = libraryAccessStore.loadSelectedRoot() {
            selectedLibraryAccess = access
            libraryRoot = access.libraryRoot
            libraryLocationDescription = "Selected Files Library"
            return
        }
        libraryRoot = nil
        libraryLocationDescription = "No Library selected"
    }
}

private final class MobileLibraryAccess {
    let selectedRoot: URL
    let libraryRoot: URL
    private let securityScopedURL: URL?

    init(selectedRoot: URL, libraryRoot: URL, securityScopedURL: URL?) {
        self.selectedRoot = selectedRoot
        self.libraryRoot = libraryRoot
        self.securityScopedURL = securityScopedURL
    }

    deinit {
        securityScopedURL?.stopAccessingSecurityScopedResource()
    }
}

private struct MobileLibraryAccessStore {
    private static let bookmarkKey = "library.selectedRootBookmark"

    var defaults: UserDefaults = .standard

    func loadSelectedRoot() -> MobileLibraryAccess? {
        guard let data = defaults.data(forKey: Self.bookmarkKey) else {
            return nil
        }
        do {
            var isStale = false
            let selectedRoot = try URL(
                resolvingBookmarkData: data,
                options: Self.bookmarkResolutionOptions,
                relativeTo: nil,
                bookmarkDataIsStale: &isStale
            )
            guard !isStale else {
                clear()
                return nil
            }
            return openSelectedRoot(selectedRoot)
        } catch {
            clear()
            return nil
        }
    }

    func saveSelectedRoot(_ selectedRoot: URL) throws -> MobileLibraryAccess {
        let access = openSelectedRoot(selectedRoot)
        let bookmark = try selectedRoot.bookmarkData(
            options: Self.bookmarkCreationOptions,
            includingResourceValuesForKeys: nil,
            relativeTo: nil
        )
        defaults.set(bookmark, forKey: Self.bookmarkKey)
        return access
    }

    func clear() {
        defaults.removeObject(forKey: Self.bookmarkKey)
    }

    private func openSelectedRoot(_ selectedRoot: URL) -> MobileLibraryAccess {
        let started = selectedRoot.startAccessingSecurityScopedResource()
        let securityScopedURL = started ? selectedRoot : nil
        let libraryRoot = LibraryPaths.existingLibraryRoot(in: selectedRoot)
        return MobileLibraryAccess(
            selectedRoot: selectedRoot,
            libraryRoot: libraryRoot,
            securityScopedURL: securityScopedURL
        )
    }

    private static var bookmarkCreationOptions: URL.BookmarkCreationOptions {
        #if os(macOS)
            [.withSecurityScope]
        #else
            []
        #endif
    }

    private static var bookmarkResolutionOptions: URL.BookmarkResolutionOptions {
        #if os(macOS)
            [.withSecurityScope]
        #else
            []
        #endif
    }
}

private extension LibrarySubscription {
    var refreshURL: URL? {
        let text = [feedURL, url]
            .compactMap { $0?.trimmingCharacters(in: .whitespacesAndNewlines) }
            .first { !$0.isEmpty }
        guard let text else { return nil }
        return URL(string: text)
    }
}

struct MobileLibraryView: View {
    @Environment(\.scenePhase) private var scenePhase
    @ObservedObject var store: MobileLibraryViewModel
    @StateObject private var navigation = MobileNavigationState()
    @AppStorage("mobile.reader.text_size") private var readerTextSizeRaw = ReadingStyleSettings.default.textSize.rawValue
    @AppStorage("mobile.reader.line_spacing") private var readerLineSpacingRaw = ReadingStyleSettings.default.lineSpacing.rawValue
    @AppStorage("mobile.reader.content_width") private var readerContentWidthRaw = ReadingStyleSettings.default.contentWidth.rawValue
    @AppStorage("mobile.reader.font") private var readerFontRaw = ReadingStyleSettings.default.fontDesign.rawValue
    @State private var isAddingSubscription = false
    @State private var isShowingSettings = false

    var body: some View {
        MobileAdaptiveShell(
            store: store,
            navigation: navigation,
            isAddingSubscription: $isAddingSubscription,
            isShowingSettings: $isShowingSettings,
            readingStyle: readingStyleBinding
        )
        .sheet(isPresented: $isAddingSubscription) {
            AddSubscriptionView(store: store)
        }
        .sheet(isPresented: $isShowingSettings) {
            MobileSettingsView(store: store)
        }
        .task {
            await store.pollLibraryUpdates()
        }
        .onChange(of: scenePhase) { _, phase in
            if phase == .active {
                store.reloadIfLibraryChanged()
            }
        }
    }

    private var readingStyleBinding: Binding<ReadingStyleSettings> {
        Binding(
            get: {
                ReadingStyleSettings(
                    textSize: ReadingTextSize(rawValue: readerTextSizeRaw) ?? ReadingStyleSettings.default.textSize,
                    lineSpacing: ReadingLineSpacing(rawValue: readerLineSpacingRaw) ?? ReadingStyleSettings.default.lineSpacing,
                    contentWidth: ReadingContentWidth(rawValue: readerContentWidthRaw) ?? ReadingStyleSettings.default.contentWidth,
                    fontDesign: ReadingFontDesign(rawValue: readerFontRaw) ?? ReadingStyleSettings.default.fontDesign
                )
            },
            set: { style in
                readerTextSizeRaw = style.textSize.rawValue
                readerLineSpacingRaw = style.lineSpacing.rawValue
                readerContentWidthRaw = style.contentWidth.rawValue
                readerFontRaw = style.fontDesign.rawValue
            }
        )
    }
}

struct EpisodeRow: View {
    let episode: LibraryEpisode

    var body: some View {
        HStack(alignment: .top, spacing: 12) {
            Image(systemName: episode.hasSyncedDocuments ? "doc.text.fill" : "tray")
                .font(.body)
                .foregroundStyle(iconColor)
                .opacity(episode.isRead ? 0.65 : 1)
                .frame(width: 24, height: 28)

            VStack(alignment: .leading, spacing: 5) {
                Text(episode.title)
                    .font(.headline)
                    .foregroundStyle(episode.isRead ? .secondary : .primary)
                    .fontWeight(episode.isRead ? .regular : .semibold)
                    .lineLimit(2)
                HStack(spacing: 6) {
                    Text(episode.seriesName ?? episode.source ?? "Podcast")
                        .lineLimit(1)
                    Text("·")
                    Text(episode.dateLabel)
                        .lineLimit(1)
                    Text("·")
                    Text(episode.hasSyncedDocuments ? "Ready" : "Metadata")
                        .lineLimit(1)
                }
                .font(.caption)
                .foregroundStyle(.secondary)
                .opacity(episode.isRead ? 0.72 : 1)
                if let description = episode.description?.trimmingCharacters(in: .whitespacesAndNewlines),
                   !description.isEmpty
                {
                    Text(description)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .opacity(episode.isRead ? 0.64 : 0.9)
                        .lineLimit(2)
                }
            }
        }
        .padding(.vertical, 4)
    }

    private var iconColor: Color {
        if episode.isRead {
            return .secondary
        }
        return episode.hasSyncedDocuments ? .blue : .secondary
    }
}

struct AddSubscriptionView: View {
    @ObservedObject var store: MobileLibraryViewModel
    @Environment(\.dismiss) private var dismiss
    @State private var urlText = ""

    var body: some View {
        NavigationStack {
            Form {
                TextField("Podcast URL", text: $urlText)
                    .textInputAutocapitalization(.never)
                    .keyboardType(.URL)
            }
            .navigationTitle("Add Subscription")
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") {
                        dismiss()
                    }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Add") {
                        Task {
                            await store.addSubscription(urlText: urlText)
                            dismiss()
                        }
                    }
                    .disabled(urlText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || store.isRefreshing)
                }
            }
        }
    }
}

struct MobileSettingsView: View {
    @ObservedObject var store: MobileLibraryViewModel
    @Environment(\.dismiss) private var dismiss
    @State private var isChoosingLibraryFolder = false
    @State private var errorMessage: String?

    init(store: MobileLibraryViewModel) {
        self.store = store
    }

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 18) {
                    settingsPane(
                        title: "Library",
                        subtitle: "Choose the shared Audio2TextLibrary folder from Files."
                    ) {
                        VStack(alignment: .leading, spacing: 8) {
                            HStack {
                                Label("Library Folder", systemImage: "books.vertical")
                                    .fontWeight(.medium)
                                Spacer()
                                Text(store.libraryLocationDescription)
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                            }
                            if let libraryRoot = store.libraryRoot {
                                Text(libraryRoot.path)
                                    .font(.caption.monospaced())
                                    .foregroundStyle(.secondary)
                                    .lineLimit(4)
                                    .textSelection(.enabled)
                                MobileSyncStatusPill(status: store.displayedLibrarySyncStatus) {
                                    store.refreshSyncStatus()
                                }
                            } else {
                                Text("Choose iCloud Drive/Audio2Text or Audio2TextLibrary to enable reading and subscription updates.")
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                            }
                            HStack(spacing: 10) {
                                Button {
                                    isChoosingLibraryFolder = true
                                } label: {
                                    Label("Choose Folder", systemImage: "folder")
                                }
                                .buttonStyle(.bordered)

                                Button(role: .destructive) {
                                    store.clearSelectedLibraryFolder()
                                } label: {
                                    Label("Forget", systemImage: "xmark.circle")
                                }
                                .buttonStyle(.bordered)
                                .disabled(store.libraryRoot == nil)
                            }
                            .padding(.top, 4)
                        }
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding(.vertical, 6)
                    }

                    if let errorMessage {
                        Text(errorMessage)
                            .font(.footnote)
                            .foregroundStyle(.red)
                    }
                }
                .padding(18)
            }
            .navigationTitle("Settings")
            .fileImporter(
                isPresented: $isChoosingLibraryFolder,
                allowedContentTypes: [.folder],
                allowsMultipleSelection: false,
                onCompletion: handleLibraryFolderSelection
            )
            .toolbar {
                ToolbarItem(placement: .confirmationAction) {
                    Button("Done") {
                        dismiss()
                    }
                    .fontWeight(.semibold)
                }
            }
        }
    }

    private func settingsPane<Content: View>(
        title: String,
        subtitle: String,
        @ViewBuilder content: () -> Content
    ) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            VStack(alignment: .leading, spacing: 4) {
                Text(title)
                    .font(.title3)
                    .fontWeight(.semibold)
                Text(subtitle)
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            VStack(alignment: .leading, spacing: 0) {
                content()
            }
            .padding(.horizontal, 14)
            .padding(.vertical, 6)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(Color.secondary.opacity(0.12))
            .clipShape(RoundedRectangle(cornerRadius: 8))
        }
    }

    private func handleLibraryFolderSelection(_ result: Result<[URL], Error>) {
        do {
            guard let selectedRoot = try result.get().first else {
                return
            }
            try store.useSelectedLibraryFolder(selectedRoot)
            errorMessage = nil
        } catch {
            errorMessage = error.localizedDescription
        }
    }
}

private extension String {
    var nilIfEmpty: String? {
        isEmpty ? nil : self
    }
}

private extension LibraryEpisode {
    var dateLabel: String {
        let text = localPublishedAt ?? publishedAt ?? ""
        return text.trimmingCharacters(in: .whitespacesAndNewlines).nilIfEmpty ?? "No date"
    }
}
