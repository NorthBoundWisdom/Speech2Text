import AppKit
import Darwin
import SwiftUI

final class AppDelegate: NSObject, NSApplicationDelegate {
    private var instanceLock: ApplicationInstanceLock?

    func applicationWillFinishLaunching(_: Notification) {
        if CommandLine.arguments.contains("--startup-smoke") { return }
        do {
            if let lock = try ApplicationInstanceLock.acquire() {
                instanceLock = lock
                return
            }
            activateExistingApplication()
            NSApp.terminate(nil)
        } catch {
            AppLogger.shared.log(.error, category: "app", event: "instance_lock_failed", message: error.localizedDescription)
        }
    }

    func applicationDidFinishLaunching(_: Notification) {
        NSApp.setActivationPolicy(.regular)
        NSApp.applicationIconImage = AppIconFactory.image()
        NSApp.activate(ignoringOtherApps: true)
        if CommandLine.arguments.contains("--startup-smoke") {
            let deadline = Date().addingTimeInterval(25)
            Timer.scheduledTimer(withTimeInterval: 0.1, repeats: true) { timer in
                if let window = NSApp.windows.first(where: { $0.isVisible && $0.contentView != nil }),
                   let view = window.contentView, view.bounds.width > 0, view.bounds.height > 0 {
                    view.displayIfNeeded()
                    let marker = "{\"type\":\"sonafolio.native_startup\",\"version\":1,\"client\":\"swift\",\"first_frame\":true}\n"
                    FileHandle.standardError.write(Data(marker.utf8))
                    timer.invalidate()
                    Darwin.exit(0)
                } else if Date() > deadline {
                    FileHandle.standardError.write(Data("Native startup smoke timed out before displaying a window.\n".utf8))
                    Darwin.exit(2)
                }
            }
        }
    }

    func applicationWillTerminate(_: Notification) {
        AppLogger.shared.log(.info, category: "app", event: "app_exit", message: "SonaFolio app is terminating")
    }

    private func activateExistingApplication() {
        guard let bundleIdentifier = Bundle.main.bundleIdentifier else {
            return
        }
        let currentProcessIdentifier = ProcessInfo.processInfo.processIdentifier
        let existingApplication = NSRunningApplication
            .runningApplications(withBundleIdentifier: bundleIdentifier)
            .first { $0.processIdentifier != currentProcessIdentifier }
        existingApplication?.activate(options: [.activateAllWindows])
    }
}

@main
struct Audio2TextApp: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) private var appDelegate
    @StateObject private var store = AppStore.makeLive(
        runsStartupCloudPreflight: !CommandLine.arguments.contains("--startup-smoke")
    )

    init() {
        if let exitCode = Audio2TextCliLauncher.runIfRequested() {
            Darwin.exit(exitCode)
        }
    }

    var body: some Scene {
        WindowGroup("SonaFolio") {
            ContentView(store: store)
                .frame(minWidth: 980, minHeight: 680)
                .onAppear {
                    NSApp.setActivationPolicy(.regular)
                    NSApp.activate(ignoringOtherApps: true)
                }
        }
        .windowStyle(.titleBar)
        .windowToolbarStyle(.unifiedCompact)
        .commands {
            Audio2TextCommands(store: store)
        }
    }
}

struct Audio2TextCommands: Commands {
    @ObservedObject var store: AppStore

    @AppStorage(LibrarySplitViewController.sourceCollapsedKey) private var sourceCollapsed = false
    @AppStorage(LibrarySplitViewController.listCollapsedKey) private var listCollapsed = false

    var body: some Commands {
        CommandGroup(after: .sidebar) {
            Button(sourceCollapsed ? "Show Sources" : "Hide Sources") { sourceCollapsed.toggle() }
                .keyboardShortcut("s", modifiers: [.control, .command])
            Button(listCollapsed ? "Show Episode List" : "Hide Episode List") { listCollapsed.toggle() }
                .keyboardShortcut("l", modifiers: [.control, .command])
            Button("Show All Columns") {
                sourceCollapsed = false
                listCollapsed = false
            }
        }
        CommandGroup(replacing: .appSettings) {
            Button("Settings...") {
                store.showSettings()
            }
            .keyboardShortcut(",", modifiers: .command)
        }

        CommandGroup(replacing: .newItem) {
            Button("New Item") {
                store.showImportPanel()
            }
            .keyboardShortcut("n", modifiers: .command)

            Button("New Group") {
                store.isNewGroupPanelPresented = true
            }
            .keyboardShortcut("n", modifiers: [.command, .shift])

            Button("Generate SRT...") {
                store.showSRTExportPanel()
            }
            .keyboardShortcut("s", modifiers: [.command, .shift])
        }

        CommandMenu("Process") {
            Button("Refresh") {
                store.job.refresh()
            }
            .keyboardShortcut("r", modifiers: .command)

            Button("Refresh Library") {
                store.job.refreshLibraryNow()
            }
            .keyboardShortcut("i", modifiers: [.command, .shift])

            Divider()

            Button(ProcessingWorkflow.transcribeAndSummarize.actionTitle(isCloudConfigured: store.job.isCloudSummaryConfigured)) {
                if let item = store.selectedLibraryItem {
                    store.job.processLibraryItem(item, workflow: .transcribeAndSummarize)
                }
            }
            .disabled(!store.job.canProcessLibraryItem(store.selectedLibraryItem, workflow: .transcribeAndSummarize))

            Button(ProcessingWorkflow.localOnly.actionTitle()) {
                if let item = store.selectedLibraryItem {
                    store.job.processLibraryItem(item, workflow: .localOnly)
                }
            }
            .keyboardShortcut(.return, modifiers: .command)
            .disabled(!store.job.canProcessLibraryItem(store.selectedLibraryItem, workflow: .localOnly))

            Button(ProcessingWorkflow.transcribeAndSummarize.actionTitle(reprocess: true, isCloudConfigured: store.job.isCloudSummaryConfigured)) {
                if let item = store.selectedLibraryItem {
                    store.job.processLibraryItem(item, reprocess: true, workflow: .transcribeAndSummarize)
                }
            }
            .disabled(!store.job.canProcessLibraryItem(store.selectedLibraryItem, reprocess: true, workflow: .transcribeAndSummarize))

            Button(ProcessingWorkflow.localOnly.actionTitle(reprocess: true)) {
                if let item = store.selectedLibraryItem {
                    store.job.processLibraryItem(item, reprocess: true, workflow: .localOnly)
                }
            }
            .keyboardShortcut(.return, modifiers: [.command, .shift])
            .disabled(!store.job.canProcessLibraryItem(store.selectedLibraryItem, reprocess: true, workflow: .localOnly))

            Button("Copy Codex summary write-back instructions") {
                if let item = store.selectedLibraryItem {
                    let prompt = """
                    Use the connected SonaFolio MCP server to summarize episode_id="\(item.id)" and publish the result.
                    Get the episode's current hashes and QA through get_episode, then page through the complete transcript with read_document.
                    Use your current model to write a Markdown summary in the output_language returned by get_episode (current setting: \(store.settings.summaryLanguage)) and retain useful timestamps; do not call the SonaFolio cloud API.
                    Pass transcript_sha256 and summary_sha256 to write_summary and set generator to Codex.
                    Replace a nonempty summary only after an explicit regeneration request; do not enable overwrite on your own.
                    """
                    NSPasteboard.general.clearContents()
                    NSPasteboard.general.setString(prompt, forType: .string)
                }
            }
            .disabled(store.selectedLibraryItem?.documentsURL == nil || !store.job.canGenerateSummary(for: store.selectedLibraryItem))

            Button("Regenerate summary with cloud API") {
                if let item = store.selectedLibraryItem {
                    store.job.generateSummary(for: item)
                }
            }
            .keyboardShortcut("s", modifiers: [.command, .option])
            .disabled(!store.job.isCloudSummaryConfigured || !store.job.canGenerateSummary(for: store.selectedLibraryItem))

            Button("Restore Missing Audio") {
                if let item = store.selectedLibraryItem {
                    store.job.restoreAudio(for: item)
                }
            }
            .keyboardShortcut("d", modifiers: [.command, .option])
            .disabled(store.job.stage.isRunning || !(store.selectedLibraryItem?.canRestoreAudio ?? false))

            Divider()

            Button("Mark Queue: unread") {
                if let item = store.selectedLibraryItem {
                    store.job.markQueueStatus(.unread, for: item)
                }
            }
            .keyboardShortcut("u", modifiers: [])
            .disabled(store.selectedLibraryItem?.isProcessed ?? true)

            Button("Mark Queue: to process") {
                if let item = store.selectedLibraryItem {
                    store.job.markQueueStatus(.toProcess, for: item)
                }
            }
            .keyboardShortcut("p", modifiers: [])
            .disabled(store.selectedLibraryItem?.isProcessed ?? true)

            Button("Mark Queue: process later") {
                if let item = store.selectedLibraryItem {
                    store.job.markQueueStatus(.processLater, for: item)
                }
            }
            .keyboardShortcut("l", modifiers: [])
            .disabled(store.selectedLibraryItem?.isProcessed ?? true)

            Button("Mark Queue: delete") {
                if let item = store.selectedLibraryItem {
                    store.job.markQueueStatus(.delete, for: item)
                }
            }
            .keyboardShortcut("x", modifiers: [])
            .disabled(store.selectedLibraryItem?.isProcessed ?? true)

            Divider()

            Button(store.selectedLibraryItem.map { $0.isRead ? "Mark Selected as Unread" : "Mark Selected as Read" } ?? "Mark Selected as Read") {
                if let item = store.selectedLibraryItem {
                    withAnimation(ProcessSidebarView.libraryListAnimation) {
                        store.job.markRead(!item.isRead, for: item)
                    }
                }
            }
            .disabled(store.selectedLibraryItem == nil)

            Button(store.selectedLibraryItem.map { store.job.isStarred($0) ? "Unstar Selected" : "Star Selected" } ?? "Star Selected") {
                if let item = store.selectedLibraryItem {
                    store.job.toggleStar(for: item)
                }
            }
            .keyboardShortcut("l", modifiers: [.command, .shift])
            .disabled(store.selectedLibraryItem == nil)

            Menu("Move Selected to Group") {
                ForEach(store.job.availableGroupNames, id: \.self) { groupName in
                    Button(groupName) {
                        if let item = store.selectedLibraryItem {
                            store.job.moveLibraryItem(item, toGroup: groupName)
                        }
                    }
                    .disabled(store.job.stage.isRunning || store.selectedLibraryItem?.groupName == groupName)
                }
            }
            .disabled(store.selectedLibraryItem == nil)
        }

        CommandGroup(after: .help) {
            Button("Reveal Logs") {
                store.revealLogs()
            }
        }
    }
}
